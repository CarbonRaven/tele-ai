"""Tests for the persistent greeting audio cache."""

from pathlib import Path

import numpy as np
import pytest

from config.settings import TTSSettings
from services.greeting_cache import GreetingCache


class FakeTTS:
    """Minimal async TTS fake for greeting cache tests."""

    def __init__(self, sample_rate: int = 24000):
        self._sample_rate = sample_rate
        self.calls: list[tuple[str, str | None, float | None]] = []

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        speed: float | None = None,
    ) -> np.ndarray:
        self.calls.append((text, voice, speed))
        return np.array([0.0, 0.25, -0.25, 0.5], dtype=np.float32)


class FakeAudioProcessor:
    """Deterministic processor fake for cache persistence tests."""

    def __init__(self):
        self.calls: list[tuple[np.ndarray, int]] = []

    def process_for_output(self, audio: np.ndarray, from_rate: int) -> bytes:
        self.calls.append((audio.copy(), from_rate))
        return b"\x01\x02telephone"


@pytest.mark.asyncio
async def test_make_key_stability_and_invalidation(tmp_path: Path):
    """Cache keys should be stable and change with relevant config."""
    tts = FakeTTS()
    processor = FakeAudioProcessor()
    settings_a = TTSSettings(model_path="/models/kokoro-v1.0.onnx", speed=1.0)
    settings_b = TTSSettings(model_path="/other/kokoro-fast.onnx", speed=1.0)

    cache_a = GreetingCache(tts, processor, settings_a, cache_dir=tmp_path / "a")
    cache_b = GreetingCache(tts, processor, settings_b, cache_dir=tmp_path / "b")

    key_1 = cache_a.make_key("Hello", "af_nova", 1.0)
    key_2 = cache_a.make_key("Hello", "af_nova", 1.0)

    assert key_1 == key_2
    assert key_1 != cache_a.make_key("Hello", "bf_emma", 1.0)
    assert key_1 != cache_a.make_key("Hello", "af_nova", 1.1)
    assert key_1 != cache_b.make_key("Hello", "af_nova", 1.0)


@pytest.mark.asyncio
async def test_get_or_synthesize_writes_processed_pcm(tmp_path: Path):
    """Cache miss should synthesize, process, and persist a PCM payload."""
    tts = FakeTTS()
    processor = FakeAudioProcessor()
    settings = TTSSettings(model_path="/models/kokoro-v1.0.onnx", speed=1.0)
    cache = GreetingCache(tts, processor, settings, cache_dir=tmp_path / "greetings")

    payload = await cache.get_or_synthesize("Hello there", "af_nova", 1.0)
    cache_path = (tmp_path / "greetings" / f"{cache.make_key('Hello there', 'af_nova', 1.0)}.pcm")

    assert payload == b"\x01\x02telephone"
    assert len(tts.calls) == 1
    assert len(processor.calls) == 1
    assert cache_path.read_bytes() == payload


@pytest.mark.asyncio
async def test_get_or_synthesize_reads_cached_file_without_resynthesizing(tmp_path: Path):
    """Second fetch should hit disk cache and skip TTS synthesis."""
    tts = FakeTTS()
    processor = FakeAudioProcessor()
    settings = TTSSettings(model_path="/models/kokoro-v1.0.onnx", speed=1.0)
    cache = GreetingCache(tts, processor, settings, cache_dir=tmp_path / "greetings")

    first = await cache.get_or_synthesize("Welcome back", "af_nova", 1.0)
    second = await cache.get_or_synthesize("Welcome back", "af_nova", 1.0)

    assert first == second
    assert len(tts.calls) == 1
    assert len(processor.calls) == 1
