"""Voice Activity Detection using TEN VAD via sherpa-onnx.

TEN VAD is a lightweight, fast, and accurate voice activity detector:
- 332KB model size
- ~0.15ms processing per 256-sample chunk on Pi 5
- 32% lower RTF than Silero VAD
- ~300ms faster speech-to-silence detection
- Apache 2.0 License
- No PyTorch dependency (uses ONNX runtime via sherpa-onnx)

Supports a model pool for concurrent call handling: each session gets
an exclusive VADModel, eliminating lock contention and state save/restore.
"""

__all__ = [
    "SpeechState",
    "VADResult",
    "VADSessionState",
    "VADModel",
    "VADModelPool",
    "TenVAD",
    "SileroVAD",  # Backwards-compatible alias
]

import asyncio
import logging
import warnings
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import AsyncIterator

import numpy as np
from numpy.typing import NDArray

from config.settings import VADSettings

logger = logging.getLogger(__name__)

# Model path relative to payphone-app root
_MODEL_PATH = Path(__file__).parent.parent / "models" / "ten-vad-sherpa.onnx"


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
    """Wrapper around a single TEN VAD model instance via sherpa-onnx.

    Each VADModel holds its own sherpa-onnx VoiceActivityDetector, so it
    can be used by a single session without locking or state save/restore.
    """

    # TEN VAD processes 256 samples at 16kHz (16ms).
    # AudioSocket sends 20ms frames -> 320 samples at 16kHz after resampling.
    # We accumulate into a buffer and extract exact-sized windows.
    WINDOW_SIZE = {16000: 256, 8000: 160}

    def __init__(self, settings: VADSettings, model_path: str | None = None):
        import sherpa_onnx

        self.settings = settings
        self._model_path = model_path or str(_MODEL_PATH)

        config = sherpa_onnx.VadModelConfig()
        config.ten_vad.model = self._model_path
        config.sample_rate = 16000
        config.num_threads = 1
        config.provider = "cpu"

        self._vad = sherpa_onnx.VoiceActivityDetector(config, buffer_size_in_seconds=30)
        self._accum = np.empty(0, dtype=np.float32)

    async def process_chunk(
        self,
        audio: NDArray[np.float32],
        sample_rate: int = 16000,
        session_state: VADSessionState | None = None,
        threshold_override: float | None = None,
    ) -> VADResult:
        """Process an audio chunk and return VAD result.

        No lock needed - this model instance is exclusively owned by one session.
        Accumulates samples and feeds exact-sized windows to TEN VAD.

        Args:
            audio: Audio samples as float32 array in range [-1.0, 1.0].
            sample_rate: Sample rate of audio (default 16kHz).
            session_state: Optional per-session state for speech/silence tracking.
            threshold_override: If set, overrides settings.threshold for this call.

        Returns:
            VADResult with speech state and probability.
        """
        window = self.WINDOW_SIZE.get(sample_rate, 256)

        # Append new audio to accumulator
        self._accum = (
            np.concatenate([self._accum, audio])
            if len(self._accum) > 0
            else audio.copy()
        )

        if len(self._accum) < window:
            return VADResult(state=SpeechState.SILENCE, probability=0.0, audio_chunk=None)

        # Extract exactly `window` samples; keep remainder
        chunk = self._accum[:window]
        self._accum = (
            self._accum[window:].copy()
            if len(self._accum) > window
            else np.empty(0, dtype=np.float32)
        )

        # Run inference - sherpa-onnx accept_waveform takes float32 samples
        loop = asyncio.get_running_loop()
        is_speech = await loop.run_in_executor(
            None,
            self._run_inference,
            chunk,
        )

        # Map sherpa-onnx binary is_speech to probability-like value
        prob = 1.0 if is_speech else 0.0

        # Use original audio (not just the window) for the audio_chunk so callers
        # get the full audio data for STT buffering
        if session_state is not None:
            threshold = (
                threshold_override
                if threshold_override is not None
                else self.settings.threshold
            )
            state = self._update_session_state(
                session_state, prob, len(audio), sample_rate, threshold
            )
        else:
            state = (
                SpeechState.SPEECH
                if prob >= (threshold_override or self.settings.threshold)
                else SpeechState.SILENCE
            )

        return VADResult(
            state=state,
            probability=prob,
            audio_chunk=audio
            if state in (SpeechState.SPEECH_START, SpeechState.SPEECH)
            else None,
        )

    def _run_inference(self, audio: NDArray[np.float32]) -> bool:
        """Run VAD inference (blocking).

        sherpa-onnx accepts float32 samples directly.
        """
        self._vad.accept_waveform(audio)
        return self._vad.is_speech_detected()

    def reset_states(self) -> None:
        """Reset the model's internal state and accumulation buffer."""
        self._vad.reset()
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
            probability: Speech probability from model (1.0 or 0.0).
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
        """Create pool_size VAD model instances.

        TEN VAD models are tiny (332KB) so this is nearly instant.
        """
        async with self._lock:
            for i in range(self.pool_size):
                logger.info(f"Creating TEN VAD model {i + 1}/{self.pool_size}...")
                vad_model = VADModel(self.settings)
                self._models.append(vad_model)
                await self._available.put(vad_model)

            logger.info(f"TEN VAD model pool initialized ({self.pool_size} models)")

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


class TenVAD:
    """TEN VAD wrapper for voice activity detection.

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
        self._model: VADModel | None = None
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

        logger.info("Loading TEN VAD model pool...")

        # Initialize the pool
        self._pool = VADModelPool(self.settings, pool_size=3)
        await self._pool.initialize()

        # Create legacy single model for backwards-compatible process_chunk
        self._model = VADModel(self.settings)

        self._initialized = True
        logger.info("TEN VAD initialized (pool + legacy model)")

    async def cleanup(self) -> None:
        """Clean up resources."""
        await self.reset_async()
        if self._pool is not None:
            await self._pool.cleanup()
            self._pool = None
        self._model = None
        self._initialized = False

    def reset(self) -> None:
        """Reset VAD state for a new conversation.

        .. deprecated::
            Use :meth:`reset_async` instead. This method modifies shared state
            without acquiring the lock and is unsafe for concurrent use.
        """
        warnings.warn(
            "TenVAD.reset() is deprecated and not thread-safe. "
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
            if session_state is None:
                # Use legacy shared state via proxy
                proxy = VADSessionState(
                    is_speaking=self._is_speaking,
                    speech_samples=self._speech_samples,
                    silence_samples=self._silence_samples,
                )
                result = await self._model.process_chunk(
                    audio, sample_rate, session_state=proxy
                )
                # Sync proxy state back to shared state
                self._is_speaking = proxy.is_speaking
                self._speech_samples = proxy.speech_samples
                self._silence_samples = proxy.silence_samples
            else:
                result = await self._model.process_chunk(
                    audio, sample_rate, session_state=session_state
                )

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


# Backwards-compatible alias
SileroVAD = TenVAD
