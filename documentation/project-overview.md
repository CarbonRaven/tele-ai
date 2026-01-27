# AI Payphone Project Overview

A self-contained AI-powered payphone running fully local voice AI, styled after 1990s telephone services. The system features Hailo NPU hardware acceleration, dual Raspberry Pi architecture, and an extensible feature system.

## Mission

Transform a vintage payphone into an interactive AI experience that:
- Runs entirely on-premise with no cloud dependencies
- Provides sub-2-second response latency
- Offers nostalgic 1990s telephone service aesthetics
- Supports multiple personas and dial-up features

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Physical Layer                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Vintage Payphone ──► Grandstream HT801 ATA ──► 5-Port Gigabit Switch     │
│                              192.168.1.20              192.168.1.1          │
│                                                             │               │
│                                    ┌────────────────────────┴───────────┐   │
│                                    │                                    │   │
│                                    ▼                                    ▼   │
│   ┌─────────────────────────────────────────────┐  ┌──────────────────────┐│
│   │       Pi #1 (pi-voice) 192.168.1.10         │  │Pi #2 192.168.1.11    ││
│   │              + AI HAT+ 2                    │  │                      ││
│   │                                             │  │  ┌────────────────┐  ││
│   │  ┌─────────┐  ┌─────────┐  ┌─────────────┐ │  │  │     Ollama     │  ││
│   │  │Asterisk │  │ Hailo   │  │   Kokoro    │ │  │  │  qwen2.5:3b    │  ││
│   │  │AudioSock│  │ Whisper │  │    TTS      │ │  │  │    :11434      │  ││
│   │  │ :9092   │  │ :10300  │  │             │ │  │  └────────────────┘  ││
│   │  └────┬────┘  └────▲────┘  └──────▲──────┘ │  │          ▲           ││
│   │       │            │              │        │  │          │           ││
│   │       ▼            │              │        │  └──────────┼───────────┘│
│   │  ┌─────────────────┴──────────────┴──────┐ │             │            │
│   │  │           Voice Pipeline              │◄┼─────────────┘            │
│   │  │      VAD → STT → LLM → TTS            │ │         HTTP API         │
│   │  └───────────────────────────────────────┘ │                          │
│   └─────────────────────────────────────────────┘                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Hardware Components

| Component | Model | Role |
|-----------|-------|------|
| Voice Processor | Raspberry Pi 5 (16GB) | Audio pipeline, STT, TTS, VAD |
| NPU Accelerator | AI HAT+ 2 (Hailo-10H) | Whisper STT acceleration (40 TOPS) |
| LLM Server | Raspberry Pi 5 (16GB) | Ollama inference for qwen2.5:3b |
| Telephony Bridge | Grandstream HT801 v2 | SIP ↔ Analog conversion |
| Network | 5-Port Gigabit Switch | Internal network backbone |
| Interface | Vintage Payphone | Physical user interaction |

### Network Topology

| Device | IP Address | Ports |
|--------|------------|-------|
| Switch/Router | 192.168.1.1 | - |
| Pi #1 (pi-voice) | 192.168.1.10 | 9092 (AudioSocket), 10300 (Wyoming STT), 10200 (TTS), 10400 (Wake Word) |
| Pi #2 (pi-ollama) | 192.168.1.11 | 11434 (Ollama API) |
| HT801 ATA | 192.168.1.20 | 5060 (SIP) |

## Voice Pipeline

The system processes voice through a streaming pipeline optimized for low latency:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          Voice Processing Flow                            │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   Caller Speech                                                          │
│        │                                                                 │
│        ▼                                                                 │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐              │
│   │   VAD   │───►│   STT   │───►│   LLM   │───►│   TTS   │              │
│   │ Silero  │    │ Whisper │    │ Ollama  │    │ Kokoro  │              │
│   │  (CPU)  │    │ (Hailo) │    │(Pi #2)  │    │  (CPU)  │              │
│   └─────────┘    └─────────┘    └─────────┘    └─────────┘              │
│        │              │              │              │                    │
│        │         Streaming      Streaming      Streaming                 │
│        │                                            │                    │
│        ▼                                            ▼                    │
│   Speech/Silence                              Audio Chunks               │
│   Detection                                        │                     │
│                                                    ▼                     │
│                                            ┌─────────────┐               │
│                                            │  Resample   │               │
│                                            │ 24k → 8kHz  │               │
│                                            └──────┬──────┘               │
│                                                   │                      │
│                                                   ▼                      │
│                                            ┌─────────────┐               │
│                                            │  Telephone  │               │
│                                            │   Filter    │               │
│                                            │ 300-3400 Hz │               │
│                                            └──────┬──────┘               │
│                                                   │                      │
│                                                   ▼                      │
│                                              To Caller                   │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### Latency Targets

| Stage | Target | Description |
|-------|--------|-------------|
| VAD → STT | <500ms | Speech detection + Hailo NPU inference |
| STT → LLM | <1000ms | Prompt encoding + first token generation |
| LLM → TTS | <500ms | Sentence buffering + synthesis start |
| **Total** | **<2000ms** | End of speech to first audio output |

## Software Architecture

### Directory Structure

```
tele-ai/
├── payphone-app/                  # Main application
│   ├── main.py                    # Entry point
│   ├── config/                    # Configuration
│   │   ├── settings.py            # Pydantic Settings v2
│   │   └── prompts.py             # Persona system prompts
│   ├── core/                      # Pipeline core
│   │   ├── audiosocket.py         # Asterisk protocol
│   │   ├── audio_processor.py     # Audio conversion
│   │   ├── pipeline.py            # Orchestration
│   │   ├── session.py             # Call state
│   │   └── state_machine.py       # Flow control
│   ├── services/                  # AI services
│   │   ├── vad.py                 # Voice activity detection
│   │   ├── stt.py                 # Speech-to-text
│   │   ├── llm.py                 # Language model
│   │   └── tts.py                 # Text-to-speech
│   └── features/                  # Plugin system
│       ├── base.py                # Base classes
│       ├── registry.py            # Auto-discovery
│       ├── operator.py            # Default persona
│       └── jokes.py               # Dial-A-Joke
├── documentation/                 # Technical docs (20 files)
├── planning/                      # System design
├── scripts/                       # Operational tools
└── research/                      # Reference materials
```

### Component Relationships

```
┌────────────────────────────────────────────────────────────────┐
│                     PayphoneApplication                        │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐ │
│  │AudioSocket   │    │   Session    │    │   StateMachine   │ │
│  │   Server     │───►│   Manager    │───►│                  │ │
│  │   :9092      │    │              │    │  IDLE→GREETING   │ │
│  └──────────────┘    └──────────────┘    │  →LISTENING      │ │
│         │                   │            │  →PROCESSING     │ │
│         │                   │            │  →SPEAKING       │ │
│         ▼                   ▼            │  →HANGUP         │ │
│  ┌──────────────────────────────────┐    └──────────────────┘ │
│  │          VoicePipeline           │              │          │
│  ├──────────────────────────────────┤              │          │
│  │ ┌────────┐ ┌────────┐ ┌────────┐ │              ▼          │
│  │ │  VAD   │ │  STT   │ │  LLM   │ │    ┌──────────────────┐ │
│  │ │Silero  │ │Wyoming │ │ Ollama │ │    │ FeatureRegistry  │ │
│  │ └────────┘ └────────┘ └────────┘ │    ├──────────────────┤ │
│  │ ┌────────┐ ┌─────────────────────┤    │ • Operator       │ │
│  │ │  TTS   │ │  AudioProcessor     │    │ • Dial-A-Joke    │ │
│  │ │Kokoro  │ │  Resample + Filter  │    │ • Fortune        │ │
│  │ └────────┘ └─────────────────────┘    │ • Horoscope      │ │
│  └──────────────────────────────────┘    │ • Trivia         │ │
│                                          └──────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

### Design Patterns

| Pattern | Location | Purpose |
|---------|----------|---------|
| Async/Await | All modules | Non-blocking I/O for concurrent calls |
| Pydantic Settings | config/settings.py | Type-safe environment configuration |
| Feature Registry | features/registry.py | Plugin auto-discovery via decorators |
| State Machine | core/state_machine.py | Conversation flow control |
| Sentence Buffer | services/llm.py | Stream chunking for TTS |
| Protocol Handler | core/audiosocket.py | Binary framing for Asterisk |

## Technology Stack

| Layer | Technology | Notes |
|-------|------------|-------|
| Runtime | Python 3.10+ asyncio | Non-blocking concurrent calls |
| Configuration | Pydantic Settings v2 | Environment variable management |
| Wake Word | openWakeWord | Wyoming protocol integration |
| STT | Hailo Whisper + faster-whisper | NPU-accelerated with CPU fallback |
| LLM | Ollama + qwen2.5:3b | 3B parameter model, streaming |
| TTS | Kokoro-82M | Sub-300ms latency, 24kHz output |
| VAD | Silero VAD | 1.8MB model, 95% accuracy |
| Telephony | Asterisk/FreePBX | AudioSocket protocol |
| Audio | numpy, scipy, soundfile | Sample rate conversion, filtering |

## Features and Personas

### Available Personas

| Persona | Description | Dial Code |
|---------|-------------|-----------|
| Operator | Friendly 1990s telephone operator | 0 |
| Detective | Noir-style private eye | *1 |
| Grandma | Warm, storytelling grandmother | *2 |
| Robot | Quirky retro-futuristic AI | *3 |

### Dial-Up Services

| Service | Description | Dial Code |
|---------|-------------|-----------|
| Dial-A-Joke | Random jokes on demand | 1 |
| Fortune | Daily fortune readings | 2 |
| Horoscope | Astrological readings | 3 |
| Trivia | Random trivia facts | 4 |
| Weather | Local weather reports | 5 |
| Time | Current time announcement | 6 |

## Performance Optimizations

| Optimization | Benefit |
|--------------|---------|
| Binary Wyoming Protocol | 33% less overhead than base64 |
| Hailo NPU Acceleration | Offloads Whisper from CPU |
| Streaming LLM | First token in <1s, continuous output |
| Sentence Buffering | TTS starts before LLM completes |
| Bounded Queues | Prevents memory exhaustion |
| Thread-safe VAD | Safe concurrent call handling |
| Model Keep-alive | No cold-start latency (24h cache) |
| Telephone Filter | Authentic 300-3400Hz audio |
| O(n) String Building | LLM streaming uses list + join vs O(n²) concat |
| Incremental Regex Search | Sentence detection searches only new tokens |
| Pre-allocated Audio Arrays | Streaming STT uses doubling for O(n) copies |
| Batched Wyoming Writes | Single drain after all audio chunks sent |
| Lazy Dtype Conversion | Skip array copy when dtype already matches |

## Deployment

### Quick Start

```bash
# Clone and install
git clone https://github.com/CarbonRaven/payphone-ai.git
cd payphone-ai/payphone-app
./install.sh

# Start service
sudo systemctl start payphone
```

### Service Management

```bash
sudo systemctl start payphone     # Start
sudo systemctl stop payphone      # Stop
sudo systemctl restart payphone   # Restart
sudo systemctl status payphone    # Status
journalctl -u payphone -f         # Live logs
```

### FreePBX Integration

Add to `/etc/asterisk/extensions_custom.conf`:

```ini
[from-internal-custom]
exten => 2255,1,Answer()
 same => n,AudioSocket(${UNIQUEID},192.168.1.10:9092)
 same => n,Hangup()
```

## Monitoring

### Health Check Script

```bash
# One-shot health check
python scripts/health-monitor.py

# Continuous monitoring
python scripts/health-monitor.py --watch

# JSON output for integration
python scripts/health-monitor.py --json
```

### Key Metrics

- CPU temperature and throttling status
- Memory usage and available capacity
- Hailo NPU status and utilization
- Service health (Asterisk, Ollama, Wyoming)
- Active call count and duration

## Documentation Index

| Document | Description |
|----------|-------------|
| [Voice Pipeline](local-voice-assistant-pipeline.md) | Complete VAD→STT→LLM→TTS guide |
| [Hailo Whisper](raspberry-pi-5-ai-hat-2-whisper.md) | NPU-accelerated STT setup |
| [FreePBX Integration](freepbx-ai-integrations.md) | Telephony configuration |
| [System Architecture](../planning/system-architecture.md) | Full system design |
| [Features List](../planning/features-list.md) | Feature roadmap |

## Project Status

| Component | Status |
|-----------|--------|
| Voice Pipeline | Complete |
| AudioSocket Protocol | Complete |
| VAD Integration | Complete |
| STT (Hailo + fallback) | Complete |
| LLM (Ollama) | Complete |
| TTS (Kokoro) | Complete |
| Feature System | Complete |
| Operator Persona | Complete |
| Additional Features | In Progress |
| Hardware Integration | Testing |
| Production Deployment | Planned |

## License

MIT License - See [LICENSE](../LICENSE) for details.
