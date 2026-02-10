"""Voice Activity Detection using Silero VAD.

Silero VAD is a lightweight, fast, and accurate voice activity detector:
- 1.8MB model size
- ~1ms processing per 30ms chunk
- 95% accuracy in noisy environments
- MIT License

Supports a model pool for concurrent call handling: each session gets
an exclusive VADModel, eliminating lock contention and state save/restore.
"""

__all__ = [
    "SpeechState",
    "VADResult",
    "VADSessionState",
    "VADModel",
    "VADModelPool",
    "SileroVAD",
]

import asyncio
import logging
import warnings
from dataclasses import dataclass
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


class VADModel:
    """Wrapper around a single Silero VAD model instance.

    Each VADModel holds its own model and LSTM state, so it can be
    used by a single session without locking or state save/restore.
    """

    # Silero VAD v5 requires EXACTLY 512 samples at 16kHz (or 256 at 8kHz).
    # AudioSocket sends 20ms frames → 320 samples at 16kHz after resampling.
    # We accumulate into a ring buffer and extract exact 512-sample windows.
    WINDOW_SIZE = {16000: 512, 8000: 256}

    def __init__(self, model, utils, settings: VADSettings):
        self._model = model
        self._utils = utils
        self.settings = settings
        self._accum = np.empty(0, dtype=np.float32)

    async def process_chunk(
        self,
        audio: NDArray[np.float32],
        sample_rate: int = 16000,
        session_state: VADSessionState | None = None,
        threshold_override: float | None = None,
    ) -> VADResult:
        """Process an audio chunk and return VAD result.

        No lock needed — this model instance is exclusively owned by one session.
        Accumulates samples and feeds exact-sized windows to Silero.

        Args:
            audio: Audio samples as float32 array in range [-1.0, 1.0].
            sample_rate: Sample rate of audio (default 16kHz).
            session_state: Optional per-session state for speech/silence tracking.
            threshold_override: If set, overrides settings.threshold for this call.

        Returns:
            VADResult with speech state and probability.
        """
        window = self.WINDOW_SIZE.get(sample_rate, 512)

        # Append new audio to accumulator
        self._accum = np.concatenate([self._accum, audio]) if len(self._accum) > 0 else audio.copy()

        if len(self._accum) < window:
            return VADResult(state=SpeechState.SILENCE, probability=0.0, audio_chunk=None)

        # Extract exactly `window` samples; keep remainder
        chunk = self._accum[:window]
        self._accum = self._accum[window:].copy() if len(self._accum) > window else np.empty(0, dtype=np.float32)

        loop = asyncio.get_running_loop()
        prob = await loop.run_in_executor(
            None,
            self._run_inference,
            chunk,
            sample_rate,
        )

        # Use original audio (not just the window) for the audio_chunk so callers
        # get the full audio data for STT buffering
        if session_state is not None:
            threshold = threshold_override if threshold_override is not None else self.settings.threshold
            state = self._update_session_state(session_state, prob, len(audio), sample_rate, threshold)
        else:
            state = SpeechState.SPEECH if prob >= (threshold_override or self.settings.threshold) else SpeechState.SILENCE

        return VADResult(
            state=state,
            probability=prob,
            audio_chunk=audio if state in (SpeechState.SPEECH_START, SpeechState.SPEECH) else None,
        )

    def _run_inference(self, audio: NDArray[np.float32], sample_rate: int) -> float:
        """Run VAD inference (blocking)."""
        import torch

        audio_tensor = torch.from_numpy(audio)
        speech_prob = self._model(audio_tensor, sample_rate).item()
        return speech_prob

    def reset_states(self) -> None:
        """Reset the model's LSTM hidden state and accumulation buffer."""
        self._model.reset_states()
        self._accum = np.empty(0, dtype=np.float32)

    @staticmethod
    def _samples_to_ms(samples: int, sample_rate: int = 16000) -> int:
        """Convert samples to milliseconds."""
        return int((samples / sample_rate) * 1000)

    def _update_session_state(
        self,
        state: VADSessionState,
        probability: float,
        chunk_samples: int,
        sample_rate: int,
        threshold: float,
    ) -> SpeechState:
        """Update per-session state based on probability.

        Args:
            state: Per-session VAD state object.
            probability: Speech probability from model.
            chunk_samples: Number of samples in the chunk.
            sample_rate: Audio sample rate.
            threshold: Speech detection threshold.

        Returns:
            Current speech state.
        """
        is_speech = probability >= threshold

        if is_speech:
            state.speech_samples += chunk_samples
            state.silence_samples = 0

            if not state.is_speaking:
                speech_ms = self._samples_to_ms(state.speech_samples, sample_rate)
                if speech_ms >= self.settings.min_speech_duration_ms:
                    state.is_speaking = True
                    return SpeechState.SPEECH_START

            return SpeechState.SPEECH if state.is_speaking else SpeechState.SILENCE

        else:
            state.silence_samples += chunk_samples

            if state.is_speaking:
                silence_ms = self._samples_to_ms(state.silence_samples, sample_rate)
                if silence_ms >= self.settings.min_silence_duration_ms:
                    state.is_speaking = False
                    state.speech_samples = 0
                    return SpeechState.SPEECH_END

                return SpeechState.SPEECH

            state.speech_samples = 0
            return SpeechState.SILENCE


class VADModelPool:
    """Pool of pre-loaded VAD models for concurrent session use.

    Each session acquires an exclusive model from the pool and releases
    it when done. No lock contention on the hot path.
    """

    def __init__(self, settings: VADSettings, pool_size: int = 3):
        self.settings = settings
        self.pool_size = pool_size
        self._models: list[VADModel] = []
        self._available: asyncio.Queue[VADModel] = asyncio.Queue()
        self._lock = asyncio.Lock()  # Only for init/cleanup

    async def initialize(self) -> None:
        """Load pool_size VAD models."""
        async with self._lock:
            loop = asyncio.get_running_loop()

            for i in range(self.pool_size):
                logger.info(f"Loading VAD model {i + 1}/{self.pool_size}...")
                model, utils = await loop.run_in_executor(None, self._load_one_model)
                vad_model = VADModel(model, utils, self.settings)
                self._models.append(vad_model)
                await self._available.put(vad_model)

            logger.info(f"VAD model pool initialized ({self.pool_size} models)")

    @staticmethod
    def _load_one_model():
        """Load a single Silero VAD model (blocking)."""
        import torch

        model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            trust_repo=True,
        )
        return model, utils

    async def acquire(self) -> VADModel:
        """Get an exclusive model from the pool.

        Blocks if all models are currently in use.
        """
        model = await self._available.get()
        return model

    async def release(self, model: VADModel) -> None:
        """Reset model state and return it to the pool."""
        model.reset_states()
        await self._available.put(model)

    async def cleanup(self) -> None:
        """Clean up all models in the pool."""
        async with self._lock:
            # Drain the queue
            while not self._available.empty():
                try:
                    self._available.get_nowait()
                except asyncio.QueueEmpty:
                    break
            self._models.clear()


class SileroVAD:
    """Silero VAD wrapper for voice activity detection.

    Uses a VADModelPool for concurrent call support. Each session acquires
    an exclusive model via acquire_model()/release_model().

    Legacy single-model path (process_chunk with lock) is preserved for
    backwards compatibility with detect_speech_end() and single-session callers.
    """

    def __init__(self, settings: VADSettings | None = None):
        if settings is None:
            settings = VADSettings()
        self.settings = settings

        # Pool for concurrent sessions
        self._pool: VADModelPool | None = None

        # Legacy single model (for backwards-compatible process_chunk)
        self._model = None
        self._utils = None
        self._initialized = False
        self._lock = asyncio.Lock()

        # Legacy state tracking (for single-session backwards compatibility)
        self._is_speaking = False
        self._speech_samples = 0
        self._silence_samples = 0

    async def initialize(self) -> None:
        """Initialize the VAD model pool and legacy single model."""
        if self._initialized:
            return

        logger.info("Loading Silero VAD model pool...")

        # Initialize the pool
        self._pool = VADModelPool(self.settings, pool_size=3)
        await self._pool.initialize()

        # Load legacy single model for backwards-compatible process_chunk
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._load_model)

        self._initialized = True
        logger.info("Silero VAD initialized (pool + legacy model)")

    def _load_model(self) -> None:
        """Load the legacy single Silero VAD model (blocking)."""
        import torch

        model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            trust_repo=True,
        )

        self._model = model
        self._utils = utils

        self._get_speech_timestamps = utils[0]
        self._save_audio = utils[1]
        self._read_audio = utils[2]
        self._vad_collector = utils[3]
        self._collect_chunks = utils[4]

    async def cleanup(self) -> None:
        """Clean up resources."""
        await self.reset_async()
        if self._pool is not None:
            await self._pool.cleanup()
            self._pool = None
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
        """Thread-safe async reset of VAD state."""
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
        """Create a new per-session state object."""
        return VADSessionState()

    async def acquire_model(self) -> VADModel:
        """Acquire an exclusive VAD model from the pool.

        Returns:
            VADModel for exclusive use by one session.
        """
        if self._pool is None:
            raise RuntimeError("VAD not initialized. Call initialize() first.")
        return await self._pool.acquire()

    async def release_model(self, model: VADModel) -> None:
        """Release a VAD model back to the pool.

        Args:
            model: The VADModel to return.
        """
        if self._pool is not None:
            await self._pool.release(model)

    async def process_chunk(
        self,
        audio: NDArray[np.float32],
        sample_rate: int = 16000,
        session_state: VADSessionState | None = None,
    ) -> VADResult:
        """Process an audio chunk using the legacy single model.

        This method uses the shared model with a lock, preserving backwards
        compatibility for detect_speech_end() and single-session callers.
        For concurrent sessions, use acquire_model() and call
        VADModel.process_chunk() directly.

        Args:
            audio: Audio samples as float32 array in range [-1.0, 1.0].
            sample_rate: Sample rate of audio (default 16kHz).
            session_state: Optional per-session state. If None, uses legacy shared state.

        Returns:
            VADResult with speech state and probability.
        """
        if not self._initialized:
            raise RuntimeError("VAD not initialized. Call initialize() first.")

        async with self._lock:
            loop = asyncio.get_running_loop()
            prob = await loop.run_in_executor(
                None,
                self._run_inference,
                audio,
                sample_rate,
            )

            if session_state is not None:
                state = self._update_session_state(session_state, prob, len(audio), sample_rate)
            else:
                state = self._update_state(prob, len(audio), sample_rate)

        return VADResult(
            state=state,
            probability=prob,
            audio_chunk=audio if state in (SpeechState.SPEECH_START, SpeechState.SPEECH) else None,
        )

    def _run_inference(self, audio: NDArray[np.float32], sample_rate: int) -> float:
        """Run VAD inference on the legacy model (blocking)."""
        import torch

        audio_tensor = torch.from_numpy(audio)
        speech_prob = self._model(audio_tensor, sample_rate).item()
        return speech_prob

    def _update_session_state(
        self,
        state: VADSessionState,
        probability: float,
        chunk_samples: int,
        sample_rate: int,
    ) -> SpeechState:
        """Update per-session state based on probability."""
        is_speech = probability >= self.settings.threshold

        if is_speech:
            state.speech_samples += chunk_samples
            state.silence_samples = 0

            if not state.is_speaking:
                speech_ms = self._samples_to_ms(state.speech_samples, sample_rate)
                if speech_ms >= self.settings.min_speech_duration_ms:
                    state.is_speaking = True
                    return SpeechState.SPEECH_START

            return SpeechState.SPEECH if state.is_speaking else SpeechState.SILENCE

        else:
            state.silence_samples += chunk_samples

            if state.is_speaking:
                silence_ms = self._samples_to_ms(state.silence_samples, sample_rate)
                if silence_ms >= self.settings.min_silence_duration_ms:
                    state.is_speaking = False
                    state.speech_samples = 0
                    return SpeechState.SPEECH_END

                return SpeechState.SPEECH

            state.speech_samples = 0
            return SpeechState.SILENCE

    def _update_state(
        self,
        probability: float,
        chunk_samples: int,
        sample_rate: int,
    ) -> SpeechState:
        """Update internal state based on probability.

        Delegates to _update_session_state using a proxy for the legacy shared state.
        """
        proxy = VADSessionState(
            is_speaking=self._is_speaking,
            speech_samples=self._speech_samples,
            silence_samples=self._silence_samples,
        )
        result = self._update_session_state(proxy, probability, chunk_samples, sample_rate)
        self._is_speaking = proxy.is_speaking
        self._speech_samples = proxy.speech_samples
        self._silence_samples = proxy.silence_samples
        return result

    async def detect_speech_end(
        self,
        audio_stream: AsyncIterator[NDArray[np.float32]],
        sample_rate: int = 16000,
    ) -> tuple[NDArray[np.float32], bool]:
        """Collect audio until speech ends.

        Uses the legacy single-model path.

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
