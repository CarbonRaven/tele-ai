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
┌─────────────────────────────────────────────────────────────────────────┐
│ Pi #1 (pi-voice) 10.10.10.10 - AI HAT+ 2                               │
│                                                                         │
│  Mic → openWakeWord → Whisper (STT) ──────────────→ Kokoro (TTS) → Speaker│
│           :10400      :10300 (Hailo)                  :10200            │
│                              │                           ▲              │
│                              ▼                           │              │
└──────────────────────────────┼───────────────────────────┼──────────────┘
                               │ HTTP                      │
                               ▼                           │
┌──────────────────────────────────────────────────────────┼──────────────┐
│ Pi #2 (pi-ollama) 10.10.10.11                           │              │
│                                                          │              │
│                    Ollama (LLM) ─────────────────────────┘              │
│                      :11434                                             │
│                   qwen3:4b                                              │
└─────────────────────────────────────────────────────────────────────────┘
```

**AI HAT+ 2 Usage**: The Hailo-10H NPU accelerates Whisper STT on Pi #1, freeing the CPU for audio processing. Standard Ollama runs on Pi #2 for better model flexibility (3B+ models).

## Repository Structure

- `documentation/` - Technical documentation for all components
  - `raspberry-pi-5-overview.md` - Main index for Pi 5 docs
  - `local-voice-assistant-pipeline.md` - End-to-end voice pipeline guide
  - `raspberry-pi-5-ai-hat-2-*.md` - Hailo AI HAT+ 2 documentation
  - `raspberry-pi-5-piper-tts.md` - Text-to-speech
  - `raspberry-pi-5-openwakeword.md` - Wake word detection
  - `freepbx-*.md` - FreePBX/Asterisk telephony integration
- `hardware.txt` - Hardware inventory
- `project-name-ideas.md` - Branding brainstorm

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
├── config/
│   ├── settings.py        # Pydantic Settings v2 with env var support
│   └── prompts.py         # System prompts for personas/features
├── core/
│   ├── audiosocket.py     # Asterisk AudioSocket protocol handler
│   ├── audio_processor.py # Sample rate conversion, telephone filter
│   ├── pipeline.py        # VAD → STT → LLM → TTS orchestration
│   ├── session.py         # Per-call state management
│   └── state_machine.py   # Conversation flow control
├── services/
│   ├── vad.py             # Silero VAD v5 (v6.2 upgrade planned) with thread-safe async reset
│   ├── stt.py             # Moonshine (5x faster) + Wyoming/Hailo + faster-whisper
│   ├── llm.py             # Ollama client with streaming timeout
│   └── tts.py             # Kokoro-82M synthesis
└── features/
    ├── base.py            # Feature base classes
    ├── registry.py        # Auto-discovery decorator pattern
    ├── operator.py        # Default operator persona
    └── jokes.py           # Dial-A-Joke feature
```

### Key Patterns

| Pattern | Location | Purpose |
|---------|----------|---------|
| Pydantic Settings | `config/settings.py` | Type-safe config with env var support |
| Feature Registry | `features/registry.py` | `@FeatureRegistry.register()` decorator |
| Wyoming Protocol | `services/stt.py` | Binary framing for audio, JSON for events |
| Sentence Buffer | `services/llm.py` | Regex-based streaming TTS chunking |
| Audio Buffer | `core/audio_processor.py` | Memory-bounded sample accumulation |

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

## Documentation Standards

All documentation uses Markdown with:
- Tables for specifications and comparisons
- Code blocks with language hints for commands/configs
- Consistent heading hierarchy
- Links between related documents via relative paths
