# System Architecture

Technical architecture for the AI Payphone project - a self-contained, locally-hosted AI voice assistant in a vintage payphone form factor.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AI PAYPHONE SYSTEM                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌───────────┐      ┌───────────┐      ┌───────────────────────────────┐  │
│   │           │      │Grandstream│      │      Raspberry Pi Cluster     │  │
│   │  PAYPHONE │─────▶│  HT801    │─────▶│  ┌─────────┐   ┌─────────┐   │  │
│   │           │ RJ11 │   ATA     │  SIP │  │  Pi 5   │   │  Pi 5   │   │  │
│   │  Handset  │      │           │      │  │ + HAT+2 │   │(Backup) │   │  │
│   │  Keypad   │      │           │      │  │         │   │         │   │  │
│   │  Coin Mech│      └───────────┘      │  │ AI Core │   │ FreePBX │   │  │
│   └───────────┘                         │  └─────────┘   └─────────┘   │  │
│                                         └───────────────────────────────┘  │
│                                                      │                      │
│                                         ┌────────────┴────────────┐        │
│                                         │    5-Port GbE Switch    │        │
│                                         └─────────────────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Hardware Components

### Bill of Materials

| Component | Model | Purpose | Qty |
|-----------|-------|---------|-----|
| Single Board Computer | Raspberry Pi 5 (16GB) | AI processing, voice pipeline | 2 |
| AI Accelerator | Raspberry Pi AI HAT+ 2 | Hailo-10H NPU for Whisper/LLM | 1 |
| Analog Telephone Adapter | Grandstream HT801 v2 | Payphone to SIP bridge | 1 |
| Network Switch | 5-port Gigabit | Internal network | 1 |
| Telephone | Vintage Payphone | User interface | 1 |

### Hardware Roles

```
┌─────────────────────────────────────────────────────────────────┐
│                    PI 5 #1 - AI CORE                            │
│                    (with AI HAT+ 2)                             │
├─────────────────────────────────────────────────────────────────┤
│  • Whisper STT (Hailo-accelerated)                              │
│  • Ollama LLM (Hailo-accelerated for small models)              │
│  • Piper TTS                                                    │
│  • openWakeWord (optional)                                      │
│  • Application logic & feature services                         │
│  • Audio processing pipeline                                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    PI 5 #2 - TELEPHONY                          │
├─────────────────────────────────────────────────────────────────┤
│  • FreePBX / Asterisk                                           │
│  • SIP server for HT801                                         │
│  • Call routing & dialplan                                      │
│  • AudioSocket bridge to AI Core                                │
│  • DTMF detection                                               │
│  • Call recording (optional)                                    │
└─────────────────────────────────────────────────────────────────┘
```

### Alternative: Single Pi Configuration

For simpler deployments, both roles can run on a single Pi 5:

```
┌─────────────────────────────────────────────────────────────────┐
│                    SINGLE PI 5 (16GB)                           │
│                    (with AI HAT+ 2)                             │
├─────────────────────────────────────────────────────────────────┤
│  Containers/Services:                                           │
│  • Asterisk (lightweight, no full FreePBX GUI)                  │
│  • Whisper (Hailo-accelerated)                                  │
│  • Ollama LLM                                                   │
│  • Piper TTS                                                    │
│  • Application service                                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Network Architecture

### Internal Network Topology

```
                    ┌─────────────────────┐
                    │   5-Port Switch     │
                    │                     │
                    │  [1] [2] [3] [4] [5]│
                    └──┬───┬───┬───┬───┬──┘
                       │   │   │   │   │
           ┌───────────┘   │   │   │   └───────────┐
           │               │   │   │               │
           ▼               ▼   │   ▼               ▼
    ┌─────────────┐ ┌─────────┐│┌─────────┐ ┌─────────────┐
    │   Pi 5 #1   │ │  Pi 5   │││ HT801   │ │  (Future)   │
    │   AI Core   │ │  #2 PBX │││   ATA   │ │  Expansion  │
    │ 192.168.1.10│ │.1.11    │││.1.20    │ │             │
    └─────────────┘ └─────────┘│└─────────┘ └─────────────┘
                               │
                               ▼
                        ┌─────────────┐
                        │   Uplink    │
                        │ (Optional)  │
                        └─────────────┘
```

### IP Address Allocation

| Device | IP Address | Hostname |
|--------|------------|----------|
| Pi 5 #1 (AI Core) | 192.168.1.10 | ai-core |
| Pi 5 #2 (FreePBX) | 192.168.1.11 | pbx |
| Grandstream HT801 | 192.168.1.20 | ata |
| Switch Management | 192.168.1.1 | switch (if managed) |

### Port Assignments

| Service | Port | Protocol | Host |
|---------|------|----------|------|
| SIP | 5060 | UDP | pbx |
| RTP Audio | 10000-20000 | UDP | pbx |
| AudioSocket | 9092 | TCP | ai-core |
| Whisper (Wyoming) | 10300 | TCP | ai-core |
| Piper (Wyoming) | 10200 | TCP | ai-core |
| openWakeWord (Wyoming) | 10400 | TCP | ai-core |
| Ollama API | 11434 | TCP | ai-core |
| Hailo-Ollama API | 8000 | TCP | ai-core |
| FreePBX Web UI | 80/443 | TCP | pbx |

---

## Software Architecture

### Technology Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER                          │
├─────────────────────────────────────────────────────────────────┤
│  Python Application                                             │
│  • Feature Services (jokes, trivia, weather, etc.)              │
│  • Session Management                                           │
│  • Persona Engine                                               │
│  • DTMF Navigation Handler                                      │
│  • Conversation State Machine                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        AI LAYER                                 │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Whisper   │  │   Ollama    │  │    Piper    │             │
│  │    (STT)    │  │    (LLM)    │  │    (TTS)    │             │
│  │             │  │             │  │             │             │
│  │ Hailo Accel │  │ Hailo/CPU   │  │    CPU      │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     TELEPHONY LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│  Asterisk / FreePBX                                             │
│  • SIP Registration (HT801)                                     │
│  • Dialplan / Call Routing                                      │
│  • AudioSocket Application                                      │
│  • DTMF Detection                                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      HARDWARE LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│  Grandstream HT801 ←──SIP/RTP──→ Asterisk                       │
│  Payphone ←──────RJ11 Analog──→ HT801                           │
│  AI HAT+ 2 ←────PCIe─────→ Pi 5                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Container Architecture (Docker)

```yaml
# Proposed container structure
services:
  # AI Core Services
  whisper:
    image: wyoming-hailo-whisper  # or standard whisper
    ports: ["10300:10300"]
    devices: ["/dev/hailo0"]

  piper:
    image: rhasspy/wyoming-piper
    ports: ["10200:10200"]

  ollama:
    image: ollama/ollama  # or hailo-ollama
    ports: ["11434:11434"]
    devices: ["/dev/hailo0"]

  # Application
  payphone-app:
    build: ./app
    depends_on: [whisper, piper, ollama]
    ports: ["9092:9092"]  # AudioSocket

  # Telephony (if on same host)
  asterisk:
    image: custom-asterisk
    ports:
      - "5060:5060/udp"
      - "10000-10100:10000-10100/udp"
```

---

## Voice Pipeline

### Call Flow Sequence

```
┌────────┐     ┌───────┐     ┌────────┐     ┌─────────┐     ┌────────────┐
│Payphone│     │ HT801 │     │Asterisk│     │App/Audio│     │ AI Stack   │
└───┬────┘     └───┬───┘     └───┬────┘     └────┬────┘     └─────┬──────┘
    │              │             │               │                 │
    │ Off-hook     │             │               │                 │
    │─────────────▶│             │               │                 │
    │              │ SIP INVITE  │               │                 │
    │              │────────────▶│               │                 │
    │              │             │ AudioSocket   │                 │
    │              │             │ Connect       │                 │
    │              │             │──────────────▶│                 │
    │              │             │               │                 │
    │ Dial tone    │◀────────────│◀──────────────│                 │
    │◀─────────────│             │               │                 │
    │              │             │               │                 │
    │ DTMF digits  │             │               │                 │
    │─────────────▶│────────────▶│──────────────▶│                 │
    │              │             │               │ Route to        │
    │              │             │               │ feature         │
    │              │             │               │                 │
    │ Voice input  │             │               │                 │
    │─────────────▶│ RTP Audio  ▶│ AudioSocket  ▶│ Whisper STT    │
    │              │             │               │────────────────▶│
    │              │             │               │                 │
    │              │             │               │◀─ Transcript ───│
    │              │             │               │                 │
    │              │             │               │─── LLM Query ──▶│
    │              │             │               │                 │
    │              │             │               │◀── Response ────│
    │              │             │               │                 │
    │              │             │               │─── TTS Gen ────▶│
    │              │             │               │                 │
    │              │             │               │◀── Audio ───────│
    │ AI Response  │◀────────────│◀──────────────│                 │
    │◀─────────────│             │               │                 │
    │              │             │               │                 │
    │ On-hook      │             │               │                 │
    │─────────────▶│ SIP BYE    │               │                 │
    │              │────────────▶│ Disconnect    │                 │
    │              │             │──────────────▶│                 │
```

### Audio Flow Detail

```
┌─────────────────────────────────────────────────────────────────┐
│                    INBOUND AUDIO PATH                           │
└─────────────────────────────────────────────────────────────────┘

Payphone Mic
     │
     ▼ (Analog audio)
┌─────────┐
│  HT801  │ ──▶ A/D Conversion ──▶ G.711 μ-law encoding
└─────────┘
     │
     ▼ (RTP packets, 8kHz, mono)
┌─────────┐
│Asterisk │ ──▶ Transcoding to 16kHz PCM (if needed)
└─────────┘
     │
     ▼ (AudioSocket, 16-bit PCM, 16kHz)
┌─────────┐
│  App    │ ──▶ Buffer audio ──▶ VAD detection
└─────────┘
     │
     ▼ (Audio chunks)
┌─────────┐
│ Whisper │ ──▶ Speech-to-Text ──▶ Transcript
└─────────┘


┌─────────────────────────────────────────────────────────────────┐
│                    OUTBOUND AUDIO PATH                          │
└─────────────────────────────────────────────────────────────────┘

LLM Response Text
     │
     ▼
┌─────────┐
│  Piper  │ ──▶ Text-to-Speech ──▶ 22050Hz WAV
└─────────┘
     │
     ▼ (Resample to 16kHz or 8kHz)
┌─────────┐
│  App    │ ──▶ Stream via AudioSocket
└─────────┘
     │
     ▼ (AudioSocket)
┌─────────┐
│Asterisk │ ──▶ Encode to G.711 ──▶ RTP packets
└─────────┘
     │
     ▼ (RTP)
┌─────────┐
│  HT801  │ ──▶ D/A Conversion
└─────────┘
     │
     ▼ (Analog audio)
Payphone Speaker
```

---

## Application Architecture

### Module Structure

```
payphone-app/
├── main.py                 # Entry point, AudioSocket server
├── config/
│   ├── settings.py         # Configuration management
│   ├── dial_codes.py       # DTMF code mappings
│   └── prompts.py          # System prompts for personas
├── core/
│   ├── session.py          # Call session management
│   ├── state_machine.py    # Conversation state handling
│   ├── dtmf_handler.py     # Touch-tone input processing
│   └── audio_processor.py  # Audio buffering and VAD
├── services/
│   ├── stt.py              # Whisper client
│   ├── llm.py              # Ollama client
│   ├── tts.py              # Piper client
│   └── weather.py          # External API clients
├── features/
│   ├── base.py             # Base feature class
│   ├── operator.py         # Main AI conversation
│   ├── time_temp.py        # Time and temperature
│   ├── jokes.py            # Dial-A-Joke
│   ├── trivia.py           # Trivia challenge
│   ├── horoscope.py        # Daily horoscope
│   ├── fortune.py          # Fortune teller
│   ├── stories.py          # Story time
│   └── ...                 # Additional features
├── personas/
│   ├── base.py             # Base persona class
│   ├── operator.py         # Default operator persona
│   ├── detective.py        # Noir detective
│   ├── grandma.py          # Southern grandma
│   └── ...                 # Additional personas
├── audio/
│   ├── sounds/             # Sound effects (dial tone, etc.)
│   ├── prompts/            # Pre-recorded prompts
│   └── music/              # Hold music
└── tests/
    └── ...
```

### State Machine

```
                            ┌─────────────┐
                            │    IDLE     │
                            │ (Waiting)   │
                            └──────┬──────┘
                                   │ Incoming call
                                   ▼
                            ┌─────────────┐
                            │   ANSWER    │
                            │ (Play greeting)
                            └──────┬──────┘
                                   │
                                   ▼
                            ┌─────────────┐
              ┌────────────▶│ MAIN_MENU   │◀────────────┐
              │             │ (Await input)│             │
              │             └──────┬──────┘             │
              │                    │                    │
              │     ┌──────────────┼──────────────┐     │
              │     │              │              │     │
              │     ▼              ▼              ▼     │
         ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
         │  OPERATOR   │  │  FEATURE    │  │   PERSONA   │
         │ (Free talk) │  │ (Specific)  │  │   (Mode)    │
         └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
                │                │                │
                │     ┌──────────┴──────────┐     │
                │     │                     │     │
                │     ▼                     ▼     │
                │ ┌─────────┐         ┌─────────┐ │
                │ │LISTENING│         │SPEAKING │ │
                │ │(STT)    │────────▶│(TTS)    │─┘
                │ └─────────┘         └─────────┘
                │         ▲                 │
                │         └─────────────────┘
                │
                │ (* or "menu")
                └──────────────────────────────────────┐
                                                       │
                            ┌─────────────┐            │
                            │   HANGUP    │◀───────────┘
                            │ (Cleanup)   │
                            └─────────────┘
```

### Feature Interface

```python
# features/base.py
from abc import ABC, abstractmethod

class BaseFeature(ABC):
    """Base class for all payphone features."""

    name: str
    dial_code: str
    description: str

    @abstractmethod
    async def handle(self, session: Session) -> None:
        """Main feature handler."""
        pass

    @abstractmethod
    def get_greeting(self) -> str:
        """Initial greeting when feature is accessed."""
        pass

    async def handle_dtmf(self, digit: str, session: Session) -> bool:
        """Handle DTMF input. Return True if handled."""
        if digit == '*':
            return False  # Return to menu
        return True
```

---

## Asterisk Integration

### Dialplan Configuration

```ini
; extensions.conf or extensions_custom.conf

[payphone-incoming]
; Answer and connect to AI application
exten => s,1,Answer()
 same => n,Set(CHANNEL(audioreadformat)=slin16)
 same => n,Set(CHANNEL(audiowriteformat)=slin16)
 same => n,AudioSocket(${UNIQUE_ID},192.168.1.10:9092)
 same => n,Hangup()

[payphone-dtmf]
; Alternative: DTMF-based routing
exten => _X.,1,Answer()
 same => n,Set(FEATURE_CODE=${EXTEN})
 same => n,AGI(agi://192.168.1.10:4573,${FEATURE_CODE})
 same => n,Hangup()
```

### SIP Configuration for HT801

```ini
; pjsip.conf

[transport-udp]
type=transport
protocol=udp
bind=0.0.0.0:5060

[payphone]
type=endpoint
context=payphone-incoming
disallow=all
allow=ulaw
allow=alaw
auth=payphone-auth
aors=payphone-aor
direct_media=no

[payphone-auth]
type=auth
auth_type=userpass
username=payphone
password=secure_password_here

[payphone-aor]
type=aor
max_contacts=1
```

---

## Data Storage

### Session Data (Redis or In-Memory)

```python
session_data = {
    "call_id": "uuid",
    "start_time": "timestamp",
    "current_state": "MAIN_MENU",
    "current_feature": "operator",
    "current_persona": "default",
    "conversation_history": [...],
    "dtmf_buffer": "",
    "achievements": [...],
    "preferences": {...}
}
```

### Persistent Storage (SQLite)

```sql
-- Call history
CREATE TABLE calls (
    id INTEGER PRIMARY KEY,
    call_id TEXT UNIQUE,
    start_time DATETIME,
    end_time DATETIME,
    duration_seconds INTEGER,
    features_used TEXT,  -- JSON array
    transcript TEXT      -- Optional
);

-- Feature usage stats
CREATE TABLE feature_stats (
    feature_name TEXT PRIMARY KEY,
    total_uses INTEGER,
    last_used DATETIME
);

-- Easter egg discoveries
CREATE TABLE discoveries (
    code TEXT PRIMARY KEY,
    discovered_at DATETIME
);
```

---

## External Integrations (Optional)

### Weather API
- **Provider**: OpenWeatherMap, WeatherAPI, or NWS
- **Data**: Current conditions, forecast
- **Caching**: 15-30 minute cache

### News API
- **Provider**: NewsAPI, RSS feeds
- **Data**: Headlines by category
- **Caching**: 1 hour cache

### Time Services
- **Source**: System time (NTP synced)
- **Timezone**: Configurable local timezone

---

## Deployment

### Docker Compose (Full Stack)

```yaml
version: '3.8'

services:
  whisper:
    image: wyoming-hailo-whisper:latest
    privileged: true
    devices:
      - /dev/hailo0:/dev/hailo0
    ports:
      - "10300:10300"
    restart: unless-stopped

  piper:
    image: rhasspy/wyoming-piper:latest
    command: --voice en_US-lessac-medium
    ports:
      - "10200:10200"
    volumes:
      - piper-data:/data
    restart: unless-stopped

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
    restart: unless-stopped

  payphone-app:
    build: ./app
    ports:
      - "9092:9092"
    environment:
      - WHISPER_HOST=whisper
      - PIPER_HOST=piper
      - OLLAMA_HOST=ollama
    depends_on:
      - whisper
      - piper
      - ollama
    restart: unless-stopped

  asterisk:
    build: ./asterisk
    ports:
      - "5060:5060/udp"
      - "10000-10100:10000-10100/udp"
    volumes:
      - ./asterisk/config:/etc/asterisk
    restart: unless-stopped

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    restart: unless-stopped

volumes:
  piper-data:
  ollama-data:
```

### Systemd Services (Non-Docker)

```ini
# /etc/systemd/system/payphone-app.service
[Unit]
Description=AI Payphone Application
After=network.target ollama.service

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/payphone
ExecStart=/opt/payphone/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## Performance Considerations

### Latency Budget

| Stage | Target | Notes |
|-------|--------|-------|
| Audio capture | <50ms | Buffering in AudioSocket |
| STT (Whisper) | <1000ms | Hailo acceleration critical |
| LLM response | <2000ms | Depends on model size |
| TTS (Piper) | <500ms | Very fast on CPU |
| Audio playback | <50ms | Streaming preferred |
| **Total** | **<4 seconds** | End-to-end response |

### Optimization Strategies

1. **Hailo Acceleration**: Use AI HAT+ 2 for Whisper encoder
2. **Model Selection**: Use smaller models (whisper-base, llama3.2:3b)
3. **Streaming TTS**: Start playback before full generation
4. **Response Caching**: Cache common responses (time, weather)
5. **Preloaded Models**: Keep models warm in memory

---

## Security Considerations

### Network Security
- Isolated internal network
- No internet required for core features
- Optional: Firewall rules if connected to broader network

### Audio Privacy
- All processing local (no cloud)
- Optional call recording with clear policy
- No persistent storage of conversations by default

### Access Control
- FreePBX admin interface password protected
- SSH key-based authentication only
- Disabled password login

---

## Monitoring & Logging

### Application Logs
```
/var/log/payphone/
├── app.log          # Main application
├── calls.log        # Call events
├── errors.log       # Errors only
└── performance.log  # Latency metrics
```

### Metrics to Track
- Calls per day
- Average call duration
- Feature usage distribution
- STT/LLM/TTS latency
- Error rates

### Health Checks
- Asterisk registration status
- AI service availability
- Hailo device status
- Disk/memory usage
