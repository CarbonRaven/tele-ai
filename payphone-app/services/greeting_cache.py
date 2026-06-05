"""Persistent cache for fully processed greeting audio.

The cache key is the SHA-256 hex digest of a deterministic null-delimited
string composed from: greeting text, voice, speed, and the basename of the
configured TTS model path. This ensures voice, speed, or model changes
naturally invalidate old cache entries.
"""

__all__ = [
    "GreetingCache",
]

import hashlib
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from config.greetings import OPERATOR_GREETING
from config.settings import TTSSettings
from services.tts import TTSProtocol, get_voice_for_feature

logger = logging.getLogger(__name__)


class GreetingCache:
    """Persistent cache of telephone-ready greeting audio.

    Greeting cache files are small raw PCM payloads, so synchronous reads and
    writes are acceptable here. Synthesis remains async and dominates latency.
    """

    def __init__(
        self,
        tts: TTSProtocol,
        audio_processor: Any,
        settings: TTSSettings,
        cache_dir: Path | None = None,
    ):
        self.tts = tts
        self.audio_processor = audio_processor
        self.settings = settings
        self.cache_dir = cache_dir or (
            Path(__file__).resolve().parent.parent / "cache" / "greetings"
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def make_key(self, text: str, voice: str, speed: float) -> str:
        """Build the stable cache key for a greeting variant.

        Args:
            text: Greeting text.
            voice: Resolved TTS voice name.
            speed: TTS speed.

        Returns:
            SHA-256 hex digest for the greeting variant.
        """
        model_basename = Path(self.settings.model_path).name
        material = "\x00".join(
            [
                text,
                voice,
                f"{float(speed):.6f}",
                model_basename,
            ]
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    async def get_or_synthesize(self, text: str, voice: str, speed: float) -> bytes:
        """Load a processed greeting from cache or synthesize it on demand.

        Args:
            text: Greeting text.
            voice: Resolved TTS voice name.
            speed: TTS speed.

        Returns:
            8kHz signed 16-bit PCM bytes ready to send to Asterisk.
        """
        cache_path = self.cache_dir / f"{self.make_key(text, voice, speed)}.pcm"

        if cache_path.exists():
            try:
                cached_bytes = cache_path.read_bytes()
                if cached_bytes:
                    return cached_bytes
                logger.warning(f"Greeting cache file was empty, rebuilding: {cache_path}")
            except OSError as exc:
                logger.warning(f"Failed to read greeting cache {cache_path}: {exc}")

        audio = await self.tts.synthesize(text, voice=voice, speed=speed)
        if len(audio) == 0:
            return b""

        output_bytes = self.audio_processor.process_for_output(
            audio,
            from_rate=self.tts.sample_rate,
        )
        if not output_bytes:
            return b""

        try:
            self._write_atomic(cache_path, output_bytes)
        except OSError as exc:
            logger.warning(f"Failed to persist greeting cache {cache_path}: {exc}")

        return output_bytes

    async def prime_operator_greeting(self) -> bytes:
        """Warm the cache for the default operator greeting."""
        voice = get_voice_for_feature(feature="operator")
        return await self.get_or_synthesize(
            OPERATOR_GREETING,
            voice,
            self.settings.speed,
        )

    def _write_atomic(self, path: Path, payload: bytes) -> None:
        """Persist greeting bytes atomically in the cache directory.

        Args:
            path: Final cache file path.
            payload: Raw PCM payload to persist.
        """
        with tempfile.NamedTemporaryFile(
            dir=path.parent,
            prefix=f"{path.stem}.",
            suffix=".tmp",
            delete=False,
        ) as tmp_file:
            tmp_file.write(payload)
            tmp_name = tmp_file.name

        try:
            os.replace(tmp_name, path)
        except Exception:
            Path(tmp_name).unlink(missing_ok=True)
            raise
