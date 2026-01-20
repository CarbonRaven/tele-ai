# Piper Text-to-Speech on Raspberry Pi 5

## Overview

Piper is a fast, local neural text-to-speech (TTS) system optimized for edge devices like the Raspberry Pi. It provides natural-sounding speech synthesis without requiring cloud services, making it ideal for privacy-conscious voice assistant applications.

### Key Features

| Feature | Description |
|---------|-------------|
| **Offline Operation** | No internet connection required |
| **Low Latency** | Real-time factor ~0.2 (5x faster than real-time) |
| **Privacy** | All processing happens locally |
| **Multi-Language** | 51+ languages supported |
| **VITS Architecture** | Neural network trained voices |
| **ONNX Runtime** | Efficient cross-platform inference |

### Project Status

Development has moved from `rhasspy/piper` to the Open Home Foundation:
- **New Repository**: [OHF-Voice/piper1-gpl](https://github.com/OHF-Voice/piper1-gpl)
- **License**: GPLv3 (changed from MIT)
- **Current Version**: 1.3.0

## Performance

### Benchmarks

| Platform | Real-Time Factor (RTF) | Notes |
|----------|------------------------|-------|
| Raspberry Pi 4 | ~1.0 | Near real-time |
| Raspberry Pi 5 | ~0.5 | 2x faster than real-time |
| x86 Desktop | ~0.2 | 5x faster than real-time |

**RTF Definition**: Ratio of synthesis time to audio duration. RTF of 0.2 means 1 second of audio is generated in 0.2 seconds.

### Speed by Voice Quality

| Quality Level | Sample Rate | Speed | File Size |
|---------------|-------------|-------|-----------|
| x_low | 16 kHz | Fastest | Smallest |
| low | 16 kHz | Fast | Small |
| medium | 22.05 kHz | Balanced | Medium |
| high | 22.05 kHz | Slower | Largest |

**Recommendation**: Use `medium` quality for the best balance of quality and speed on Raspberry Pi 5.

## Voice Models

### Supported Languages (51+)

| Region | Languages |
|--------|-----------|
| **Western European** | English, German, French, Spanish, Italian, Dutch, Portuguese |
| **Nordic** | Norwegian, Swedish, Danish, Finnish, Icelandic |
| **Eastern European** | Polish, Czech, Slovak, Hungarian, Romanian, Ukrainian, Russian |
| **Asian** | Chinese, Japanese, Korean, Vietnamese, Thai |
| **Middle Eastern** | Arabic, Hebrew, Turkish, Persian |
| **Other** | Greek, Georgian, Kazakh, Nepali, Swahili |

### Popular English Voices

| Voice | Quality | Gender | Accent | Notes |
|-------|---------|--------|--------|-------|
| en_US-lessac-medium | Medium | Male | US | High quality, recommended |
| en_US-amy-medium | Medium | Female | US | Natural sounding |
| en_US-arctic-medium | Medium | Mixed | US | Multiple speakers |
| en_GB-alba-medium | Medium | Female | UK | British accent |
| en_GB-southern_english_female-low | Low | Female | UK Southern | Lightweight |
| en_AU-* | Various | Various | Australian | Several options |

### Voice Model Structure

Each voice requires two files:

```
voice_name.onnx       # Neural network model (VITS)
voice_name.onnx.json  # Configuration file
```

### Downloading Voices

```bash
# From Hugging Face (recommended)
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json

# Using piper download utility (v1.3.0+)
python -m piper.download_voices --voice en_US-lessac-medium
```

### Voice Sources

- [Hugging Face - piper-voices](https://huggingface.co/rhasspy/piper-voices)
- [Piper Voice Samples](https://rhasspy.github.io/piper-samples/)
- [VOICES.md](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/VOICES.md)

## Installation

### Method 1: pip (Recommended)

```bash
# Create virtual environment
python3 -m venv piper-env
source piper-env/bin/activate

# Install piper-tts
pip install piper-tts

# Verify installation
python -c "import piper; print('Piper installed successfully')"
```

### Method 2: Pre-built Binary

```bash
# Download ARM64 binary
wget https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_aarch64.tar.gz

# Extract
tar -xzf piper_linux_aarch64.tar.gz
cd piper

# Test
echo "Hello world" | ./piper --model en_US-lessac-medium.onnx --output_file test.wav
```

### Method 3: Docker

```bash
# Using LinuxServer.io image
docker run -d \
  --name piper \
  -e PIPER_VOICE=en_US-lessac-medium \
  -p 10200:10200 \
  -v ~/piper-data:/config \
  --restart unless-stopped \
  lscr.io/linuxserver/piper:latest

# Or using official Rhasspy image
docker run -d \
  --name wyoming-piper \
  -p 10200:10200 \
  -v ~/piper-data:/data \
  rhasspy/wyoming-piper \
  --voice en_US-lessac-medium
```

### Dependencies

```bash
# Audio playback (optional)
sudo apt install -y alsa-utils pulseaudio

# For building from source
sudo apt install -y build-essential cmake
```

## Command Line Usage

### Basic Synthesis

```bash
# Text to WAV file
echo "Hello, this is Piper text to speech" | \
  piper --model en_US-lessac-medium.onnx --output_file output.wav

# Play directly (requires aplay)
echo "Hello world" | \
  piper --model en_US-lessac-medium.onnx --output-raw | \
  aplay -r 22050 -f S16_LE -t raw -
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--model` | Path to .onnx voice model | Required |
| `--config` | Path to .onnx.json config | Auto-detected |
| `--output_file` | Output WAV file path | - |
| `--output-raw` | Output raw PCM audio | - |
| `--length-scale` | Speech speed (>1 slower) | 1.0 |
| `--noise-scale` | Audio variation | 0.667 |
| `--noise-w` | Speaking variation | 0.8 |
| `--speaker` | Speaker ID (multi-speaker) | 0 |
| `--sentence-silence` | Pause between sentences (sec) | 0.2 |
| `--cuda` | Use GPU acceleration | False |

### Examples

```bash
# Slower speech
echo "Speaking more slowly" | \
  piper --model en_US-lessac-medium.onnx \
        --length-scale 1.5 \
        --output_file slow.wav

# More expressive
echo "This is exciting news!" | \
  piper --model en_US-lessac-medium.onnx \
        --noise-scale 1.0 \
        --noise-w 1.0 \
        --output_file expressive.wav

# Process text file
cat story.txt | piper --model en_US-lessac-medium.onnx --output_file story.wav
```

## Python API

### Basic Usage

```python
import wave
from piper import PiperVoice

# Load voice model
voice = PiperVoice.load("en_US-lessac-medium.onnx")

# Synthesize to WAV file
with wave.open("output.wav", "wb") as wav_file:
    voice.synthesize_wav("Hello, this is Piper!", wav_file)
```

### With Synthesis Configuration

```python
from piper import PiperVoice, SynthesisConfig

voice = PiperVoice.load("en_US-lessac-medium.onnx")

# Custom synthesis settings
config = SynthesisConfig(
    length_scale=1.2,    # Slower speech
    noise_scale=0.667,   # Audio variation
    noise_w_scale=0.8,   # Speaking variation
)

with wave.open("output.wav", "wb") as wav_file:
    voice.synthesize_wav("Custom settings example", wav_file, syn_config=config)
```

### Streaming Synthesis

```python
from piper import PiperVoice, SynthesisConfig

voice = PiperVoice.load("en_US-lessac-medium.onnx")

# Generate audio chunks
for audio_chunk in voice.synthesize("Hello world", SynthesisConfig()):
    # Process each chunk (numpy array)
    print(f"Chunk: {len(audio_chunk.audio_bytes)} bytes")
```

### Real-time Playback

```python
import sounddevice as sd
import numpy as np
from piper import PiperVoice, SynthesisConfig

voice = PiperVoice.load("en_US-lessac-medium.onnx")

def speak(text):
    """Synthesize and play audio in real-time."""
    audio_data = []

    for chunk in voice.synthesize(text, SynthesisConfig()):
        audio_data.append(np.frombuffer(chunk.audio_bytes, dtype=np.int16))

    # Concatenate and play
    audio = np.concatenate(audio_data)
    sd.play(audio, samplerate=voice.config.sample_rate)
    sd.wait()

speak("This plays in real-time!")
```

### GPU Acceleration (CUDA)

```python
from piper import PiperVoice

# Requires onnxruntime-gpu package
# pip install onnxruntime-gpu

voice = PiperVoice.load("en_US-lessac-medium.onnx", use_cuda=True)
```

## Home Assistant Integration

### Option 1: Add-on (Easiest)

For Home Assistant OS or Supervised installations:

1. Go to **Settings** → **Add-ons**
2. Click **Add-on Store**
3. Search for "Piper"
4. Install the official Piper add-on
5. Start the add-on
6. The Wyoming integration should auto-discover it

### Option 2: Docker Container

```bash
# Start Wyoming-Piper container
docker run -d \
  --name wyoming-piper \
  -p 10200:10200 \
  -v ~/piper-data:/data \
  --restart unless-stopped \
  rhasspy/wyoming-piper \
  --voice en_US-lessac-medium
```

### Option 3: Docker Compose

```yaml
version: "3"
services:
  wyoming-piper:
    image: rhasspy/wyoming-piper
    container_name: wyoming-piper
    ports:
      - "10200:10200"
    volumes:
      - ./piper-data:/data
    command:
      - --voice
      - en_US-lessac-medium
    restart: unless-stopped
```

### Connecting to Home Assistant

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for **Wyoming Protocol**
4. Enter:
   - **Host**: IP address of Piper server (or `localhost` for add-on)
   - **Port**: `10200`
5. Click **Submit**

### Voice Assistant Pipeline

Configure a complete local voice pipeline:

| Component | Service | Port |
|-----------|---------|------|
| Wake Word | openWakeWord | 10400 |
| Speech-to-Text | Whisper | 10300 |
| **Text-to-Speech** | **Piper** | **10200** |

## Configuration Options

### Docker Environment Variables (LinuxServer.io)

| Variable | Description | Default |
|----------|-------------|---------|
| `PIPER_VOICE` | Voice model name | Required |
| `PIPER_LENGTH` | Speech speed | 1.0 |
| `PIPER_NOISE` | Audio noise | 0.667 |
| `PIPER_NOISEW` | Speaking variation | 0.333 |
| `PIPER_SPEAKER` | Speaker ID | 0 |
| `LOCAL_ONLY` | Disable auto-download | false |
| `TZ` | Timezone | UTC |

### Wyoming-Piper Arguments

```bash
docker run rhasspy/wyoming-piper \
  --voice en_US-lessac-medium \
  --length-scale 1.0 \
  --noise-scale 0.667 \
  --noise-w 0.8 \
  --speaker 0 \
  --max-piper-procs 1 \
  --debug
```

## Voice Training

### Prerequisites

```bash
# Install training dependencies
pip install piper-tts[train]

# Or from source
git clone https://github.com/OHF-Voice/piper1-gpl.git
cd piper1-gpl
pip install -e ".[train]"
```

### Quick Training (Transfer Learning)

Using a pre-trained checkpoint significantly speeds up training:

```bash
# Download checkpoint
wget https://huggingface.co/rhasspy/piper-checkpoints/resolve/main/en/en_US/lessac/medium/epoch=2164-step=1355540.ckpt

# Prepare your dataset (LJSpeech format)
# audio/: WAV files (22050 Hz, mono)
# metadata.csv: filename|transcription

# Start training
python -m piper.train \
  --dataset-dir ./my-dataset \
  --checkpoint-path epoch=2164-step=1355540.ckpt \
  --output-dir ./my-voice \
  --batch-size 16 \
  --epochs 1000
```

### Dataset Format

```
my-dataset/
├── audio/
│   ├── 001.wav
│   ├── 002.wav
│   └── ...
└── metadata.csv
```

**metadata.csv format**:
```
001|This is the first sentence.
002|This is the second sentence.
```

### Export to ONNX

```bash
python -m piper.export \
  --checkpoint ./my-voice/checkpoint.ckpt \
  --output ./my-voice.onnx
```

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Choppy audio on Pi 5 | Try a different voice model, use medium quality |
| "Model not found" | Ensure both .onnx and .onnx.json files exist |
| Slow synthesis | Use lower quality model (low or x_low) |
| No audio output | Check ALSA configuration, try `aplay -l` |
| Wyoming not connecting | Verify port 10200 is accessible |

### Audio Testing

```bash
# List audio devices
aplay -l

# Test audio output
speaker-test -t wav -c 2

# Generate and play test
echo "Testing audio" | piper --model en_US-lessac-medium.onnx --output-raw | \
  aplay -r 22050 -f S16_LE -t raw -
```

### Debug Mode

```bash
# Wyoming-Piper with debug logging
docker run rhasspy/wyoming-piper \
  --voice en_US-lessac-medium \
  --debug

# Check logs
docker logs wyoming-piper
```

### Performance Tips

1. **Use medium quality** - Best balance for Pi 5
2. **Pre-load voice** - Load once, synthesize many times
3. **Enable GPU** - If using Pi with external GPU/NPU
4. **Limit concurrent processes** - `--max-piper-procs 1` for stability

## Integration Examples

### With Whisper (Complete Voice Assistant)

```python
import whisper
from piper import PiperVoice
import sounddevice as sd
import numpy as np

# Load models
whisper_model = whisper.load_model("tiny")
piper_voice = PiperVoice.load("en_US-lessac-medium.onnx")

def listen_and_respond():
    # Record audio (simplified)
    print("Listening...")
    audio = sd.rec(int(5 * 16000), samplerate=16000, channels=1)
    sd.wait()

    # Transcribe
    result = whisper_model.transcribe(audio.flatten())
    user_text = result["text"]
    print(f"You said: {user_text}")

    # Generate response (placeholder)
    response = f"You said: {user_text}"

    # Speak response
    audio_data = []
    for chunk in piper_voice.synthesize(response):
        audio_data.append(np.frombuffer(chunk.audio_bytes, dtype=np.int16))

    sd.play(np.concatenate(audio_data), samplerate=22050)
    sd.wait()
```

### REST API Server

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from piper import PiperVoice
import io
import wave

app = FastAPI()
voice = PiperVoice.load("en_US-lessac-medium.onnx")

@app.get("/speak")
async def speak(text: str):
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        voice.synthesize_wav(text, wav)

    buffer.seek(0)
    return StreamingResponse(buffer, media_type="audio/wav")

# Run: uvicorn server:app --host 0.0.0.0 --port 8000
# Use: curl "http://localhost:8000/speak?text=Hello" --output hello.wav
```

## Resources

### Official Documentation
- [OHF-Voice/piper1-gpl](https://github.com/OHF-Voice/piper1-gpl) - New official repository
- [Piper Voice Samples](https://rhasspy.github.io/piper-samples/)
- [VOICES.md](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/VOICES.md)
- [Python API Docs](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/API_PYTHON.md)
- [Training Guide](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/TRAINING.md)

### Voice Downloads
- [Hugging Face - piper-voices](https://huggingface.co/rhasspy/piper-voices)
- [Hugging Face - piper-checkpoints](https://huggingface.co/rhasspy/piper-checkpoints) (for training)

### Docker Images
- [LinuxServer.io Piper](https://docs.linuxserver.io/images/docker-piper/)
- [rhasspy/wyoming-piper](https://hub.docker.com/r/rhasspy/wyoming-piper)

### Home Assistant
- [Piper Integration](https://www.home-assistant.io/integrations/piper/)
- [Wyoming Protocol](https://www.home-assistant.io/integrations/wyoming/)
- [Local Voice Assistant Guide](https://www.home-assistant.io/voice_control/voice_remote_local_assistant/)

### Community
- [Home Assistant Voice Forum](https://community.home-assistant.io/c/voice-assistant/)
- [Piper Discussions (archived)](https://github.com/rhasspy/piper/discussions)
