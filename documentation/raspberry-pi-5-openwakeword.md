# openWakeWord: Wake Word Detection on Raspberry Pi

## Overview

openWakeWord is an open-source wake word detection framework that enables voice-activated applications. Created by David Scripka, it provides pre-trained models and tools for training custom wake words using synthetic speech data.

### Key Features

| Feature | Description |
|---------|-------------|
| **Open Source** | Apache-2.0 license |
| **Efficient** | 15-20 models on single Pi 3 core |
| **Synthetic Training** | No manual data collection needed |
| **Low Error Rates** | <0.5/hr false accepts, <5% false rejects |
| **English Focus** | Best support for English wake words |
| **Wyoming Protocol** | Home Assistant integration |

### Performance

| Metric | Target |
|--------|--------|
| False Accept Rate | <0.5 per hour |
| False Reject Rate | <5% |
| Frame Size | 80 ms |
| Audio Format | 16-bit PCM, 16kHz |

## Architecture

openWakeWord uses a three-component architecture:

```
Audio Input (16-bit, 16kHz PCM)
    ↓
[1] Melspectrogram Pre-processing (ONNX)
    ↓
[2] Shared Feature Extraction Backbone (Google TFHub)
    ↓
[3] Wake Word Classification Model (TFLite/ONNX)
    ↓
Confidence Score (0-1)
```

### Components

1. **Melspectrogram**: ONNX implementation of Torch's melspectrogram
2. **Feature Backbone**: Pre-trained Google embedding model (frozen)
3. **Classifier**: Small fully-connected network (trainable)

The shared backbone enables adding multiple wake words with minimal resource overhead.

## Pre-Trained Models

### Available Wake Words

| Model | Wake Word/Phrase | Documentation |
|-------|------------------|---------------|
| `alexa` | "Alexa" | [docs](https://github.com/dscripka/openWakeWord/blob/main/docs/models/alexa.md) |
| `hey_mycroft` | "Hey Mycroft" | [docs](https://github.com/dscripka/openWakeWord/blob/main/docs/models/hey_mycroft.md) |
| `hey_jarvis` | "Hey Jarvis" | [docs](https://github.com/dscripka/openWakeWord/blob/main/docs/models/hey_jarvis.md) |
| `hey_rhasspy` | "Hey Rhasspy" | TBD |
| `ok_nabu` | "Ok Nabu" | Home Assistant default |
| `current_weather` | "What's the weather" | [docs](https://github.com/dscripka/openWakeWord/blob/main/docs/models/current_weather.md) |
| `timers` | "Set a timer" | [docs](https://github.com/dscripka/openWakeWord/blob/main/docs/models/timers.md) |

### Model Licensing

Pre-trained models are licensed under **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International** (CC BY-NC-SA 4.0) due to training data constraints.

### Downloading Models

```python
import openwakeword

# Download all pre-trained models
openwakeword.utils.download_models()

# Download specific models
openwakeword.utils.download_models(model_names=["alexa", "hey_jarvis"])
```

## Installation

### pip Installation

```bash
# Basic installation
pip install openwakeword

# With microphone support
pip install openwakeword pyaudio

# For Speex noise suppression (Linux only)
sudo apt-get install libspeexdsp-dev
pip install https://github.com/dscripka/openWakeWord/releases/download/v0.1.1/speexdsp_ns-0.1.2-cp38-cp38-linux_aarch64.whl
```

### Dependencies

| Platform | Inference Framework |
|----------|---------------------|
| Linux | onnxruntime + tflite-runtime |
| Windows | onnxruntime only |
| macOS | onnxruntime |

### Docker Installation

```bash
# Basic container
docker run -d \
  --name openwakeword \
  -p 10400:10400 \
  rhasspy/wyoming-openwakeword \
  --preload-model 'ok_nabu'

# With custom models
docker run -d \
  --name openwakeword \
  -p 10400:10400 \
  -v /path/to/models:/custom \
  rhasspy/wyoming-openwakeword \
  --preload-model 'ok_nabu' \
  --custom-model-dir /custom
```

### From Source

```bash
git clone https://github.com/dscripka/openWakeWord.git
cd openWakeWord
pip install -e .
```

## Basic Usage

### Python API

```python
import openwakeword
from openwakeword.model import Model

# Download models (one-time)
openwakeword.utils.download_models()

# Load model(s)
model = Model(
    wakeword_models=["hey_jarvis"],  # or leave empty for all models
    inference_framework="tflite"      # or "onnx"
)

# Process audio frame (80ms of 16kHz 16-bit PCM)
# frame should be numpy array or bytes
prediction = model.predict(audio_frame)

# Check detection
for wake_word, score in prediction.items():
    if score > 0.5:  # threshold
        print(f"Detected: {wake_word} (score: {score:.2f})")
```

### Microphone Detection Example

```python
import pyaudio
import numpy as np
from openwakeword.model import Model

# Audio settings
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1280  # 80ms at 16kHz

# Initialize
audio = pyaudio.PyAudio()
model = Model(wakeword_models=["hey_jarvis"])

# Open microphone stream
stream = audio.open(
    format=FORMAT,
    channels=CHANNELS,
    rate=RATE,
    input=True,
    frames_per_buffer=CHUNK
)

print("Listening for wake word...")

try:
    while True:
        # Read audio frame
        audio_data = stream.read(CHUNK, exception_on_overflow=False)
        audio_array = np.frombuffer(audio_data, dtype=np.int16)

        # Get prediction
        prediction = model.predict(audio_array)

        # Check for detection
        for wake_word, score in prediction.items():
            if score > 0.5:
                print(f"Wake word detected: {wake_word} ({score:.2f})")

except KeyboardInterrupt:
    print("Stopping...")
finally:
    stream.stop_stream()
    stream.close()
    audio.terminate()
```

### Processing Audio Files

```python
from openwakeword.model import Model

model = Model(wakeword_models=["hey_jarvis"])

# Single file
results = model.predict_clip("path/to/audio.wav")
print(results)

# Bulk processing with multiprocessing
from openwakeword.utils import bulk_predict

results = bulk_predict(
    file_paths=["file1.wav", "file2.wav", "file3.wav"],
    wakeword_models=["hey_jarvis"],
    ncpu=4
)
```

## Advanced Configuration

### Model Parameters

```python
model = Model(
    wakeword_models=["hey_jarvis", "alexa"],
    inference_framework="tflite",      # "tflite" or "onnx"
    enable_speex_noise_suppression=True,  # Linux only
    vad_threshold=0.5,                 # Voice activity detection (0-1)
    device="cpu"                       # "cpu" or "gpu"
)
```

### Noise Suppression

Enable Speex noise suppression for noisy environments:

```python
model = Model(
    wakeword_models=["hey_jarvis"],
    enable_speex_noise_suppression=True
)
```

**Note**: Only available on x86 and ARM64 Linux.

### Voice Activity Detection (VAD)

Reduce false positives with built-in Silero VAD:

```python
model = Model(
    wakeword_models=["hey_jarvis"],
    vad_threshold=0.5  # Only activate when speech detected
)
```

### Threshold Tuning

Default threshold is 0.5, but adjust based on your environment:

```python
# More sensitive (more detections, more false positives)
threshold = 0.3

# Less sensitive (fewer detections, fewer false positives)
threshold = 0.7

# Check detection
if prediction["hey_jarvis"] > threshold:
    print("Detected!")
```

## Home Assistant Integration

### Add-on Installation (Easiest)

1. Go to **Settings** → **Add-ons**
2. Click **Add-on Store**
3. Search for "openWakeWord"
4. Click **Install**
5. Start the add-on
6. Go to **Settings** → **Devices & Services**
7. The Wyoming integration should auto-discover it

### Manual Wyoming Integration

```bash
# Start wyoming-openwakeword
docker run -d \
  --name wyoming-openwakeword \
  -p 10400:10400 \
  --restart unless-stopped \
  rhasspy/wyoming-openwakeword \
  --preload-model 'ok_nabu'
```

Then in Home Assistant:
1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for **Wyoming Protocol**
4. Enter host IP and port `10400`

### Voice Assistant Pipeline

| Component | Service | Port |
|-----------|---------|------|
| **Wake Word** | **openWakeWord** | **10400** |
| Speech-to-Text | Whisper | 10300 |
| Text-to-Speech | Piper | 10200 |

### Wyoming Satellite Setup

For remote microphones:

```bash
# Install wyoming-satellite
git clone https://github.com/rhasspy/wyoming-satellite.git
cd wyoming-satellite

# Run with openWakeWord
script/run \
  --name 'living-room' \
  --uri 'tcp://0.0.0.0:10700' \
  --mic-command 'arecord -r 16000 -c 1 -f S16_LE -t raw' \
  --snd-command 'aplay -r 22050 -c 1 -f S16_LE -t raw' \
  --wake-uri 'tcp://localhost:10400' \
  --wake-word-name 'ok_nabu'
```

## Training Custom Wake Words

### Quick Training (Google Colab)

Use the official notebook: [automatic_model_training.ipynb](https://github.com/dscripka/openWakeWord/blob/main/notebooks/automatic_model_training.ipynb)

Training takes ~30-60 minutes on Google Colab with T4 GPU.

### Training Process Overview

1. **Generate Synthetic Clips**: Uses Piper TTS to create training audio
2. **Generate Negative Examples**: Background noise and non-target speech
3. **Train Classifier**: Small network on top of frozen backbone
4. **Export Model**: Converts to ONNX and TFLite formats

### Local Training (Linux Only)

```bash
# Clone repository
git clone https://github.com/dscripka/openWakeWord.git
cd openWakeWord

# Install training dependencies
pip install -e ".[train]"

# Run training notebook
jupyter notebook notebooks/automatic_model_training.ipynb
```

### Training Configuration

```python
# Example configuration
config = {
    "target_phrase": "hey computer",
    "n_samples": 5000,           # Synthetic clips to generate
    "n_background_samples": 10000,
    "epochs": 100,
    "batch_size": 256,
}
```

### Using Custom Models

```python
# Load custom model
model = Model(
    wakeword_models=["path/to/my_custom_model.tflite"]
)

# Or with Wyoming
docker run -d \
  -p 10400:10400 \
  -v /path/to/models:/custom \
  rhasspy/wyoming-openwakeword \
  --custom-model-dir /custom
```

## microWakeWord Alternative

For ESP32 and low-power devices, consider [microWakeWord](https://github.com/kahrendt/esphome-on-device-wake-word).

### Comparison

| Feature | openWakeWord | microWakeWord |
|---------|--------------|---------------|
| Target Hardware | Raspberry Pi, servers | ESP32-S3 |
| Processing Location | Server-side | On-device |
| Power Consumption | Higher | Very low |
| Latency | ~100ms | <20ms |
| Model Size | ~1MB+ | ~50KB |
| Multiple Models | 15-20 simultaneous | 3 simultaneous |

### When to Use Each

| Use Case | Recommendation |
|----------|----------------|
| Raspberry Pi voice assistant | openWakeWord |
| ESP32 satellite | microWakeWord |
| Battery-powered device | microWakeWord |
| Multiple wake words | openWakeWord |
| Lowest latency | microWakeWord |

## Systemd Service

### Create Service File

```ini
# /etc/systemd/system/openwakeword.service
[Unit]
Description=openWakeWord Wake Word Detection
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/wyoming-openwakeword
ExecStart=/home/pi/wyoming-openwakeword/script/run \
  --uri 'tcp://0.0.0.0:10400' \
  --preload-model 'ok_nabu'
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Enable Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable openwakeword
sudo systemctl start openwakeword
sudo systemctl status openwakeword
```

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| High false accepts | Increase threshold, enable VAD |
| Missed detections | Lower threshold, check mic quality |
| Slow performance | Use tflite instead of onnx |
| No audio detected | Check mic permissions, ALSA config |
| Model not found | Run `openwakeword.utils.download_models()` |

### Debug Mode

```bash
# Wyoming with debug logging
docker run rhasspy/wyoming-openwakeword \
  --preload-model 'ok_nabu' \
  --debug

# Python debug
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Audio Testing

```bash
# Check microphone
arecord -l

# Test recording
arecord -D plughw:1,0 -f S16_LE -r 16000 -c 1 -d 5 test.wav

# Play back
aplay test.wav
```

### Performance Tuning

```python
# Optimize for speed
model = Model(
    wakeword_models=["hey_jarvis"],
    inference_framework="tflite",  # Faster on most platforms
    vad_threshold=0.5,             # Reduce processing when no speech
)

# Process larger chunks for efficiency (tradeoff: higher latency)
CHUNK = 2560  # 160ms instead of 80ms
```

## Limitations

### Current Constraints

- **English only**: Best performance for English wake words
- **No JavaScript port**: Web apps need websocket streaming
- **Linux-only features**: Speex noise suppression
- **Model size**: Too large for microcontrollers (use microWakeWord)
- **Training**: Requires Linux for local training

### Not Suitable For

| Use Case | Alternative |
|----------|-------------|
| Microcontrollers | microWakeWord |
| Non-English languages | Limited support |
| Commercial deployment | Check CC BY-NC-SA license |
| Ultra-low latency (<10ms) | microWakeWord |

## Resources

### Official Documentation
- [GitHub Repository](https://github.com/dscripka/openWakeWord)
- [PyPI Package](https://pypi.org/project/openwakeword/)
- [HuggingFace Demo](https://huggingface.co/spaces/davidscripka/openWakeWord)
- [Pre-trained Models](https://huggingface.co/davidscripka/openwakeword)

### Training Resources
- [Training Notebook](https://github.com/dscripka/openWakeWord/blob/main/notebooks/automatic_model_training.ipynb)
- [Manual Training Guide](https://github.com/dscripka/openWakeWord/blob/main/notebooks/training_models.ipynb)

### Home Assistant Integration
- [Wyoming Protocol](https://www.home-assistant.io/integrations/wyoming/)
- [Wake Word Setup](https://www.home-assistant.io/voice_control/install_wake_word_add_on/)
- [Custom Wake Words](https://www.home-assistant.io/voice_control/create_wake_word/)
- [wyoming-openwakeword](https://github.com/rhasspy/wyoming-openwakeword)

### Related Projects
- [microWakeWord](https://github.com/kahrendt/esphome-on-device-wake-word) - ESP32 alternative
- [wyoming-satellite](https://github.com/rhasspy/wyoming-satellite) - Remote voice satellites
- [OpenVoiceOS Plugin](https://github.com/OpenVoiceOS/ovos-ww-plugin-openWakeWord)

### Community
- [Rhasspy Forum](https://community.rhasspy.org/)
- [Home Assistant Voice Forum](https://community.home-assistant.io/c/voice-assistant/)
