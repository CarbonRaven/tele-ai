# Local Voice Assistant Pipeline

## Overview

This guide covers building a complete local voice assistant pipeline by combining the components documented in this project:

- **Wake Word Detection**: openWakeWord
- **Speech-to-Text (STT)**: Whisper (optionally accelerated with AI HAT+ 2)
- **Language Model (LLM)**: Ollama or Hailo-accelerated models
- **Text-to-Speech (TTS)**: Piper

The pipeline can be deployed as a standalone Python application, integrated with Home Assistant, or connected to FreePBX for telephony applications.

### Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     LOCAL VOICE ASSISTANT PIPELINE                   │
└─────────────────────────────────────────────────────────────────────┘

     ┌─────────┐    ┌─────────────┐    ┌─────────┐    ┌─────────┐
     │   Mic   │───▶│ openWakeWord│───▶│ Whisper │───▶│   LLM   │
     └─────────┘    │ (Wake Word) │    │  (STT)  │    │(Ollama) │
                    └─────────────┘    └─────────┘    └────┬────┘
                                                          │
     ┌─────────┐    ┌─────────────┐                       │
     │ Speaker │◀───│    Piper    │◀──────────────────────┘
     └─────────┘    │    (TTS)    │
                    └─────────────┘
```

### Component Summary

| Component | Tool | Port (Wyoming) | Hardware Acceleration |
|-----------|------|----------------|----------------------|
| Wake Word | openWakeWord | 10400 | CPU (15-20 models on Pi 3 core) |
| STT | Whisper | 10300 | **Hailo AI HAT+ 2 (recommended)** |
| LLM | Ollama | 11434 | CPU (dedicated Pi recommended) |
| TTS | Piper | 10200 | CPU (1.6s voice per second on Pi 4) |

**Recommended Dual-Pi Architecture:**
- **Pi #1**: Hailo-accelerated Whisper STT + Piper TTS + openWakeWord (frees CPU for audio processing)
- **Pi #2**: Standard Ollama with 3B+ models (full 16GB RAM available for LLM)

---

## Architecture Options

### Option 1: Home Assistant Integration

Best for smart home control with existing Home Assistant setup.

```
┌──────────────────────────────────────────────────────────────┐
│                       HOME ASSISTANT                          │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                    ASSIST PIPELINE                       │ │
│  │                                                          │ │
│  │  Wake Word ──▶ STT ──▶ Conversation Agent ──▶ TTS       │ │
│  │  (Wyoming)    (Wyoming)    (Ollama/HA)      (Wyoming)   │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
   │openWake- │  │ Whisper  │  │  Ollama  │  │  Piper   │
   │  Word    │  │          │  │          │  │          │
   │:10400    │  │:10300    │  │:11434    │  │:10200    │
   └──────────┘  └──────────┘  └──────────┘  └──────────┘
```

### Option 2: Standalone Python Application

Best for custom applications without Home Assistant dependency.

```
┌──────────────────────────────────────────────────────────────┐
│                    STANDALONE PIPELINE                        │
│                                                               │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐         │
│  │PyAudio  │──│openWake │──│faster-  │──│ Ollama  │         │
│  │  Mic    │  │  Word   │  │whisper  │  │  LLM    │         │
│  └─────────┘  └─────────┘  └─────────┘  └────┬────┘         │
│                                              │               │
│  ┌─────────┐  ┌─────────┐                    │               │
│  │PyAudio  │◀─│  Piper  │◀───────────────────┘               │
│  │ Speaker │  │  TTS    │                                    │
│  └─────────┘  └─────────┘                                    │
└──────────────────────────────────────────────────────────────┘
```

### Option 3: Linux Voice Assistant (ESPHome Protocol)

The newest approach for Home Assistant satellites, replacing Wyoming-satellite.

```
┌──────────────────────────────────────────────────────────────┐
│               LINUX VOICE ASSISTANT                           │
│              (ESPHome Protocol)                               │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  microWakeWord ──▶ Home Assistant ◀──▶ mpv (audio)     │  │
│  │       │                   │                             │  │
│  │       └───────────────────┼────────────────────────────┘  │
│  │                           │                               │
│  │                           ▼                               │
│  │                    ESPHome Protocol                       │
│  │                      (Port 6053)                          │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

---

## Standalone Python Implementation

### Quick Start: ollama-STT-TTS

A complete 100% local voice assistant using openWakeWord, Whisper, Ollama, and Piper.

#### Prerequisites

```bash
# Install system dependencies
sudo apt-get update && sudo apt-get install -y portaudio19-dev ffmpeg

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama3
```

#### Installation

```bash
# Clone repository
git clone https://github.com/sancliffe/ollama-STT-TTS.git
cd ollama-STT-TTS

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install .
```

#### Configuration

Edit `config.ini`:

```ini
[Models]
ollama_model = llama3
whisper_model = base.en
piper_model = en_US-lessac-medium

[Functionality]
wakeword = hey_jarvis
wakeword_threshold = 0.5
vad_aggressiveness = 2
```

#### Running

```bash
python run.py
```

**Commands**:
- Say "Hey Jarvis" to activate
- Say "goodbye" or "exit" to stop
- Say "new chat" to clear conversation history

---

### Alternative: local_ai_assistant

A simpler implementation with SQLite conversation persistence.

#### Installation

```bash
git clone https://github.com/djsharman/local_ai_assistant.git
cd local_ai_assistant

# Install Ollama and model
ollama run llama3:8b

# Download Piper voice
wget -O en_US-joe-medium.onnx https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/joe/medium/en_US-joe-medium.onnx
wget -O en_US-joe-medium.onnx.json https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/joe/medium/en_US-joe-medium.onnx.json

# Setup environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Running

```bash
python3 src/main.py
```

---

## Home Assistant Voice Pipeline

### Add-on Installation (Home Assistant OS)

1. **Install Speech-to-Text Add-on**:
   - Settings → Add-ons → Add-on Store
   - Install **Whisper** or **Speech-to-Phrase**
   - Start the add-on

2. **Install Text-to-Speech Add-on**:
   - Install **Piper**
   - Start the add-on

3. **Install Wake Word Add-on**:
   - Install **openWakeWord**
   - Start the add-on

4. **Configure Wyoming Integration**:
   - Settings → Devices & Services
   - Add Wyoming integration for each service
   - Services will be auto-discovered

5. **Create Voice Assistant**:
   - Settings → Voice assistants → Add assistant
   - Configure STT, TTS, and conversation agent

### Docker Installation (Home Assistant Core)

```yaml
# docker-compose.yml
version: '3'
services:
  whisper:
    image: rhasspy/wyoming-whisper
    command: --model base-int8 --language en
    ports:
      - "10300:10300"
    volumes:
      - whisper-data:/data
    restart: unless-stopped

  piper:
    image: rhasspy/wyoming-piper
    command: --voice en_US-lessac-medium
    ports:
      - "10200:10200"
    volumes:
      - piper-data:/data
    restart: unless-stopped

  openwakeword:
    image: rhasspy/wyoming-openwakeword
    command: --preload-model ok_nabu
    ports:
      - "10400:10400"
    restart: unless-stopped

volumes:
  whisper-data:
  piper-data:
```

### Adding Ollama for Conversations

For best performance, run Ollama on a dedicated Pi (Pi #2) separate from the voice pipeline.

1. **Install Ollama on Pi #2**:
```bash
# SSH to Pi #2 (pi-ollama)
ssh pi@10.10.10.11

curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:3b
```

2. **Configure Ollama for Network Access**:
```bash
# Edit Ollama service
sudo systemctl edit ollama.service

# Add:
[Service]
Environment="OLLAMA_HOST=0.0.0.0"

# Restart
sudo systemctl restart ollama
```

3. **Verify from Pi #1**:
```bash
curl http://10.10.10.11:11434/api/tags
```

3. **Add Ollama Integration in Home Assistant**:
   - Settings → Devices & Services → Add Integration
   - Search for "Ollama"
   - Enter IP address and port 11434
   - Select model and enable "Assist"

4. **Configure Voice Assistant**:
   - Settings → Voice assistants
   - Edit your assistant
   - Change "Conversation agent" to Ollama model

---

## Linux Voice Assistant (Newest Approach)

The official replacement for wyoming-satellite using ESPHome protocol.

### Features

- Announcements and media playback
- Start/continue conversation
- Timers support
- microWakeWord and openWakeWord
- Acoustic echo cancellation (AEC)

### Installation

```bash
# Install dependencies
sudo apt-get install libportaudio2 build-essential libmpv-dev

# Clone repository
git clone https://github.com/OHF-Voice/linux-voice-assistant.git
cd linux-voice-assistant
script/setup
```

### Configuration

```bash
# List audio devices
script/run --list-input-devices
script/run --list-output-devices

# Run with specific devices
script/run \
  --name "living-room" \
  --audio-input-device "USB Audio" \
  --audio-output-device "USB Audio" \
  --wake-model hey_jarvis
```

### Custom Wake Words

```bash
# Add openWakeWord models
mkdir -p wakewords/openWakeWord

# Download custom wake word
wget -O wakewords/openWakeWord/glados.tflite <model-url>

# Create config file
cat > wakewords/openWakeWord/glados.json << EOF
{
  "type": "openWakeWord",
  "wake_word": "GLaDOS",
  "model": "glados.tflite"
}
EOF

# Run with custom wake word
script/run --wake-word-dir wakewords/openWakeWord --wake-model glados
```

### Acoustic Echo Cancellation

```bash
# Enable PulseAudio echo cancel module
pactl load-module module-echo-cancel \
  aec_method=webrtc \
  aec_args="analog_gain_control=0 digital_gain_control=1 noise_suppression=1"

# Use echo-cancelled devices
script/run \
  --audio-input-device 'Echo-Cancel Source' \
  --audio-output-device 'pipewire/echo-cancel-sink'
```

### Connect to Home Assistant

1. Settings → Device & services
2. Add integration → ESPHome
3. Enter satellite IP address with port 6053
4. The satellite appears as an ESPHome device

---

## Hardware Acceleration with AI HAT+ 2

### Whisper on Hailo

The AI HAT+ 2 with Hailo-10H can accelerate Whisper inference significantly.

#### Supported Models

| Model | Parameters | Performance |
|-------|------------|-------------|
| whisper-tiny | 39M | ~47 TPS |
| whisper-tiny.en | 39M | Best for English |
| whisper-base | 74M | Good accuracy |
| whisper-base.en | 74M | Best English accuracy |

#### Hybrid Mode Architecture

```
Audio Input (16kHz)
    ↓
Spectrogram (CPU)
    ↓
Whisper Encoder (Hailo NPU) ←── Accelerated
    ↓
Whisper Decoder (CPU)
    ↓
Transcribed Text
```

#### Installation

```bash
# Clone Hailo Whisper repository
git clone https://github.com/hailocs/hailo-whisper.git
cd hailo-whisper

# Setup
python3 setup.py
source whisper_env/bin/activate

# Install HailoRT
pip install hailort-4.21.0-cp310-cp310-linux_aarch64.whl
```

#### Wyoming Integration

```bash
# Build Wyoming-Hailo-Whisper container
git clone https://github.com/mpeex/wyoming-hailo-whisper.git
cd wyoming-hailo-whisper
docker build -t wyoming-hailo-whisper .

# Run with Hailo acceleration
docker run -d \
  --privileged \
  --name wyoming-whisper \
  -p 10300:10300 \
  wyoming-hailo-whisper
```

### LLM Architecture Options

#### Recommended: Standard Ollama on Dedicated Pi

For best model quality and flexibility, run standard Ollama on a separate Raspberry Pi 5:

```bash
# On Pi #2 (dedicated LLM server)
curl -fsSL https://ollama.com/install.sh | sh

# Configure for network access
sudo systemctl edit ollama
# Add: Environment="OLLAMA_HOST=0.0.0.0"

sudo systemctl restart ollama
ollama pull qwen2.5:3b  # Or larger models
```

**Benefits:**
- Full 16GB RAM available for LLM (no competition with STT/TTS)
- Support for 3B+ models with better response quality
- Standard Ollama API compatibility
- AI HAT+ 2 free for Whisper STT acceleration on Pi #1

#### Alternative: hailo-ollama (Hailo-accelerated LLM)

For single-Pi deployments or smaller models:

```bash
# Start hailo-ollama server
docker run -d \
  --privileged \
  --name hailo-ollama \
  -p 8000:8000 \
  hailo/hailo-ollama:latest

# Use with Ollama API
curl http://localhost:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen2.5:1.5b",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

**Note:** hailo-ollama is limited to ~1.5B models due to Hailo-10H's 8GB LPDDR4X memory. For better response quality, use standard Ollama with 3B+ models on a dedicated Pi.

---

## Wyoming Protocol Reference

### Standard Ports

| Service | Port | Protocol |
|---------|------|----------|
| Piper (TTS) | 10200 | TCP |
| Whisper (STT) | 10300 | TCP |
| openWakeWord | 10400 | TCP |
| Satellite | 10700 | TCP |

### Event Flow

```
1. audio-chunk     → Wake Word Service (continuous streaming)
2. detection       ← Wake word detected
3. audio-start     → STT Service
4. audio-chunk     → STT Service (voice command)
5. audio-stop      → STT Service
6. transcript      ← Transcribed text
7. synthesize      → TTS Service
8. audio-start     ← TTS response begins
9. audio-chunk     ← TTS audio data
10. audio-stop     ← TTS complete
```

### Python Client Example

```python
import asyncio
import json

async def wyoming_stt(audio_data: bytes, host: str = "localhost", port: int = 10300):
    """Send audio to Whisper via Wyoming protocol."""
    reader, writer = await asyncio.open_connection(host, port)

    # Send transcribe request
    header = json.dumps({"type": "transcribe", "data": {"language": "en"}})
    writer.write(f"{header}\n".encode())

    # Send audio start
    audio_start = json.dumps({
        "type": "audio-start",
        "data": {"rate": 16000, "width": 2, "channels": 1}
    })
    writer.write(f"{audio_start}\n".encode())

    # Send audio chunks
    chunk_size = 1024
    for i in range(0, len(audio_data), chunk_size):
        chunk = audio_data[i:i+chunk_size]
        chunk_header = json.dumps({
            "type": "audio-chunk",
            "data": {"rate": 16000, "width": 2, "channels": 1},
            "payload_length": len(chunk)
        })
        writer.write(f"{chunk_header}\n".encode())
        writer.write(chunk)

    # Send audio stop
    audio_stop = json.dumps({"type": "audio-stop"})
    writer.write(f"{audio_stop}\n".encode())
    await writer.drain()

    # Read transcript response
    response = await reader.readline()
    result = json.loads(response)

    writer.close()
    await writer.wait_closed()

    return result.get("data", {}).get("text", "")

# Usage
transcript = asyncio.run(wyoming_stt(audio_bytes))
print(f"Transcribed: {transcript}")
```

---

## Performance Optimization

### Latency Targets

| Component | Target Latency | Notes |
|-----------|---------------|-------|
| Wake Word | <100ms | openWakeWord on Pi CPU |
| STT | <1s | With Hailo acceleration |
| LLM | <2s | Depends on model size |
| TTS | <500ms | Piper is very fast |
| **Total** | **<4s** | Comparable to cloud assistants |

### Hardware Recommendations

| Setup | Hardware | Expected Latency |
|-------|----------|------------------|
| **Budget** | Raspberry Pi 4 (4GB) | 5-10s total |
| **Balanced** | Raspberry Pi 5 (8GB) | 3-5s total |
| **Optimal** | Pi 5 + AI HAT+ 2 (single Pi) | 2-4s total |
| **Recommended** | 2x Pi 5 (16GB) + AI HAT+ 2 | 1.5-3s total |
| **Best** | Mini PC + GPU | <2s total |

**Recommended Dual-Pi Configuration:**
- **Pi #1 (pi-voice)**: AI HAT+ 2 for Whisper STT + Piper TTS + VAD
- **Pi #2 (pi-ollama)**: Standard Ollama with qwen2.5:3b (full 16GB for LLM)

### Optimization Tips

#### Whisper Optimization

```python
# Use smaller, faster models
model_sizes = {
    "tiny.en": "Fastest, English only",
    "base.en": "Good balance, English only",
    "small.en": "Better accuracy, slower",
}

# Use INT8 quantization
whisper_model = "base-int8"

# Reduce beam size
beam_size = 0  # Greedy decoding (fastest)
```

#### Piper Optimization

```bash
# Use medium quality (good balance)
--voice en_US-lessac-medium

# Enable streaming for faster first response
--streaming
```

#### LLM Optimization

```bash
# Use smaller models
ollama pull qwen2.5:1.5b  # Fastest
ollama pull llama3.2:3b   # Good balance

# Reduce context length
/set parameter num_ctx 2048

# Enable streaming responses
stream: true
```

#### System Optimization

```bash
# Increase GPU memory on Pi 5
sudo raspi-config
# Advanced Options → Memory Split → 256

# Use performance CPU governor
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Disable unnecessary services
sudo systemctl disable bluetooth
sudo systemctl disable avahi-daemon
```

---

## Complete Pipeline Example

### Standalone Voice Assistant Script

```python
#!/usr/bin/env python3
"""Complete local voice assistant pipeline."""

import pyaudio
import numpy as np
import requests
from openwakeword.model import Model as WakeWordModel
from faster_whisper import WhisperModel
from piper import PiperVoice
import wave
import io

# Configuration
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = 1280  # 80ms for openWakeWord
WAKE_WORD = "hey_jarvis"
WAKE_THRESHOLD = 0.5
OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3"

class VoiceAssistant:
    def __init__(self):
        # Initialize wake word
        self.wake_model = WakeWordModel(
            wakeword_models=[WAKE_WORD],
            inference_framework="tflite"
        )

        # Initialize STT
        self.whisper = WhisperModel("base.en", device="cpu")

        # Initialize TTS
        self.piper = PiperVoice.load("en_US-lessac-medium.onnx")

        # Initialize audio
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE
        )

        self.conversation_history = []

    def listen_for_wake_word(self):
        """Listen for wake word activation."""
        print(f"Listening for '{WAKE_WORD}'...")
        while True:
            audio_data = self.stream.read(CHUNK_SIZE, exception_on_overflow=False)
            audio_array = np.frombuffer(audio_data, dtype=np.int16)

            prediction = self.wake_model.predict(audio_array)
            if prediction.get(WAKE_WORD, 0) > WAKE_THRESHOLD:
                print("Wake word detected!")
                return True

    def record_command(self, silence_threshold=500, silence_duration=1.5):
        """Record user's voice command until silence."""
        print("Listening for command...")
        frames = []
        silent_chunks = 0
        max_silent_chunks = int(silence_duration * SAMPLE_RATE / CHUNK_SIZE)

        while True:
            audio_data = self.stream.read(CHUNK_SIZE, exception_on_overflow=False)
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            frames.append(audio_data)

            # Simple silence detection
            if np.abs(audio_array).mean() < silence_threshold:
                silent_chunks += 1
                if silent_chunks > max_silent_chunks:
                    break
            else:
                silent_chunks = 0

        return b''.join(frames)

    def transcribe(self, audio_data):
        """Transcribe audio using Whisper."""
        # Convert to WAV format
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(CHANNELS)
            wav_file.setsampwidth(2)
            wav_file.setframerate(SAMPLE_RATE)
            wav_file.writeframes(audio_data)
        wav_buffer.seek(0)

        # Transcribe
        segments, _ = self.whisper.transcribe(wav_buffer)
        text = " ".join([seg.text for seg in segments])
        print(f"You said: {text}")
        return text.strip()

    def get_response(self, text):
        """Get LLM response from Ollama."""
        self.conversation_history.append({"role": "user", "content": text})

        response = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "messages": self.conversation_history,
            "stream": False
        })

        assistant_message = response.json()["message"]["content"]
        self.conversation_history.append({"role": "assistant", "content": assistant_message})

        print(f"Assistant: {assistant_message}")
        return assistant_message

    def speak(self, text):
        """Convert text to speech using Piper."""
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(22050)
            self.piper.synthesize(text, wav_file)
        wav_buffer.seek(0)

        # Play audio
        play_stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=22050,
            output=True
        )
        play_stream.write(wav_buffer.read())
        play_stream.stop_stream()
        play_stream.close()

    def run(self):
        """Main loop."""
        print("Voice Assistant Ready!")
        try:
            while True:
                if self.listen_for_wake_word():
                    self.speak("Yes?")
                    audio_data = self.record_command()
                    text = self.transcribe(audio_data)

                    if text.lower() in ["goodbye", "exit", "quit"]:
                        self.speak("Goodbye!")
                        break

                    if text:
                        response = self.get_response(text)
                        self.speak(response)

        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.stream.stop_stream()
            self.stream.close()
            self.audio.terminate()

if __name__ == "__main__":
    assistant = VoiceAssistant()
    assistant.run()
```

### Requirements

```txt
# requirements.txt
openwakeword>=0.5.0
faster-whisper>=0.10.0
piper-tts>=1.2.0
pyaudio>=0.2.13
numpy>=1.24.0
requests>=2.31.0
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| No audio input | Check `arecord -l`, verify device index |
| Slow transcription | Use smaller model, enable Hailo acceleration |
| Wake word not detecting | Lower threshold, check microphone quality |
| Ollama connection refused | Ensure `OLLAMA_HOST=0.0.0.0` is set |
| High CPU usage | Reduce model sizes, use quantized models |

### Debug Commands

```bash
# Test microphone
arecord -D plughw:1,0 -f S16_LE -r 16000 -c 1 -d 5 test.wav
aplay test.wav

# Test Whisper
whisper test.wav --model base.en

# Test Piper
echo "Hello world" | piper --model en_US-lessac-medium.onnx --output_file test.wav

# Test Ollama
curl http://localhost:11434/api/chat -d '{"model":"llama3","messages":[{"role":"user","content":"Hi"}]}'

# Check Wyoming services
curl http://localhost:10200/info  # Piper
curl http://localhost:10300/info  # Whisper
curl http://localhost:10400/info  # openWakeWord
```

---

## Resources

### GitHub Repositories

- [ollama-STT-TTS](https://github.com/sancliffe/ollama-STT-TTS) - Complete standalone pipeline
- [local_ai_assistant](https://github.com/djsharman/local_ai_assistant) - Simple Python implementation
- [linux-voice-assistant](https://github.com/OHF-Voice/linux-voice-assistant) - ESPHome protocol satellite
- [wyoming](https://github.com/OHF-Voice/wyoming) - Wyoming protocol specification
- [wyoming-satellite](https://github.com/rhasspy/wyoming-satellite) - (Deprecated) Wyoming satellite

### Documentation

- [Home Assistant Voice Control](https://www.home-assistant.io/voice_control/)
- [Wyoming Protocol](https://www.home-assistant.io/integrations/wyoming/)
- [Piper Voices](https://rhasspy.github.io/piper-samples/)
- [openWakeWord](https://github.com/dscripka/openWakeWord)

### Tutorials

- [Home Assistant Local Voice Setup](https://www.home-assistant.io/voice_control/voice_remote_local_assistant/)
- [Voice + Ollama Setup Guide](https://techteamgb.co.uk/2025/02/28/home-assistance-voice-ollama-setup-guide-the-ultimate-local-llm-solution/)
- [Build Voice Assistant with Whisper + Ollama](https://medium.com/@vndee.huynh/build-your-own-voice-assistant-and-run-it-locally-whisper-ollama-bark-c80e6f815cba)

### Related Documentation

- [openWakeWord Wake Word Detection](./raspberry-pi-5-openwakeword.md)
- [AI HAT+ 2 Whisper Speech-to-Text](./raspberry-pi-5-ai-hat-2-whisper.md)
- [Piper Text-to-Speech](./raspberry-pi-5-piper-tts.md)
- [AI HAT+ 2 Access Methods](./raspberry-pi-5-ai-hat-2-access.md)
- [FreePBX AI Integrations](./freepbx-ai-integrations.md)
