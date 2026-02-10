"""Speech-to-Text service with multiple backend support.

Supports three backends:
1. Moonshine - 5x faster than Whisper tiny, optimized for edge devices (recommended)
2. Hailo-accelerated Whisper via Wyoming protocol (for Pi #1 with AI HAT+ 2)
3. faster-whisper for CPU-only fallback or development

Moonshine (UsefulSensors) uses an encoder-decoder transformer with RoPE
instead of absolute position embeddings, trained without zero-padding
for greater encoder efficiency.
"""

__all__ = [
    "STTBackend",
    "TranscriptionResult",
    "WyomingSTTClient",
    "WhisperSTT",
    "STTService",
]

import asyncio
import json
import logging
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

    MOONSHINE = "moonshine"  # Moonshine (5x faster than Whisper tiny)
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

            # Batch audio chunks without draining after each one
            # This reduces syscalls from O(n) to O(1) for the audio send phase
            chunk_size = 4096  # bytes
            for i in range(0, len(pcm_data), chunk_size):
                chunk = pcm_data[i : i + chunk_size]
                self._write_event_no_drain("audio-chunk", {"audio": chunk})

            # Single drain after all chunks are written
            await self._writer.drain()

            # Send audio-stop
            await self._send_event("audio-stop", {})

            # Receive transcript
            event = await self._receive_event()

            # Validate response structure
            if not event:
                logger.warning("Wyoming returned empty response")
                return TranscriptionResult(
                    text="",
                    language=language,
                    confidence=0.0,
                    duration_seconds=duration,
                )

            if not isinstance(event, dict):
                logger.warning(f"Wyoming returned non-dict response: {type(event)}")
                return TranscriptionResult(
                    text="",
                    language=language,
                    confidence=0.0,
                    duration_seconds=duration,
                )

            event_type = event.get("type")
            if event_type == "transcript":
                data = event.get("data", {})
                if not isinstance(data, dict):
                    logger.warning(f"Wyoming transcript data is not dict: {type(data)}")
                    text = ""
                else:
                    text = data.get("text", "")
                    if not isinstance(text, str):
                        logger.warning(f"Wyoming text is not string: {type(text)}")
                        text = str(text) if text else ""

                return TranscriptionResult(
                    text=text.strip(),
                    language=language,
                    confidence=0.9,  # Wyoming doesn't provide confidence
                    duration_seconds=duration,
                )

            elif event_type == "error":
                error_msg = event.get("data", {}).get("message", "Unknown error")
                logger.error(f"Wyoming returned error: {error_msg}")

            return TranscriptionResult(
                text="",
                language=language,
                confidence=0.0,
                duration_seconds=duration,
            )

        except asyncio.CancelledError:
            raise  # Don't catch cancellation

        except ConnectionError as e:
            logger.error(f"Wyoming connection error: {e}")
            await self.disconnect()
            raise

        except Exception as e:
            logger.exception(f"Wyoming transcription error: {e}")
            # Disconnect and allow reconnect with backoff on next call
            await self.disconnect()
            raise

    def reset_reconnect_attempts(self) -> None:
        """Reset reconnection attempt counter (call after successful operations)."""
        self._reconnect_attempts = 0

    def _write_event_no_drain(self, event_type: str, data: dict) -> None:
        """Write a Wyoming protocol event without draining.

        Use this for batching multiple writes, then call drain() once at the end.
        """
        # Separate binary audio from JSON data without mutating caller's dict
        audio_data = data.get("audio")
        event_data = {k: v for k, v in data.items() if k != "audio"} if audio_data is not None else data

        if audio_data is not None:
            # Wyoming audio-chunk format:
            # 1. Send JSON line with payload_length in data dict
            # 2. Send raw audio bytes
            payload_length = len(audio_data)
            event_data["payload_length"] = payload_length
            event = {"type": event_type, "data": event_data}
            message = json.dumps(event) + "\n"
            self._writer.write(message.encode("utf-8"))
            self._writer.write(audio_data)
        else:
            # Standard JSON lines for non-audio events
            event = {"type": event_type, "data": event_data}
            message = json.dumps(event) + "\n"
            self._writer.write(message.encode("utf-8"))

    async def _send_event(self, event_type: str, data: dict) -> None:
        """Send a Wyoming protocol event.

        Wyoming protocol uses JSON-lines format where each message is a JSON object
        followed by a newline. Audio data uses a special format:
        - For audio-chunk: JSON line (with payload_length in data), then raw audio bytes

        Reference: https://github.com/rhasspy/wyoming
        """
        self._write_event_no_drain(event_type, data)
        await self._writer.drain()

    async def _receive_event(self, timeout: float = 30.0) -> dict | None:
        """Receive a Wyoming protocol event.

        Wyoming events are JSON-lines, optionally followed by binary payloads
        if the JSON includes a "payload_length" field.
        """
        try:
            line = await asyncio.wait_for(
                self._reader.readline(),
                timeout=timeout,
            )
            if not line:
                return None

            event = json.loads(line.decode("utf-8"))

            # Check if there's a binary payload to read
            payload_length = event.get("data", {}).get("payload_length", 0)
            if payload_length > 0:
                payload = await asyncio.wait_for(
                    self._reader.readexactly(payload_length),
                    timeout=timeout,
                )
                event["payload"] = payload

            return event

        except asyncio.TimeoutError:
            logger.warning("Wyoming response timeout")
        except asyncio.IncompleteReadError as e:
            logger.error(f"Wyoming incomplete read: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Wyoming JSON decode error: {e}")

        return None


class WhisperSTT:
    """Speech-to-Text service with pluggable backends.

    Backend priority (when backend="auto"):
    1. Moonshine - 5x faster than Whisper tiny, recommended for edge
    2. Wyoming/Hailo - NPU accelerated Whisper on AI HAT+ 2
    3. faster-whisper - CPU-based fallback

    Moonshine uses encoder-decoder transformer with RoPE and no zero-padding,
    achieving 5x speedup over Whisper tiny with equivalent accuracy.
    """

    def __init__(self, settings: STTSettings | None = None):
        if settings is None:
            settings = STTSettings()
        self.settings = settings

        self._backend: STTBackend | None = None
        self._model = None  # For faster-whisper or Moonshine
        self._processor = None  # For Moonshine
        self._wyoming_client: WyomingSTTClient | None = None
        self._initialized = False
        self._device: str = "cpu"

    async def initialize(self) -> None:
        """Initialize the STT service.

        Backend selection order (for backend="auto"):
        1. Moonshine (if transformers available) - fastest
        2. Wyoming/Hailo (if server reachable) - NPU accelerated
        3. faster-whisper (always available) - CPU fallback
        """
        if self._initialized:
            return

        backend = self.settings.backend

        # Determine device
        self._device = self.settings.device
        if self._device == "auto":
            try:
                import torch
                self._device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                self._device = "cpu"

        # Try Moonshine first (fastest option)
        if backend in ("moonshine", "auto"):
            if await self._try_moonshine():
                return

        # Try Hailo Wyoming (NPU accelerated)
        if backend in ("hailo", "auto"):
            if await self._try_wyoming():
                return

        # Fallback to faster-whisper
        if backend in ("whisper", "auto"):
            await self._load_faster_whisper()
            return

        raise RuntimeError(f"No STT backend available for backend={backend}")

    async def _try_moonshine(self) -> bool:
        """Try to initialize Moonshine backend."""
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._load_moonshine)
            self._backend = STTBackend.MOONSHINE
            self._initialized = True
            logger.info(
                f"Using Moonshine STT ({self.settings.moonshine_model}) "
                f"on {self._device} - 5x faster than Whisper tiny"
            )
            return True
        except ImportError as e:
            logger.warning(f"Moonshine unavailable (install transformers>=4.48): {e}")
            return False
        except Exception as e:
            logger.warning(f"Moonshine initialization failed: {e}")
            return False

    async def _try_wyoming(self) -> bool:
        """Try to initialize Wyoming/Hailo backend."""
        if not await self._check_wyoming_available():
            return False

        try:
            self._wyoming_client = WyomingSTTClient(
                host=self.settings.wyoming_host,
                port=self.settings.wyoming_port,
            )
            await self._wyoming_client.connect()
            self._backend = STTBackend.HAILO_WYOMING
            self._initialized = True
            logger.info(
                f"Using Hailo-accelerated Whisper via Wyoming at "
                f"{self.settings.wyoming_host}:{self.settings.wyoming_port}"
            )
            return True
        except Exception as e:
            logger.warning(f"Hailo Wyoming unavailable: {e}")
            self._wyoming_client = None
            return False

    async def _load_faster_whisper(self) -> None:
        """Load faster-whisper as fallback."""
        logger.info(f"Loading faster-whisper model: {self.settings.whisper_model}")
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._load_faster_whisper_sync)
        self._backend = STTBackend.FASTER_WHISPER
        self._initialized = True
        logger.info(f"Using faster-whisper ({self.settings.whisper_model}) on {self._device}")

    def _load_moonshine(self) -> None:
        """Load the Moonshine model (blocking)."""
        from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
        import torch

        model_id = self.settings.moonshine_model
        torch_dtype = torch.float16 if self._device == "cuda" else torch.float32

        logger.info(f"Loading Moonshine model: {model_id}")

        self._processor = AutoProcessor.from_pretrained(model_id)
        self._model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_id,
            torch_dtype=torch_dtype,
            low_cpu_mem_usage=True,
        )
        self._model.to(self._device)

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

    def _load_faster_whisper_sync(self) -> None:
        """Load the faster-whisper model (blocking)."""
        from faster_whisper import WhisperModel

        compute_type = self.settings.compute_type
        if compute_type == "auto":
            compute_type = "int8" if self._device == "cpu" else "float16"

        logger.info(f"faster-whisper using device: {self._device}, compute_type: {compute_type}")

        self._model = WhisperModel(
            self.settings.whisper_model,
            device=self._device,
            compute_type=compute_type,
        )

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self._wyoming_client:
            await self._wyoming_client.disconnect()
            self._wyoming_client = None
        self._model = None
        self._processor = None
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

    @property
    def is_moonshine(self) -> bool:
        """Return True if using Moonshine backend."""
        return self._backend == STTBackend.MOONSHINE

    async def transcribe(
        self,
        audio: NDArray[np.float32],
        sample_rate: int = 16000,
    ) -> TranscriptionResult:
        """Transcribe audio to text.

        Args:
            audio: Audio samples as float32 array in range [-1.0, 1.0].
            sample_rate: Sample rate of audio (must be 16kHz).

        Returns:
            TranscriptionResult with text and metadata.
        """
        if not self._initialized:
            raise RuntimeError("STT not initialized. Call initialize() first.")

        if sample_rate != 16000:
            raise ValueError(f"STT requires 16kHz audio, got {sample_rate}Hz")

        if len(audio) == 0:
            return TranscriptionResult(
                text="",
                language=self.settings.language,
                confidence=0.0,
                duration_seconds=0.0,
            )

        # Route to appropriate backend
        if self._backend == STTBackend.MOONSHINE:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                None,
                self._transcribe_moonshine,
                audio,
            )
        elif self._backend == STTBackend.HAILO_WYOMING:
            return await self._wyoming_client.transcribe(
                audio, sample_rate, self.settings.language
            )
        else:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                None,
                self._transcribe_faster_whisper,
                audio,
            )

    def _transcribe_moonshine(
        self, audio: NDArray[np.float32]
    ) -> TranscriptionResult:
        """Synchronous transcription via Moonshine (blocking)."""
        import torch

        duration = len(audio) / 16000

        # Prepare inputs for Moonshine
        inputs = self._processor(
            audio,
            sampling_rate=16000,
            return_tensors="pt",
        )

        # Move to device
        input_features = inputs.input_features.to(self._device)
        if self._device == "cuda":
            input_features = input_features.half()

        # Generate transcription
        with torch.no_grad():
            generated_ids = self._model.generate(
                input_features,
                max_new_tokens=256,
            )

        # Decode
        text = self._processor.batch_decode(
            generated_ids, skip_special_tokens=True
        )[0]

        return TranscriptionResult(
            text=text.strip(),
            language=self.settings.language,
            confidence=0.9,  # Moonshine doesn't provide confidence scores
            duration_seconds=duration,
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

        Uses pre-allocated array with doubling strategy for O(n) total
        complexity instead of O(n²) from repeated concatenation.

        Args:
            audio_stream: Async iterator of audio chunks.
            sample_rate: Sample rate of audio (must be 16kHz).

        Yields:
            Partial transcription strings.
        """
        if not self._initialized:
            raise RuntimeError("STT not initialized. Call initialize() first.")

        chunk_duration = 2.0  # seconds
        samples_per_chunk = int(chunk_duration * sample_rate)

        # Pre-allocate array with doubling strategy for O(n) total copies
        # Initial size: 4 transcription chunks worth of audio
        audio_array = np.zeros(samples_per_chunk * 4, dtype=np.float32)
        write_pos = 0
        last_transcription = ""

        async for chunk in audio_stream:
            chunk_len = len(chunk)

            # Resize array if needed (doubling strategy: O(log n) resizes total)
            if write_pos + chunk_len > len(audio_array):
                new_size = max(len(audio_array) * 2, write_pos + chunk_len)
                new_array = np.zeros(new_size, dtype=np.float32)
                new_array[:write_pos] = audio_array[:write_pos]
                audio_array = new_array

            # Copy chunk into pre-allocated array (O(chunk_len))
            audio_array[write_pos : write_pos + chunk_len] = chunk
            write_pos += chunk_len

            if write_pos >= samples_per_chunk:
                result = await self.transcribe(audio_array[:write_pos], sample_rate)

                if result.text and result.text != last_transcription:
                    new_text = result.text
                    if last_transcription and new_text.startswith(last_transcription):
                        yield new_text[len(last_transcription) :].strip()
                    else:
                        yield new_text
                    last_transcription = result.text

        if write_pos > 0:
            result = await self.transcribe(audio_array[:write_pos], sample_rate)
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

        audio = self._resample_to_16k(audio, sample_rate)
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

        loop = asyncio.get_running_loop()
        audio, sample_rate = await loop.run_in_executor(
            None,
            self._read_audio_file,
            file_path,
        )

        audio = self._resample_to_16k(audio, sample_rate)
        return await self.transcribe(audio, 16000)

    def _read_audio_file(self, file_path: Path) -> tuple[NDArray[np.float32], int]:
        """Read audio file and return samples with sample rate."""
        import soundfile as sf

        audio, sample_rate = sf.read(str(file_path), dtype="float32")

        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)

        return audio, sample_rate

    @staticmethod
    def _resample_to_16k(audio: NDArray[np.float32], sample_rate: int) -> NDArray[np.float32]:
        """Resample audio to 16kHz for STT models.

        Args:
            audio: Audio samples as float32 array.
            sample_rate: Current sample rate of audio.

        Returns:
            Resampled audio at 16kHz.
        """
        if sample_rate == 16000:
            return audio

        from math import gcd
        from scipy.signal import resample_poly

        g = gcd(sample_rate, 16000)
        up = 16000 // g
        down = sample_rate // g
        return resample_poly(audio, up, down).astype(np.float32)


# Alias for the main STT service class
STTService = WhisperSTT
