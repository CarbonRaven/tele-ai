# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**tele-ai** is an AI-powered payphone project. The goal is a self-contained 90s-style payphone running a fully local AI that users can interact with for information, jokes, and services styled after 1990s telephone services.

### Target Hardware
- 2x Raspberry Pi 5 (16GB)
- Raspberry Pi AI HAT+ 2 (Hailo-10H, 40 TOPS)
- Grandstream HT801 v2 (ATA for payphone interface)
- 5-port gigabit switch
- Physical payphone

### Voice Pipeline Architecture
```
Mic → openWakeWord → Whisper (STT) → Ollama (LLM) → Piper (TTS) → Speaker
         :10400        :10300         :11434         :10200
```

The AI HAT+ 2 can accelerate Whisper and small LLMs via Hailo NPU.

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

| Component | Technology | Notes |
|-----------|------------|-------|
| Wake Word | openWakeWord | Wyoming protocol, port 10400 |
| STT | Whisper | Hailo-accelerated, port 10300 |
| LLM | Ollama / hailo-ollama | Local inference, port 11434 / 8000 |
| TTS | Piper | Fast neural TTS, port 10200 |
| Telephony | FreePBX/Asterisk | AudioSocket protocol for AI integration |
| Protocol | Wyoming | Home Assistant voice service integration |

## Documentation Standards

All documentation uses Markdown with:
- Tables for specifications and comparisons
- Code blocks with language hints for commands/configs
- Consistent heading hierarchy
- Links between related documents via relative paths
