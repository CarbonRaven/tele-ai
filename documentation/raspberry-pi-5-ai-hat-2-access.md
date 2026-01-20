# Accessing AI Models on Raspberry Pi AI HAT+ 2

## Overview

The Raspberry Pi AI HAT+ 2 provides multiple interfaces for accessing AI models, from simple REST APIs to low-level hardware access. This guide covers all available methods.

| Method | Use Case | Complexity |
|--------|----------|------------|
| REST API (hailo-ollama) | LLM chat, text generation | Easy |
| Open WebUI | Browser-based chat interface | Easy |
| picamera2 + Hailo | Camera-based inference | Medium |
| hailo-apps-infra | Custom vision pipelines | Medium |
| GStreamer/TAPPAS | Video streaming inference | Medium-Hard |
| HailoRT Python API | Direct hardware access | Hard |
| C++ API | Maximum performance | Hard |
| Command Line | Testing and benchmarks | Easy |

## 1. REST API (hailo-ollama)

The easiest way to access LLMs on the AI HAT+ 2. The hailo-ollama server provides an Ollama-compatible REST API.

### Installation

```bash
# Download and install Hailo GenAI package
# Get from Hailo Developer Zone (requires account)
sudo dpkg -i hailo-model-zoo-genai_5.1.1_arm64.deb
```

### Starting the Server

```bash
# Start hailo-ollama server (default port 8000)
hailo-ollama serve

# Or specify a different port
hailo-ollama serve --port 11434
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/tags` | GET | List available models |
| `/api/pull` | POST | Download a model |
| `/api/generate` | POST | Generate text completion |
| `/api/chat` | POST | Chat completion |
| `/api/embeddings` | POST | Generate embeddings |

### Pull a Model

```bash
curl http://localhost:8000/api/pull \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen2.5:1.5b",
    "stream": true
  }'
```

### Generate Text

```bash
curl http://localhost:8000/api/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen2.5:1.5b",
    "prompt": "Write a haiku about Raspberry Pi",
    "stream": false
  }'
```

### Chat Completion

```bash
curl http://localhost:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen2.5:1.5b",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "What is the capital of France?"}
    ]
  }'
```

### Python Example

```python
import requests

def chat(prompt, model="qwen2.5:1.5b"):
    response = requests.post(
        "http://localhost:8000/api/chat",
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }
    )
    return response.json()["message"]["content"]

# Usage
answer = chat("Explain quantum computing in simple terms")
print(answer)
```

### Available Models

```bash
# List models
curl http://localhost:8000/api/tags
```

| Model | Parameters | Best For |
|-------|------------|----------|
| `qwen2:1.5b` | 1.5B | General chat |
| `qwen2.5:1.5b` | 1.5B | Improved general chat |
| `qwen2.5-coder:1.5b` | 1.5B | Code generation |
| `llama3.2:1b` | 1B | General chat |
| `deepseek_r1:1.5b` | 1.5B | Reasoning tasks |

## 2. Open WebUI (Browser Interface)

A web-based chat interface that connects to hailo-ollama.

### Prerequisites

- Docker installed on Raspberry Pi 5
- hailo-ollama server running

### Installation

```bash
# Ensure hailo-ollama is running first
hailo-ollama serve &

# Run Open WebUI container
docker run -d \
  -e OLLAMA_BASE_URL=http://127.0.0.1:8000 \
  -v open-webui:/app/backend/data \
  --name open-webui \
  --network=host \
  --restart always \
  ghcr.io/open-webui/open-webui:main
```

### Access

Open browser to: `http://<raspberry-pi-ip>:8080`

### First-Time Setup

1. Create an admin account
2. Select a model from the dropdown
3. Start chatting

### Security Warning

Open WebUI binds to all network interfaces by default. For local-only access:

```bash
# Use localhost binding
docker run -d \
  -e OLLAMA_BASE_URL=http://127.0.0.1:8000 \
  -p 127.0.0.1:8080:8080 \
  -v open-webui:/app/backend/data \
  --name open-webui \
  --restart always \
  ghcr.io/open-webui/open-webui:main
```

## 3. Picamera2 + Hailo Python API

Direct integration with Raspberry Pi camera for real-time inference.

### Installation

```bash
# Install required packages
sudo apt update
sudo apt install -y python3-picamera2 python3-libcamera
pip install hailo-platform
```

### Object Detection Example

```python
from picamera2 import Picamera2
from hailo_platform import HEF, VDevice, ConfigureParams, InferVStreams, InputVStreamParams, OutputVStreamParams
import numpy as np

# Initialize camera
picam2 = Picamera2()
config = picam2.create_preview_configuration(
    main={"size": (640, 480), "format": "RGB888"},
    lores={"size": (320, 320), "format": "RGB888"}
)
picam2.configure(config)
picam2.start()

# Load Hailo model
hef = HEF("/usr/share/hailo-models/yolov8s_h8l.hef")
target = VDevice()
configure_params = ConfigureParams.create_from_hef(hef, interface=target)
network_group = target.configure(hef, configure_params)[0]
network_group_params = network_group.create_params()

# Create input/output streams
input_vstreams_params = InputVStreamParams.make(network_group)
output_vstreams_params = OutputVStreamParams.make(network_group)

# Inference loop
with InferVStreams(network_group, input_vstreams_params, output_vstreams_params) as pipeline:
    while True:
        # Capture frame
        frame = picam2.capture_array("lores")

        # Preprocess (normalize)
        input_data = frame.astype(np.float32) / 255.0
        input_data = np.expand_dims(input_data, axis=0)

        # Run inference
        results = pipeline.infer({input_vstreams_params[0].name(): input_data})

        # Process results
        detections = results[output_vstreams_params[0].name()]
        # ... handle detections
```

### Official Picamera2 Hailo Example

```bash
# Clone official examples
git clone https://github.com/raspberrypi/picamera2
cd picamera2/examples/hailo

# Run detection example
python3 detect.py
```

## 4. hailo-apps-infra (Vision Pipelines)

High-level Python API for building vision applications.

### Installation

```bash
# Clone repository
git clone https://github.com/hailo-ai/hailo-apps-infra.git
cd hailo-apps-infra
pip install -e .

# Also install RPi5 examples
git clone https://github.com/hailo-ai/hailo-rpi5-examples.git
```

### Detection Pipeline Example

```python
from hailo_apps_infra.gstreamer_app import GStreamerDetectionApp, app_callback_class

class MyCallback(app_callback_class):
    def __init__(self):
        super().__init__()

    def callback(self, pad, info, user_data):
        # Get detection results
        buffer = info.get_buffer()
        detections = self.get_detections(buffer)

        for detection in detections:
            label = detection.label
            confidence = detection.confidence
            bbox = detection.bbox  # (x_min, y_min, x_max, y_max)
            print(f"Detected: {label} ({confidence:.2f})")

        return True

# Run detection app
app = GStreamerDetectionApp(
    callback=MyCallback(),
    model_path="/usr/share/hailo-models/yolov8s_h8l.hef"
)
app.run()
```

### Running Built-in Examples

```bash
cd hailo-rpi5-examples

# Object detection
python basic_pipelines/detection.py

# Pose estimation
python basic_pipelines/pose_estimation.py

# Instance segmentation
python basic_pipelines/instance_segmentation.py

# With custom input source
python basic_pipelines/detection.py --input /path/to/video.mp4
python basic_pipelines/detection.py --input /dev/video0  # USB camera
```

### Input Source Options

| Option | Description |
|--------|-------------|
| (none) | Auto-detect camera |
| `--input rpi` | Raspberry Pi Camera Module |
| `--input usb` | USB webcam |
| `--input /path/to/file.mp4` | Video file |
| `--input rtsp://...` | RTSP stream (requires modification) |

## 5. GStreamer Pipelines

Direct GStreamer pipeline construction for maximum flexibility.

### Basic Detection Pipeline

```bash
gst-launch-1.0 \
  libcamerasrc ! \
  video/x-raw,width=640,height=480,framerate=30/1 ! \
  videoconvert ! \
  hailonet hef-path=/usr/share/hailo-models/yolov8s_h8l.hef ! \
  hailofilter so-path=/usr/lib/hailo-post-processes/libyolo_hailortpp_post.so ! \
  hailooverlay ! \
  videoconvert ! \
  autovideosink
```

### Key GStreamer Elements

| Element | Description |
|---------|-------------|
| `hailonet` | Runs inference on Hailo NPU |
| `hailofilter` | Post-processing with custom .so |
| `hailooverlay` | Draw bounding boxes/labels |
| `hailomuxer` | Combine multiple streams |
| `hailotracker` | Object tracking |

### Python GStreamer Example

```python
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

Gst.init(None)

pipeline_str = """
    libcamerasrc !
    video/x-raw,width=640,height=480 !
    videoconvert !
    hailonet hef-path=/usr/share/hailo-models/yolov8s_h8l.hef !
    hailofilter so-path=/usr/lib/hailo-post-processes/libyolo_hailortpp_post.so !
    hailooverlay !
    videoconvert !
    autovideosink
"""

pipeline = Gst.parse_launch(pipeline_str)
pipeline.set_state(Gst.State.PLAYING)

loop = GLib.MainLoop()
try:
    loop.run()
except KeyboardInterrupt:
    pass

pipeline.set_state(Gst.State.NULL)
```

## 6. HailoRT Python API (Low-Level)

Direct access to the Hailo runtime for maximum control.

### Installation

```bash
pip install hailort
```

### Minimal Inference Example

```python
from hailo_platform import (
    HEF, VDevice, HailoStreamInterface,
    ConfigureParams, InferVStreams,
    InputVStreamParams, OutputVStreamParams,
    FormatType
)
import numpy as np

# Load model
hef_path = "/usr/share/hailo-models/yolov8s_h8l.hef"
hef = HEF(hef_path)

# Get model info
input_vstream_info = hef.get_input_vstream_infos()[0]
output_vstream_info = hef.get_output_vstream_infos()[0]

print(f"Input shape: {input_vstream_info.shape}")
print(f"Output shape: {output_vstream_info.shape}")

# Create virtual device
with VDevice() as target:
    # Configure network
    configure_params = ConfigureParams.create_from_hef(
        hef,
        interface=HailoStreamInterface.PCIe
    )
    network_group = target.configure(hef, configure_params)[0]

    # Create stream parameters
    input_params = InputVStreamParams.make(
        network_group,
        format_type=FormatType.FLOAT32
    )
    output_params = OutputVStreamParams.make(
        network_group,
        format_type=FormatType.FLOAT32
    )

    # Run inference
    with InferVStreams(network_group, input_params, output_params) as pipeline:
        # Prepare input (example: random data)
        input_data = np.random.rand(1, 320, 320, 3).astype(np.float32)

        # Infer
        input_dict = {input_vstream_info.name: input_data}
        output = pipeline.infer(input_dict)

        # Get results
        result = output[output_vstream_info.name]
        print(f"Output shape: {result.shape}")
```

### Async Inference

```python
from hailo_platform import (
    HEF, VDevice, ConfigureParams,
    InputVStreams, OutputVStreams,
    InputVStreamParams, OutputVStreamParams
)
import numpy as np
from queue import Queue
from threading import Thread

def async_inference(hef_path, input_queue, output_queue):
    hef = HEF(hef_path)

    with VDevice() as target:
        network_group = target.configure(hef)[0]

        input_params = InputVStreamParams.make(network_group)
        output_params = OutputVStreamParams.make(network_group)

        with InputVStreams(network_group, input_params) as input_streams, \
             OutputVStreams(network_group, output_params) as output_streams:

            network_group.activate()

            while True:
                data = input_queue.get()
                if data is None:
                    break

                # Write input
                for stream, input_data in zip(input_streams, [data]):
                    stream.send(input_data)

                # Read output
                outputs = []
                for stream in output_streams:
                    outputs.append(stream.recv())

                output_queue.put(outputs)
```

## 7. Command Line Tools

### hailortcli

```bash
# Check device info
hailortcli fw-control identify

# Run inference benchmark
hailortcli run /path/to/model.hef

# Parse model info
hailortcli parse-hef /path/to/model.hef

# Monitor device
hailortcli monitor
```

### rpicam-apps with Hailo

```bash
# Detection with camera preview
rpicam-hello -t 0 \
  --post-process-file /usr/share/rpi-camera-assets/hailo_yolov8_inference.json

# Save detection video
rpicam-vid -t 10000 -o output.h264 \
  --post-process-file /usr/share/rpi-camera-assets/hailo_yolov8_inference.json
```

### Model Information

```bash
# List installed models
ls /usr/share/hailo-models/

# Get model details
hailortcli parse-hef /usr/share/hailo-models/yolov8s_h8l.hef
```

## 8. C++ API

For maximum performance in production applications.

### Example Structure

```cpp
#include "hailo/hailort.hpp"
#include <iostream>

int main() {
    // Create virtual device
    auto vdevice = hailort::VDevice::create();
    if (!vdevice) {
        std::cerr << "Failed to create VDevice" << std::endl;
        return 1;
    }

    // Load HEF
    auto hef = hailort::Hef::create("/path/to/model.hef");
    if (!hef) {
        std::cerr << "Failed to load HEF" << std::endl;
        return 1;
    }

    // Configure network group
    auto network_group = vdevice->configure(*hef);
    if (!network_group) {
        std::cerr << "Failed to configure" << std::endl;
        return 1;
    }

    // Create input/output streams and run inference
    // ... (see Hailo Application Code Examples for full examples)

    return 0;
}
```

### Build Example

```bash
# Install development headers
sudo apt install libhailort-dev

# Compile
g++ -o inference inference.cpp \
    -I/usr/include/hailort \
    -lhailort \
    -std=c++17
```

### Resources

- [Hailo Application Code Examples](https://github.com/hailo-ai/Hailo-Application-Code-Examples)
- C++ examples in `runtime/cpp/` directory

## Performance Comparison

| Method | Latency | Throughput | CPU Usage |
|--------|---------|------------|-----------|
| REST API (LLM) | ~100ms | 5-15 tok/s | Low |
| picamera2 | ~30ms | 30+ FPS | Medium |
| GStreamer | ~25ms | 30+ FPS | Low |
| HailoRT Python | ~20ms | 40+ FPS | Medium |
| C++ API | ~15ms | 60+ FPS | Low |

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "Device not found" | Check PCIe connection, run `lspci` |
| "Model not compatible" | Verify HEF is compiled for H10 (not H8) |
| Permission denied | Add user to `hailo` group |
| Low performance | Enable Gen 3 PCIe in config.txt |
| hailo-ollama won't start | Check port not in use, verify model exists |

### Debug Commands

```bash
# Check Hailo device
lspci | grep Hailo
dmesg | grep hailo

# Check driver loaded
lsmod | grep hailo

# Test device
hailortcli fw-control identify

# Check logs
journalctl -u hailo-ollama -f
```

## Resources

### Official Documentation
- [Raspberry Pi AI Software](https://www.raspberrypi.com/documentation/computers/ai.html)
- [Hailo Developer Zone](https://hailo.ai/developer-zone/)
- [HailoRT Documentation](https://hailo.ai/developer-zone/documentation/hailort/)

### GitHub Repositories
- [hailo-rpi5-examples](https://github.com/hailo-ai/hailo-rpi5-examples)
- [hailo-apps-infra](https://github.com/hailo-ai/hailo-apps-infra)
- [hailo-apps](https://github.com/hailo-ai/hailo-apps)
- [TAPPAS](https://github.com/hailo-ai/tappas)
- [picamera2 Hailo examples](https://github.com/raspberrypi/picamera2/tree/main/examples/hailo)

### Community
- [Hailo Community Forum](https://community.hailo.ai/)
- [Raspberry Pi Forums](https://forums.raspberrypi.com/)
