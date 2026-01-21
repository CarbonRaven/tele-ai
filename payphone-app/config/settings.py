"""Application settings using Pydantic Settings for type safety and env var support."""

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
    """Voice Activity Detection configuration."""

    model_config = SettingsConfigDict(env_prefix="VAD_")

    # Silero VAD settings
    threshold: float = 0.5
    min_speech_duration_ms: int = 250
    min_silence_duration_ms: int = 500
    speech_pad_ms: int = 100

    # Window size for VAD (30ms chunks)
    window_size_samples: int = 512  # 512 samples at 16kHz = 32ms


class STTSettings(BaseSettings):
    """Speech-to-Text configuration."""

    model_config = SettingsConfigDict(env_prefix="STT_")

    # faster-whisper model (HuggingFace repo ID or local path)
    # Options: "tiny", "base", "small", "medium", "large-v2", "large-v3"
    #          or HuggingFace: "distil-whisper/distil-large-v3", "Systran/faster-distil-whisper-large-v3"
    model_name: str = "distil-whisper/distil-large-v3"
    device: Literal["cpu", "cuda", "auto"] = "cpu"
    compute_type: Literal["int8", "float16", "float32", "auto"] = "int8"

    # Transcription settings
    language: str = "en"
    beam_size: int = 1  # Use greedy decoding for speed
    vad_filter: bool = True
    initial_prompt: str | None = None


class LLMSettings(BaseSettings):
    """Language Model configuration."""

    model_config = SettingsConfigDict(env_prefix="LLM_")

    # Ollama settings
    host: str = "http://localhost:11434"
    model: str = "qwen2.5:3b"

    # Generation parameters
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 150  # Keep responses concise for phone
    timeout: float = 10.0  # Timeout in seconds

    # Keep model loaded
    keep_alive: str = "24h"


class TTSSettings(BaseSettings):
    """Text-to-Speech configuration."""

    model_config = SettingsConfigDict(env_prefix="TTS_")

    # Kokoro-82M settings
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
