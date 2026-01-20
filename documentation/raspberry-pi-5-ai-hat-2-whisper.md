# Whisper Speech-to-Text on Raspberry Pi AI HAT+ 2

## Overview

OpenAI's Whisper is an automatic speech recognition (ASR) model that can transcribe spoken audio to text with multilingual support. The Raspberry Pi AI HAT+ 2 with Hailo-10H accelerator can run Whisper models locally for private, offline speech recognition.

### Key Benefits

| Benefit | Description |
|---------|-------------|
| **Privacy** | Audio processed locally, never leaves device |
| **Offline** | No internet connection required |
| **Low Latency** | Edge processing reduces round-trip delays |
| **Low Power** | ~2.5W during inference |
| **CPU Offload** | Frees Pi 5 CPU for other tasks |

## Supported Whisper Models

### Hailo-Optimized Models

| Model | Parameters | Size | Languages | Best For |
|-------|------------|------|-----------|----------|
| whisper-tiny | 39M | ~75MB | Multilingual | Resource-constrained, quick transcription |
| whisper-tiny.en | 39M | ~75MB | English only | Better English accuracy on tiny |
| whisper-base | 74M | 155MB | Multilingual | Balance of speed and accuracy |
| whisper-base.en | 74M | 155MB | English only | Best for English-only applications |

### Performance Metrics (Hailo-10H)

| Metric | Value |
|--------|-------|
| Load Time | ~1.33 seconds |
| Time to First Token | ~0.07 seconds |
| Tokens Per Second | ~47.55 TPS |
| Audio Window | 10 seconds |
| Sample Rate | 16 kHz |

### Quantization

- **Numerical Scheme**: A8W8 (8-bit activations, 8-bit weights)
- **Quantization Type**: Symmetric, channel-wise
- **Format**: Hailo Executable Format (HEF)

## Architecture

```
Audio Input (16kHz)
    ↓
Spectrogram Conversion (10s windows)
    ↓
Transformer Encoder (on Hailo NPU)
    ↓
Transformer Decoder (autoregressive)
    ↓
Text Tokens → Transcribed Text
```

### Hybrid Inference Mode

For best real-time performance, use hybrid mode:
- **Encoder**: Runs on Hailo NPU (accelerated)
- **Decoder**: Runs on Raspberry Pi 5 CPU

This achieves ~250ms refresh time for live captioning, much faster than running the full model on Hailo alone.

## Installation

### Prerequisites

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install audio dependencies
sudo apt install -y ffmpeg libportaudio2 portaudio19-dev

# Install Python dependencies
sudo apt install -y python3-pip python3-venv
```

### Method 1: Official Hailo Whisper Repository

```bash
# Clone repository
git clone https://github.com/hailocs/hailo-whisper.git
cd hailo-whisper

# Run setup script
python3 setup.py

# Activate virtual environment
source whisper_env/bin/activate

# Install HailoRT (download from Hailo Developer Zone)
pip install hailort-4.21.0-cp310-cp310-linux_aarch64.whl
```

### Method 2: Hailo Application Code Examples

```bash
# Clone examples repository
git clone https://github.com/hailo-ai/Hailo-Application-Code-Examples.git
cd Hailo-Application-Code-Examples/runtime/hailo-8/python/speech_recognition

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Method 3: Pre-built Docker Container

```bash
# Pull and run Whisper server container
docker pull cstrue/raspberrypi5-hailo8l-whisper-server

docker run -d \
  --privileged \
  --name whisper-server \
  -p 8080:8080 \
  cstrue/raspberrypi5-hailo8l-whisper-server
```

## Basic Usage

### Recording and Transcribing

```python
import sounddevice as sd
import numpy as np
from hailo_platform import HEF, VDevice, InferVStreams

# Audio settings
SAMPLE_RATE = 16000
DURATION = 5  # seconds

# Record audio
print("Recording...")
audio = sd.rec(int(DURATION * SAMPLE_RATE),
               samplerate=SAMPLE_RATE,
               channels=1,
               dtype='float32')
sd.wait()
print("Recording complete")

# Load Whisper model
hef = HEF("/path/to/whisper_base_encoder.hef")

with VDevice() as device:
    # Configure and run inference
    network_group = device.configure(hef)[0]

    # Preprocess audio to spectrogram
    spectrogram = preprocess_audio(audio)

    # Run encoder inference
    with InferVStreams(network_group, input_params, output_params) as pipeline:
        encoder_output = pipeline.infer({"input": spectrogram})

    # Decode tokens (on CPU)
    transcription = decode_tokens(encoder_output)
    print(f"Transcription: {transcription}")
```

### Using the Speech Recognition Example

```bash
cd Hailo-Application-Code-Examples/runtime/hailo-8/python/speech_recognition

# Run with default settings (5 second recording)
python speech_recognition.py

# The application will:
# 1. Record audio from microphone
# 2. Process through Whisper on Hailo
# 3. Display transcribed text
```

### REST API Server

```python
from fastapi import FastAPI, UploadFile
import tempfile

app = FastAPI()

@app.post("/transcribe")
async def transcribe(audio: UploadFile):
    # Save uploaded audio
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        tmp.write(await audio.read())
        tmp.flush()

        # Run Whisper inference
        transcription = whisper_transcribe(tmp.name)

    return {"transcription": transcription}

# Run with: uvicorn server:app --host 0.0.0.0 --port 8080
```

## Home Assistant Integration

### Wyoming Protocol

The Wyoming protocol enables Home Assistant to use external speech services.

#### Installation

```bash
# Clone Wyoming-Hailo-Whisper
git clone https://github.com/mpeex/wyoming-hailo-whisper.git
cd wyoming-hailo-whisper

# Build Docker image
docker build -t wyoming-hailo-whisper .

# Run container
docker run -d \
  --privileged \
  --name wyoming-whisper \
  -p 10300:10300 \
  wyoming-hailo-whisper
```

#### Home Assistant Configuration

1. Go to **Settings** → **Integrations** → **Add Integration**
2. Search for **Wyoming Protocol**
3. Enter:
   - Host: `<raspberry-pi-ip>`
   - Port: `10300`
4. The Whisper service will appear in your voice assistant pipeline

### Voice Assistant Pipeline

Complete local voice assistant setup:

| Component | Tool | Hardware |
|-----------|------|----------|
| Wake Word | openWakeWord | Pi 5 CPU |
| Speech-to-Text | Whisper | AI HAT+ 2 |
| Intent Recognition | Home Assistant | Pi 5 CPU |
| Text-to-Speech | Piper | Pi 5 CPU |

### Piper TTS (Text-to-Speech)

Complement Whisper with local TTS:

```bash
# Install Piper
pip install piper-tts

# Download voice model
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json

# Test TTS
echo "Hello, this is a test" | piper \
  --model en_US-lessac-medium.onnx \
  --output_file test.wav

aplay test.wav
```

## Real-Time Transcription

### Live Captioning Setup

For ~250ms latency live captioning:

```python
import sounddevice as sd
import numpy as np
from threading import Thread
from queue import Queue

class RealtimeTranscriber:
    def __init__(self, model_path):
        self.audio_queue = Queue()
        self.running = False
        self.load_model(model_path)

    def audio_callback(self, indata, frames, time, status):
        if status:
            print(f"Audio error: {status}")
        self.audio_queue.put(indata.copy())

    def transcribe_loop(self):
        buffer = np.array([])
        while self.running:
            # Accumulate audio
            while not self.audio_queue.empty():
                chunk = self.audio_queue.get()
                buffer = np.concatenate([buffer, chunk.flatten()])

            # Process when we have enough audio
            if len(buffer) >= 16000 * 2:  # 2 seconds
                transcription = self.transcribe(buffer)
                print(f"\r{transcription}", end="", flush=True)
                buffer = buffer[16000:]  # Keep last second for context

    def start(self):
        self.running = True

        # Start audio stream
        self.stream = sd.InputStream(
            samplerate=16000,
            channels=1,
            callback=self.audio_callback
        )
        self.stream.start()

        # Start transcription thread
        self.thread = Thread(target=self.transcribe_loop)
        self.thread.start()

    def stop(self):
        self.running = False
        self.stream.stop()
        self.thread.join()

# Usage
transcriber = RealtimeTranscriber("/path/to/whisper.hef")
transcriber.start()
input("Press Enter to stop...")
transcriber.stop()
```

## Performance Optimization

### Tips for Better Performance

| Optimization | Impact |
|--------------|--------|
| Use hybrid mode (encoder on Hailo, decoder on CPU) | 2-3x faster |
| Use .en models for English-only | Better accuracy |
| Use whisper-tiny for speed-critical apps | Fastest inference |
| Process in 10-second windows | Optimal for Hailo |
| Pre-warm model before first inference | Reduces first-token latency |

### Comparison: CPU vs Hailo

| Metric | Pi 5 CPU Only | AI HAT+ 2 (Hybrid) |
|--------|---------------|-------------------|
| whisper-tiny (10s audio) | ~8 seconds | ~2 seconds |
| whisper-base (10s audio) | ~15 seconds | ~4 seconds |
| Power consumption | ~8W | ~5W |
| CPU availability | 0% (busy) | ~80% free |

## Microphone Recommendations

### Tested Microphones

| Type | Model | Notes |
|------|-------|-------|
| USB Microphone | Blue Snowball | Good quality, plug-and-play |
| USB Webcam | Logitech C920 | Built-in mic works well |
| USB Array | ReSpeaker | 4-mic array, good for far-field |
| I2S MEMS | INMP441 | Requires GPIO wiring |
| Bluetooth | Various | Requires Pipewire setup |

### Audio Setup

```bash
# List audio devices
arecord -l

# Test recording
arecord -D plughw:1,0 -f S16_LE -r 16000 -c 1 -d 5 test.wav

# Play back
aplay test.wav
```

### Troubleshooting Audio

```bash
# Check if microphone is detected
lsusb | grep -i audio

# Check ALSA configuration
cat /proc/asound/cards

# Set default microphone
# Edit ~/.asoundrc or /etc/asound.conf
```

## Use Cases

### Ideal Applications

| Use Case | Description |
|----------|-------------|
| **Voice Assistant** | Local Alexa/Google alternative with Home Assistant |
| **Meeting Transcription** | Offline meeting notes |
| **Accessibility** | Real-time captions for hearing impaired |
| **Voice Commands** | Robotics and automation control |
| **Language Learning** | Pronunciation feedback |
| **Note Taking** | Voice memos to text |

### Not Recommended For

| Use Case | Reason |
|----------|--------|
| Long-form transcription (>1hr) | Better suited for cloud/desktop |
| Real-time translation | Additional model required |
| Speaker diarization | Not supported natively |
| Noisy environments | May need preprocessing |

## Limitations

### Current Constraints

- **Audio Window**: 10 seconds maximum per inference
- **Model Size**: Limited to tiny/base (small/medium/large require more memory)
- **Language Detection**: Works but adds latency
- **Streaming**: Not true streaming; processes in chunks
- **Accuracy**: Small models have higher word error rate than large

### Word Error Rate (WER) Comparison

| Model | LibriSpeech WER | Size |
|-------|-----------------|------|
| whisper-tiny | ~7.6% | 39M |
| whisper-base | ~5.0% | 74M |
| whisper-small | ~3.4% | 244M (not on Hailo) |
| whisper-medium | ~2.9% | 769M (not on Hailo) |

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "No Hailo device found" | Check PCIe connection, run `hailortcli fw-control identify` |
| Poor transcription quality | Use .en model for English, check mic quality |
| High latency | Use hybrid mode, try whisper-tiny |
| Audio not detected | Check `arecord -l`, verify permissions |
| Out of memory | Ensure using tiny/base model, not larger |

### Debug Commands

```bash
# Verify Hailo device
hailortcli fw-control identify

# Check audio devices
arecord -l
pactl list sources

# Test microphone
arecord -d 5 -f S16_LE -r 16000 test.wav && aplay test.wav

# Check Hailo driver
dmesg | grep hailo
```

## Resources

### Official Documentation
- [Hailo Model Explorer - Whisper-Base](https://hailo.ai/products/hailo-software/model-explorer/generative-ai/whisper-base/)
- [Hailo Developer Zone](https://hailo.ai/developer-zone/)

### GitHub Repositories
- [hailocs/hailo-whisper](https://github.com/hailocs/hailo-whisper) - Official conversion tools
- [Hailo Application Code Examples](https://github.com/hailo-ai/Hailo-Application-Code-Examples/tree/main/runtime/hailo-8/python/speech_recognition)
- [wyoming-hailo-whisper](https://github.com/mpeex/wyoming-hailo-whisper) - Home Assistant integration
- [raspberrypi5-hailo8L-whisper-server](https://github.com/CStrue/raspberrypi5-hailo8L-whisper-server)

### Community Resources
- [Hailo Community Forum - Whisper Topics](https://community.hailo.ai/tag/whisper)
- [Real-time ASR on Raspberry Pi + Hailo8L](https://community.hailo.ai/t/real-time-asr-on-raspberry-pi-hailo8l-with-whisper/17936)
- [Whisper Full Release Announcement](https://community.hailo.ai/t/whisper-full-release-now-available/16228)

### Related Projects
- [Piper TTS](https://github.com/rhasspy/piper) - Local text-to-speech
- [openWakeWord](https://github.com/dscripka/openWakeWord) - Wake word detection
- [Home Assistant Voice](https://www.home-assistant.io/voice_control/)
