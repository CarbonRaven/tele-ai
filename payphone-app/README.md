# AI Payphone

A fully local AI voice assistant designed for vintage payphones. Connects via Asterisk/FreePBX AudioSocket to provide interactive voice experiences styled after 1990s telephone services.

## Features

- **Fully Local Processing**: All AI runs on-premise (dual Raspberry Pi 5 setup)
- **Hailo NPU Acceleration**: Whisper STT accelerated by AI HAT+ 2
- **Low Latency**: ~1.5s end-to-end response time with streaming optimizations
- **Concurrent Calls**: Per-session state isolation supports multiple simultaneous calls
- **Voice Activity Detection**: Silero VAD for accurate speech detection
- **Speech-to-Text**: Hailo-accelerated Whisper via Wyoming protocol
- **Language Model**: Ollama with Qwen2.5-7B on dedicated Pi
- **Text-to-Speech**: Kokoro-82M with optional remote offloading
- **Streaming Pipeline**: Overlapped LLM+TTS for reduced latency
- **Barge-in Support**: Interrupt AI with DTMF tones
- **Multiple Personas**: Operator, Detective, Grandma, Robot
- **Extensible Features**: Dial-A-Joke, Fortune, Horoscope, Trivia

## Architecture

```
                                    ┌─────────────────────────────────────┐
                                    │          Pi #2 (pi-ollama)          │
                                    │           192.168.1.11              │
                                    │                                     │
                                    │    ┌─────────────────────────┐     │
                                    │    │   Ollama (qwen2.5:7b)   │     │
                                    │    │       Port 11434        │     │
                                    │    └─────────────────────────┘     │
                                    │                                     │
                                    │    ┌─────────────────────────┐     │
                                    │    │  TTS Server (optional)  │     │
                                    │    │       Port 10200        │     │
                                    │    └─────────────────────────┘     │
                                    └──────────────▲──────────────────────┘
                                                   │ HTTP API
                                                   │
Payphone → HT801 ATA → Asterisk → AudioSocket ─────┼─────────────────────────
                                    │              │                         │
                    ┌───────────────┼──────────────┼─────────────────────────┤
                    │               │              │    Pi #1 (pi-voice)     │
                    │               │              │     192.168.1.10        │
                    │               │              │     + AI HAT+ 2         │
                    ▼               ▼              ▼                         │
              Silero VAD    Hailo Whisper    Kokoro TTS                     │
              (CPU)         (NPU :10300)     (local/remote)                 │
                    │               │              ▲                         │
                    └───────────────┴──────────────┘                         │
                                                                             │
                    └────────────────────────────────────────────────────────┘
```

### Dual-Pi Benefits

| Pi #1 (pi-voice) | Pi #2 (pi-ollama) |
|------------------|-------------------|
| AudioSocket server | Ollama LLM (7B model) |
| VAD (CPU) | TTS server (optional) |
| STT via Hailo NPU | |
| TTS (local or remote) | |

## Quick Start

### Prerequisites

**Pi #1 (pi-voice) - Voice Pipeline:**
- Raspberry Pi 5 (16GB)
- Raspberry Pi AI HAT+ 2 (Hailo-10H)
- Raspberry Pi OS 64-bit (Bookworm)
- Static IP: 192.168.1.10
- FreePBX/Asterisk with AudioSocket support

**Pi #2 (pi-ollama) - LLM Server:**
- Raspberry Pi 5 (16GB)
- Raspberry Pi OS 64-bit (Bookworm)
- Static IP: 192.168.1.11
- Ollama with qwen2.5:7b model (~8GB RAM)

**Telephony:**
- Grandstream HT801 ATA (or similar)

### Installation

```bash
# Clone repository
git clone https://github.com/CarbonRaven/payphone-ai.git ~/tele-ai
cd ~/tele-ai/payphone-app

# Run automated installer
chmod +x install.sh
./install.sh

# Start the service
sudo systemctl start payphone
```

### Manual Installation

See [SETUP.md](SETUP.md) for detailed manual installation steps.

## Configuration

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

### Core Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `LLM_HOST` | Ollama server (Pi #2) | `http://192.168.1.11:11434` |
| `LLM_MODEL` | Language model | `qwen2.5:7b` |
| `STT_DEVICE` | STT backend (`hailo` or `auto`) | `hailo` |
| `STT_WYOMING_PORT` | Wyoming Whisper port | `10300` |
| `TTS_MODE` | TTS mode (`local` or `remote`) | `local` |
| `TTS_VOICE` | Kokoro voice | `af_bella` |
| `AUDIO_AUDIOSOCKET_PORT` | AudioSocket port | `9092` |

### Remote TTS (Optional)

Offload TTS to Pi #2 to reduce Pi #1 CPU load by ~30%:

```bash
# On Pi #2: Install and run TTS server
pip install ".[tts-server]"
python tts_server.py

# On Pi #1: Configure remote TTS
TTS_MODE=remote
TTS_REMOTE_HOST=http://192.168.1.11:10200
```

The STT service auto-detects Wyoming/Hailo and falls back to faster-whisper CPU if unavailable.

## FreePBX Integration

Add to `/etc/asterisk/extensions_custom.conf`:

```ini
[from-internal-custom]
exten => 2255,1,Answer()
 same => n,AudioSocket(${UNIQUEID},192.168.1.10:9092)
 same => n,Hangup()
```

Then reload: `asterisk -rx "dialplan reload"`

## Project Structure

```
payphone-app/
├── main.py                 # Application entry point
├── install.sh              # Automated installer
├── tts_server.py           # Remote TTS server (for Pi #2)
├── tts-server.service      # Systemd unit for TTS server
├── config/
│   ├── settings.py         # Pydantic settings
│   └── prompts.py          # System prompts for personas
├── core/
│   ├── audiosocket.py      # AudioSocket server
│   ├── audio_processor.py  # Resampling, telephone filter
│   ├── pipeline.py         # Voice pipeline orchestration
│   ├── session.py          # Call session management
│   └── state_machine.py    # Conversation state machine
├── services/
│   ├── vad.py              # Silero VAD wrapper
│   ├── stt.py              # Hailo Whisper (Wyoming) + fallback
│   ├── llm.py              # Ollama client with streaming
│   └── tts.py              # Kokoro TTS (local + remote)
└── features/
    ├── base.py             # Feature base classes
    ├── registry.py         # Auto-discovery registry
    ├── operator.py         # Default operator
    └── jokes.py            # Dial-A-Joke
```

## Adding Features

Create a new feature in `features/`:

```python
from features.base import ConversationalFeature
from features.registry import FeatureRegistry

@FeatureRegistry.register("myfeature")
class MyFeature(ConversationalFeature):
    name = "myfeature"
    description = "My custom feature"
    dtmf_code = "1234"  # Dial this to access

    def get_system_prompt(self) -> str:
        return "You are a helpful assistant..."

    def get_greeting(self) -> str:
        return "Welcome to my feature!"
```

## Service Management

```bash
# Start
sudo systemctl start payphone

# Stop
sudo systemctl stop payphone

# Restart
sudo systemctl restart payphone

# View logs
journalctl -u payphone -f

# Check status
sudo systemctl status payphone
```

### TTS Server (Pi #2, Optional)

```bash
# Install
sudo cp tts-server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable tts-server

# Start
sudo systemctl start tts-server

# View logs
journalctl -u tts-server -f
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No audio | Check AudioSocket port, verify FreePBX dialplan |
| Slow responses | Enable remote TTS, check Ollama performance |
| Connection refused | Verify service is running, check firewall |
| Poor transcription | Adjust VAD thresholds, check audio quality |
| Wyoming connection fails | Check wyoming-hailo-whisper service, will auto-retry with backoff |
| LLM streaming hangs | Timeout protection auto-recovers after configured timeout |
| Concurrent call issues | Per-session VAD state isolates calls automatically |

Enable debug logging:

```bash
# In .env
DEBUG=true
LOG_LEVEL=DEBUG
```

## Performance Optimizations

The voice pipeline includes extensive optimizations for low-latency operation:

### Streaming & Concurrency

| Optimization | Description |
|--------------|-------------|
| **Overlapped LLM+TTS** | Producer-consumer pattern streams sentences to TTS while LLM generates |
| **Per-session VAD State** | Each call tracks speech independently, enabling 3+ concurrent calls |
| **Thread-safe TTS** | asyncio.Lock prevents model corruption with concurrent synthesis |
| **Bounded Sentence Queue** | Max 5 sentences queued to balance latency and memory |

### Protocol & I/O

| Optimization | Description |
|--------------|-------------|
| **Binary Wyoming Protocol** | Audio sent as binary frames instead of base64 (~33% less overhead) |
| **Exponential Backoff** | Wyoming reconnection uses backoff (0.5s → 4s) to prevent storms |
| **Backpressure-aware Pacing** | Audio playback tracks actual vs expected time to prevent drift |
| **Connection Lifecycle** | Proper tracking with graceful shutdown and task cancellation |

### Memory & CPU

| Optimization | Description |
|--------------|-------------|
| **O(1) Audio Buffer** | Uses `deque.popleft()` instead of `list.pop(0)` |
| **Incremental Sample Tracking** | STT tracks samples incrementally, avoiding O(n²) |
| **Optimized History Trimming** | Conversation context tracks non-system count incrementally |
| **Bounded Queues** | Audio/DTMF queues have max sizes with drop-oldest strategy |
| **Remote TTS Option** | Offload synthesis to Pi #2, reducing Pi #1 CPU by ~30% |

### Validation & Security

| Optimization | Description |
|--------------|-------------|
| **Input Validation** | DTMF digits and payload sizes validated |
| **Streaming Timeout** | Separate first-token (15s) and inter-token (5s) timeouts |
| **Structured Exceptions** | Specific exception types enable targeted error recovery |

## Hardware Requirements

### Pi #1 (Voice Pipeline)

| Component | Requirement |
|-----------|-------------|
| Board | Raspberry Pi 5 (16GB) |
| Accelerator | AI HAT+ 2 (Hailo-10H, 40 TOPS) |
| Storage | 64GB+ SD card |
| Network | Gigabit Ethernet |

### Pi #2 (LLM + Optional TTS Server)

| Component | Requirement |
|-----------|-------------|
| Board | Raspberry Pi 5 (16GB) |
| Storage | 64GB+ SD card |
| Network | Gigabit Ethernet |
| RAM Usage | ~8GB for qwen2.5:7b + ~200MB for TTS |

## API Endpoints (TTS Server)

When running `tts_server.py` on Pi #2:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check, returns sample rate and voices |
| `/synthesize` | POST | Synthesize text to audio |

Example:
```bash
curl http://192.168.1.11:10200/health
curl -X POST http://192.168.1.11:10200/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "voice": "af_bella", "speed": 1.0}'
```

## License

MIT License - See LICENSE file for details.

## Acknowledgments

- [faster-whisper](https://github.com/guillaumekln/faster-whisper) - Fast Whisper inference
- [Silero VAD](https://github.com/snakers4/silero-vad) - Voice activity detection
- [Ollama](https://ollama.com/) - Local LLM inference
- [Kokoro](https://github.com/thewh1teagle/kokoro-onnx) - Fast TTS synthesis
- [Asterisk](https://www.asterisk.org/) - Telephony platform
- [FastAPI](https://fastapi.tiangolo.com/) - TTS server framework
