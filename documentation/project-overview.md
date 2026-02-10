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
│                              10.10.10.20              10.10.10.1          │
│                                                             │               │
│                                    ┌────────────────────────┴───────────┐   │
│                                    │                                    │   │
│                                    ▼                                    ▼   │
│   ┌─────────────────────────────────────────────┐  ┌──────────────────────┐│
│   │       Pi #1 (pi-voice) 10.10.10.10         │  │Pi #2 10.10.10.11    ││
│   │              + AI HAT+ 2                    │  │                      ││
│   │                                             │  │  ┌────────────────┐  ││
│   │  ┌─────────┐  ┌─────────┐  ┌─────────────┐ │  │  │     Ollama     │  ││
│   │  │Asterisk │  │ Hailo   │  │   Kokoro    │ │  │  │  qwen3:4b    │  ││
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
| LLM Server | Raspberry Pi 5 (16GB) | Ollama inference for qwen3:4b |
| Telephony Bridge | Grandstream HT801 v2 | SIP ↔ Analog conversion |
| Network | 5-Port Gigabit Switch | Internal network backbone |
| Interface | Vintage Payphone | Physical user interaction |

### Network Topology

| Device | IP Address | Ports |
|--------|------------|-------|
| Switch/Router | 10.10.10.1 | - |
| Pi #1 (pi-voice) | 10.10.10.10 | 9092 (AudioSocket), 10300 (Wyoming STT), 10200 (TTS), 10400 (Wake Word) |
| Pi #2 (pi-ollama) | 10.10.10.11 | 11434 (Ollama API) |
| HT801 ATA | 10.10.10.20 | 5060 (SIP) |

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
│   │   ├── phone_directory.py     # 44 phone numbers → features/personas
│   │   └── prompts.py             # LLM system prompts (35 features, 9 personas)
│   ├── core/                      # Pipeline core
│   │   ├── audiosocket.py         # Asterisk protocol
│   │   ├── audio_processor.py     # Audio conversion
│   │   ├── phone_router.py        # Number dialed → feature routing
│   │   ├── pipeline.py            # Orchestration
│   │   ├── session.py             # Call state (VAD model, barge-in buffer)
│   │   └── state_machine.py       # Flow control
│   ├── services/                  # AI services
│   │   ├── vad.py                 # VAD model pool + voice barge-in
│   │   ├── stt.py                 # Speech-to-text
│   │   ├── llm.py                 # Language model
│   │   └── tts.py                 # Text-to-speech
│   └── features/                  # Plugin system
│       ├── base.py                # Base classes
│       ├── registry.py            # Auto-discovery
│       ├── operator.py            # Default persona
│       └── jokes.py               # Dial-A-Joke
├── documentation/                 # Technical docs (26 files)
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
│  │ ┌────────┐ ┌─────────────────────┤    │ 35 features      │ │
│  │ │  TTS   │ │  AudioProcessor     │    │ 9 personas       │ │
│  │ │Kokoro  │ │  Resample + Filter  │    │ 44 phone numbers │ │
│  │ └────────┘ └─────────────────────┘    │                  │ │
│  └──────────────────────────────────┘    │ PhoneDirectory   │ │
│                                          └──────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

### Design Patterns

| Pattern | Location | Purpose |
|---------|----------|---------|
| Async/Await | All modules | Non-blocking I/O for concurrent calls |
| Pydantic Settings | config/settings.py | Type-safe environment configuration |
| Feature Registry | features/registry.py | Plugin auto-discovery via decorators |
| Phone Directory | config/phone_directory.py | Number → feature/persona routing with TypedDict |
| Phone Router | core/phone_router.py | Dialed number lookup, DTMF shortcuts, birthday pattern |
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
| LLM | Ollama + qwen3:4b | 3B parameter model, streaming |
| TTS | Kokoro-82M | Sub-300ms latency, 24kHz output |
| VAD | Silero VAD (pool of 3) | 1.8MB model, 95% accuracy, per-session exclusive models |
| Telephony | Asterisk/FreePBX | AudioSocket protocol |
| Audio | numpy, scipy, soundfile | Sample rate conversion, filtering |

## Features and Personas

### Personas (10)

Each persona has a dedicated phone number and unique LLM system prompt.

| Persona | Phone Number | Description |
|---------|--------------|-------------|
| The Operator | 555-0000 | Friendly 1990s telephone operator (default) |
| Wise Sage | 555-7243 (SAGE) | Ancient philosopher, cryptic wisdom |
| Comedian | 555-5264 (LAFF) | Stand-up comic, always "on" |
| Noir Detective | 555-3383 (DETE) | Hard-boiled 1940s private eye |
| Southern Grandma | 555-4726 (GRAN) | Warm, folksy, full of sayings |
| Robot from Future | 555-2687 (BOTT) | COMP-U-TRON 3000, amazed by 90s tech |
| Valley Girl | 555-8255 (VALL) | 1980s mall culture, totally tubular |
| Beatnik Poet | 555-7638 (POET) | Jazz-influenced, stream of consciousness |
| Game Show Host | 555-4263 (GAME) | Over-the-top enthusiasm, everything's a contest |
| Conspiracy Theorist | 555-9427 (XFIL) | Hushed whispers, everything is connected |

### Service Directory (35 features across 7 categories)

| Category | Services | Phone Numbers |
|----------|----------|---------------|
| **Information** (5) | Time & Temperature, Weather, News, Sports, Horoscope | 767-2676, 555-9328, 555-6397, 555-7767, 555-4676 |
| **Entertainment** (7) | Jokes, Trivia, Stories, Fortune, Mad Libs, Would You Rather, 20 Questions | 555-5653, 555-8748, 555-7867, 555-3678, 555-6235, 555-9687, 555-2090 |
| **Advice & Support** (6) | Advice, Compliment, Roast, Life Coach, Confession, Vent | 555-2384, 555-2667, 555-7627, 555-5433, 555-2663, 555-8368 |
| **Nostalgic** (4) | Moviefone, Collect Call, Nintendo Tips, Time Traveler | 777-3456, 555-2655, 555-8477, 555-8463 |
| **Utilities** (7) | Calculator, Translator, Spelling Bee, Dictionary, Recipe, Debate, Interview | 555-2252, 555-8726, 555-7735, 555-3428, 555-7324, 555-3322, 555-4688 |
| **Easter Eggs** (5+1) | Jenny (867-5309), Phreaker, Hacker, Pizza, Haunted, Birthday (555-MMDD) | 867-5309, 555-2600, 555-1337, 555-7492, 555-1313, 555-MMDD |

### DTMF Shortcuts

| Key | Service | Key | Service |
|-----|---------|-----|---------|
| 0 | Operator | 5 | Stories |
| 1 | Jokes | 6 | Compliment |
| 2 | Trivia | 7 | Advice |
| 3 | Fortune | 8 | Time & Temp |
| 4 | Horoscope | 9 | Roast |

## Performance Optimizations

| Optimization | Benefit |
|--------------|---------|
| Binary Wyoming Protocol | 33% less overhead than base64 |
| Hailo NPU Acceleration | Offloads Whisper from CPU |
| Streaming LLM | First token in <1s, continuous output |
| Sentence Buffering | TTS starts before LLM completes |
| Bounded Queues | Prevents memory exhaustion |
| VAD Model Pool | 3 pre-loaded models, each session gets exclusive access, no lock on hot path |
| Voice Barge-In | Detects speech during TTS playback (threshold 0.8), buffers audio for STT handoff |
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
 same => n,AudioSocket(${UNIQUEID},10.10.10.10:9092)
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
| Phone Directory (44 numbers) | Complete |
| LLM System Prompts (35 features, 9 personas) | Complete |
| Phone Routing & DTMF Shortcuts | Complete |
| Hardware Integration | Testing |
| Production Deployment | Planned |

## License

MIT License - See [LICENSE](../LICENSE) for details.
