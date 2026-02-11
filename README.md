# payphone-ai

**An AI-powered payphone running fully local voice AI, styled after 1990s telephone services.**

[![GitHub](https://img.shields.io/github/license/CarbonRaven/payphone-ai)](https://github.com/CarbonRaven/payphone-ai)

## Architecture

```
                              ┌─────────────────────────────────┐
                              │      Pi #2 (pi-ollama)          │
                              │        10.10.10.11             │
                              │                                 │
                              │   ┌─────────────────────────┐   │
                              │   │  Ollama (qwen3:4b-instruct)       │   │
                              │   │      Port 11434         │   │
                              │   └─────────────────────────┘   │
                              └───────────────▲─────────────────┘
                                              │ HTTP API
                                              │
┌──────────┐    ┌─────────┐    ┌──────────┐   │
│ Payphone │───▶│ HT801   │───▶│ Asterisk │───┼──────────────────────────────┐
│ (Analog) │RJ11│  ATA    │SIP │ FreePBX  │   │    Pi #1 (pi-voice)          │
└──────────┘    └─────────┘    └────┬─────┘   │      10.10.10.10            │
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
| Pi #1 (pi-voice) | Raspberry Pi 5 (16GB) + AI HAT+ 2 | Voice pipeline: Moonshine/Whisper STT, Kokoro TTS, VAD |
| Pi #2 (pi-ollama) | Raspberry Pi 5 (16GB) | LLM server: Standard Ollama with qwen3:4b-instruct |
| AI Accelerator | AI HAT+ 2 (Hailo-10H, 40 TOPS) | Whisper STT acceleration |
| ATA | Grandstream HT801 v2 | Converts analog phone to SIP |
| Network | 5-port Gigabit switch | Internal network |

## Voice Pipeline

| Component | Technology | Port | Location |
|-----------|------------|------|----------|
| Wake Word | openWakeWord | 10400 | Pi #1 |
| STT | Moonshine (5x faster) / Whisper | 10300 | Pi #1 |
| LLM | Ollama (qwen3:4b-instruct) | 11434 | Pi #2 |
| TTS | Kokoro-82M | - | Pi #1 |
| VAD | Silero VAD v5 (pool of 3) | - | Pi #1 |
| Entry Point | AudioSocket | 9092 | Pi #1 |

**STT Backend Priority** (auto mode): Moonshine → Wyoming/Hailo → faster-whisper

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
│   │   ├── phone_directory.py   # 44 phone numbers → features/personas
│   │   └── prompts.py           # LLM system prompts (35 features, 9 personas)
│   ├── core/
│   │   ├── audiosocket.py       # AudioSocket server
│   │   ├── phone_router.py      # Number dialed → feature routing
│   │   ├── pipeline.py          # Voice pipeline orchestration
│   │   └── state_machine.py     # Conversation state machine
│   ├── services/
│   │   ├── vad.py               # Silero VAD (model pool + voice barge-in)
│   │   ├── stt.py               # Moonshine / Hailo Whisper / faster-whisper
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
- **Moonshine STT**: 5x faster than Whisper tiny with equivalent accuracy
- **Hailo NPU Fallback**: Whisper STT can use AI HAT+ 2 acceleration
- **44-Number Phone Directory**: Dial-in services with unique greetings and LLM personas
- **10 Personas**: Operator, Detective, Grandma, Robot, Sage, Comedian, Valley Girl, Beatnik, Game Show Host, Conspiracy Theorist
- **35 Features**: Information, entertainment, advice, nostalgic services, utilities, and easter eggs
- **Voice & DTMF Barge-In**: Interrupt AI by speaking or pressing keys
- **Telephony Integration**: FreePBX/Asterisk via AudioSocket
- **Optimized Pipeline**: O(n) algorithms, batched I/O, memory-bounded buffers

### Phone Directory Highlights

| Category | Services |
|----------|----------|
| Information | Weather, News, Sports, Horoscope, Time & Temperature |
| Entertainment | Dial-A-Joke, Trivia, Stories, Fortune, Mad Libs, Would You Rather, 20 Questions |
| Advice & Support | Advice Line, Compliment Line, Roast Line, Life Coach, Confession, Vent Line |
| Nostalgic | Moviefone (777-FILM), Collect Call Simulator, Nintendo Tip Line, Time Traveler |
| Utilities | Calculator, Translator, Spelling Bee, Dictionary, Recipe Line, Debate Partner, Interview Coach |
| Easter Eggs | Jenny (867-5309), Phone Phreaker (555-2600), Hacker Mode, Joe's Pizza, Haunted Line, Birthday (555-MMDD) |
| Personas | Wise Sage, Comedian, Noir Detective, Southern Grandma, Robot, Valley Girl, Beatnik Poet, Game Show Host, Conspiracy Theorist |

## Quick Start

```bash
# On Pi #1 (voice pipeline)
git clone <repo-url> ~/tele-ai
cd ~/tele-ai/payphone-app
./install.sh
sudo systemctl start payphone

# On Pi #2 (LLM server)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen3:4b-instruct
```

See [payphone-app/SETUP.md](payphone-app/SETUP.md) for detailed installation instructions.

## Target Latency

| Stage | Target (Moonshine) | Target (Whisper) |
|-------|-------------------|------------------|
| VAD → STT | <100ms | <500ms |
| STT → LLM | <1s | <1s |
| LLM → TTS | <500ms | <500ms |
| **Total** | **1-1.5s** | **1.5-2s** |

## Documentation

- [Setup Guide](payphone-app/SETUP.md) - Complete installation instructions
- [Project Overview](documentation/project-overview.md) - Architecture and service catalog
- [System Architecture](planning/system-architecture.md) - Technical design
- [Voice Pipeline Guide](documentation/local-voice-assistant-pipeline.md) - Pipeline details
- [Phone Directory](planning/phone-book-content.md) - Full phone book content
- [AI HAT+ 2 Whisper](documentation/raspberry-pi-5-ai-hat-2-whisper.md) - Hailo STT setup
- [FreePBX Integration](documentation/freepbx-ai-integrations.md) - Telephony setup

## License

MIT License
