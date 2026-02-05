"""Voice Activity Detection using Silero VAD.

Silero VAD is a lightweight, fast, and accurate voice activity detector:
- 1.8MB model size
- ~1ms processing per 30ms chunk
- 95% accuracy in noisy environments
- MIT License
"""

__all__ = [
    "SpeechState",
    "VADResult",
    "VADSessionState",
    "SileroVAD",
]

import asyncio
import logging
import warnings
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncIterator

import numpy as np
from numpy.typing import NDArray

from config.settings import VADSettings

logger = logging.getLogger(__name__)


class SpeechState(Enum):
    """Current speech detection state."""

    SILENCE = "silence"
    SPEECH_START = "speech_start"
    SPEECH = "speech"
    SPEECH_END = "speech_end"


@dataclass
class VADResult:
    """Result from VAD processing."""

    state: SpeechState
    probability: float
    audio_chunk: NDArray[np.float32] | None = None


@dataclass
class VADSessionState:
    """Per-session VAD state for concurrent call handling.

    Each call gets its own state instance to track speech/silence
    independently without interference from other calls.
    """

    is_speaking: bool = False
    speech_samples: int = 0
    silence_samples: int = 0

    def reset(self) -> None:
        """Reset state for a new utterance."""
        self.is_speaking = False
        self.speech_samples = 0
        self.silence_samples = 0


class SileroVAD:
    """Silero VAD wrapper for voice activity detection.

    Uses the Silero VAD model to detect speech in audio streams.
    Optimized for real-time processing with ~1ms latency per chunk.

    Thread-safe: Uses a lock for model inference and per-session state
    for tracking speech across concurrent calls.
    """

    def __init__(self, settings: VADSettings | None = None):
        if settings is None:
            settings = VADSettings()
        self.settings = settings

        self._model = None
        self._utils = None
        self._initialized = False
        self._lock = asyncio.Lock()  # Lock for model inference

        # Legacy state tracking (for single-session backwards compatibility)
        self._is_speaking = False
        self._speech_samples = 0
        self._silence_samples = 0

    async def initialize(self) -> None:
        """Initialize the Silero VAD model."""
        if self._initialized:
            return

        logger.info("Loading Silero VAD model...")

        # Load model in executor to avoid blocking
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._load_model)

        self._initialized = True
        logger.info("Silero VAD model loaded successfully")

    def _load_model(self) -> None:
        """Load the Silero VAD model (blocking)."""
        import torch

        # Load model from torch hub
        model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            trust_repo=True,
        )

        self._model = model
        self._utils = utils

        # Get the helper functions
        self._get_speech_timestamps = utils[0]
        self._save_audio = utils[1]
        self._read_audio = utils[2]
        self._vad_collector = utils[3]
        self._collect_chunks = utils[4]

    async def cleanup(self) -> None:
        """Clean up resources.

        Uses async reset to ensure thread-safe cleanup even if
        other coroutines are still processing.
        """
        # Use async reset to safely clear state under lock
        await self.reset_async()
        self._model = None
        self._utils = None
        self._initialized = False

    def reset(self) -> None:
        """Reset VAD state for a new conversation.

        .. deprecated::
            Use :meth:`reset_async` instead. This method modifies shared state
            without acquiring the lock and is unsafe for concurrent use.
        """
        warnings.warn(
            "SileroVAD.reset() is deprecated and not thread-safe. "
            "Use reset_async() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self._is_speaking = False
        self._speech_samples = 0
        self._silence_samples = 0
        if self._model is not None:
            self._model.reset_states()

    async def reset_async(self) -> None:
        """Thread-safe async reset of VAD state.

        Use this when resetting from an async context to ensure model state
        reset doesn't interfere with concurrent inference.
        """
        async with self._lock:
            self._is_speaking = False
            self._speech_samples = 0
            self._silence_samples = 0
            if self._model is not None:
                self._model.reset_states()

    def _samples_to_ms(self, samples: int, sample_rate: int = 16000) -> int:
        """Convert samples to milliseconds."""
        return int((samples / sample_rate) * 1000)

    def _ms_to_samples(self, ms: int, sample_rate: int = 16000) -> int:
        """Convert milliseconds to samples."""
        return int((ms / 1000) * sample_rate)

    def create_session_state(self) -> VADSessionState:
        """Create a new per-session state object.

        Returns:
            New VADSessionState for tracking a single call's speech state.
        """
        return VADSessionState()

    async def process_chunk(
        self,
        audio: NDArray[np.float32],
        sample_rate: int = 16000,
        session_state: VADSessionState | None = None,
    ) -> VADResult:
        """Process an audio chunk and return VAD result.

        Args:
            audio: Audio samples as float32 array in range [-1.0, 1.0].
            sample_rate: Sample rate of audio (default 16kHz).
            session_state: Optional per-session state. If None, uses legacy shared state.

        Returns:
            VADResult with speech state and probability.
        """
        if not self._initialized:
            raise RuntimeError("VAD not initialized. Call initialize() first.")

        # Run inference AND state update with lock to prevent race conditions.
        # Both operations must be atomic to prevent concurrent calls from
        # corrupting shared state.
        async with self._lock:
            loop = asyncio.get_running_loop()
            prob = await loop.run_in_executor(
                None,
                self._run_inference,
                audio,
                sample_rate,
            )

            # Determine state transition inside the lock
            if session_state is not None:
                # Per-session state doesn't need lock protection, but keeping
                # it inside for consistency and because inference must complete first
                state = self._update_session_state(session_state, prob, len(audio), sample_rate)
            else:
                # Legacy shared state - MUST be inside lock to prevent race conditions
                state = self._update_state(prob, len(audio), sample_rate)

        return VADResult(
            state=state,
            probability=prob,
            audio_chunk=audio if state in (SpeechState.SPEECH_START, SpeechState.SPEECH) else None,
        )

    def _run_inference(self, audio: NDArray[np.float32], sample_rate: int) -> float:
        """Run VAD inference (blocking)."""
        import torch

        # Convert to tensor
        audio_tensor = torch.from_numpy(audio)

        # Run model
        speech_prob = self._model(audio_tensor, sample_rate).item()

        return speech_prob

    def _update_session_state(
        self,
        state: VADSessionState,
        probability: float,
        chunk_samples: int,
        sample_rate: int,
    ) -> SpeechState:
        """Update per-session state based on probability.

        Args:
            state: Per-session VAD state object.
            probability: Speech probability from model.
            chunk_samples: Number of samples in the chunk.
            sample_rate: Audio sample rate.

        Returns:
            Current speech state.
        """
        is_speech = probability >= self.settings.threshold

        if is_speech:
            state.speech_samples += chunk_samples
            state.silence_samples = 0

            if not state.is_speaking:
                # Check if we've had enough speech to trigger
                speech_ms = self._samples_to_ms(state.speech_samples, sample_rate)
                if speech_ms >= self.settings.min_speech_duration_ms:
                    state.is_speaking = True
                    return SpeechState.SPEECH_START

            return SpeechState.SPEECH if state.is_speaking else SpeechState.SILENCE

        else:  # Silence detected
            state.silence_samples += chunk_samples

            if state.is_speaking:
                # Check if we've had enough silence to end speech
                silence_ms = self._samples_to_ms(state.silence_samples, sample_rate)
                if silence_ms >= self.settings.min_silence_duration_ms:
                    state.is_speaking = False
                    state.speech_samples = 0
                    return SpeechState.SPEECH_END

                # Still in speech (brief pause)
                return SpeechState.SPEECH

            # Reset speech counter during silence
            state.speech_samples = 0
            return SpeechState.SILENCE

    def _update_state(
        self,
        probability: float,
        chunk_samples: int,
        sample_rate: int,
    ) -> SpeechState:
        """Update internal state based on probability.

        Args:
            probability: Speech probability from model.
            chunk_samples: Number of samples in the chunk.
            sample_rate: Audio sample rate.

        Returns:
            Current speech state.
        """
        is_speech = probability >= self.settings.threshold

        if is_speech:
            self._speech_samples += chunk_samples
            self._silence_samples = 0

            if not self._is_speaking:
                # Check if we've had enough speech to trigger
                speech_ms = self._samples_to_ms(self._speech_samples, sample_rate)
                if speech_ms >= self.settings.min_speech_duration_ms:
                    self._is_speaking = True
                    return SpeechState.SPEECH_START

            return SpeechState.SPEECH if self._is_speaking else SpeechState.SILENCE

        else:  # Silence detected
            self._silence_samples += chunk_samples

            if self._is_speaking:
                # Check if we've had enough silence to end speech
                silence_ms = self._samples_to_ms(self._silence_samples, sample_rate)
                if silence_ms >= self.settings.min_silence_duration_ms:
                    self._is_speaking = False
                    self._speech_samples = 0
                    return SpeechState.SPEECH_END

                # Still in speech (brief pause)
                return SpeechState.SPEECH

            # Reset speech counter during silence
            self._speech_samples = 0
            return SpeechState.SILENCE

    async def detect_speech_end(
        self,
        audio_stream: AsyncIterator[NDArray[np.float32]],
        sample_rate: int = 16000,
    ) -> tuple[NDArray[np.float32], bool]:
        """Collect audio until speech ends.

        Args:
            audio_stream: Async iterator of audio chunks.
            sample_rate: Audio sample rate.

        Returns:
            Tuple of (collected audio, whether speech was detected).
        """
        chunks = []
        speech_detected = False

        async for chunk in audio_stream:
            result = await self.process_chunk(chunk, sample_rate)

            if result.state == SpeechState.SPEECH_START:
                speech_detected = True
                chunks.append(chunk)

            elif result.state == SpeechState.SPEECH:
                if speech_detected:
                    chunks.append(chunk)

            elif result.state == SpeechState.SPEECH_END:
                # Add padding at the end
                pad_samples = self._ms_to_samples(self.settings.speech_pad_ms, sample_rate)
                if len(chunk) > pad_samples:
                    chunks.append(chunk[:pad_samples])
                break

        if not chunks:
            return np.array([], dtype=np.float32), False

        return np.concatenate(chunks), speech_detected

    @property
    def is_speaking(self) -> bool:
        """Check if speech is currently being detected."""
        return self._is_speaking
