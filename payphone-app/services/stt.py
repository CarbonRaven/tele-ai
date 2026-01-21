"""Speech-to-Text service using faster-whisper.

faster-whisper provides 4-6x speedup over standard Whisper:
- Uses CTranslate2 backend for optimized inference
- Supports INT8 quantization for further speed gains
- Compatible with distil-whisper models for even faster inference
"""

import asyncio
import logging
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator

import numpy as np
from numpy.typing import NDArray

from config.settings import STTSettings

logger = logging.getLogger(__name__)


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


class WhisperSTT:
    """faster-whisper based Speech-to-Text service.

    Uses the faster-whisper library with optional distil-whisper models
    for optimized inference on edge devices.
    """

    def __init__(self, settings: STTSettings | None = None):
        if settings is None:
            settings = STTSettings()
        self.settings = settings

        self._model = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the Whisper model."""
        if self._initialized:
            return

        logger.info(f"Loading faster-whisper model: {self.settings.model_name}")

        # Load model in executor to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load_model)

        self._initialized = True
        logger.info("faster-whisper model loaded successfully")

    def _load_model(self) -> None:
        """Load the Whisper model (blocking)."""
        from faster_whisper import WhisperModel

        # Determine device
        device = self.settings.device
        if device == "auto":
            try:
                import torch

                device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                device = "cpu"

        # Determine compute type
        compute_type = self.settings.compute_type
        if compute_type == "auto":
            compute_type = "int8" if device == "cpu" else "float16"

        logger.info(f"Using device: {device}, compute_type: {compute_type}")

        self._model = WhisperModel(
            self.settings.model_name,
            device=device,
            compute_type=compute_type,
        )

    async def cleanup(self) -> None:
        """Clean up resources."""
        self._model = None
        self._initialized = False

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

        # Run transcription in executor
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._transcribe_sync,
            audio,
        )

        return result

    def _transcribe_sync(self, audio: NDArray[np.float32]) -> TranscriptionResult:
        """Synchronous transcription (blocking)."""
        duration = len(audio) / 16000

        # Run transcription
        segments, info = self._model.transcribe(
            audio,
            language=self.settings.language,
            beam_size=self.settings.beam_size,
            vad_filter=self.settings.vad_filter,
            initial_prompt=self.settings.initial_prompt,
        )

        # Collect all segments
        text_parts = []
        total_confidence = 0.0
        segment_count = 0

        for segment in segments:
            text_parts.append(segment.text)
            # Average log probability as confidence proxy
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

        # Buffer for collecting audio
        audio_buffer = []
        last_transcription = ""

        # Transcribe every ~2 seconds of audio
        chunk_duration = 2.0  # seconds
        samples_per_chunk = int(chunk_duration * sample_rate)

        async for chunk in audio_stream:
            audio_buffer.append(chunk)

            # Calculate total samples
            total_samples = sum(len(c) for c in audio_buffer)

            if total_samples >= samples_per_chunk:
                # Concatenate and transcribe
                full_audio = np.concatenate(audio_buffer)
                result = await self.transcribe(full_audio, sample_rate)

                if result.text and result.text != last_transcription:
                    # Yield new text since last transcription
                    new_text = result.text
                    if last_transcription and new_text.startswith(last_transcription):
                        # Yield only the new part
                        yield new_text[len(last_transcription) :].strip()
                    else:
                        yield new_text
                    last_transcription = result.text

        # Final transcription of remaining audio
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
        # Convert bytes to float32
        samples = np.frombuffer(audio_bytes, dtype=np.int16)
        audio = samples.astype(np.float32) / 32768.0

        # Resample if needed
        if sample_rate != 16000:
            from scipy.signal import resample_poly
            from math import gcd

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

        # Read audio file
        loop = asyncio.get_event_loop()
        audio, sample_rate = await loop.run_in_executor(
            None,
            self._read_audio_file,
            file_path,
        )

        # Resample if needed
        if sample_rate != 16000:
            from scipy.signal import resample_poly
            from math import gcd

            g = gcd(sample_rate, 16000)
            up = 16000 // g
            down = sample_rate // g
            audio = resample_poly(audio, up, down).astype(np.float32)

        return await self.transcribe(audio, 16000)

    def _read_audio_file(self, file_path: Path) -> tuple[NDArray[np.float32], int]:
        """Read audio file and return samples with sample rate."""
        import soundfile as sf

        audio, sample_rate = sf.read(str(file_path), dtype="float32")

        # Convert stereo to mono if needed
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)

        return audio, sample_rate
