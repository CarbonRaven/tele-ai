# AI Payphone

A fully local AI voice assistant designed for vintage payphones. Connects via Asterisk/FreePBX AudioSocket to provide interactive voice experiences styled after 1990s telephone services.

## Features

- **Fully Local Processing**: All AI runs on-device (Raspberry Pi 5)
- **Low Latency**: 1.5-2.0s end-to-end response time target
- **Voice Activity Detection**: Silero VAD for accurate speech detection
- **Speech-to-Text**: faster-whisper with distil-whisper support
- **Language Model**: Ollama with Qwen2.5-3B (or other models)
- **Text-to-Speech**: Kokoro-82M for natural voice synthesis
- **Barge-in Support**: Interrupt AI with DTMF tones
- **Multiple Personas**: Operator, Detective, Grandma, Robot
- **Extensible Features**: Dial-A-Joke, Fortune, Horoscope, Trivia

## Architecture

```
Payphone → HT801 ATA → FreePBX/Asterisk → AudioSocket → Voice Pipeline
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         │                         │
                    ▼                         ▼                         ▼
              Silero VAD              faster-whisper              Kokoro TTS
            (Voice Detection)       (Speech-to-Text)          (Text-to-Speech)
                    │                         │                         ▲
                    └─────────────────────────┼─────────────────────────┘
                                              │
                                              ▼
                                      Ollama (Qwen2.5-3B)
                                      (Language Model)
```

## Quick Start

### Prerequisites

- Raspberry Pi 5 (16GB recommended)
- Raspberry Pi OS 64-bit (Bookworm)
- FreePBX/Asterisk with AudioSocket support
- Grandstream HT801 ATA (or similar)

### Installation

```bash
# Clone repository
git clone <repo-url> ~/tele-ai
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

Key settings:

| Setting | Description | Default |
|---------|-------------|---------|
| `LLM_HOST` | Ollama server URL | `http://localhost:11434` |
| `LLM_MODEL` | Language model | `qwen2.5:3b` |
| `STT_MODEL_NAME` | Whisper model | `base` |
| `TTS_VOICE` | Kokoro voice | `af_bella` |
| `AUDIO_AUDIOSOCKET_PORT` | AudioSocket port | `9092` |

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
│   ├── stt.py              # faster-whisper STT
│   ├── llm.py              # Ollama client
│   └── tts.py              # Kokoro TTS
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

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No audio | Check AudioSocket port, verify FreePBX dialplan |
| Slow responses | Use smaller Whisper model, check Ollama performance |
| Connection refused | Verify service is running, check firewall |
| Poor transcription | Adjust VAD thresholds, check audio quality |

Enable debug logging:

```bash
# In .env
DEBUG=true
LOG_LEVEL=DEBUG
```

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | Quad-core ARM | Raspberry Pi 5 |
| RAM | 8GB | 16GB |
| Storage | 32GB | 128GB |
| Network | 100Mbps | Gigabit |

## License

MIT License - See LICENSE file for details.

## Acknowledgments

- [faster-whisper](https://github.com/guillaumekln/faster-whisper) - Fast Whisper inference
- [Silero VAD](https://github.com/snakers4/silero-vad) - Voice activity detection
- [Ollama](https://ollama.com/) - Local LLM inference
- [Kokoro](https://github.com/thewh1teagle/kokoro-onnx) - Fast TTS synthesis
- [Asterisk](https://www.asterisk.org/) - Telephony platform
