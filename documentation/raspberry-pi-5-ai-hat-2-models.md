# Raspberry Pi AI HAT+ 2: Supported AI Models

## Overview

The Raspberry Pi AI HAT+ 2 is built around the **Hailo-10H** neural network accelerator, specifically designed for generative AI workloads including Large Language Models (LLMs) and Vision-Language Models (VLMs).

### Hardware Specifications

| Specification | Details |
|---------------|---------|
| Accelerator | Hailo-10H |
| Performance | 40 TOPS (INT4) |
| Dedicated RAM | 8GB LPDDR4X |
| Power Consumption | <3.5W typical |
| Interface | PCIe Gen 3 x1 |
| Price | $130 |

**Key Difference from AI HAT+**: The 8GB dedicated on-board RAM enables running much larger models (up to ~3B parameters) compared to the original AI HAT+ which relied on shared system memory.

## Supported Large Language Models (LLMs)

### Official Hailo Model Zoo LLMs

These models are pre-compiled and available in the Hailo Gen-AI Model Zoo:

| Model | Parameters | Size | Use Case |
|-------|------------|------|----------|
| qwen2:1.5b | 1.5B | ~1.5GB | General chat |
| qwen2.5:1.5b | 1.5B | ~1.5GB | General chat (improved) |
| qwen2.5-coder:1.5b | 1.5B | ~1.5GB | Code generation |
| llama3.2:1b | 1B | ~1GB | General chat |
| deepseek_r1:1.5b | 1.5B | ~1.5GB | Reasoning tasks |

### Additional Supported Models (INT4 Quantized)

Larger models can run with INT4 quantization:

| Model | Parameters | Notes |
|-------|------------|-------|
| Llama 2 | 7B | ~10 tokens/sec |
| Llama 3 | 8B | Requires INT4 quantization |
| Llama 3.2 | 3B | Instruct version supported |
| Phi-2 | 2.7B | Microsoft small language model |

**Quantization Requirement**: All models must use INT4 quantization and be compiled to Hailo Executable Format (HEF) using the Hailo Dataflow Compiler.

### LLM Performance Benchmarks

| Model Size | Token Rate | First Token Latency |
|------------|------------|---------------------|
| 1B-1.5B params | 5-15 tokens/sec | <1 second |
| 3B params | 1.5-5 tokens/sec | 1-2 seconds |
| 7B params | ~10 tokens/sec | ~2 seconds |

**Reality Check**: While Hailo claims up to 10 tokens/sec for 7B models, real-world testing shows the Raspberry Pi 5's ARM CPU can match or exceed the Hailo-10H on many LLM workloads. The Hailo's advantage is lower power consumption (~3W vs ~10W for CPU) and freeing the CPU for other tasks.

## Vision-Language Models (VLMs)

### Supported VLMs

| Model | Parameters | Capability |
|-------|------------|------------|
| Qwen2.5-VL | 3B | Image understanding + text |
| Llama-3.2-Vision | 3B | Multimodal instruct model |

### VLM Capabilities

- Image captioning
- Visual question answering
- Scene understanding
- Document analysis
- Live camera input processing

**Note**: VLM performance with live camera input is functional but response quality is typically lower than cloud-based alternatives. Best suited for constrained, domain-specific applications.

## Computer Vision Models

The AI HAT+ 2 delivers excellent performance for traditional computer vision tasks, offering significant speedups over CPU-only processing.

### Object Detection

| Model | Performance | Notes |
|-------|-------------|-------|
| YOLOv5 | Real-time | Multiple sizes (n, s, m, l) |
| YOLOv8 | Real-time | Latest generation |
| YOLOv11 | ~30 FPS | 10x speedup vs CPU |
| YOLOv12n | Real-time | Newest addition |
| SSD MobileNet | Real-time | Lightweight |

### Classification

| Model | Supported Platforms |
|-------|---------------------|
| MobileNet v1/v2/v3 | All Hailo devices |
| EfficientNet | Hailo-10H, 15H |
| PoolFormer s12 | Hailo-10H, 15H |
| ResNet | All Hailo devices |

### Segmentation

| Model | Type |
|-------|------|
| DeepLab v3+ | Semantic segmentation |
| U-Net | Medical/general segmentation |
| YOLO Segmentation | Instance segmentation |

### Depth Estimation

| Model | Supported |
|-------|-----------|
| StereoNet | Hailo-10H and Hailo-15H only |
| MiDaS | Monocular depth |

### Vision Transformers & CLIP

| Model | Resolution | Notes |
|-------|------------|-------|
| CLIP ViT-Base-16 | Various | Zero-shot classification |
| CLIP ViT-Base-32 | Various | Language-image pre-training |
| CLIP ViT-Large-14 | 336x336 | Hailo-10H/15H only |
| SigLIP | Various | Improved CLIP variant |

### Other Vision Tasks

| Task | Models |
|------|--------|
| Pose Estimation | HRNet, PoseNet |
| Face Detection | RetinaFace, SCRFD |
| Face Recognition | ArcFace |
| OCR | PaddleOCR v5 (mobile) |
| Super Resolution | Real-ESRGAN x4 |

## Generative AI Models

### Image Generation

| Model | Performance | Notes |
|-------|-------------|-------|
| Stable Diffusion 2.1 | ~5 sec/image | Basic image generation |

**Limitation**: Image generation is significantly slower than dedicated GPUs. Best for occasional use, not production workloads.

## Model Deployment

### Installation Steps

1. **Install Hailo Software**
   ```bash
   # Download hailo-model-zoo-genai for Raspberry Pi 5
   # Version 5.1.1 or later
   sudo dpkg -i hailo-model-zoo-genai_*.deb
   ```

2. **Start hailo-ollama Server**
   ```bash
   # Start the Ollama-compatible API server
   hailo-ollama serve
   ```

3. **Pull and Run Models**
   ```bash
   # Pull a model
   curl http://localhost:11434/api/pull -d '{"name": "qwen2.5:1.5b"}'

   # Send a query
   curl http://localhost:11434/api/generate -d '{
     "model": "qwen2.5:1.5b",
     "prompt": "Hello, how are you?"
   }'
   ```

### Optional: Open WebUI

For a browser-based chat interface:

```bash
# Run Open WebUI in Docker
docker run -d -p 3000:8080 \
  --add-host=host.docker.internal:host-gateway \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  -v open-webui:/app/backend/data \
  ghcr.io/open-webui/open-webui:main
```

Access at `http://<pi-ip>:3000`

**Note**: Open WebUI requires Docker because it's incompatible with Python 3.13 on Raspberry Pi OS Trixie.

### Using Hailo Model Zoo for Vision

```bash
# Clone examples repository
git clone https://github.com/hailo-ai/hailo-rpi5-examples.git

# Run object detection example
python3 hailo-rpi5-examples/basic_pipelines/detection.py
```

## Performance Comparison

### AI HAT+ 2 vs CPU vs Original AI HAT+

| Workload | AI HAT+ 2 | Pi 5 CPU | AI HAT+ (26T) |
|----------|-----------|----------|---------------|
| LLM 1.5B (tokens/sec) | 5-15 | 5-12 | N/A |
| LLM 7B (tokens/sec) | ~10 | ~8 | N/A |
| YOLOv11m (FPS) | ~30 | ~3 | ~25 |
| Power (typical) | 3W | 10W | 2W |
| Dedicated RAM | 8GB | Shared | None |

**Key Insight**: For LLMs, the AI HAT+ 2's main advantage is **offloading** work from the CPU, not raw speed. This matters for robotics and projects where the CPU needs to handle GPIO, sensors, or other tasks simultaneously.

## Use Cases

### Best Suited For

| Use Case | Why It Works |
|----------|--------------|
| Offline voice assistants | Low latency, no cloud dependency |
| Robotics | Frees CPU for motor control |
| Battery-powered devices | Low 3W power consumption |
| Secure/private AI | No data leaves the device |
| Edge kiosks | Predictable latency |
| Real-time object detection | 10x speedup vs CPU |
| Document/image analysis | Local VLM processing |

### Not Recommended For

| Use Case | Why |
|----------|-----|
| Complex reasoning | 1-7B models have limited knowledge |
| Creative writing | Quality gap vs cloud LLMs |
| High-volume generation | Image generation is slow |
| Multi-user servers | Limited concurrent capacity |
| Tasks requiring >7B models | RAM/quantization limits |

## Limitations

### Model Constraints

- **Maximum Parameters**: ~7B (with INT4 quantization)
- **Optimal Range**: 1-3B parameters
- **Accuracy Trade-off**: INT4 quantization provides 90-95% of FP16 baseline accuracy
- **Model Availability**: Only models compiled for Hailo runtime work; cannot run arbitrary GGUF/ONNX models directly

### Quality Considerations

- Small LLMs (1-7B) have significantly reduced knowledge compared to cloud models (500B-2T parameters)
- Best for constrained, domain-specific tasks rather than general knowledge
- VLM responses may be lower quality than expected
- Consider fine-tuning with LoRA for specific use cases

## Resources

### Official Documentation
- [Raspberry Pi AI HAT+ 2 Product Page](https://www.raspberrypi.com/products/ai-hat-plus-2/)
- [AI Software Documentation](https://www.raspberrypi.com/documentation/computers/ai.html)
- [Hailo Developer Zone](https://hailo.ai/developer-zone/)

### Model Repositories
- [Hailo Model Zoo (GitHub)](https://github.com/hailo-ai/hailo_model_zoo)
- [Hailo Model Explorer](https://hailo.ai/products/hailo-software/model-explorer/)
- [Hailo RPi5 Examples](https://github.com/hailo-ai/hailo-rpi5-examples)

### Community & Guides
- [Hackster.io AI HAT+ 2 Review](https://www.hackster.io/news/gen-ai-on-your-raspberry-pi-a-hands-on-review-of-the-raspberry-pi-ai-hat-2-3c829a8894dd)
- [Jeff Geerling's AI HAT+ 2 Testing](https://www.jeffgeerling.com/blog/2026/raspberry-pi-ai-hat-2/)
- [Hailo Community Forum](https://community.hailo.ai/)
- [Tom's Hardware Review](https://www.tomshardware.com/raspberry-pi/raspberry-pi-ai-hat-plus-2-review)

### Benchmarks
- [Face of IT Compatibility Guide](https://www.faceofit.com/raspberry-pi-ai-hat-2-compatibility/)
- [Hardware Corner LLM Analysis](https://www.hardware-corner.net/local-llms-raspberry-pi-ai-hat-plus-2/)
