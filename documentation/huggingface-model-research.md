# Hugging Face Models for Raspberry Pi 5 Voice Assistant

Research conducted: 2026-01-27

## Executive Summary

This document provides a comprehensive overview of AI models available on Hugging Face suitable for deployment on Raspberry Pi 5 (16GB RAM) with Hailo-10H NPU for a voice assistant application. Models are categorized by function with detailed specifications, performance metrics, and deployment recommendations.

---

## 1. Speech-to-Text (STT) Models

### 1.1 Whisper Variants

#### **Distil-Whisper Large-v3** ⭐ RECOMMENDED
- **Hugging Face**: `distil-whisper/distil-large-v3`
- **Parameters**: 756M (vs 1550M for Whisper large-v3)
- **Model Size**: ~1.5GB (FP16)
- **Performance**:
  - 6.3x faster than Whisper large-v3
  - 9.7% WER on short-form audio (vs 8.4% for large-v3)
  - Within 1% WER on long-form audio
- **Speed**: Optimized for real-time transcription
- **Formats Available**:
  - ✅ ONNX: `distil-whisper/distil-large-v3-onnx`
  - ✅ GGML (whisper.cpp): `distil-whisper/distil-large-v3-ggml`
  - ✅ CTranslate2 (faster-whisper): Native support
  - ✅ OpenAI format: `distil-whisper/distil-large-v3-openai`
- **Pi 5 Suitability**: ⭐⭐⭐⭐⭐ Excellent for CPU, perfect for Hailo acceleration
- **References**: [Model Card](https://huggingface.co/distil-whisper/distil-large-v3), [GitHub](https://github.com/huggingface/distil-whisper)

#### **Whisper Large-v3-Turbo**
- **Hugging Face**: `openai/whisper-large-v3-turbo`
- **Parameters**: 809M (reduced decoder: 4 layers vs 32)
- **Model Size**: ~1.6GB (FP16)
- **Performance**:
  - 6x faster than Whisper large-v3
  - Near state-of-the-art accuracy
  - 99 languages supported
- **Speed**: Significantly faster than full large-v3
- **Formats Available**:
  - ✅ PyTorch (Transformers)
  - ✅ ONNX (via optimum)
  - ✅ CTranslate2 compatible
- **Optimizations**: Flash Attention 2, torch.compile (4.5x speedup)
- **Pi 5 Suitability**: ⭐⭐⭐⭐ Very good, slight accuracy trade-off vs distil-large-v3
- **References**: [Model Card](https://huggingface.co/openai/whisper-large-v3-turbo), [Discussion](https://github.com/openai/whisper/discussions/2363)

#### **Distil-Whisper Large-v3.5** (Newer)
- **Hugging Face**: `distil-whisper/distil-large-v3.5`
- **Performance**:
  - 1.5x faster than Whisper-Large-v3-Turbo
  - Slightly better on short-form transcription
  - ~1% behind on long-form
- **Pi 5 Suitability**: ⭐⭐⭐⭐⭐ Latest optimizations
- **References**: [Model Card](https://huggingface.co/distil-whisper/distil-large-v3.5)

#### **Faster-Distil-Whisper-Large-v3** (Systran Optimized)
- **Hugging Face**: `Systran/faster-distil-whisper-large-v3`
- **Optimizations**: CTranslate2-optimized variant
- **Pi 5 Suitability**: ⭐⭐⭐⭐⭐ Best for faster-whisper backend
- **References**: [Model Card](https://huggingface.co/Systran/faster-distil-whisper-large-v3)

#### **Qualcomm Whisper-Large-V3-Turbo** (Edge-Optimized)
- **Hugging Face**: `qualcomm/Whisper-Large-V3-Turbo`
- **Optimizations**:
  - Single-Head Attention (SHA) vs Multi-Head Attention (MHA)
  - Conv layers vs linear layers
  - Robust performance in noisy environments
- **Pi 5 Suitability**: ⭐⭐⭐⭐⭐ Specifically optimized for edge inference
- **References**: [Model Card](https://huggingface.co/qualcomm/Whisper-Large-V3-Turbo)

### 1.2 Alternative STT Models

#### **Moonshine ASR** ⭐ BEST FOR EDGE
- **GitHub**: `moonshine-ai/moonshine`
- **Hugging Face**: Models available for 8 languages
- **Parameters**:
  - Tiny: 27M (~190MB)
  - Base: 62M (~400MB)
- **Performance**:
  - 5-15x faster than Whisper (variable-length processing)
  - English Tiny: 12.66 WER (vs Whisper Tiny: 12.81)
  - English Base: 10.07 WER (vs Whisper Base: 10.32)
  - Outperforms larger Whisper models in non-English languages
- **Languages**: English, Arabic, Chinese, Japanese, Korean, Spanish, Ukrainian, Vietnamese
- **Formats Available**:
  - ✅ ONNX (recommended for Raspberry Pi)
  - ✅ PyTorch
- **Pi 5 Suitability**: ⭐⭐⭐⭐⭐ Specifically designed for SBCs and edge devices
- **Special Features**:
  - Offline transcription
  - Privacy-focused (no cloud)
  - Rotary Position Embedding (RoPE)
  - Hardware-specific optimizations for ARM processors
- **References**: [GitHub](https://github.com/moonshine-ai/moonshine), [Speech Signal Tool](https://github.com/moonshine-ai/speech_signal), [ArXiv Paper](https://arxiv.org/abs/2410.15608)

#### **Wav2Vec2**
- **Hugging Face**: Multiple variants (e.g., `facebook/wav2vec2-base-960h`)
- **Performance**:
  - 37.04% WER on clean speech
  - 54.69% WER on noisy speech
- **Pi 5 Suitability**: ⭐⭐ Struggles in production, better for fine-tuning
- **Use Cases**: Research, domain-specific fine-tuning, low-resource languages
- **References**: [Benchmark Article](https://northflank.com/blog/best-open-source-speech-to-text-stt-model-in-2026-benchmarks)

### 1.3 Telephony-Specific Considerations

For 8kHz telephony audio:
- **Whisper models**: Support 8kHz input, may need upsampling to 16kHz
- **Moonshine**: ONNX runtime provides ARM optimizations ideal for telephony
- **Recommendation**: Test Moonshine Tiny (27M) for lowest latency on telephony audio

---

## 2. Language Models (LLM)

### 2.1 Qwen2.5 Series ⭐ RECOMMENDED

#### **Qwen2.5-0.5B**
- **Hugging Face**: `Qwen/Qwen2.5-0.5B-Instruct-GGUF`
- **Parameters**: 0.5B
- **Model Size**: 398MB (int4 quantization)
- **Performance**:
  - ~20 tokens/sec on Pi 5
  - Outperforms Gemma2-2.6B on math and coding tasks
- **Pi 5 Suitability**: ⭐⭐⭐⭐⭐ Best for ultra-low latency
- **References**: [GGUF Model](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF), [DFRobot Tutorial](https://www.dfrobot.com/blog-15784.html)

#### **Qwen2.5-1.5B**
- **Hugging Face**: `Qwen/Qwen2.5-1.5B-Instruct-GGUF`
- **Performance**:
  - High throughput with low memory consumption
  - Best balance of speed and quality for edge
- **Pi 5 Suitability**: ⭐⭐⭐⭐⭐ Excellent balance
- **References**: [GGUF Model](https://huggingface.co/QuantFactory/Qwen2-1.5B-GGUF)

#### **Qwen2.5-3B** ⭐ BEST QUALITY
- **Hugging Face**: `Qwen/Qwen2.5-3B-Instruct-GGUF`
- **Parameters**: 3B
- **Performance**:
  - 4-7 tokens/sec (Q4 quantization)
  - Memory: ~5.4GB RAM usage (out of 8GB)
  - Math: 75.5 on MATH benchmark
  - Coding: 84.8 on HumanEval
  - Outperforms Gemma2-9B and Llama3.1-8B on most tasks
- **Pi 5 Suitability**: ⭐⭐⭐⭐⭐ Sweet spot for quality/speed
- **Ollama**: `ollama pull qwen2.5:3b`
- **References**: [GGUF Model](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF), [Qwen Blog](https://qwenlm.github.io/blog/qwen2.5-llm/)

#### **Qwen3-8B**
- **Hugging Face**: `Qwen/Qwen3-8B-GGUF`
- **Performance**: High quality but requires 8GB+ RAM
- **Pi 5 Suitability**: ⭐⭐⭐ Feasible on 16GB Pi 5 but slower
- **References**: [GGUF Model](https://huggingface.co/Qwen/Qwen3-8B-GGUF)

### 2.2 Llama 3.2 Series

#### **Llama 3.2-1B**
- **Hugging Face**: `QuantFactory/Llama-3.2-1B-GGUF`
- **Performance**: 7+ tokens/sec on Pi 5
- **Pi 5 Suitability**: ⭐⭐⭐⭐ Fast but less capable than Qwen2.5-1.5B
- **Ollama**: `ollama pull llama3.2:1b`
- **References**: [GGUF Model](https://huggingface.co/QuantFactory/Llama-3.2-1B-GGUF), [Ollama](https://ollama.com/library/llama3.2:1b)

#### **Llama 3.2-3B**
- **Hugging Face**: `meta-llama/Llama-3.2-3B-Instruct` (GGUF via QuantFactory)
- **Performance**:
  - 4-7 tokens/sec (Q4 quantization)
  - Strong general performance
- **Pi 5 Suitability**: ⭐⭐⭐⭐ Good but Qwen2.5-3B benchmarks better
- **Ollama**: `ollama pull llama3.2:3b`
- **References**: [Ollama](https://ollama.com/library/llama3.2:3b), [Benchmark Article](https://medium.com/aidatatools/raspberry-pi-os-2024-10-22-benchmark-for-ollama-llama3-2-3b-and-1b-c649ebc1acd4)

### 2.3 Phi Series

#### **Phi-3.5-Mini (3.8B)**
- **Hugging Face**: `microsoft/Phi-3.5-mini-instruct`
- **Performance**:
  - Comparable to 7B-9B models
  - Quantized: ~2.4GB package size
  - "Pound for pound" accuracy champion
- **Pi 5 Suitability**: ⭐⭐⭐⭐ Excellent quality for size
- **References**: [Benchmark Article](https://medium.com/@darrenoberst/best-small-language-models-for-accuracy-and-enterprise-use-cases-benchmark-results-cf71964759c8)

#### **Phi-4-Mini**
- **Performance**: Reasoning and multilingual comparable to 7B-9B models
- **Pi 5 Suitability**: ⭐⭐⭐⭐ Latest iteration
- **References**: [Model Series](https://towardsdatascience.com/small-language-models-using-3-8b-phi-3-and-8b-llama-3-models-on-a-pc-and-raspberry-pi-9ed70127fe61/)

### 2.4 Gemma Series

#### **Gemma3-1B**
- **Performance**: Most efficient model, highest token throughput at 1B scale
- **Pi 5 Suitability**: ⭐⭐⭐⭐⭐ Best speed-to-resource ratio
- **References**: [Performance Guide](https://collabnix.com/best-ollama-models-in-2025-complete-performance-comparison/)

#### **Gemma2-2B/3B**
- **Performance**: Competitive but generally behind Qwen2.5 and SmolLM3 at similar scales
- **Pi 5 Suitability**: ⭐⭐⭐ Good alternative
- **References**: [BentoML Guide](https://www.bentoml.com/blog/the-best-open-source-small-language-models)

### 2.5 Other Notable Models

#### **SmolLM3-3B**
- **Performance**: Outperforms Llama-3.2-3B and Qwen2.5-3B, competitive with 4B models
- **Pi 5 Suitability**: ⭐⭐⭐⭐⭐ Emerging strong contender
- **References**: [BentoML Guide](https://www.bentoml.com/blog/the-best-open-source-small-language-models)

### 2.6 Quantization Recommendations

| Quantization | Size Impact | Quality | RAM Requirement | Use Case |
|-------------|-------------|---------|-----------------|----------|
| **Q4_K_M** | Moderate | High | 4-6GB | **Default recommendation** |
| **Q3_K_M** | Small | Good | 3-4GB | Limited RAM scenarios |
| **Q5_K_M** | Large | Very High | 6-8GB | Maximum quality |
| **Q8_0** | Very Large | Near-FP16 | 8-12GB | Benchmarking |

### 2.7 LLM Recommendations by Use Case

| Use Case | Model | Reason |
|----------|-------|--------|
| **Ultra-low latency** | Qwen2.5-0.5B | 20 tokens/sec, 398MB |
| **Best balance** | Qwen2.5-1.5B or Gemma3-1B | High throughput, low memory |
| **Best quality** | Qwen2.5-3B | Outperforms larger models |
| **Conversational** | Llama 3.2-3B | Strong dialogue capabilities |
| **Reasoning** | Phi-3.5-Mini | Best accuracy per parameter |

---

## 3. Text-to-Speech (TTS) Models

### 3.1 Kokoro-82M ⭐ CURRENT & RECOMMENDED

#### **Kokoro-82M-v1.0-ONNX**
- **Hugging Face**: `onnx-community/Kokoro-82M-v1.0-ONNX`
- **Parameters**: 82M
- **Model Sizes**:
  - FP32: 326MB
  - FP16: 163MB
  - Q8: 92.4MB ⭐ Recommended
  - Q4: 154MB (with FP16 fallback)
- **Performance**:
  - #1 ranking in TTS Spaces Arena
  - Outperforms XTTS v2 (467M), MetaVoice (1.2B), Fish Speech (~500M)
  - 24kHz sample rate
- **Languages**: English (US/British), French, Korean, Japanese, Mandarin
- **Voices**: 24 total (20 US English, 4 British English)
  - Female voices: af_heart, af_bella, af_sarah, bf_alice, etc.
  - Male voices: am_adam, am_liam, bm_george, etc.
- **Formats**:
  - ✅ ONNX (multiple quantizations)
  - ✅ JavaScript/Node.js: `kokoro-js` package
  - ✅ Python: Direct ONNX Runtime
  - ✅ Android: Via sherpa-onnx
- **Pi 5 Suitability**: ⭐⭐⭐⭐⭐ Lightweight, high quality, ONNX optimized
- **References**: [ONNX Model](https://huggingface.co/onnx-community/Kokoro-82M-v1.0-ONNX), [Website](https://kokorottsai.com/), [Medium Article](https://medium.com/data-science-in-your-pocket/kokoro-82m-the-best-tts-model-in-just-82-million-parameters-512b4ba4f94c)

### 3.2 Piper TTS

#### **Piper VITS Models**
- **Hugging Face**: `rhasspy/piper-voices`
- **Models**: 100+ pre-trained models for 40+ languages
- **Architecture**: VITS-based ONNX models
- **Popular Models**:
  - `en_US-lessac-medium`: High-quality US English
  - `en_US-libritts_r-medium`: 904 speakers
- **Sample Rate**: 16-22kHz (model dependent)
- **Formats**:
  - ✅ ONNX
  - ✅ Sherpa-ONNX integration
- **Pi 5 Suitability**: ⭐⭐⭐⭐⭐ Battle-tested, widely used
- **References**: [Sherpa Docs](https://k2-fsa.github.io/sherpa/onnx/tts/piper.html), [Piper Collection](https://huggingface.co/collections/mukhortov/piper-tts), [HAL-9000 Example](https://huggingface.co/campwill/HAL-9000-Piper-TTS)

### 3.3 Other TTS Models

#### **StyleTTS2**
- **Hugging Face**: `hexgrad/styletts2`, `ak36/styletts2`
- **Architecture**: Style diffusion + adversarial training with large SLMs
- **Features**: Human-level TTS synthesis
- **Formats**:
  - ✅ ONNX conversions available
  - Powers WebUI for CPU inference
- **Pi 5 Suitability**: ⭐⭐⭐ Larger models, slower inference
- **References**: [ONNX Model](https://huggingface.co/hexgrad/styletts2), [GitHub](https://github.com/yl4579/StyleTTS2), [Paper](https://huggingface.co/papers/2306.07691)

#### **Bark**
- **Hugging Face**: `suno/bark`
- **Architecture**: Transformer-based text-to-audio
- **Variants**: Small and Large checkpoints
- **Features**:
  - Multi-lingual TTS
  - Music and sound effects generation
  - Conversational speech
- **Formats**:
  - PyTorch (Transformers)
  - ONNX export requested but not fully supported
- **Pi 5 Suitability**: ⭐⭐ Large models, slow for real-time
- **References**: [Model Card](https://huggingface.co/suno/bark), [GitHub](https://github.com/suno-ai/bark), [Coqui Docs](https://docs.coqui.ai/en/latest/models/bark.html)

#### **VITS Models (General)**
- **Sherpa-ONNX**: `k2-fsa/sherpa-onnx` releases include VITS models
- **Pi 5 Suitability**: ⭐⭐⭐⭐ Fast, lightweight
- **References**: [Sherpa VITS Docs](https://k2-fsa.github.io/sherpa/onnx/tts/pretrained_models/vits.html)

### 3.4 TTS Framework Recommendations

#### **sherpa-onnx** ⭐ Recommended Framework
- Unified framework for Piper, Kokoro, VITS
- Android APK support
- Multi-platform (Linux, Windows, macOS, Android, iOS)
- Optimized for edge devices
- **References**: [Sherpa TTS Docs](https://k2-fsa.github.io/sherpa/onnx/tts/index.html)

---

## 4. Voice Activity Detection (VAD)

### 4.1 Silero VAD ⭐ CURRENT & RECOMMENDED

#### **Silero VAD v5**
- **GitHub**: `snakers4/silero-vad`
- **PyTorch Hub**: `snakers4_silero-vad_vad`
- **Model Size**: ~2MB
- **Performance**:
  - <1ms processing time per 30ms audio chunk (single CPU thread)
  - 4-5x faster with ONNX runtime
  - Batching and GPU further improve speed
- **Sample Rates**: ✅ 8000 Hz, ✅ 16000 Hz (telephony standard)
- **Languages**: Trained on 6000+ languages
- **Robustness**: Handles various background noise and quality levels
- **Formats**:
  - ✅ PyTorch (JIT)
  - ✅ ONNX
- **Requirements**:
  - Python 3.8+
  - 1GB+ RAM
  - Modern CPU with AVX/AVX2/AVX-512/AMX
- **Pi 5 Suitability**: ⭐⭐⭐⭐⭐ Lightweight, fast, telephony-ready
- **References**: [GitHub](https://github.com/snakers4/silero-vad), [PyTorch Hub](https://pytorch.org/hub/snakers4_silero-vad_vad/), [NVIDIA NGC](https://catalog.ngc.nvidia.com/orgs/nvidia/teams/riva/models/silero_vad)

### 4.2 Pyannote VAD

#### **Pyannote Voice Activity Detection**
- **Hugging Face**: `pyannote/voice-activity-detection`
- **Features**:
  - State-of-the-art VAD
  - Speaker segmentation support
  - Overlap detection
- **Performance**:
  - More accurate than Silero in benchmarks
  - Slower than Silero
- **Sample Rates**: 16000 Hz standard
- **Format**: PyTorch
- **Requirements**: Hugging Face access token
- **Pi 5 Suitability**: ⭐⭐⭐⭐ Higher accuracy, higher compute
- **Use Case**: When accuracy > speed (e.g., post-processing)
- **References**: [Model Card](https://huggingface.co/pyannote/voice-activity-detection), [ArXiv Paper](https://arxiv.org/pdf/2104.04045), [Issue #1498](https://github.com/pyannote/pyannote-audio/issues/1498)

### 4.3 VAD Comparison

| Model | Size | Speed | Accuracy | Telephony Support | Recommendation |
|-------|------|-------|----------|------------------|----------------|
| **Silero VAD v5** | 2MB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ 8kHz/16kHz | **Default choice** |
| **Pyannote VAD** | Larger | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ 16kHz | Accuracy-critical |

---

## 5. Wake Word Detection

### 5.1 openWakeWord ⭐ RECOMMENDED

#### **openWakeWord Framework**
- **GitHub**: `dscripka/openWakeWord`
- **Hugging Face**: Demo available on Spaces
- **Performance**:
  - 15-20 models simultaneously on Raspberry Pi 3 (single core)
  - Real-time processing
  - 80ms audio frames
  - Shared feature extraction backbone
- **Training**:
  - 100% synthetic TTS-generated training data
  - Google Colab notebook for custom training (<1 hour)
  - Custom verifier models for specific voices (2nd-stage filtering)
- **Pre-trained Models**: Common wake words and phrases
- **Output**: Confidence score 0-1 per frame
- **Pi 5 Suitability**: ⭐⭐⭐⭐⭐ Designed for edge, proven on Pi
- **Wyoming Protocol**: Compatible (port 10400)
- **References**: [GitHub](https://github.com/dscripka/openWakeWord), [Rhasspy Forum](https://community.rhasspy.org/t/openwakeword-new-library-and-pre-trained-models-for-wakeword-and-phrase-detection/4162), [PyPI](https://pypi.org/project/openwakeword/), [Home Assistant Integration](https://www.home-assistant.io/voice_control/about_wake_word/)

### 5.2 Alternative Solutions

- **Porcupine (Picovoice)**: Commercial, limited free tier
- **Mycroft Precise**: Older, less active development
- **Recommendation**: openWakeWord for open-source, performance, and customization

---

## 6. Emotion Detection

### 6.1 SpeechBrain Emotion Recognition ⭐ RECOMMENDED

#### **SpeechBrain Wav2Vec2 IEMOCAP**
- **Hugging Face**: `speechbrain/emotion-recognition-wav2vec2-IEMOCAP`
- **Architecture**: Fine-tuned Wav2Vec2 (base)
- **Emotions**: 8 emotion classes
- **Features**:
  - Complete SER toolkit
  - Speaker verification via cosine distance
  - SpeechBrain ecosystem integration
- **Pi 5 Suitability**: ⭐⭐⭐⭐ Good for offline emotion analysis
- **References**: [Model Card](https://huggingface.co/speechbrain/emotion-recognition-wav2vec2-IEMOCAP), [Medium Article](https://medium.com/@jaimonjk/removing-background-noise-from-speech-using-speechbrain-models-e5546d103355)

### 6.2 Other Emotion Models

- **ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition**: Fine-tuned for SER
- **r-f/wav2vec-english-speech-emotion-recognition**: English-specific
- **Dpngtm/wav2vec2-emotion-recognition**: 8 emotion classes
- **superb/wav2vec2-base-superb-er**: SUPERB benchmark model
- **audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim**: Robust, dimensional emotions

**References**: [ehcalabres model](https://huggingface.co/ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition), [r-f model](https://huggingface.co/r-f/wav2vec-english-speech-emotion-recognition), [Dpngtm model](https://huggingface.co/Dpngtm/wav2vec2-emotion-recognition), [SUPERB model](https://huggingface.co/superb/wav2vec2-base-superb-er), [audeering model](https://huggingface.co/audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim)

---

## 7. Speech Enhancement / Noise Reduction

### 7.1 DeepFilterNet2 ⭐ RECOMMENDED FOR EDGE

#### **DeepFilterNet2**
- **GitHub**: `Rikorose/DeepFilterNet`
- **Hugging Face Space**: `hshr/DeepFilterNet2`
- **Features**:
  - Real-time speech enhancement
  - Full-band audio (48kHz)
  - Low complexity for embedded devices
  - Deep filtering approach
- **Deployment**:
  - ✅ Pre-compiled binary (no Python dependencies)
  - ✅ LADSPA plugin
  - ✅ PipeWire filter-chain integration
- **Pi 5 Suitability**: ⭐⭐⭐⭐⭐ Designed for embedded/edge
- **References**: [GitHub](https://github.com/Rikorose/DeepFilterNet), [HF Space](https://huggingface.co/spaces/hshr/DeepFilterNet2)

### 7.2 SpeechBrain Enhancement Models

#### **SepFormer Models**
- **Hugging Face**:
  - `speechbrain/sepformer-wham-enhancement`
  - `speechbrain/sepformer-dns4-16k-enhancement`
- **Architecture**: Separation transformer (SepFormer)
- **Sample Rate**: 16kHz
- **Features**: Speech separation and enhancement
- **Pi 5 Suitability**: ⭐⭐⭐ Moderate compute requirements
- **References**: [WHAM Model](https://huggingface.co/speechbrain/sepformer-wham-enhancement), [DNS4 Model](https://huggingface.co/speechbrain/sepformer-dns4-16k-enhancement)

### 7.3 RNNoise

#### **RNNoise (Xiph.org)**
- **GitHub**: `xiph/rnnoise`
- **Architecture**: Recurrent neural network
- **Features**:
  - Noise suppression
  - RAW 16-bit mono PCM
  - 48kHz sample rate
  - Command-line tool
- **Model Size**: Very small (<1MB)
- **Pi 5 Suitability**: ⭐⭐⭐⭐⭐ Lightweight, real-time
- **Use Case**: Pre-processing telephony audio
- **References**: [GitHub](https://github.com/xiph/rnnoise), [RNNoise-Ex Paper](https://arxiv.org/pdf/2105.11813)

### 7.4 Other Enhancement Tools

#### **ClearerVoice-Studio (ModelScope)**
- **GitHub**: `modelscope/ClearerVoice-Studio`
- **Features**: SOTA speech enhancement, separation, target speaker extraction
- **Pi 5 Suitability**: ⭐⭐ Heavy models, research-focused
- **References**: [GitHub](https://github.com/modelscope/ClearerVoice-Studio)

#### **Hugging Face Audio-to-Audio Task**
- **Overview**: Libraries like SpeechBrain, Asteroid, ESPNet
- **References**: [Task Overview](https://huggingface.co/tasks/audio-to-audio)

### 7.5 Speech Enhancement Recommendations

| Model | Size | Latency | Quality | Edge Deployment | Use Case |
|-------|------|---------|---------|----------------|----------|
| **RNNoise** | <1MB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ✅ Excellent | Pre-processing telephony |
| **DeepFilterNet2** | Small | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ Excellent | Real-time enhancement |
| **SepFormer** | Medium | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⚠️ Moderate | Post-processing |

---

## 8. Deployment Recommendations by Component

### 8.1 Pi #1 (pi-voice) - AI HAT+ 2 (Hailo-10H)

| Component | Recommended Model | Format | Notes |
|-----------|------------------|--------|-------|
| **Wake Word** | openWakeWord | PyTorch | Wyoming port 10400 |
| **STT** | Distil-Whisper-Large-v3 or Moonshine Tiny | ONNX/Hailo | Wyoming port 10300, Hailo acceleration |
| **TTS** | Kokoro-82M Q8 | ONNX | Port 10200, 92MB model |
| **VAD** | Silero VAD v5 | ONNX | <1ms latency, telephony support |
| **Enhancement** | RNNoise | Binary | Pre-processing for telephony |

### 8.2 Pi #2 (pi-ollama) - LLM Server

| Component | Recommended Model | Format | Notes |
|-----------|------------------|--------|-------|
| **LLM (Quality)** | Qwen2.5-3B | GGUF Q4_K_M | Best performance/quality balance |
| **LLM (Speed)** | Qwen2.5-1.5B | GGUF Q4_K_M | Fastest with good quality |
| **LLM (Ultra-fast)** | Qwen2.5-0.5B | GGUF int4 | 20 tokens/sec, 398MB |
| **Runtime** | Ollama | Native | Port 11434 |

### 8.3 Optional Enhancement Models (Post-processing/Offline)

| Component | Model | Use Case |
|-----------|-------|----------|
| **Emotion Analysis** | speechbrain/emotion-recognition-wav2vec2-IEMOCAP | Call sentiment analysis |
| **Speaker ID** | Pyannote speaker diarization | Multi-speaker scenarios |
| **Noise Reduction** | DeepFilterNet2 | Clean up recordings |

---

## 9. Model Size Summary

### Ultra-Light (<100MB)
- Silero VAD: 2MB
- RNNoise: <1MB
- Kokoro-82M Q8: 92MB

### Light (100-500MB)
- Moonshine Tiny: 190MB
- Qwen2.5-0.5B int4: 398MB
- Moonshine Base: 400MB

### Medium (500MB-2GB)
- Distil-Whisper-Large-v3: ~1.5GB
- Whisper-Large-v3-Turbo: ~1.6GB
- Qwen2.5-1.5B Q4: ~1GB
- Qwen2.5-3B Q4: ~2GB

### Large (2GB+)
- Llama 3.2-3B: ~2-3GB (Q4)
- Qwen2.5-7B: ~4-5GB (Q4)

---

## 10. Performance Benchmarks Summary

### STT Benchmark (WER - Lower is Better)

| Model | Parameters | WER (Short) | Speed vs Whisper-Large-v3 | Edge Optimized |
|-------|-----------|-------------|---------------------------|----------------|
| Moonshine Tiny | 27M | 12.66% | 5-15x faster | ✅ |
| Whisper Tiny | ~39M | 12.81% | ~3x faster | ⚠️ |
| Moonshine Base | 62M | 10.07% | 5-15x faster | ✅ |
| Whisper Base | ~74M | 10.32% | ~2x faster | ⚠️ |
| Distil-Whisper-Large-v3 | 756M | 9.7% | 6.3x faster | ✅ |
| Whisper-Large-v3 | 1550M | 8.4% | 1.0x (baseline) | ❌ |

### LLM Benchmark (Raspberry Pi 5)

| Model | Parameters | Tokens/sec | RAM Usage | Quality (1-5) | Best For |
|-------|-----------|------------|-----------|---------------|----------|
| Qwen2.5-0.5B int4 | 0.5B | ~20 | <1GB | ⭐⭐⭐ | Ultra-low latency |
| Gemma3-1B | 1B | ~15 | ~2GB | ⭐⭐⭐⭐ | Speed + efficiency |
| Qwen2.5-1.5B Q4 | 1.5B | ~10 | ~2GB | ⭐⭐⭐⭐ | Balance |
| Llama 3.2-3B Q4 | 3B | 4-7 | ~4GB | ⭐⭐⭐⭐ | Conversation |
| Qwen2.5-3B Q4 | 3B | 4-7 | ~5.4GB | ⭐⭐⭐⭐⭐ | Best quality |
| Phi-3.5-Mini | 3.8B | 4-6 | ~2.4GB | ⭐⭐⭐⭐⭐ | Reasoning |

### TTS Benchmark

| Model | Parameters | Quality Rank | Latency | Size (Q8/Optimized) | Pi 5 Ready |
|-------|-----------|--------------|---------|---------------------|------------|
| Kokoro-82M | 82M | #1 (TTS Arena) | Low | 92MB | ✅ |
| Piper (medium) | ~20-50M | High | Very Low | ~30-80MB | ✅ |
| XTTS v2 | 467M | High | Medium | ~900MB | ⚠️ |
| StyleTTS2 | Large | Very High | High | Large | ❌ |
| Bark | ~1B+ | High | Very High | ~2GB+ | ❌ |

---

## 11. Quick Start Model Recommendations

### Minimal Setup (Fastest Deployment)
```bash
# Pi #1 (pi-voice) - STT/TTS/VAD
- STT: Moonshine Tiny ONNX (190MB)
- TTS: Kokoro-82M Q8 (92MB)
- VAD: Silero VAD v5 (2MB)
- Wake: openWakeWord (lightweight)

# Pi #2 (pi-ollama) - LLM
- LLM: Qwen2.5-0.5B int4 (398MB) or Qwen2.5-1.5B Q4 (~1GB)
- ollama pull qwen2.5:0.5b  # or qwen2.5:1.5b
```

### Balanced Setup (Quality + Speed)
```bash
# Pi #1 (pi-voice)
- STT: Distil-Whisper-Large-v3 with Hailo acceleration
- TTS: Kokoro-82M Q8
- VAD: Silero VAD v5
- Wake: openWakeWord

# Pi #2 (pi-ollama)
- LLM: Qwen2.5-3B Q4_K_M (~2GB)
- ollama pull qwen2.5:3b
```

### Maximum Quality Setup
```bash
# Pi #1 (pi-voice)
- STT: Distil-Whisper-Large-v3.5 with Hailo
- TTS: Kokoro-82M FP16 or Piper high-quality voice
- VAD: Pyannote VAD (accuracy > speed)
- Wake: openWakeWord with custom verifier
- Enhancement: DeepFilterNet2 for audio cleanup

# Pi #2 (pi-ollama)
- LLM: Qwen2.5-3B Q5_K_M or Phi-4-Mini
- ollama pull qwen2.5:3b
```

---

## 12. Key References and Resources

### Model Hubs
- **Hugging Face**: https://huggingface.co/models
- **Ollama Library**: https://ollama.com/library
- **Sherpa-ONNX**: https://k2-fsa.github.io/sherpa/onnx/

### Benchmarks & Comparisons
- [Best Open Source STT 2026 Benchmarks](https://northflank.com/blog/best-open-source-speech-to-text-stt-model-in-2026-benchmarks)
- [Best Open Source SLMs 2026](https://www.bentoml.com/blog/the-best-open-source-small-language-models)
- [Best Open Source TTS 2026](https://www.bentoml.com/blog/exploring-the-world-of-open-source-text-to-speech-models)
- [Best Ollama Models 2025](https://collabnix.com/best-ollama-models-in-2025-complete-performance-comparison/)
- [Pi 5 LLM Performance Analysis](https://www.stratosphereips.org/blog/2025/6/5/how-well-do-llms-perform-on-a-raspberry-pi-5)

### Edge AI & Pi Deployment
- [Running Llama on Pi 5 (2025)](https://aicompetence.org/running-llama-on-raspberry-pi-5/)
- [SLMs on PC and Pi](https://towardsdatascience.com/small-language-models-using-3-8b-phi-3-and-8b-llama-3-models-on-a-pc-and-raspberry-pi-9ed70127fe61/)
- [Qwen2.5 on Pi 5 Tutorial](https://www.dfrobot.com/blog-15784.html)
- [Edge AI Pipeline (Audio/Vision)](https://mjrovai.github.io/EdgeML_Made_Ease_ebook/raspi/audio_pipeline/audio_pipeline.html)

### Wyoming Protocol (Voice Assistant Integration)
- **openWakeWord**: Wyoming-compatible wake word detection
- **Whisper**: Wyoming satellite protocol for STT
- **Piper**: Wyoming TTS service
- **Home Assistant Voice**: https://www.home-assistant.io/voice_control/

---

## 13. Confidence Assessment

### High Confidence (Well-Established)
- ✅ Whisper variants (distil-whisper, turbo) - Production-ready, widely deployed
- ✅ Qwen2.5 series - Extensive benchmarks, proven on Pi 5
- ✅ Kokoro-82M - #1 TTS Arena ranking, ONNX optimized
- ✅ Silero VAD - Battle-tested, telephony-proven
- ✅ openWakeWord - Raspberry Pi validated

### Medium Confidence (Emerging Strong)
- ⚠️ Moonshine - New but specifically designed for edge, strong benchmarks
- ⚠️ SmolLM3 - Recent release, outperforms established models
- ⚠️ DeepFilterNet2 - Less widely adopted but designed for embedded

### Lower Confidence (Needs Validation)
- ⚠️ StyleTTS2 on Pi - Limited edge deployment reports
- ⚠️ Bark on Pi - Known to be slow, not recommended for real-time

### Gaps Requiring Additional Research
- Hailo-specific Whisper optimizations (may require custom ONNX export)
- Real-world 8kHz telephony performance for Moonshine
- Qwen2.5 vs Llama 3.2 on multi-turn conversation quality
- Custom openWakeWord training for telephony audio

---

## 14. Actionable Next Steps

1. **Immediate Testing** (Pi #1):
   - Deploy Moonshine Tiny ONNX for STT comparison vs Whisper
   - Benchmark Kokoro-82M Q8 vs current Piper implementation
   - Test openWakeWord with custom payphone wake phrase

2. **LLM Evaluation** (Pi #2):
   - Compare Qwen2.5-3B vs current Llama 3.2-3B on conversation quality
   - Test Qwen2.5-1.5B for latency improvement
   - Benchmark token generation rates with Q4_K_M vs Q3_K_M

3. **Enhancement Pipeline**:
   - Add RNNoise pre-processing for 8kHz telephony audio
   - Evaluate DeepFilterNet2 for background noise reduction
   - Test Silero VAD at 8kHz vs 16kHz for telephony

4. **Hailo Optimization**:
   - Research Hailo SDK for custom Whisper ONNX export
   - Test distil-whisper-large-v3 with Hailo acceleration
   - Benchmark latency improvements vs CPU-only

5. **Model Downloads** (Priority Order):
   ```bash
   # High Priority
   huggingface-cli download distil-whisper/distil-large-v3-onnx
   huggingface-cli download onnx-community/Kokoro-82M-v1.0-ONNX model_q8f16.onnx
   ollama pull qwen2.5:3b

   # Medium Priority
   huggingface-cli download Qwen/Qwen2.5-1.5B-Instruct-GGUF
   git clone https://github.com/moonshine-ai/moonshine.git

   # Testing/Evaluation
   ollama pull qwen2.5:1.5b
   ollama pull gemma3:1b
   ```

---

## 15. Conclusion

The Hugging Face ecosystem provides excellent model options for your Raspberry Pi 5 voice assistant:

- **STT**: Distil-Whisper-Large-v3 or Moonshine Tiny offer the best edge-optimized transcription
- **LLM**: Qwen2.5-3B provides the best quality/speed balance at the 3B scale
- **TTS**: Kokoro-82M is the current SOTA for lightweight, high-quality synthesis
- **VAD**: Silero VAD v5 is production-ready for telephony (8kHz/16kHz)
- **Wake Word**: openWakeWord is proven on Raspberry Pi with custom training support

All recommended models support ONNX/GGUF formats optimized for edge deployment and fit well within 16GB RAM constraints. The dual-Pi architecture allows optimal distribution of compute between Hailo-accelerated STT/TTS (Pi #1) and flexible LLM inference (Pi #2).

---

**Document Version**: 1.0
**Last Updated**: 2026-01-27
**Next Review**: 2026-02-27 (monthly updates recommended due to rapid model releases)
