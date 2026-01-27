"""Text-to-Speech service using Kokoro-82M.

Kokoro-82M provides sub-300ms latency TTS:
- Only 82M parameters (~150-200MB model)
- Built on StyleTTS2 + ISTFTNet
- CPU-friendly, runs on embedded devices
- Apache 2.0 license

Supports two modes:
- Local: Model runs on Pi #1 (default)
- Remote: Calls TTS server on Pi #2 to offload CPU
"""

__all__ = [
    "TTSResult",
    "KokoroTTS",
    "RemoteTTS",
    "create_tts",
    "VOICE_MAP",
    "get_voice_for_feature",
]

import asyncio
import base64
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, Protocol

import numpy as np
from numpy.typing import NDArray

from config.settings import TTSSettings

logger = logging.getLogger(__name__)


class TTSProtocol(Protocol):
    """Protocol for TTS implementations."""

    async def initialize(self) -> None: ...
    async def cleanup(self) -> None: ...
    async def synthesize(
        self, text: str, voice: str | None = None, speed: float | None = None
    ) -> NDArray[np.float32]: ...
    @property
    def sample_rate(self) -> int: ...


@dataclass
class TTSResult:
    """Result from text-to-speech synthesis."""

    audio: NDArray[np.float32]
    sample_rate: int
    duration_seconds: float
    text: str


class KokoroTTS:
    """Kokoro-82M based Text-to-Speech service.

    Provides fast, high-quality TTS optimized for real-time voice applications.
    Outputs 24kHz audio by default.

    Thread-safe: Uses asyncio.Lock to prevent concurrent synthesis calls
    from corrupting model state during multi-call scenarios.
    """

    def __init__(self, settings: TTSSettings | None = None):
        if settings is None:
            settings = TTSSettings()
        self.settings = settings

        self._model = None
        self._voices = None
        self._initialized = False
        self._sample_rate = 24000  # Kokoro outputs 24kHz
        self._lock: asyncio.Lock | None = None  # Created on first use

    async def initialize(self) -> None:
        """Initialize the Kokoro TTS model."""
        if self._initialized:
            return

        logger.info("Loading Kokoro TTS model...")

        # Load model in executor to avoid blocking
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._load_model)

        self._initialized = True
        logger.info("Kokoro TTS model loaded successfully")

    def _load_model(self) -> None:
        """Load the Kokoro model (blocking)."""
        try:
            from kokoro_onnx import Kokoro

            # Load model and voices
            self._model = Kokoro(
                self.settings.model_path,
                self.settings.voices_path,
            )

            logger.info(f"Available voices: {self._model.get_voices()}")

        except ImportError:
            logger.warning(
                "kokoro-onnx not available, using fallback TTS. "
                "Install with: pip install kokoro-onnx"
            )
            self._model = None

        except FileNotFoundError as e:
            logger.warning(f"Kokoro model files not found: {e}. Using fallback TTS.")
            self._model = None

    async def cleanup(self) -> None:
        """Clean up resources."""
        self._model = None
        self._initialized = False

    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        speed: float | None = None,
    ) -> NDArray[np.float32]:
        """Synthesize text to audio.

        Thread-safe: Acquires lock to prevent concurrent synthesis calls
        from corrupting model state.

        Args:
            text: Text to synthesize.
            voice: Optional voice override.
            speed: Optional speed override (1.0 = normal).

        Returns:
            Audio samples as float32 array at 24kHz.
        """
        if not self._initialized:
            raise RuntimeError("TTS not initialized. Call initialize() first.")

        if not text or not text.strip():
            return np.array([], dtype=np.float32)

        voice = voice or self.settings.voice
        speed = speed or self.settings.speed

        # Lazy-create lock on first use (must be in async context)
        if self._lock is None:
            self._lock = asyncio.Lock()

        # Acquire lock to prevent concurrent synthesis corrupting model state
        async with self._lock:
            loop = asyncio.get_running_loop()

            if self._model is not None:
                audio = await loop.run_in_executor(
                    None,
                    self._synthesize_kokoro,
                    text,
                    voice,
                    speed,
                )
            else:
                # Fallback to silent audio (for testing without model)
                logger.warning("Using silent fallback - no TTS model loaded")
                duration = len(text) * 0.05  # ~50ms per character estimate
                audio = np.zeros(int(duration * self._sample_rate), dtype=np.float32)

        return audio

    def _synthesize_kokoro(
        self,
        text: str,
        voice: str,
        speed: float,
    ) -> NDArray[np.float32]:
        """Synchronous Kokoro synthesis (blocking)."""
        samples, sample_rate = self._model.create(
            text,
            voice=voice,
            speed=speed,
        )

        # Kokoro returns float32 audio
        return samples.astype(np.float32)

    async def synthesize_to_result(
        self,
        text: str,
        voice: str | None = None,
        speed: float | None = None,
    ) -> TTSResult:
        """Synthesize text to TTSResult with metadata.

        Args:
            text: Text to synthesize.
            voice: Optional voice override.
            speed: Optional speed override.

        Returns:
            TTSResult with audio and metadata.
        """
        audio = await self.synthesize(text, voice, speed)

        return TTSResult(
            audio=audio,
            sample_rate=self._sample_rate,
            duration_seconds=len(audio) / self._sample_rate,
            text=text,
        )

    async def synthesize_streaming(
        self,
        text_stream: AsyncIterator[str],
        voice: str | None = None,
        speed: float | None = None,
    ) -> AsyncIterator[NDArray[np.float32]]:
        """Synthesize streaming text to streaming audio.

        Uses sentence chunking to provide audio as soon as sentences
        are complete, reducing perceived latency.

        Args:
            text_stream: Async iterator of text chunks (typically sentences).
            voice: Optional voice override.
            speed: Optional speed override.

        Yields:
            Audio chunks as float32 arrays.
        """
        async for text in text_stream:
            if text and text.strip():
                audio = await self.synthesize(text, voice, speed)
                if len(audio) > 0:
                    yield audio

    async def synthesize_sentences(
        self,
        sentences: list[str],
        voice: str | None = None,
        speed: float | None = None,
    ) -> AsyncIterator[tuple[str, NDArray[np.float32]]]:
        """Synthesize multiple sentences, yielding each as completed.

        Args:
            sentences: List of sentences to synthesize.
            voice: Optional voice override.
            speed: Optional speed override.

        Yields:
            Tuples of (sentence, audio) for each sentence.
        """
        for sentence in sentences:
            if sentence and sentence.strip():
                audio = await self.synthesize(sentence, voice, speed)
                yield sentence, audio

    @property
    def sample_rate(self) -> int:
        """Get the output sample rate."""
        return self._sample_rate

    def get_available_voices(self) -> list[str]:
        """Get list of available voices."""
        if self._model is not None:
            return self._model.get_voices()
        return []


class RemoteTTS:
    """Remote TTS client that calls a TTS server on Pi #2.

    Offloads CPU-intensive synthesis to a remote server, reducing
    Pi #1 CPU load by ~30% during speech output.

    The remote server should run tts_server.py and expose an HTTP endpoint.
    """

    def __init__(self, settings: TTSSettings | None = None):
        if settings is None:
            settings = TTSSettings()
        self.settings = settings

        self._session = None
        self._initialized = False
        self._sample_rate = 24000  # Kokoro outputs 24kHz

    async def initialize(self) -> None:
        """Initialize the HTTP client session."""
        if self._initialized:
            return

        try:
            import aiohttp

            # Create persistent session for connection reuse
            timeout = aiohttp.ClientTimeout(total=self.settings.remote_timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)

            # Test connection to remote server
            async with self._session.get(f"{self.settings.remote_host}/health") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self._sample_rate = data.get("sample_rate", 24000)
                    logger.info(
                        f"Connected to remote TTS server at {self.settings.remote_host}"
                    )
                else:
                    raise ConnectionError(f"TTS server returned status {resp.status}")

            self._initialized = True

        except ImportError:
            raise RuntimeError(
                "aiohttp required for remote TTS. Install with: pip install aiohttp"
            )
        except Exception as e:
            logger.error(f"Failed to connect to remote TTS server: {e}")
            raise

    async def cleanup(self) -> None:
        """Clean up HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
        self._initialized = False

    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        speed: float | None = None,
    ) -> NDArray[np.float32]:
        """Synthesize text via remote TTS server.

        Args:
            text: Text to synthesize.
            voice: Optional voice override.
            speed: Optional speed override.

        Returns:
            Audio samples as float32 array at 24kHz.
        """
        if not self._initialized:
            raise RuntimeError("Remote TTS not initialized. Call initialize() first.")

        if not text or not text.strip():
            return np.array([], dtype=np.float32)

        voice = voice or self.settings.voice
        speed = speed or self.settings.speed

        try:
            async with self._session.post(
                f"{self.settings.remote_host}/synthesize",
                json={"text": text, "voice": voice, "speed": speed},
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"Remote TTS error: {error_text}")
                    return np.array([], dtype=np.float32)

                data = await resp.json()

                # Decode base64 audio data
                audio_bytes = base64.b64decode(data["audio"])
                audio = np.frombuffer(audio_bytes, dtype=np.float32)

                return audio

        except asyncio.TimeoutError:
            logger.error(
                f"Remote TTS timed out after {self.settings.remote_timeout}s"
            )
            return np.array([], dtype=np.float32)

        except Exception as e:
            logger.error(f"Remote TTS request failed: {e}")
            return np.array([], dtype=np.float32)

    async def synthesize_to_result(
        self,
        text: str,
        voice: str | None = None,
        speed: float | None = None,
    ) -> TTSResult:
        """Synthesize text to TTSResult with metadata."""
        audio = await self.synthesize(text, voice, speed)

        return TTSResult(
            audio=audio,
            sample_rate=self._sample_rate,
            duration_seconds=len(audio) / self._sample_rate if len(audio) > 0 else 0,
            text=text,
        )

    @property
    def sample_rate(self) -> int:
        """Get the output sample rate."""
        return self._sample_rate


def create_tts(settings: TTSSettings | None = None) -> KokoroTTS | RemoteTTS:
    """Factory function to create the appropriate TTS instance.

    Creates either local KokoroTTS or RemoteTTS based on settings.mode.

    Args:
        settings: TTS settings. If None, uses defaults.

    Returns:
        TTS instance (KokoroTTS or RemoteTTS).
    """
    if settings is None:
        settings = TTSSettings()

    if settings.mode == "remote":
        logger.info("Using remote TTS mode (Pi #2)")
        return RemoteTTS(settings)
    else:
        logger.info("Using local TTS mode (Kokoro)")
        return KokoroTTS(settings)


# Mapping of persona/feature to voice preferences
# Valid Kokoro voices: af_bella, af_nicole, af_sarah, af_sky (American Female)
#                      am_adam, am_michael (American Male)
#                      bf_emma, bf_isabella (British Female)
#                      bm_george, bm_lewis (British Male)
VOICE_MAP = {
    # Features
    "operator": "af_bella",  # American female, warm
    "jokes": "am_adam",  # American male, energetic
    "fortune": "bf_emma",  # British female, mysterious
    "horoscope": "bf_emma",
    "trivia": "am_michael",  # Game show energy
    "time_temp": "af_sky",  # Clear, professional
    "stories": "af_nicole",  # Warm storytelling
    "compliment": "af_bella",  # Warm and supportive
    "advice": "af_sarah",  # Thoughtful
    # Personas
    "detective": "am_adam",  # American male, noir
    "grandma": "af_sarah",  # American female, older
    "robot": "am_michael",  # Can be processed for robotic effect
}


def get_voice_for_feature(feature: str | None = None, persona: str | None = None) -> str:
    """Get appropriate voice for a feature or persona.

    Args:
        feature: Feature name.
        persona: Persona name.

    Returns:
        Voice identifier string.
    """
    if persona and persona in VOICE_MAP:
        return VOICE_MAP[persona]
    if feature and feature in VOICE_MAP:
        return VOICE_MAP[feature]
    return "af_bella"  # Default voice
