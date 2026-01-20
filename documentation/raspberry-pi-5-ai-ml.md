# Raspberry Pi 5 AI & Machine Learning Capabilities

## Overview

The Raspberry Pi 5 does **not** have a built-in Neural Processing Unit (NPU). However, its improved CPU performance (2-3x faster than Pi 4), PCIe 2.0 interface, and better USB 3.0 controller make it an excellent platform for AI/ML workloads when paired with external accelerators.

**Key Limitation**: The Pi 5 can only run inference on pre-trained models. Training neural networks is not practical due to limited compute resources.

## Native CPU Performance for ML

### TensorFlow / TensorFlow Lite

| Metric | Pi 4 | Pi 5 | Improvement |
|--------|------|------|-------------|
| Full TensorFlow | Baseline | ~5x faster | Significant |
| TensorFlow Lite | Baseline | ~5x faster | Significant |

- TensorFlow Lite is the recommended framework for edge deployment
- Pi 5 now offers similar performance to Coral TPU for some workloads
- Optimized for ARM architecture

### PyTorch

- Out-of-box support via `pip install torch torchvision`
- MobileNet v2 runs at 30-40 fps on CPU
- No lite version available; higher resource usage than TensorFlow Lite
- **Tip**: Export models to ONNX for better performance with ncnn or MNN

### Other Supported Frameworks

| Framework | Best For |
|-----------|----------|
| **TensorFlow Lite** | Edge deployment, production use |
| **PyTorch Mobile** | Rapid prototyping, computer vision |
| **OpenVINO** | Optimized inference, real-time processing |
| **ncnn** | ARM-optimized C++ inference |
| **MNN** | Mobile/embedded neural networks |
| **OpenCV DNN** | Multi-format model support (TF, Caffe, ONNX, Darknet) |

## AI Accelerator Options

### Raspberry Pi AI HAT+ (Recommended)

The official AI expansion board with integrated Hailo accelerator.

| Variant | NPU Chip | Performance | Price | Interface |
|---------|----------|-------------|-------|-----------|
| AI HAT+ 13 TOPS | Hailo-8L | 13 TOPS | ~$70 | PCIe Gen 2 |
| AI HAT+ 26 TOPS | Hailo-8 | 26 TOPS | $110 | PCIe Gen 3 |

**Features**:
- Direct PCB integration (better thermal management)
- Auto-detected by Raspberry Pi OS
- Native support in `rpicam-apps`
- Supported frameworks: TensorFlow, TensorFlow Lite, ONNX, Keras, PyTorch
- 3-4 TOPS/W efficiency
- Production availability guaranteed until January 2030

**Applications**:
- Object detection
- Semantic/instance segmentation
- Pose estimation
- Face recognition
- Security systems
- Robotics

### Raspberry Pi AI HAT+ 2 (Latest - 2026)

| Specification | Details |
|---------------|---------|
| NPU | Hailo-10H |
| Performance | 40 TOPS |
| Dedicated AI RAM | 8GB LPDDR4X |
| New Capability | Large Language Models (LLMs) |

**Supported LLMs**:
- DeepSeek-R1-Distill
- Llama 3.2
- Qwen family

**Key Advancement**: Moves beyond computer vision to support multimodal AI and language models locally on the device.

### Raspberry Pi AI Kit (Discontinued)

| Specification | Details |
|---------------|---------|
| NPU | Hailo-8L |
| Performance | 13 TOPS |
| Form Factor | M.2 2242 on M.2 HAT+ |
| Status | No longer in production |

**Note**: Replaced by AI HAT+ series. Functionally equivalent to AI HAT+ 13 TOPS.

### Google Coral TPU

| Product | Interface | Performance |
|---------|-----------|-------------|
| Coral USB Accelerator | USB 3.0 | 4 TOPS |
| Coral M.2 Accelerator | M.2 (via HAT) | 4 TOPS |
| Coral Dual Edge TPU | M.2 | 8 TOPS |

**Compatibility Notes**:
- Works with Pi 5 but requires workarounds
- PyCoral library only supports Python 3.6-3.9
- Google has largely abandoned Coral project (no updates 2021-2025)
- May require Docker with older Debian or Pi OS Bullseye
- 10-15x faster inference vs CPU when working
- Power issues possible; use powered USB hub

**Recommendation**: For new projects, prefer Hailo-based AI HAT+ over Coral due to better Pi 5 integration and active support.

## Performance Comparison

| Accelerator | TOPS | Power Efficiency | Pi 5 Integration |
|-------------|------|------------------|------------------|
| CPU Only (Pi 5) | ~0.5 | Low | Native |
| Coral USB | 4 | Medium | Requires workarounds |
| AI HAT+ 13T | 13 | High (3-4 TOPS/W) | Excellent |
| AI HAT+ 26T | 26 | High | Excellent |
| AI HAT+ 2 | 40 | High | Excellent |

## Software Stack

### Raspberry Pi OS Integration

- Hailo accelerators auto-detected on boot
- `rpicam-apps` natively supports NPU acceleration
- No manual driver installation required (with up-to-date OS)

### Installation Commands

```bash
# TensorFlow Lite
pip install tflite-runtime

# PyTorch
pip install torch torchvision

# For Hailo (if not auto-configured)
sudo apt update
sudo apt install hailo-all
```

### Recommended Development Tools

- **Hailo Model Zoo**: Pre-trained models optimized for Hailo
- **Hailo Dataflow Compiler**: Convert models for Hailo NPU
- **TensorFlow Lite Model Maker**: Create edge-optimized models

## Use Cases

| Application | Recommended Setup |
|-------------|-------------------|
| Object Detection | AI HAT+ 13T or 26T |
| Pose Estimation | AI HAT+ 13T or 26T |
| Face Recognition | AI HAT+ 13T or 26T |
| LLM Inference | AI HAT+ 2 (40 TOPS) |
| Real-time Video Processing | AI HAT+ 26T |
| Low-power IoT | AI HAT+ 13T |
| Legacy/Budget Projects | Coral USB (with caveats) |

## Resources

### Official Documentation
- [Raspberry Pi AI HATs Documentation](https://www.raspberrypi.com/documentation/accessories/ai-hat-plus.html)
- [AI HAT+ Product Brief (PDF)](https://datasheets.raspberrypi.com/ai-hat-plus/raspberry-pi-ai-hat-plus-product-brief.pdf)

### Frameworks
- [PyTorch on Raspberry Pi Tutorial](https://docs.pytorch.org/tutorials/intermediate/realtime_rpi.html)
- [TensorFlow Lite for Microcontrollers](https://www.tensorflow.org/lite)
- [Hailo Developer Zone](https://hailo.ai/developer-zone/)

### Community Resources
- [Q-engineering Deep Learning Guides](https://qengineering.eu/deep-learning-with-raspberry-pi-and-alternatives.html)
- [Jeff Geerling's AI Kit Testing](https://www.jeffgeerling.com/blog/2024/testing-raspberry-pis-ai-kit-13-tops-70)
