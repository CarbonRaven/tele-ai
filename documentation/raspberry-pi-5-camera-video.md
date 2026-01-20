# Raspberry Pi 5 Camera Modules & Video Capabilities

## Camera Interface

### MIPI CSI-2 Connectors

The Pi 5 features **two 4-lane MIPI CSI-2 camera connectors**, a significant upgrade from previous models.

| Specification | Pi 4 | Pi 5 |
|---------------|------|------|
| Connectors | 1 camera, 1 display | 2 camera/display (shared) |
| Lanes per connector | 2 | 4 |
| Connector type | 15-pin | 22-pin (same as Pi Zero) |
| Max bandwidth | 1 Gbps/lane | 1 Gbps/lane (4 Gbps total) |

**Important**: Pi 5 uses a different cable than Pi 4. You need a **22-pin to 15-pin adapter cable** (often included with newer cameras).

### Connector Locations

- **CAM/DISP0** and **CAM/DISP1**: Located between micro-HDMI and Ethernet ports
- Either connector can be used for camera or display
- Supports simultaneous dual cameras

## Official Raspberry Pi Cameras

### Camera Module 3 (Recommended)

The latest official camera with autofocus and HDR support.

| Specification | Details |
|---------------|---------|
| Sensor | Sony IMX708 |
| Resolution | 11.9MP (4608 × 2592) |
| Pixel Size | 1.4μm × 1.4μm |
| Autofocus | Phase Detection (PDAF) |
| HDR | Yes (up to 3MP output) |
| Field of View | 75° (standard) / 120° (wide) |
| Dimensions | 25 × 24 × 11.5mm |

#### Video Modes

| Resolution | Max FPS | Notes |
|------------|---------|-------|
| 4608 × 2592 | 14 fps | Full resolution |
| 2304 × 1296 | 56 fps | HDR supported at 30fps |
| 1536 × 864 | 120 fps | High speed |
| 1080p | 50 fps | Full HD |
| 720p | 100 fps | HD |

#### Variants

| Model | Lens | IR Filter | Use Case |
|-------|------|-----------|----------|
| Standard | 75° | Yes | General purpose |
| Wide | 120° | Yes | Wide angle shots |
| NoIR | 75° | No | Night vision (with IR lights) |
| Wide NoIR | 120° | No | Wide angle night vision |

#### Autofocus Modes

```bash
# Fixed focus at infinity
rpicam-still --lens-position 0.0 -o image.jpg

# Fixed focus at ~10cm (macro)
rpicam-still --lens-position 10.0 -o image.jpg

# Continuous autofocus
rpicam-vid --autofocus-mode continuous -o video.h264

# Autofocus on capture
rpicam-still --autofocus-on-capture -o image.jpg
```

### High Quality (HQ) Camera

Professional-grade camera with interchangeable lenses.

| Specification | Details |
|---------------|---------|
| Sensor | Sony IMX477 |
| Resolution | 12.3MP (4056 × 3040) |
| Pixel Size | 1.55μm × 1.55μm |
| Lens Mount | C/CS-mount or M12 |
| Max Exposure | 670.74 seconds |
| IR Filter | Hoya CM500 (removable) |
| External Trigger | Yes (for multi-camera sync) |

**Best for**: High-resolution photography, astrophotography, professional video

### Global Shutter Camera

Specialized camera for fast motion capture.

| Specification | Details |
|---------------|---------|
| Sensor | Sony IMX296 |
| Resolution | 1.6MP |
| Pixel Size | 3.45μm × 3.45μm |
| Shutter Type | Global (no rolling shutter artifacts) |
| Min Exposure | 30μs |
| Lens Mount | C/CS-mount |
| Dimensions | 38 × 38 × 19.8mm |

**Best for**: Machine vision, fast motion capture, barcode scanning, robotics

### Camera Comparison

| Feature | Camera Module 3 | HQ Camera | Global Shutter |
|---------|-----------------|-----------|----------------|
| Resolution | 11.9MP | 12.3MP | 1.6MP |
| Autofocus | Yes (PDAF) | No (manual lens) | No (manual lens) |
| HDR | Yes | No | No |
| Interchangeable Lens | No | Yes (C/CS) | Yes (C/CS) |
| Best For | General use | High quality | Fast motion |
| Price | ~$25-35 | ~$50 | ~$50 |

## Video Encoding/Decoding (Critical Limitation)

### Hardware Codec Support

| Codec | Decode | Encode | Notes |
|-------|--------|--------|-------|
| **H.265/HEVC** | Hardware (4K) | Software only | Only HW-accelerated codec |
| **H.264/AVC** | Software | Software | No hardware support |
| **VP9** | Software | Software | - |
| **AV1** | Software | Software | - |

**Major Change from Pi 4**: The Pi 5 removed the legacy H.264 hardware encoder/decoder that existed since Pi 1. This was a deliberate design decision because the CPU can now handle software decode faster than the old 15-year-old hardware block.

### Performance Impact

| Task | Pi 5 Performance |
|------|------------------|
| H.264 software decode | Faster than Pi 4 HW decode |
| H.264 software encode | ~4K25 (exceeds old HW block's 1080p50) |
| H.265 hardware decode | Up to 4Kp60 |
| H.265 encode | Software only |

### Implications

- **NVR/Surveillance**: Most IP cameras output H.264; Pi 5 must decode in software
- **Jellyfin/Plex**: Hardware transcoding deprecated; falls back to CPU
- **Frigate**: Running multiple H.264 streams is CPU-intensive
- **Streaming**: Consider H.265 sources when possible

## Camera Software Stack

### libcamera

The open-source camera library that replaced the legacy `raspicam` stack.

- Provides C++ API for camera configuration
- Handles image buffers in system memory
- Supports still image and video encoding
- Auto-detects Pi cameras on boot

### rpicam-apps (Command Line)

Pre-installed camera applications for capture and streaming.

| Application | Purpose |
|-------------|---------|
| `rpicam-hello` | Preview stream (test camera) |
| `rpicam-jpeg` | Capture JPEG still images |
| `rpicam-still` | Full-featured still capture |
| `rpicam-vid` | Video recording |
| `rpicam-raw` | RAW image capture |

**Note**: Renamed from `libcamera-*` to `rpicam-*` in Bookworm. Symbolic links maintain backward compatibility.

#### Common Commands

```bash
# Test camera with preview
rpicam-hello

# Capture still image
rpicam-still -o image.jpg

# Record 10 seconds of video
rpicam-vid -t 10000 -o video.h264

# Record with specific resolution
rpicam-vid --width 1920 --height 1080 -o video.h264

# Stream to network (RTSP requires additional setup)
rpicam-vid -t 0 --inline -o - | cvlc stream:///dev/stdin --sout '#rtp{sdp=rtsp://:8554/stream}'
```

### Picamera2 (Python)

The official Python library for camera control, replacing the legacy `picamera`.

```bash
# Install (recommended via apt)
sudo apt install python3-picamera2
```

```python
from picamera2 import Picamera2
import time

# Initialize camera
picam2 = Picamera2()

# Capture still image
picam2.start()
time.sleep(1)
picam2.capture_file("image.jpg")
picam2.stop()

# Record video
picam2.start_and_record_video("video.mp4", duration=5)
```

**Compatibility**: Requires Raspberry Pi OS Bullseye or later. Pre-installed on full Raspberry Pi OS (not Lite).

## Multi-Camera Support

### Dual Camera Setup

Pi 5 supports two cameras simultaneously via CAM/DISP0 and CAM/DISP1.

```bash
# List available cameras
rpicam-hello --list-cameras

# Use specific camera
rpicam-still --camera 0 -o cam0.jpg
rpicam-still --camera 1 -o cam1.jpg
```

### Camera Multiplexers

CSI2 multiplexer boards (e.g., Arducam) allow connecting more cameras, but only 2 can stream simultaneously.

## AI Camera Integration

When paired with AI HAT+ (Hailo NPU), the camera software natively supports AI acceleration:

- `rpicam-apps` automatically uses NPU for post-processing
- Object detection, pose estimation run on Hailo
- Frees CPU for other tasks

## Third-Party Camera Compatibility

Many third-party cameras work with Pi 5 via the MIPI CSI interface:

| Manufacturer | Notable Models |
|--------------|----------------|
| Arducam | 16MP, 64MP, PTZ cameras |
| Waveshare | Various IMX sensors |
| InnoMaker | Industrial cameras |

**Requirement**: Must have libcamera driver support

## Resources

- [Official Camera Documentation](https://www.raspberrypi.com/documentation/accessories/camera.html)
- [Camera Software Documentation](https://www.raspberrypi.com/documentation/computers/camera_software.html)
- [Camera Module 3 Product Brief (PDF)](https://datasheets.raspberrypi.com/camera/camera-module-3-product-brief.pdf)
- [Picamera2 GitHub](https://github.com/raspberrypi/picamera2)
- [Arducam libcamera Guide](https://docs.arducam.com/Raspberry-Pi-Camera/Native-camera/Libcamera-User-Guide/)
