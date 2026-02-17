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

    model_config = SettingsConfigDict(env_prefix="AUDIO_", env_file=".env", env_file_encoding="utf-8", extra="ignore")

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

    Uses Silero VAD v5 (v6.2 recommended upgrade) - optimized for telephony with native 8kHz support.
    Settings tuned for conversational telephone AI (January 2026 research).

    Alternative: TEN VAD (via sherpa-onnx) for potentially lower latency.
    """

    model_config = SettingsConfigDict(env_prefix="VAD_", env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Silero VAD v5 settings (v6.2 recommended upgrade) - optimized for telephony
    threshold: float = 0.5  # Balanced sensitivity for phone audio
    min_speech_duration_ms: int = 250  # Minimum speech to trigger
    min_silence_duration_ms: int = 800  # Telephony standard for turn-taking
    speech_pad_ms: int = 300  # Prevent clipping end of utterance

    # Window size for VAD (32ms chunks at 16kHz)
    window_size_samples: int = 512  # 512 samples at 16kHz = 32ms

    # Maximum utterance duration to prevent runaway recordings
    max_utterance_seconds: int = 30

    # Voice barge-in settings
    barge_in_enabled: bool = True  # Master switch for voice barge-in
    barge_in_threshold: float = 0.8  # Higher than normal to reduce echo false positives


class STTSettings(BaseSettings):
    """Speech-to-Text configuration.

    Supports three backends:
    1. Hailo-accelerated Whisper via Wyoming protocol (most accurate on telephone audio)
    2. Moonshine v2 - native streaming, ~2x better WER than Whisper-Base, ONNX on CPU
    3. faster-whisper for CPU-only last resort

    Backend priority (when backend="auto"):
    1. Wyoming/Hailo (if available) - NPU-accelerated Whisper
    2. Moonshine v2 (if installed) - best WER in class, native streaming, CPU via ONNX
    3. faster-whisper (last resort) - CPU based

    Moonshine v2 models (February 2026 - arxiv.org/abs/2602.12241):
    - "moonshine/tiny" (34M params) - 80-150ms latency, 12.01% WER
    - "moonshine/small" (123M params) - 250-450ms latency, 7.84% WER (recommended)
    - "moonshine/medium" (245M params) - 450-800ms latency, 6.65% WER

    Legacy Moonshine v1 (HuggingFace transformers):
    - "UsefulSensors/moonshine-tiny" (27M) - original, via transformers

    Whisper models:
    - "tiny" (~0.7-1.2s latency for 3-5s audio on Pi 5)
    - "base" (~1.8-3.0s latency)
    - "large-v3-turbo" (best accuracy)
    """

    model_config = SettingsConfigDict(env_prefix="STT_", env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Backend selection: "moonshine", "hailo", "whisper", or "auto"
    # "auto" tries hailo/wyoming -> moonshine -> faster-whisper
    backend: Literal["moonshine", "hailo", "whisper", "auto"] = "auto"

    # Device for model inference: "cpu", "cuda", or "auto"
    device: Literal["cpu", "cuda", "auto"] = "auto"

    # Moonshine settings (CPU fallback via ONNX runtime)
    # Moonshine v2 (ONNX): "moonshine/tiny", "moonshine/small", "moonshine/medium"
    # Legacy v1 (transformers): "UsefulSensors/moonshine-tiny", "UsefulSensors/moonshine-base"
    moonshine_model: str = "moonshine/small"

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

    Standard Ollama runs on Pi #2 (10.10.10.11) for better model flexibility.

    Recommended models (February 2026):
    - Recommended: smollm3:3b (IFEval 76.7, ~5-5.5 TPS, best instruction-following)
    - Fallback: qwen3:4b-instruct (~4.5 TPS, best general knowledge/reasoning)
    - Speed: gemma3:1b (~11.6 TPS, lowest latency)

    SmolLM3-3B scores 8 points above Qwen3-4B on IFEval (instruction-following),
    which matters most for a phone operator that must follow persona instructions
    precisely. Being 3B vs 4B, it's also ~10-20% faster.

    NOTE: If using qwen3 as fallback, use qwen3:4b-instruct (NOT qwen3:4b).
    The default qwen3:4b has mandatory thinking mode that wastes all tokens.

    Use Q5_K_M quantization for best quality/speed balance with 16GB RAM.
    """

    model_config = SettingsConfigDict(env_prefix="LLM_", env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Ollama settings - default to Pi #2 (pi-ollama)
    # Change to localhost:11434 if running single-Pi setup
    host: str = "http://10.10.10.11:11434"

    # SmolLM3-3B: best instruction-following (IFEval 76.7) in 3-4B class
    # Alternatives: qwen3:4b-instruct (reasoning), gemma3:1b (speed)
    model: str = "smollm3:3b"

    # Generation parameters
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 150  # Keep responses concise for phone
    timeout: float = 10.0  # Overall timeout in seconds

    # Streaming timeout settings
    # First token can take longer due to model loading/prompt processing
    first_token_timeout: float = 25.0  # Timeout for first token (cold-start prompt eval ~20s on Pi 5)
    inter_token_timeout: float = 5.0  # Timeout between subsequent tokens

    # Streaming: overlap LLM generation with TTS for lower perceived latency
    streaming_enabled: bool = True

    # Keep model loaded (prevent unloading between calls)
    keep_alive: str = "24h"


class TTSSettings(BaseSettings):
    """Text-to-Speech configuration.

    Supports two modes:
    1. Local: Kokoro-82M v1.0 runs on Pi #1 (default)
    2. Remote: TTS service runs on Pi #2, reducing Pi #1 CPU load

    Kokoro v1.0 (February 2026): 54 voices, voice blending, ONNX optimized.
    For better performance, use Int8 quantized model (2x speedup).
    Speed fallback: Piper v1.4.1 (10-20x real-time, ARM64 pip wheel).

    Set mode="remote" and configure remote_host to offload TTS to Pi #2.
    """

    model_config = SettingsConfigDict(env_prefix="TTS_", env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # TTS mode: "local" or "remote"
    mode: Literal["local", "remote"] = "local"

    # Remote TTS server (when mode="remote")
    # Run tts_server.py on Pi #2 to handle synthesis
    remote_host: str = "http://10.10.10.11:10200"
    remote_timeout: float = 10.0  # Timeout for remote TTS calls

    # Kokoro-82M settings (for local mode or remote server)
    # Use quantized models for better performance:
    # - kokoro-v1.0.onnx (default, FP32)
    # - kokoro-v1.0-int8.onnx (2x faster, minimal quality loss)
    # - kokoro-v1.0-int4.onnx (4x faster, test quality for your use case)
    model_path: str = "kokoro-v1.0.onnx"
    voices_path: str = "voices-v1.0.bin"
    voice: str = "af_nova"  # Default voice (see services/tts.py VOICE_MAP for all 54 v1.0 voices)

    # Synthesis settings
    speed: float = 1.0

    # Sentence chunking for streaming
    min_sentence_length: int = 10
    sentence_delimiters: str = ".!?,"


class TimeoutSettings(BaseSettings):
    """Timeout configuration for conversation flow."""

    model_config = SettingsConfigDict(env_prefix="TIMEOUT_", env_file=".env", env_file_encoding="utf-8", extra="ignore")

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
    """Get cached settings instance.

    Uses lru_cache to ensure a single Settings instance is shared across
    the application. Call get_settings.cache_clear() to reload settings.
    """
    return Settings()
