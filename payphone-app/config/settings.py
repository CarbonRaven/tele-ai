"""Application settings using Pydantic Settings for type safety and env var support."""

__all__ = [
    "AudioSettings",
    "VADSettings",
    "STTSettings",
    "LLMSettings",
    "TTSSettings",
    "TimeoutSettings",
    "Settings",
    "get_settings",
]

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AudioSettings(BaseSettings):
    """Audio processing configuration."""

    model_config = SettingsConfigDict(env_prefix="AUDIO_")

    # AudioSocket settings
    audiosocket_host: str = "0.0.0.0"
    audiosocket_port: int = 9092

    # Asterisk sends 8kHz signed 16-bit PCM
    input_sample_rate: int = 8000
    input_channels: int = 1
    input_sample_width: int = 2  # 16-bit = 2 bytes

    # STT expects 16kHz
    stt_sample_rate: int = 16000

    # TTS outputs 24kHz (Kokoro)
    tts_output_rate: int = 24000

    # Output to Asterisk at 8kHz
    output_sample_rate: int = 8000

    # Telephone bandpass filter (300-3400 Hz)
    telephone_lowcut: float = 300.0
    telephone_highcut: float = 3400.0

    # Audio chunk size (320 bytes = 20ms at 8kHz mono 16-bit)
    chunk_size: int = 320


class VADSettings(BaseSettings):
    """Voice Activity Detection configuration.

    Uses Silero VAD v5 - optimized for telephony with native 8kHz support.
    Settings tuned for conversational telephone AI (January 2026 research).

    Alternative: TEN VAD (via sherpa-onnx) for potentially lower latency.
    """

    model_config = SettingsConfigDict(env_prefix="VAD_")

    # Silero VAD v5 settings - optimized for telephony
    threshold: float = 0.5  # Balanced sensitivity for phone audio
    min_speech_duration_ms: int = 250  # Minimum speech to trigger
    min_silence_duration_ms: int = 800  # Telephony standard for turn-taking
    speech_pad_ms: int = 300  # Prevent clipping end of utterance

    # Window size for VAD (32ms chunks at 16kHz)
    window_size_samples: int = 512  # 512 samples at 16kHz = 32ms

    # Maximum utterance duration to prevent runaway recordings
    max_utterance_seconds: int = 30


class STTSettings(BaseSettings):
    """Speech-to-Text configuration.

    Supports three backends:
    1. Moonshine - 5x faster than Whisper tiny, optimized for edge (recommended)
    2. Hailo-accelerated Whisper via Wyoming protocol (for Pi #1 with AI HAT+)
    3. faster-whisper for CPU-only fallback

    Backend priority (when backend="auto"):
    1. Moonshine (if installed) - fastest option
    2. Wyoming/Hailo (if available) - NPU accelerated
    3. faster-whisper (fallback) - CPU based

    Moonshine models (January 2026):
    - "moonshine-tiny" (27M params) - 5x faster than Whisper tiny, recommended
    - "moonshine-base" (61M params) - better accuracy, still fast

    Whisper models:
    - "tiny" (~0.7-1.2s latency for 3-5s audio on Pi 5)
    - "base" (~1.8-3.0s latency)
    - "large-v3-turbo" (best accuracy)
    """

    model_config = SettingsConfigDict(env_prefix="STT_")

    # Backend selection: "moonshine", "hailo", "whisper", or "auto"
    # "auto" tries moonshine -> hailo/wyoming -> faster-whisper
    backend: Literal["moonshine", "hailo", "whisper", "auto"] = "auto"

    # Device for model inference: "cpu", "cuda", or "auto"
    device: Literal["cpu", "cuda", "auto"] = "auto"

    # Moonshine settings (recommended - 5x faster than Whisper tiny)
    # Models: "UsefulSensors/moonshine-tiny" (27M), "UsefulSensors/moonshine-base" (61M)
    moonshine_model: str = "UsefulSensors/moonshine-tiny"

    # Wyoming server settings (for Hailo-accelerated Whisper on Pi #1)
    wyoming_host: str = "localhost"
    wyoming_port: int = 10300

    # faster-whisper model (fallback when other backends unavailable)
    # Speed options: "tiny" (fastest), "base" (balanced)
    # Quality options: "large-v3-turbo" (best accuracy, 8x faster than large-v3)
    whisper_model: str = "tiny"
    compute_type: Literal["int8", "float16", "float32", "auto"] = "int8"

    # Transcription settings
    language: str = "en"
    beam_size: int = 1  # Use greedy decoding for speed
    vad_filter: bool = True
    initial_prompt: str | None = None


class LLMSettings(BaseSettings):
    """Language Model configuration.

    Standard Ollama runs on Pi #2 (192.168.1.11) for better model flexibility.

    Recommended models (January 2026):
    - Speed priority: llama3.2:3b-instruct-q4_K_M (~5-6 TPS on Pi 5)
    - Quality priority: ministral:8b (~2-3 TPS, best conversational quality)
    - Balanced: qwen2.5:7b-instruct-q4_K_M (~2 TPS, strong logic)

    Use Q4_K_M quantization for best speed/quality balance on Pi 5.
    """

    model_config = SettingsConfigDict(env_prefix="LLM_")

    # Ollama settings - default to Pi #2 (pi-ollama)
    # Change to localhost:11434 if running single-Pi setup
    host: str = "http://192.168.1.11:11434"

    # Default to Llama 3.2 3B for best latency in voice applications
    # Use ministral:8b for better quality, qwen2.5:7b for strong logic
    model: str = "llama3.2:3b-instruct-q4_K_M"

    # Generation parameters
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 150  # Keep responses concise for phone
    timeout: float = 10.0  # Overall timeout in seconds

    # Streaming timeout settings
    # First token can take longer due to model loading/prompt processing
    first_token_timeout: float = 15.0  # Timeout for first token
    inter_token_timeout: float = 5.0  # Timeout between subsequent tokens

    # Keep model loaded (prevent unloading between calls)
    keep_alive: str = "24h"


class TTSSettings(BaseSettings):
    """Text-to-Speech configuration.

    Supports two modes:
    1. Local: Kokoro-82M runs on Pi #1 (default)
    2. Remote: TTS service runs on Pi #2, reducing Pi #1 CPU load

    Kokoro-82M remains the gold standard for edge TTS (January 2026).
    For better performance, use Int8 quantized model (2x speedup).

    Future: Qwen3-TTS (0.6B) offers ~97ms latency and voice cloning.
    Set mode="remote" and configure remote_host to offload TTS to Pi #2.
    """

    model_config = SettingsConfigDict(env_prefix="TTS_")

    # TTS mode: "local" or "remote"
    mode: Literal["local", "remote"] = "local"

    # Remote TTS server (when mode="remote")
    # Run tts_server.py on Pi #2 to handle synthesis
    remote_host: str = "http://192.168.1.11:10200"
    remote_timeout: float = 10.0  # Timeout for remote TTS calls

    # Kokoro-82M settings (for local mode or remote server)
    # Use quantized models for better performance:
    # - kokoro-v1.0.onnx (default, FP32)
    # - kokoro-v1.0-int8.onnx (2x faster, minimal quality loss)
    # - kokoro-v1.0-int4.onnx (4x faster, test quality for your use case)
    model_path: str = "kokoro-v1.0.onnx"
    voices_path: str = "voices-v1.0.bin"
    voice: str = "af_bella"  # American female voice (valid: af_bella, af_nicole, af_sarah, af_sky)

    # Synthesis settings
    speed: float = 1.0

    # Sentence chunking for streaming
    min_sentence_length: int = 10
    sentence_delimiters: str = ".!?,"


class TimeoutSettings(BaseSettings):
    """Timeout configuration for conversation flow."""

    model_config = SettingsConfigDict(env_prefix="TIMEOUT_")

    silence_prompt: int = 10  # Seconds before "Are you still there?"
    silence_goodbye: int = 30  # Additional seconds before auto-hangup
    dtmf_inter_digit: int = 3  # Seconds between DTMF digits
    feature_idle: int = 60  # Seconds idle in feature before menu return
    max_call_duration: int = 1800  # 30 minutes max


class Settings(BaseSettings):
    """Main application settings aggregating all sub-settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Sub-settings
    audio: AudioSettings = Field(default_factory=AudioSettings)
    vad: VADSettings = Field(default_factory=VADSettings)
    stt: STTSettings = Field(default_factory=STTSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    tts: TTSSettings = Field(default_factory=TTSSettings)
    timeouts: TimeoutSettings = Field(default_factory=TimeoutSettings)

    # Application settings
    debug: bool = False
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
