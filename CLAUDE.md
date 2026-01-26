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
│ Pi #1 (pi-voice) 192.168.1.10 - AI HAT+ 2                               │
│                                                                         │
│  Mic → openWakeWord → Whisper (STT) ──────────────→ Piper (TTS) → Speaker│
│           :10400      :10300 (Hailo)                  :10200            │
│                              │                           ▲              │
│                              ▼                           │              │
└──────────────────────────────┼───────────────────────────┼──────────────┘
                               │ HTTP                      │
                               ▼                           │
┌──────────────────────────────────────────────────────────┼──────────────┐
│ Pi #2 (pi-ollama) 192.168.1.11                           │              │
│                                                          │              │
│                    Ollama (LLM) ─────────────────────────┘              │
│                      :11434                                             │
│                   qwen2.5:3b                                            │
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
| STT | Whisper (Hailo) | Pi #1 | Hailo-10H accelerated, port 10300 |
| LLM | Ollama | Pi #2 | Standard Ollama, qwen2.5:3b, port 11434 |
| TTS | Piper | Pi #1 | Fast neural TTS, port 10200 |
| VAD | Silero VAD | Pi #1 | CPU-based voice activity detection |
| Telephony | FreePBX/Asterisk | Pi #1 | AudioSocket protocol for AI integration |
| Protocol | Wyoming | Pi #1 | Home Assistant voice service integration |

## Documentation Standards

All documentation uses Markdown with:
- Tables for specifications and comparisons
- Code blocks with language hints for commands/configs
- Consistent heading hierarchy
- Links between related documents via relative paths
