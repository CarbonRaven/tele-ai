"""Speech-to-Text service with Hailo NPU acceleration.

Supports two backends:
1. Hailo-accelerated Whisper via Wyoming protocol (recommended for Pi #1 with AI HAT+ 2)
2. faster-whisper for CPU-only fallback or development

The Hailo backend offloads Whisper inference to the Hailo-10H NPU, freeing
the CPU for other tasks like TTS and audio processing.
"""

import asyncio
import logging
import socket
import struct
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import AsyncIterator, Literal

import numpy as np
from numpy.typing import NDArray

from config.settings import STTSettings

logger = logging.getLogger(__name__)


class STTBackend(str, Enum):
    """Available STT backends."""

    HAILO_WYOMING = "hailo_wyoming"  # Hailo-accelerated via Wyoming protocol
    FASTER_WHISPER = "faster_whisper"  # CPU-based faster-whisper


@dataclass
class TranscriptionResult:
    """Result from speech transcription."""

    text: str
    language: str
    confidence: float
    duration_seconds: float

    @property
    def is_empty(self) -> bool:
        """Check if transcription is empty or just whitespace."""
        return not self.text or not self.text.strip()


class WyomingSTTClient:
    """Wyoming protocol client for Hailo-accelerated Whisper.

    Connects to a Wyoming Whisper server (e.g., wyoming-hailo-whisper)
    running on port 10300.

    Uses proper Wyoming binary protocol for audio data to avoid base64 overhead.
    """

    def __init__(self, host: str = "localhost", port: int = 10300):
        self.host = host
        self.port = port
        self._reader = None
        self._writer = None
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        self._base_reconnect_delay = 0.5  # seconds

    async def connect(self) -> None:
        """Connect to Wyoming server with exponential backoff."""
        while self._reconnect_attempts < self._max_reconnect_attempts:
            try:
                self._reader, self._writer = await asyncio.open_connection(
                    self.host, self.port
                )
                self._reconnect_attempts = 0  # Reset on successful connection
                logger.info(f"Connected to Wyoming Whisper at {self.host}:{self.port}")
                return
            except (ConnectionRefusedError, OSError) as e:
                self._reconnect_attempts += 1
                if self._reconnect_attempts >= self._max_reconnect_attempts:
                    raise RuntimeError(
                        f"Cannot connect to Wyoming Whisper at {self.host}:{self.port} "
                        f"after {self._max_reconnect_attempts} attempts. "
                        "Ensure wyoming-hailo-whisper is running."
                    )
                # Exponential backoff: 0.5s, 1s, 2s, 4s...
                delay = self._base_reconnect_delay * (2 ** (self._reconnect_attempts - 1))
                logger.warning(
                    f"Wyoming connection failed ({e}), retrying in {delay:.1f}s "
                    f"(attempt {self._reconnect_attempts}/{self._max_reconnect_attempts})"
                )
                await asyncio.sleep(delay)

    async def disconnect(self) -> None:
        """Disconnect from Wyoming server."""
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
        self._reader = None
        self._writer = None

    async def transcribe(
        self,
        audio: NDArray[np.float32],
        sample_rate: int = 16000,
        language: str = "en",
    ) -> TranscriptionResult:
        """Transcribe audio via Wyoming protocol.

        Args:
            audio: Audio samples as float32 array in range [-1.0, 1.0].
            sample_rate: Sample rate (must be 16kHz).
            language: Language code.

        Returns:
            TranscriptionResult with text and metadata.
        """
        if self._writer is None:
            await self.connect()

        duration = len(audio) / sample_rate

        # Convert to 16-bit PCM bytes for Wyoming
        pcm_data = (audio * 32767).astype(np.int16).tobytes()

        # Wyoming protocol: send audio-start, audio chunks, audio-stop
        # then receive transcript
        try:
            # Send audio-start event
            await self._send_event(
                "audio-start",
                {
                    "rate": sample_rate,
                    "width": 2,
                    "channels": 1,
                },
            )

            # Send audio chunks (Wyoming expects chunks)
            chunk_size = 4096  # bytes
            for i in range(0, len(pcm_data), chunk_size):
                chunk = pcm_data[i : i + chunk_size]
                await self._send_event("audio-chunk", {"audio": chunk})

            # Send audio-stop
            await self._send_event("audio-stop", {})

            # Receive transcript
            event = await self._receive_event()

            if event and event.get("type") == "transcript":
                text = event.get("data", {}).get("text", "")
                return TranscriptionResult(
                    text=text.strip(),
                    language=language,
                    confidence=0.9,  # Wyoming doesn't provide confidence
                    duration_seconds=duration,
                )

            return TranscriptionResult(
                text="",
                language=language,
                confidence=0.0,
                duration_seconds=duration,
            )

        except Exception as e:
            logger.error(f"Wyoming transcription error: {e}")
            # Disconnect and allow reconnect with backoff on next call
            await self.disconnect()
            raise

    def reset_reconnect_attempts(self) -> None:
        """Reset reconnection attempt counter (call after successful operations)."""
        self._reconnect_attempts = 0

    async def _send_event(self, event_type: str, data: dict) -> None:
        """Send a Wyoming protocol event.

        Uses binary framing for audio data to avoid base64 overhead (33% savings).
        Protocol: 4-byte length prefix (big-endian) + JSON header + binary payload
        """
        import json

        # Separate binary audio from JSON data
        audio_data = data.pop("audio", None)

        # Wyoming uses JSON lines protocol for events
        event = {"type": event_type, "data": data}

        if audio_data is not None:
            # Binary protocol: length-prefixed frame
            # Format: [4 bytes: total length][JSON header][binary audio]
            header = json.dumps(event).encode("utf-8")
            total_length = len(header) + len(audio_data)

            # Write length prefix + header + binary audio
            self._writer.write(struct.pack(">I", total_length))
            self._writer.write(header)
            self._writer.write(audio_data)
        else:
            # Standard JSON lines for non-audio events
            message = json.dumps(event) + "\n"
            self._writer.write(message.encode("utf-8"))

        await self._writer.drain()

    async def _receive_event(self, timeout: float = 30.0) -> dict | None:
        """Receive a Wyoming protocol event."""
        import json

        try:
            line = await asyncio.wait_for(
                self._reader.readline(),
                timeout=timeout,
            )
            if line:
                return json.loads(line.decode("utf-8"))
        except asyncio.TimeoutError:
            logger.warning("Wyoming response timeout")
        except json.JSONDecodeError as e:
            logger.error(f"Wyoming JSON decode error: {e}")

        return None


class WhisperSTT:
    """Speech-to-Text service with pluggable backends.

    Recommended: Use Hailo-accelerated Whisper via Wyoming protocol on Pi #1
    with AI HAT+ 2 for best performance and CPU efficiency.

    Fallback: faster-whisper for development or systems without AI HAT+ 2.
    """

    def __init__(self, settings: STTSettings | None = None):
        if settings is None:
            settings = STTSettings()
        self.settings = settings

        self._backend: STTBackend | None = None
        self._model = None  # For faster-whisper
        self._wyoming_client: WyomingSTTClient | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the STT service.

        Attempts to connect to Hailo Wyoming server first.
        Falls back to faster-whisper if unavailable.
        """
        if self._initialized:
            return

        # Try Hailo Wyoming first (recommended for Pi #1 with AI HAT+ 2)
        if self.settings.device == "hailo" or await self._check_wyoming_available():
            try:
                self._wyoming_client = WyomingSTTClient(
                    host=self.settings.wyoming_host,
                    port=self.settings.wyoming_port,
                )
                await self._wyoming_client.connect()
                self._backend = STTBackend.HAILO_WYOMING
                logger.info(
                    f"Using Hailo-accelerated Whisper via Wyoming at "
                    f"{self.settings.wyoming_host}:{self.settings.wyoming_port}"
                )
                self._initialized = True
                return
            except Exception as e:
                logger.warning(f"Hailo Wyoming unavailable: {e}")
                self._wyoming_client = None

        # Fallback to faster-whisper
        logger.info(f"Loading faster-whisper model: {self.settings.model_name}")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load_faster_whisper)
        self._backend = STTBackend.FASTER_WHISPER
        self._initialized = True
        logger.info("Using faster-whisper (CPU) for STT")

    async def _check_wyoming_available(self) -> bool:
        """Check if Wyoming Whisper server is reachable."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(
                    self.settings.wyoming_host,
                    self.settings.wyoming_port,
                ),
                timeout=2.0,
            )
            writer.close()
            await writer.wait_closed()
            return True
        except (ConnectionRefusedError, asyncio.TimeoutError, OSError):
            return False

    def _load_faster_whisper(self) -> None:
        """Load the faster-whisper model (blocking)."""
        from faster_whisper import WhisperModel

        device = self.settings.device
        if device == "auto" or device == "hailo":
            try:
                import torch

                device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                device = "cpu"

        compute_type = self.settings.compute_type
        if compute_type == "auto":
            compute_type = "int8" if device == "cpu" else "float16"

        logger.info(f"faster-whisper using device: {device}, compute_type: {compute_type}")

        self._model = WhisperModel(
            self.settings.model_name,
            device=device,
            compute_type=compute_type,
        )

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self._wyoming_client:
            await self._wyoming_client.disconnect()
            self._wyoming_client = None
        self._model = None
        self._initialized = False
        self._backend = None

    @property
    def backend(self) -> STTBackend | None:
        """Return the active backend type."""
        return self._backend

    @property
    def is_hailo_accelerated(self) -> bool:
        """Return True if using Hailo NPU acceleration."""
        return self._backend == STTBackend.HAILO_WYOMING

    async def transcribe(
        self,
        audio: NDArray[np.float32],
        sample_rate: int = 16000,
    ) -> TranscriptionResult:
        """Transcribe audio to text.

        Args:
            audio: Audio samples as float32 array in range [-1.0, 1.0].
            sample_rate: Sample rate of audio (must be 16kHz for Whisper).

        Returns:
            TranscriptionResult with text and metadata.
        """
        if not self._initialized:
            raise RuntimeError("STT not initialized. Call initialize() first.")

        if sample_rate != 16000:
            raise ValueError(f"Whisper requires 16kHz audio, got {sample_rate}Hz")

        if len(audio) == 0:
            return TranscriptionResult(
                text="",
                language=self.settings.language,
                confidence=0.0,
                duration_seconds=0.0,
            )

        # Route to appropriate backend
        if self._backend == STTBackend.HAILO_WYOMING:
            return await self._wyoming_client.transcribe(
                audio, sample_rate, self.settings.language
            )
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                self._transcribe_faster_whisper,
                audio,
            )

    def _transcribe_faster_whisper(
        self, audio: NDArray[np.float32]
    ) -> TranscriptionResult:
        """Synchronous transcription via faster-whisper (blocking)."""
        duration = len(audio) / 16000

        segments, info = self._model.transcribe(
            audio,
            language=self.settings.language,
            beam_size=self.settings.beam_size,
            vad_filter=self.settings.vad_filter,
            initial_prompt=self.settings.initial_prompt,
        )

        text_parts = []
        total_confidence = 0.0
        segment_count = 0

        for segment in segments:
            text_parts.append(segment.text)
            if segment.avg_logprob:
                total_confidence += np.exp(segment.avg_logprob)
                segment_count += 1

        text = " ".join(text_parts).strip()
        avg_confidence = total_confidence / segment_count if segment_count > 0 else 0.0

        return TranscriptionResult(
            text=text,
            language=info.language if info else self.settings.language,
            confidence=avg_confidence,
            duration_seconds=duration,
        )

    async def transcribe_streaming(
        self,
        audio_stream: AsyncIterator[NDArray[np.float32]],
        sample_rate: int = 16000,
    ) -> AsyncIterator[str]:
        """Transcribe audio stream with partial results.

        Note: Whisper is not a true streaming model, so this collects
        audio in chunks and transcribes periodically.

        Args:
            audio_stream: Async iterator of audio chunks.
            sample_rate: Sample rate of audio (must be 16kHz).

        Yields:
            Partial transcription strings.
        """
        if not self._initialized:
            raise RuntimeError("STT not initialized. Call initialize() first.")

        audio_buffer = []
        last_transcription = ""

        chunk_duration = 2.0  # seconds
        samples_per_chunk = int(chunk_duration * sample_rate)

        async for chunk in audio_stream:
            audio_buffer.append(chunk)
            total_samples = sum(len(c) for c in audio_buffer)

            if total_samples >= samples_per_chunk:
                full_audio = np.concatenate(audio_buffer)
                result = await self.transcribe(full_audio, sample_rate)

                if result.text and result.text != last_transcription:
                    new_text = result.text
                    if last_transcription and new_text.startswith(last_transcription):
                        yield new_text[len(last_transcription) :].strip()
                    else:
                        yield new_text
                    last_transcription = result.text

        if audio_buffer:
            full_audio = np.concatenate(audio_buffer)
            result = await self.transcribe(full_audio, sample_rate)
            if result.text and result.text != last_transcription:
                yield result.text

    async def transcribe_from_bytes(
        self,
        audio_bytes: bytes,
        sample_rate: int = 16000,
    ) -> TranscriptionResult:
        """Transcribe from raw audio bytes.

        Args:
            audio_bytes: Raw audio bytes (signed 16-bit PCM).
            sample_rate: Sample rate of audio.

        Returns:
            TranscriptionResult with text and metadata.
        """
        samples = np.frombuffer(audio_bytes, dtype=np.int16)
        audio = samples.astype(np.float32) / 32768.0

        if sample_rate != 16000:
            from math import gcd

            from scipy.signal import resample_poly

            g = gcd(sample_rate, 16000)
            up = 16000 // g
            down = sample_rate // g
            audio = resample_poly(audio, up, down).astype(np.float32)

        return await self.transcribe(audio, 16000)

    async def transcribe_from_file(self, file_path: str | Path) -> TranscriptionResult:
        """Transcribe from an audio file.

        Args:
            file_path: Path to audio file (WAV format).

        Returns:
            TranscriptionResult with text and metadata.
        """
        if not self._initialized:
            raise RuntimeError("STT not initialized. Call initialize() first.")

        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        loop = asyncio.get_event_loop()
        audio, sample_rate = await loop.run_in_executor(
            None,
            self._read_audio_file,
            file_path,
        )

        if sample_rate != 16000:
            from math import gcd

            from scipy.signal import resample_poly

            g = gcd(sample_rate, 16000)
            up = 16000 // g
            down = sample_rate // g
            audio = resample_poly(audio, up, down).astype(np.float32)

        return await self.transcribe(audio, 16000)

    def _read_audio_file(self, file_path: Path) -> tuple[NDArray[np.float32], int]:
        """Read audio file and return samples with sample rate."""
        import soundfile as sf

        audio, sample_rate = sf.read(str(file_path), dtype="float32")

        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)

        return audio, sample_rate
