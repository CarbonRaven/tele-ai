# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**payphone-ai** is an AI-powered payphone project. The goal is a self-contained 90s-style payphone running a fully local AI that users can interact with for information, jokes, and services styled after 1990s telephone services.

**Repository**: https://github.com/CarbonRaven/payphone-ai

### Target Hardware
- **Pi #1 (pi-voice)**: Raspberry Pi 5 (16GB) + AI HAT+ 2 (Hailo-10H)
- **Pi #2 (pi-ollama)**: Raspberry Pi 5 (16GB) - standard, no HAT
- Grandstream HT801 v2 (ATA for payphone interface)
- 5-port gigabit switch
- Physical payphone

### Dual-Pi Architecture
```
Payphone → HT801 ATA (SIP) → Asterisk/FreePBX
                                     │
                                AudioSocket :9092
                                     │
┌────────────────────────────────────┼────────────────────────────────────┐
│ Pi #1 (pi-voice) 10.10.10.10      │         + AI HAT+ 2               │
│                                    ▼                                    │
│              Silero VAD → Whisper (STT) ──────────→ Kokoro (TTS)       │
│               (CPU)       :10300 (Hailo)               (CPU)           │
│                                │                         ▲              │
│                                ▼                         │              │
└────────────────────────────────┼─────────────────────────┼──────────────┘
                                 │ HTTP                     │
                                 ▼                          │
┌────────────────────────────────────────────────────────────┼─────────────┐
│ Pi #2 (pi-ollama) 10.10.10.11                             │             │
│                     Ollama (LLM) ─────────────────────────┘             │
│                       :11434 / qwen3:4b                                 │
└─────────────────────────────────────────────────────────────────────────┘
```

**AI HAT+ 2 Usage**: The Hailo-10H NPU accelerates Whisper STT on Pi #1, freeing the CPU for audio processing. Standard Ollama runs on Pi #2 for better model flexibility (3B+ models).

## Repository Structure

- `payphone-app/` - Main Python application (see Code Architecture below)
- `documentation/` - Technical documentation (26 files)
  - `project-overview.md` - Architecture and service catalog
  - `local-voice-assistant-pipeline.md` - End-to-end voice pipeline guide
  - `raspberry-pi-5-ai-hat-2-*.md` - Hailo AI HAT+ 2 documentation
  - `raspberry-pi-5-openwakeword.md` - Wake word detection
  - `freepbx-*.md` - FreePBX/Asterisk telephony integration
  - `network-configuration.md` - Dual-Pi network setup
  - `*-research*.md` - LLM, STT, and model research
- `planning/` - Design and feature planning
  - `system-architecture.md` - System design document
  - `features-list.md` - Full feature roadmap with phone numbers
  - `phone-book-content.md` - Physical phone book content draft
- `scripts/` - Operational tooling
  - `asterisk/` - Asterisk/FreePBX configuration
  - `health-monitor.py` - System health monitoring
  - `payphone-ops.sh` - Operations management script
- `research/` - Reference materials and model research
- `hardware.txt` - Hardware inventory

## Key Technologies

| Component | Technology | Location | Notes |
|-----------|------------|----------|-------|
| Wake Word | openWakeWord | Pi #1 | Wyoming protocol, port 10400 |
| STT | Moonshine/Whisper | Pi #1 | Moonshine (5x faster) or Hailo-accelerated Whisper |
| LLM | Ollama | Pi #2 | Standard Ollama, qwen3:4b, port 11434 |
| TTS | Kokoro-82M | Pi #1 | Fast neural TTS, 24kHz output |
| VAD | Silero VAD | Pi #1 | CPU-based voice activity detection |
| Telephony | FreePBX/Asterisk | Pi #1 | AudioSocket protocol for AI integration |
| Protocol | Wyoming | Pi #1 | Home Assistant voice service integration |

## Code Architecture

### Voice Pipeline (`payphone-app/`)

```
main.py                    # Application entry point, service initialization
pyproject.toml             # Package config, dependencies, optional extras
install.sh                 # Automated installer
tts_server.py              # Standalone TTS server (for Pi #2 offloading)
├── config/
│   ├── settings.py        # Pydantic Settings v2 with env var support
│   ├── phone_directory.py # 44 phone numbers → features/personas (TypedDict entries)
│   └── prompts.py         # LLM system prompts (35 features, 9 personas)
├── core/
│   ├── audiosocket.py     # Asterisk AudioSocket protocol handler
│   ├── audio_processor.py # Sample rate conversion, telephone filter
│   ├── phone_router.py    # Number dialed → feature routing, DTMF shortcuts
│   ├── pipeline.py        # VAD → STT → LLM → TTS orchestration
│   ├── session.py         # Per-call state management
│   └── state_machine.py   # Conversation flow control
├── services/
│   ├── vad.py             # Silero VAD v5 with thread-safe async reset
│   ├── stt.py             # Moonshine (5x faster) + Wyoming/Hailo + faster-whisper
│   ├── llm.py             # Ollama client with streaming timeout
│   └── tts.py             # Kokoro-82M synthesis
├── features/
│   ├── base.py            # Feature base classes
│   ├── registry.py        # Auto-discovery decorator pattern
│   ├── operator.py        # Default operator persona
│   └── jokes.py           # Dial-A-Joke feature
├── tests/
│   └── test_phone_routing.py  # Phone directory and routing tests
├── scripts/
│   └── generate_audio.py  # Generates 17 telephone sound effects (Bellcore GR-506)
└── audio/                 # Audio assets (music/, prompts/, sounds/)
    └── sounds/            # 17 generated WAV files (8kHz 16-bit PCM mono)
```

### Key Patterns

| Pattern | Location | Purpose |
|---------|----------|---------|
| Pydantic Settings | `config/settings.py` | Type-safe config with env var support |
| Phone Directory | `config/phone_directory.py` | 44-number TypedDict registry with greetings |
| Phone Router | `core/phone_router.py` | Number lookup, DTMF shortcuts, birthday regex |
| Feature Registry | `features/registry.py` | `@FeatureRegistry.register()` decorator |
| Wyoming Protocol | `services/stt.py` | Binary framing for audio, JSON for events |
| Sentence Buffer | `services/llm.py` | Regex-based streaming TTS chunking |
| Audio Buffer | `core/audio_processor.py` | Memory-bounded sample accumulation |
| SIT Tri-tone | `core/state_machine.py` | Plays `sit_intercept.wav` before "not in service" TTS |

### Performance Optimizations

- **Wyoming binary protocol**: Audio sent as binary frames (not base64) for 33% less overhead
- **Exponential backoff**: Wyoming reconnection with 0.5s → 4s backoff
- **Thread-safe VAD**: `reset_async()` acquires lock before model state reset
- **Streaming timeout**: LLM protected against indefinite hangs
- **Dynamic pacing**: Audio playback paced by actual chunk duration
- **O(n) string building**: LLM streaming uses list + join instead of O(n²) concatenation
- **Incremental sentence detection**: Regex searches only new content, not entire buffer
- **Pre-allocated audio arrays**: Streaming STT uses doubling strategy for O(n) total copies
- **Batched Wyoming writes**: Audio chunks written without drain, single flush at end
- **Lazy dtype conversion**: TTS/resampling skip copy when dtype already matches

## Build & Test

```bash
cd payphone-app
pip install -e ".[dev]"       # Install with dev dependencies
pytest tests/                 # Run tests
python3 -c "import ast; ast.parse(open('config/prompts.py').read())"  # Quick syntax check
python3 scripts/generate_audio.py   # Regenerate telephone sound effects
```

The app requires Python 3.10+ and uses `pydantic-settings` for configuration via environment variables (see `config/settings.py` and `.env.example`).

## Audio Assets

`payphone-app/audio/sounds/` contains 17 programmatically generated telephone sound effects based on Bellcore GR-506 specs. All files are 8kHz 16-bit PCM WAV mono, matching the pipeline's `output_sample_rate`.

To regenerate: `cd payphone-app && python3 scripts/generate_audio.py`

The `play_sound()` method in `core/pipeline.py` loads these files, resamples if needed, applies the telephone bandpass filter (300-3400 Hz), and sends via AudioSocket. Currently the SIT intercept tri-tone (`sit_intercept.wav`) is wired into both invalid-number paths in `state_machine.py`.

## Hardware Testing

`payphone-app/HARDWARE_TEST_PLAN.md` contains a 138-test plan across 9 phases for validating the system on hardware, including stress tests and adversarial scenarios to break features. See that file for the full plan and results template.

## Documentation Standards

All documentation uses Markdown with:
- Tables for specifications and comparisons
- Code blocks with language hints for commands/configs
- Consistent heading hierarchy
- Links between related documents via relative paths
