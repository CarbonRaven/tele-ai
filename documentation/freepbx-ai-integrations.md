# FreePBX AI Integrations

## Overview

FreePBX and Asterisk can be enhanced with AI capabilities to create intelligent voice assistants, automated IVR systems, call transcription services, and conversational AI agents. This guide covers the major integration options available for adding AI functionality to your PBX system.

### Integration Approaches

| Approach | Complexity | Cost | Use Case |
|----------|------------|------|----------|
| **Voice Agent Platforms** | Low-Medium | Free-$$ | Full conversational AI |
| **Commercial Modules** | Low | $$/month | Enterprise transcription/analytics |
| **DIY AGI Scripts** | High | API costs only | Custom applications |
| **Middleware Gateways** | Medium | Varies | Existing infrastructure |

### Key Technologies

| Technology | Purpose |
|------------|---------|
| **AudioSocket** | Real-time bidirectional audio streaming (Asterisk 18+) |
| **ARI** | Asterisk REST Interface for call control |
| **AGI** | Asterisk Gateway Interface for scripting |
| **Wyoming Protocol** | Home Assistant voice service integration |

## Open-Source Voice Agent Platforms

### Asterisk AI Voice Agent

The most powerful open-source AI voice agent for Asterisk/FreePBX, featuring modular pipeline architecture and 5 production-ready configurations.

#### Key Features

| Feature | Description |
|---------|-------------|
| **Modular Pipeline** | Mix and match STT, LLM, TTS providers |
| **Dual Transport** | AudioSocket and ExternalMedia RTP |
| **Tool Calling** | Transfers, voicemail, email summaries |
| **Admin UI** | Web dashboard for configuration |
| **Local Hybrid** | Audio stays on-premises, cloud LLM |
| **Ollama Support** | Self-hosted LLM without API keys |

#### Golden Baseline Configurations

| Configuration | Response Time | Best For |
|---------------|---------------|----------|
| OpenAI Realtime | <2s | Enterprise, quick setup |
| Deepgram Voice Agent | <3s | Advanced reasoning |
| Google Live API | <2s | Multimodal AI (Gemini) |
| ElevenLabs Agent | <2s | Premium voice quality |
| Local Hybrid | 3-7s | Privacy-focused |

#### Installation

```bash
# Clone repository
git clone https://github.com/hkjarral/Asterisk-AI-Voice-Agent.git
cd Asterisk-AI-Voice-Agent

# Run preflight check (creates .env, generates JWT_SECRET)
sudo ./preflight.sh --apply-fixes

# Start Admin UI
docker compose up -d --build admin_ui

# Access dashboard at http://localhost:3003
# Default login: admin / admin
```

#### FreePBX Dialplan Integration

Add to `/etc/asterisk/extensions_custom.conf`:

```ini
[from-ai-agent]
exten => s,1,NoOp(Asterisk AI Voice Agent)
 same => n,Set(AI_PROVIDER=google_live)      ; Optional: select provider
 same => n,Set(AI_CONTEXT=sales-agent)       ; Optional: select persona
 same => n,Stasis(asterisk-ai-voice-agent)
 same => n,Hangup()
```

#### System Requirements

| Type | CPU | RAM | Disk |
|------|-----|-----|------|
| Cloud providers | 2+ cores | 4GB | 1GB |
| Local Hybrid | 4+ cores | 8GB+ | 2GB |

**Platform**: x86_64 Linux only (Ubuntu 20.04+, Debian 11+, Rocky 8+)

#### Resources

- [GitHub Repository](https://github.com/hkjarral/Asterisk-AI-Voice-Agent)
- [FreePBX Integration Guide](https://github.com/hkjarral/Asterisk-AI-Voice-Agent/blob/main/docs/FreePBX-Integration-Guide.md)
- [Configuration Reference](https://github.com/hkjarral/Asterisk-AI-Voice-Agent/blob/main/docs/Configuration-Reference.md)

---

### Agent Voice Response (AVR)

Enterprise-grade conversational AI platform with ultra-low latency and advanced features for Asterisk-based systems.

#### Key Features

| Feature | Description |
|---------|-------------|
| **Real-Time Speech-to-Speech** | Sub-second response times |
| **Intelligent VAD** | Natural interruption handling (barge-in) |
| **Noise Suppression** | AI-powered background noise filtering |
| **Multi-Provider Support** | Cloud and local AI providers |
| **Visual Agent Builder** | No-code agent design |
| **Microservices Architecture** | Independent scaling of components |

#### Supported AI Providers

| Category | Cloud | Local |
|----------|-------|-------|
| **ASR** | Google, Deepgram, ElevenLabs | Vosk, Silero |
| **LLM** | OpenAI, Anthropic, OpenRouter | Ollama |
| **TTS** | Google, Deepgram, ElevenLabs | CoquiTTS, Kokoro |
| **STS** | OpenAI Realtime, Ultravox, Deepgram | - |

#### PBX Compatibility

- FreePBX
- VitalPBX
- Vicidial
- Elastix
- Any Asterisk-based system

#### Architecture

```
┌─────────────────┐     ┌──────────────┐
│  Asterisk PBX   │────▶│ Core Service │
│  (AudioSocket)  │     └──────┬───────┘
└─────────────────┘            │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
              ┌─────────┐ ┌─────────┐ ┌─────────┐
              │   ASR   │ │   LLM   │ │   TTS   │
              │ Service │ │ Service │ │ Service │
              └─────────┘ └─────────┘ └─────────┘
```

#### Resources

- [Website](https://www.agentvoiceresponse.com/)
- [GitHub Repository](https://github.com/agentvoiceresponse)
- [Documentation](https://www.agentvoiceresponse.com/docs)

---

### VEXYL

Self-hosted middleware gateway that bridges FreePBX/Asterisk to AI providers with enterprise features.

#### Key Features

| Feature | Description |
|---------|-------------|
| **Self-Hosted** | Complete data sovereignty |
| **Response Time** | 2.2-3.3 seconds end-to-end |
| **TTS Caching** | 90% hit rate, 2ms for repeated responses |
| **Multi-Language** | 100+ languages including Indian languages |
| **17+ Providers** | Bring your own API keys |
| **Failover** | Multi-provider redundancy |

#### Operating Modes

| Mode | Description |
|------|-------------|
| **Standard** | Full STT→LLM→TTS pipeline with custom data |
| **Gateway** | Direct streaming to OpenAI Realtime/ElevenLabs |

#### Current Capabilities

- Inbound call handling
- Outbound calling with pre-warmed greetings
- Context-aware conversations
- Circuit breakers and retry logic
- Session management across transfers

#### Pricing Model

Tiered licensing based on concurrent calls (10/20/50 channels) with BYOK (Bring Your Own Keys) model.

#### Resources

- [Website](https://vexyl.ai)
- [FreePBX Community Thread](https://community.freepbx.org/t/introducing-vexyl-ai-voice-gateway-for-freepbx-asterisk-systems/108761)

---

## Commercial Solutions

### Scribe for FreePBX

Official commercial module from Sangoma for AI-powered transcription and analytics.

#### Features

| Feature | Description |
|---------|-------------|
| **Speech-to-Text** | Transcribes calls and voicemails |
| **Call Summarization** | Concise summaries without replaying |
| **Sentiment Analysis** | AI-driven customer sentiment tracking |
| **Multi-Language** | Supports multiple languages |
| **Dashboard** | Visual sentiment overview |

#### Technical Details

- **Partner**: Deepgram (AI transcription provider)
- **Compatibility**: FreePBX/PBXact 15, 16, 17
- **Security**: TLS encryption for data transfer
- **Audio**: Stereo recording recommended for better diarization

#### Use Cases

- Quality assurance monitoring
- Compliance and record-keeping
- Customer service improvement
- Training and coaching

#### Resources

- [Official Product Page](https://www.freepbx.org/add-on/scribe-for-freepbx/)
- [Sangoma KB Documentation](https://sangomakb.atlassian.net/wiki/spaces/PG/pages/488898594/PBX+GUI+-+Scribe)

---

### Dillo AI

Commercial AI voice automation platform with FreePBX integration for intelligent call handling.

#### Features

| Capability | Description |
|------------|-------------|
| **Auto-Answer** | Answer 100% of calls, 24/7 |
| **Caller Identification** | Greet by name from CRM |
| **Smart Routing** | Redirect to appropriate department |
| **Message Collection** | Voicemail with reason for call |
| **Action Triggers** | Create tickets, send emails |
| **Information Provider** | Answer FAQs from knowledge base |

#### Capabilities

- Identify callers and personalize greetings
- Route calls based on department, request, or caller history
- Accept/reject call transfers with callbacks
- Priority-based extension failover
- Multi-channel support (voice, WhatsApp, chatbot)

#### Resources

- [FreePBX Integration Page](https://www.dillo.cloud/freepbx-integration/)
- [Website](https://dillo.cloud)

---

### TeleConnx Speech-to-Text

Deepgram-powered real-time speech recognition for Asterisk/FreePBX.

#### Features

- Real-time speech-to-text
- Handles hundreds of simultaneous calls
- Deepgram partnership for accuracy

#### Resources

- [Deepgram Partnership Announcement](https://deepgram.com/learn/teleconnx-stt-asterisk-freepbx-partnership)

---

## DIY Integrations

### Incredible PBX ChatGPT

Voice-activated ChatGPT accessible by dialing extension 2428 (C-H-A-T).

#### Components Required

1. Incredible PBX 2027 (Debian 11 or Ubuntu 22.04)
2. OpenAI API key (for ChatGPT)
3. IBM Watson Speech-to-Text API key

#### Installation

```bash
cd /
wget https://filedn.com/lBgbGypMOdDm8PWOoOiBR7j/ChatGPT/incredible-chat.tar.gz
tar zxvf incredible-chat.tar.gz
cd /root
```

Edit configuration files with your API keys:
- `chat` - Line 6: OPENAI_KEY
- `chatgpt` - Line 15: OPENAI_KEY
- `chatgpt.sh` - Lines 12, 16, 17: OPENAI_KEY, IBM STT API_KEY, API_URL

Complete installation:

```bash
cd /root
sed -i '/\[from-internal-custom\]/r chat.code' /etc/asterisk/extensions_custom.conf
chmod +x chat*
mv chat /usr/local/sbin
mv chatgpt /usr/local/bin
mv chatgpt.sh /var/lib/asterisk/agi-bin
asterisk -rx "dialplan reload"
```

#### Usage

Dial **2428** from any extension and speak your query. Good queries are concise (e.g., "What are the five best Atlantic coast beaches?").

#### Resources

- [Nerd Vittles Article](https://nerdvittles.com/incredible-chatgpt-artificial-intelligence-for-your-phone/)

---

### VitalPBX AI Agent

AGI-based AI agent using OpenAI ChatGPT, Whisper, and Azure TTS.

#### Requirements

- VitalPBX 4
- OpenAI API key
- Microsoft Azure TTS API key
- Python 3 with dependencies

#### Installation

```bash
# Install dependencies
apt update
apt install python3 python3-pip
pip install azure-cognitiveservices-speech

# Install Python packages
pip install pyst2 pydub python-dotenv langchain openai chromadb tiktoken
```

Create environment file at `/var/lib/asterisk/agi-bin/.env`:

```env
OPENAI_API_KEY = "sk-..."
AZURE_SPEECH_KEY = "..."
AZURE_SERVICE_REGION = "eastus"
PATH_TO_DOCUMENTS = "/var/lib/asterisk/agi-bin/docs/"
PATH_TO_DATABASE = "/var/lib/asterisk/agi-bin/data/"
```

#### Quick Install Script

```bash
wget https://raw.githubusercontent.com/VitalPBX/vitalpbx_agent_ai_chatgpt/main/vpbx-agent-ai.sh
chmod +x vpbx-agent-ai.sh
./vpbx-agent-ai.sh
```

#### Resources

- [GitHub Repository](https://github.com/VitalPBX/vitalpbx_agent_ai)
- [VitalPBX Blog Tutorial](https://vitalpbx.com/blog/vitalpbx-ai-agent-with-openai-chatgpt/)

---

### Custom Python AGI

Build your own AI voice agent using Python and Asterisk AGI.

#### Basic AGI Structure

```python
#!/usr/bin/env python3
import sys
import openai
from asterisk.agi import AGI

agi = AGI()
openai.api_key = "your-api-key"

def main():
    # Record user's question
    agi.appexec('Record', '/tmp/question.wav,3,30,y')

    # Transcribe with Whisper
    with open('/tmp/question.wav', 'rb') as audio:
        transcript = openai.Audio.transcribe("whisper-1", audio)

    question = transcript.text
    agi.verbose(f"Question: {question}")

    # Get ChatGPT response
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": question}],
        temperature=0.2
    )

    answer = response['choices'][0]['message']['content']
    agi.verbose(f"Answer: {answer}")

    # Convert to speech and play
    # (Add TTS implementation here)

if __name__ == "__main__":
    main()
```

#### Dialplan Example

```ini
[ai-assistant]
exten => 100,1,Answer()
 same => n,AGI(ai-assistant.py)
 same => n,Hangup()
```

---

## AudioSocket Protocol

AudioSocket is the recommended protocol for real-time AI voice integration with Asterisk 18+.

### Why AudioSocket?

| Method | Audio Access | Blocking | Complexity |
|--------|--------------|----------|------------|
| AGI | Limited | Yes | Low |
| EAGI | Read-only | Yes | Medium |
| ARI External Media | Full | No | High (WebRTC/RTP) |
| **AudioSocket** | **Full bidirectional** | **No** | **Medium** |

### How It Works

```
┌──────────────┐    TCP/16-bit PCM    ┌──────────────┐
│   Asterisk   │◀──────────────────▶│  AI Service  │
│   (Call)     │    @16kHz mono      │  (Python)    │
└──────────────┘                      └──────────────┘
```

### Dialplan Configuration

```ini
[ai-audiosocket]
exten => s,1,Answer()
 same => n,AudioSocket(uuid,hostname:port)
 same => n,Hangup()
```

### Python AudioSocket Server

```python
import socket
import struct

def handle_connection(conn):
    while True:
        # Read audio frame
        header = conn.recv(3)
        if not header:
            break

        msg_type = header[0]
        length = struct.unpack('>H', header[1:3])[0]

        if msg_type == 0x10:  # Audio data
            audio_data = conn.recv(length)
            # Process audio with STT
            # Get LLM response
            # Convert to speech with TTS
            # Send audio back
            response_audio = process_audio(audio_data)
            conn.send(struct.pack('>BH', 0x10, len(response_audio)))
            conn.send(response_audio)

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(('0.0.0.0', 9999))
server.listen(5)

while True:
    conn, addr = server.accept()
    handle_connection(conn)
```

---

## AI Provider Quick Reference

### Speech-to-Text (STT)

| Provider | Type | Latency | Languages | Best For |
|----------|------|---------|-----------|----------|
| OpenAI Whisper | Cloud | ~1-2s | 100+ | Accuracy |
| Deepgram | Cloud | <300ms | 30+ | Speed |
| Google Cloud | Cloud | <500ms | 125+ | Multi-language |
| Azure Speech | Cloud | <500ms | 100+ | Enterprise |
| Vosk | Local | <500ms | 20+ | Privacy |
| Silero | Local | <200ms | Limited | Edge devices |

### Large Language Models (LLM)

| Provider | Type | Response | Best For |
|----------|------|----------|----------|
| OpenAI GPT-4 | Cloud | <2s | Quality |
| OpenAI GPT-3.5 | Cloud | <1s | Speed/cost |
| Claude (Anthropic) | Cloud | <2s | Reasoning |
| Google Gemini | Cloud | <2s | Multimodal |
| Ollama (local) | Local | 2-5s | Privacy |
| llama.cpp | Local | 2-5s | Privacy |

### Text-to-Speech (TTS)

| Provider | Type | Quality | Latency |
|----------|------|---------|---------|
| ElevenLabs | Cloud | Premium | <500ms |
| OpenAI TTS | Cloud | High | <1s |
| Azure Speech | Cloud | High | <500ms |
| Google TTS | Cloud | High | <500ms |
| Piper | Local | Good | <200ms |
| Coqui TTS | Local | Good | <500ms |

### Real-Time Speech-to-Speech

| Provider | Latency | Features |
|----------|---------|----------|
| OpenAI Realtime | <500ms | Native voice, interruption |
| Deepgram Voice Agent | <1s | Think stage |
| ElevenLabs Conversational | <500ms | Premium voices |
| Ultravox | <500ms | Low latency |

---

## Comparison Matrix

### Open-Source Solutions

| Solution | Setup | Features | Local AI | Commercial Use |
|----------|-------|----------|----------|----------------|
| Asterisk AI Voice Agent | Docker | Excellent | Yes | MIT License |
| Agent Voice Response | Docker | Excellent | Yes | Free |
| VEXYL | Binary/Docker | Good | Limited | Licensed |
| VitalPBX AI Agent | Manual | Basic | No | GPL |
| Incredible PBX ChatGPT | Manual | Basic | No | GPL |

### Commercial Solutions

| Solution | Integration | Features | Pricing |
|----------|-------------|----------|---------|
| Scribe | Native module | Transcription, analytics | Per-seat |
| Dillo AI | API | Full automation | Contact |
| TeleConnx | Integration | STT at scale | Contact |

---

## Best Practices

### Security

- Never expose AI endpoints publicly without authentication
- Use TLS/SSL for all API communications
- Store API keys in environment variables, not code
- Implement rate limiting to prevent abuse
- Audit AI responses for sensitive data leakage

### Performance

- Use streaming where possible for lower latency
- Implement TTS caching for repeated responses
- Choose appropriate model sizes (smaller = faster)
- Use local AI for privacy-critical applications
- Monitor API costs and set usage limits

### Quality

- Test with diverse accents and audio quality
- Implement fallback responses for AI failures
- Log conversations for quality improvement
- Use VAD to reduce processing of silence
- Tune confidence thresholds for your use case

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| No audio in AudioSocket | Check firewall, verify port binding |
| High latency | Use faster providers, enable streaming |
| Poor transcription | Check audio quality, use noise suppression |
| AI not responding | Verify API keys, check rate limits |
| Dialplan not working | Reload dialplan: `asterisk -rx "dialplan reload"` |

### Debug Commands

```bash
# Check Asterisk connectivity
asterisk -rx "core show channels"

# View active calls
asterisk -rx "ari show apps"

# Check AudioSocket module
asterisk -rx "module show like audiosocket"

# Enable verbose logging
asterisk -rx "core set verbose 5"

# View real-time logs
asterisk -rvvvv
```

---

## Resources

### Documentation

- [Asterisk AudioSocket Documentation](https://wiki.asterisk.org/wiki/display/AST/AudioSocket)
- [Asterisk REST Interface (ARI)](https://wiki.asterisk.org/wiki/display/AST/Getting+Started+with+ARI)
- [FreePBX Wiki](https://wiki.freepbx.org/)

### GitHub Repositories

- [Asterisk-AI-Voice-Agent](https://github.com/hkjarral/Asterisk-AI-Voice-Agent) - Production-ready voice agent
- [Agent Voice Response](https://github.com/agentvoiceresponse) - AVR platform
- [VitalPBX AI Agent](https://github.com/VitalPBX/vitalpbx_agent_ai) - ChatGPT integration
- [asterisk-assistant](https://github.com/bkbilly/asterisk-assistant) - Python AGI for speech recognition

### Tutorials

- [Build AI Voice Agent with OpenAI Realtime API](https://towardsai.net/p/machine-learning/how-to-build-an-ai-voice-agent-with-openai-realtime-api-asterisk-sip-2025-using-python-with-github-repo)
- [Real-Time AI Voice Agents with AudioSocket](https://medium.com/@shubhanshutiwari74156/real-time-ai-voice-agents-with-asterisk-audiosocket-build-conversational-telephony-systems-in-4768a7a80a76)
- [VitalPBX AI Agent Tutorial](https://vitalpbx.com/blog/vitalpbx-ai-agent-with-openai-chatgpt/)

### Community

- [FreePBX Community Forums](https://community.freepbx.org/)
- [Asterisk Community Forums](https://community.asterisk.org/)
- [Agent Voice Response Discord](https://www.agentvoiceresponse.com/)
