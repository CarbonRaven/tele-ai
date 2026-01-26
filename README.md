# payphone-ai

**An AI-powered payphone running fully local voice AI, styled after 1990s telephone services.**

[![GitHub](https://img.shields.io/github/license/CarbonRaven/payphone-ai)](https://github.com/CarbonRaven/payphone-ai)

## Architecture

```
                              ┌─────────────────────────────────┐
                              │      Pi #2 (pi-ollama)          │
                              │        192.168.1.11             │
                              │                                 │
                              │   ┌─────────────────────────┐   │
                              │   │  Ollama (qwen2.5:3b)    │   │
                              │   │      Port 11434         │   │
                              │   └─────────────────────────┘   │
                              └───────────────▲─────────────────┘
                                              │ HTTP API
                                              │
┌──────────┐    ┌─────────┐    ┌──────────┐   │
│ Payphone │───▶│ HT801   │───▶│ Asterisk │───┼──────────────────────────────┐
│ (Analog) │RJ11│  ATA    │SIP │ FreePBX  │   │    Pi #1 (pi-voice)          │
└──────────┘    └─────────┘    └────┬─────┘   │      192.168.1.10            │
                                    │         │      + AI HAT+ 2             │
                              AudioSocket     │                              │
                               :9092          ▼                              │
                              ┌───────────────────────────────────────────┐  │
                              │  Silero VAD → Hailo Whisper → Kokoro TTS  │  │
                              │    (CPU)       (NPU :10300)    (CPU)      │  │
                              └───────────────────────────────────────────┘  │
                              └──────────────────────────────────────────────┘
```

## Hardware

| Component | Model | Purpose |
|-----------|-------|---------|
| Pi #1 (pi-voice) | Raspberry Pi 5 (16GB) + AI HAT+ 2 | Voice pipeline: Hailo Whisper STT, Piper TTS, VAD |
| Pi #2 (pi-ollama) | Raspberry Pi 5 (16GB) | LLM server: Standard Ollama with qwen2.5:3b |
| AI Accelerator | AI HAT+ 2 (Hailo-10H, 40 TOPS) | Whisper STT acceleration |
| ATA | Grandstream HT801 v2 | Converts analog phone to SIP |
| Network | 5-port Gigabit switch | Internal network |

## Voice Pipeline

| Component | Technology | Port | Location |
|-----------|------------|------|----------|
| Wake Word | openWakeWord | 10400 | Pi #1 |
| STT | Hailo Whisper (Wyoming) | 10300 | Pi #1 |
| LLM | Ollama (qwen2.5:3b) | 11434 | Pi #2 |
| TTS | Kokoro-82M | - | Pi #1 |
| VAD | Silero VAD | - | Pi #1 |
| Entry Point | AudioSocket | 9092 | Pi #1 |

## Repository Structure

```
tele-ai/
├── CLAUDE.md                    # Project guidance for Claude Code
├── payphone-app/                # Main application
│   ├── main.py                  # Entry point
│   ├── install.sh               # Automated installer
│   ├── SETUP.md                 # Detailed setup guide
│   ├── config/
│   │   ├── settings.py          # Pydantic settings (env vars)
│   │   └── prompts.py           # System prompts for personas
│   ├── core/
│   │   ├── audiosocket.py       # AudioSocket server
│   │   ├── pipeline.py          # Voice pipeline orchestration
│   │   └── state_machine.py     # Conversation state machine
│   ├── services/
│   │   ├── vad.py               # Silero VAD
│   │   ├── stt.py               # Hailo Whisper + faster-whisper fallback
│   │   ├── llm.py               # Ollama client
│   │   └── tts.py               # Kokoro TTS
│   └── features/
│       ├── operator.py          # Default operator persona
│       └── jokes.py             # Dial-A-Joke feature
├── documentation/               # Technical docs
│   ├── local-voice-assistant-pipeline.md
│   ├── raspberry-pi-5-ai-hat-2-whisper.md
│   ├── freepbx-ai-integrations.md
│   └── ...
├── planning/
│   └── system-architecture.md   # System design document
└── scripts/
    ├── health-monitor.py        # Hardware monitoring
    └── quick-health.sh          # Quick health check
```

## Features

- **Fully Local**: No cloud services, all processing on-device
- **Hailo NPU Acceleration**: Whisper STT offloaded to AI HAT+ 2
- **Multiple Personas**: Operator, Detective, Grandma, Robot
- **Extensible Features**: Dial-A-Joke, Fortune, Horoscope, Trivia
- **Barge-in Support**: Interrupt AI with DTMF tones
- **Telephony Integration**: FreePBX/Asterisk via AudioSocket

## Quick Start

```bash
# On Pi #1 (voice pipeline)
git clone <repo-url> ~/tele-ai
cd ~/tele-ai/payphone-app
./install.sh
sudo systemctl start payphone

# On Pi #2 (LLM server)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:3b
```

See [payphone-app/SETUP.md](payphone-app/SETUP.md) for detailed installation instructions.

## Target Latency

| Stage | Target |
|-------|--------|
| VAD → STT | <500ms |
| STT → LLM | <1s |
| LLM → TTS | <500ms |
| **Total** | **1.5-2s** |

## Documentation

- [Setup Guide](payphone-app/SETUP.md) - Complete installation instructions
- [System Architecture](planning/system-architecture.md) - Technical design
- [Voice Pipeline Guide](documentation/local-voice-assistant-pipeline.md) - Pipeline details
- [AI HAT+ 2 Whisper](documentation/raspberry-pi-5-ai-hat-2-whisper.md) - Hailo STT setup
- [FreePBX Integration](documentation/freepbx-ai-integrations.md) - Telephony setup

## License

MIT License
