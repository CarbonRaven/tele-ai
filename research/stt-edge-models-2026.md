# State-of-the-Art Edge STT Models for Raspberry Pi 5 (2026)

**Research Date**: February 6, 2026
**Target Hardware**: Raspberry Pi 5 (16GB RAM), ARM64
**Use Case**: Real-time speech-to-text for voice assistant with <2s latency for 5s utterances

## Executive Summary

As of early 2026, the edge STT landscape is dominated by three model families optimized for embedded ARM64 deployment:

1. **Moonshine (UsefulSensors)** - Newest entry, claims 5x faster than Whisper with comparable accuracy
2. **Whisper variants** - Multiple optimized implementations (faster-whisper, whisper.cpp, Hailo-accelerated)
3. **Lightweight alternatives** - Vosk, sherpa-onnx Zipformer for minimal footprint

**Key Finding**: No direct Raspberry Pi 5 benchmarks exist for most models. Best available data comes from:
- Pi 5 CTranslate2/Whisper study (MDPI 2025) - most authoritative Pi 5 data
- Pi 4 faster-whisper benchmarks (Willow Inference Server)
- Community whisper.cpp benchmarks (various ARM platforms)

**Recommendation for Your Project**: Moonshine tiny (27M params) offers best latency-accuracy tradeoff for Pi 5 deployment, with Hailo-accelerated Whisper base as NPU-backed alternative.

---

## 1. Moonshine (UsefulSensors)

**Status**: Active development, latest release November 2025
**Official Repository**: https://github.com/moonshine-ai/moonshine

### Model Variants

| Variant | Parameters | Memory | WER (avg) | WER LibriSpeech Clean | Target Use Case |
|---------|-----------|--------|-----------|---------------------|-----------------|
| Tiny | 27M | ~190MB | 12.66% | 4.52% | Mobile/embedded |
| Base | 62M | ~400MB | 10.07% | 3.23% | Edge servers |

### Performance Claims

**Latency Improvements** (vs Whisper):
- 5x reduction in compute for 10-second segments
- Up to 3x latency reduction (scales with audio length)
- 5x-15x faster for short segments due to variable-length encoding
- Documented lower bound: Whisper tiny.en shows ~500ms latency on ARM regardless of audio length

**Accuracy** (OpenASR benchmarks):
- Better than Whisper tiny.en: 12.81% → 12.66% WER
- Better than Whisper base.en: 10.32% → 10.07% WER

### Multilingual Support (Moonshine Flavors, Sep 2025)

Specialized variants show dramatic improvements over Whisper tiny:

| Language | Dataset | Whisper Tiny | Moonshine Tiny | Improvement |
|----------|---------|--------------|----------------|-------------|
| Arabic | CV17 | 88.9% | 36.6% | 2.4x better |
| Arabic | Fleurs | 66.0% | 20.8% | 3.2x better |
| Japanese | Fleurs | 47.2% CER | 17.9% CER | 2.6x better |
| Korean | Fleurs | 15.8% CER | 8.9% CER | 1.8x better |

### ARM64/Pi Deployment

**Official Statements**:
- Tested on "low-cost ARM-based processor"
- Marketed as running on Raspberry Pis
- ONNX package available: `useful-moonshine-onnx` (Nov 2025 releases)

**Missing Data**:
- No published Pi 5-specific latency benchmarks (ms or RTF)
- No ARM64 memory usage profiling
- Community benchmarks needed

### Python Library

```bash
pip install useful-moonshine-onnx
```

**Advantages**:
- Native ONNX support for cross-platform deployment
- Active maintenance (2025 releases)
- Significantly faster than Whisper on short utterances

**Limitations**:
- Newer model with limited production deployment history
- No official Pi 5 benchmarks
- Smaller than Whisper base for accuracy-critical applications

---

## 2. Faster-Whisper (CTranslate2 Backend)

**Status**: Mature, stable, widely deployed
**Official Repository**: https://github.com/SYSTRAN/faster-whisper

### Raspberry Pi 5 Benchmarks (MDPI 2025 Study)

**60-second audio batch processing** via CTranslate2 on Pi 5:

| Model | Quantization | Runtime | RTF | Memory | Latency Type |
|-------|-------------|---------|-----|--------|--------------|
| Tiny | int8 | 15-27s | 0.25-0.45 | <0.5GB RSS | Batch (non-streaming) |
| Base | int8_float32 | ~41s | ~0.68 | Not specified | Batch (non-streaming) |
| Small | float32 | ~253s | ~4.22 | Not specified | Batch (non-streaming) |
| Medium | int8 | ~261s | ~4.35 | ~5GB RSS | Batch (non-streaming) |

**Important**: These are full-clip processing times, not streaming first-token latency.

### Raspberry Pi 4 Benchmarks (Willow Inference Server)

**Faster-whisper v0.5.1, int8 quantization, OMP_NUM_THREADS=4**:

| Model | Audio Length | Processing Time | RTF | Realtime Speed |
|-------|--------------|-----------------|-----|----------------|
| Tiny | 3.84s | 3.333s | 0.87 | 1.15x realtime |
| Base | 3.84s | 6.207s | 1.62 | 0.62x realtime |
| Medium | 3.84s | 50.807s | 13.23 | 0.08x realtime |

**Interpretation**: Only tiny model achieves faster-than-realtime on Pi 4.

### Low-Confidence Pi 5 Data (Unverified Blog)

Single datapoint from product comparison blog (not peer-reviewed):
- Model: faster-whisper small int8 CPU
- Hardware: Pi 5 8GB
- Avg time: 42.3s
- RTF: 1.41
- RAM: 1.1GB

**Use with caution** - unclear methodology, no reproducible test protocol.

### CTranslate2 Optimizations

**Backend Features** (relevant to ARM64):
- Layer fusion, padding removal, batch reordering, in-place operations, caching
- Quantization support: FP16, BF16, INT16, INT8, AWQ INT4
- ARM64 backends: Ruy (recommended for ARM CPUs), OpenBLAS
- AArch64-specific optimizations

**Quantization Efficiency**:
- 8-bit quantization documented to improve CPU/GPU efficiency
- Common deployment: `compute_type="int8"` for CPU inference

### Python Usage

```python
from faster_whisper import WhisperModel

model = WhisperModel("tiny", device="cpu", compute_type="int8")
segments, info = model.transcribe("audio.wav")
```

**Advantages**:
- Most mature Whisper optimization
- Proven CTranslate2 backend
- Wide model size range (tiny → large)
- Best Pi 4 benchmarks available

**Limitations**:
- Limited Pi 5-specific data
- Batch processing focus (not streaming-optimized)
- Base model still slower than realtime on Pi 4

---

## 3. Hailo-10H NPU Accelerated Whisper (AI HAT+ 2)

**Status**: Official support, 2026-01 software release
**Hardware**: Hailo AI HAT+ 2 (Hailo-10H NPU)

### Available Models

**Officially Compiled for Hailo-10H**:

| Model | Load Time | Throughput (TPS) | Precision | APIs |
|-------|-----------|-----------------|-----------|------|
| Whisper-Base | ~3.89s | ~23.36 TPS | Mixed | C++/Python |
| Whisper-Small | ~11.92s | ~8.71 TPS | Mixed | C++/Python |

**Development Support** (hailo-whisper repo):
- Whisper tiny, tiny.en, base, base.en
- Conversion scripts for Hailo-8 and Hailo-10H
- HEF (Hailo Executable Format) compilation tooling

### Recent Updates (2026-01 Software Suite)

- Whisper-Small added as GenAI model
- HailoRT Speech-to-Text API enhancements
- Automatic language detection support
- Mixed-precision compilation

### Missing Benchmarks

**Not Available**:
- WER scores for Hailo-compiled models
- Real-time factor (RTF) measurements
- End-to-end latency for typical utterances
- Memory usage profiles
- Power consumption data

**TPS metric** (tokens per second) does not directly translate to audio RTF without additional context.

### Non-Whisper Alternatives

**Official Statement**: No non-Whisper ASR models publicly listed for Hailo-10H as of February 2026.

The authoritative model list is in `hailo_model_zoo_genai/docs/MODELS.rst`, which currently only lists Whisper variants for speech recognition.

**Advantages**:
- NPU acceleration offloads CPU
- Official support from Hailo
- Mixed-precision optimization
- Larger models (small) feasible

**Limitations**:
- No WER/RTF benchmarks published
- Whisper-only (no alternatives)
- Requires AI HAT+ 2 hardware
- Compilation complexity for custom models

---

## 4. Whisper.cpp (GGML Quantized)

**Status**: Active development, v1.7.5+ (2025-2026)
**Official Repository**: https://github.com/ggml-org/whisper.cpp

### Model Memory Footprint (Unquantized Baseline)

| Model | Memory |
|-------|--------|
| Tiny | 273 MB |
| Base | 388 MB |
| Small | 852 MB |
| Medium | 2.1 GB |
| Large | 3.9 GB |

**Quantized variants** (Q5_0, Q5_1, Q8_0) reduce these by ~50-70%, but exact numbers vary by model and quantization scheme.

### Raspberry Pi Benchmarks

**Pi 5 Quantized Data**: None found from authoritative sources as of Feb 2026.

**Pi 4 Community Benchmarks** (whisper.cpp issue #89):
- Tiny and base models have reported NEON timings
- Provides ARM64 CPU-only baseline
- Not comprehensive (missing quantization comparisons)

**OpenBenchmarking.org** (Jan 31, 2026):
- Large public benchmark aggregation
- No Raspberry Pi 5 entries found in current dataset

### Quantization Performance on ARM

**Important Finding** (Issue #3491, 2025):
- Q5_0 can be **slower than Q8_0** on ARM platforms (Qualcomm QCS6490)
- Quantization performance is not monotonic with bit-width on ARM
- Requires empirical testing per platform

**Implication**: Don't assume Q5_0 is faster than Q8_0 on Pi 5 without benchmarking.

### ARM64 Optimizations (2025-2026 Updates)

**v1.7.5 Release**:
- CoreML build/convert instructions updated (Apple platforms only)
- Performance gains for Metal (Apple GPU)
- ARM NEON continues as first-class optimization target

**Supported ARM Features**:
- ARM NEON SIMD
- Accelerate framework (Apple only)
- Metal/CoreML (Apple only - not available on Pi 5)

**Note**: CoreML is Apple-specific and does not apply to Raspberry Pi.

### Compilation

```bash
git clone https://github.com/ggml-org/whisper.cpp
cd whisper.cpp
make

# Download quantized model
./models/download-ggml-model.sh base.en
./models/quantize-ggml-model.sh base.en Q8_0

# Run inference
./main -m models/ggml-base.en-q8_0.bin -f audio.wav
```

**Advantages**:
- Minimal dependencies (C/C++)
- Multiple quantization levels
- Active ARM64 optimization
- Proven on various ARM platforms

**Limitations**:
- No official Pi 5 benchmarks
- Quantization performance unpredictable on ARM
- Primarily encoder benchmarking (not end-to-end)
- Command-line focused (limited library integration)

---

## 5. Distil-Whisper Variants (2025 Updates)

**Status**: Active, March 2025 updates
**Official Repository**: https://huggingface.co/distil-whisper

### Available Formats (distil-large-v3.5)

**Updated March 25, 2025**:

| Format | Repository | Use Case | Backend |
|--------|-----------|----------|---------|
| PyTorch | distil-whisper/distil-large-v3.5 | Standard inference | transformers |
| CTranslate2 | deepdml/faster-distil-whisper-large-v3.5 | Faster inference | faster-whisper |
| GGML | distil-whisper/distil-large-v3.5-ggml | whisper.cpp | whisper.cpp |

### Model Characteristics

**Distil-Large-v3.5**:
- Distilled from Whisper large-v3
- Reduced parameters vs full model
- Multiple deployment formats for flexibility

**Deployment Strategy**:
- Use CTranslate2 format with faster-whisper for best Pi performance
- GGML format for whisper.cpp integration
- PyTorch for development/fine-tuning

**Advantages**:
- Smaller than full Whisper large
- Multiple optimized formats available
- Recent updates (2025)

**Limitations**:
- Still larger than tiny/base variants
- No Pi-specific benchmarks
- "Large" variant may be too heavy for Pi 5 real-time inference

---

## 6. NVIDIA Canary & Parakeet (2025)

**Status**: Released August 15, 2025
**Training Dataset**: Granary (NVIDIA)

### Model Families

| Model | Parameters | Focus | Use Case |
|-------|-----------|-------|----------|
| Canary-1B-v2 | 1B | Accuracy | Multilingual, high-quality transcription |
| Canary-1B Flash | 1B | Speed | Faster variant |
| Canary-180M Flash | 180M | Edge | Smallest Canary variant |
| Parakeet-TDT-0.6B-v3 | 600M | Throughput | Low-latency, streaming |
| Parakeet CTC/RNNT | 600M | Variants | Different decoding strategies |

### Deployment Profiles

**NVIDIA Riva ASR NIM** (June 2025 release):
- Lower-GPU-memory profile for Parakeet 0.6B CTC
- Size-optimized containers
- Streaming and chunked inference support

### Edge Suitability for Pi 5

**Analysis**:
- Parakeet-TDT-0.6B (600M params) too large for Pi 5 real-time inference
- Canary-180M Flash more appropriate for edge, but still 6x larger than Moonshine tiny
- Primarily GPU-optimized (NVIDIA Riva focus)
- No ARM CPU benchmarks published

**Verdict**: Not recommended for Raspberry Pi 5 deployment due to size and GPU focus.

**Advantages**:
- State-of-art accuracy (Canary)
- High throughput (Parakeet)
- Strong multilingual support
- Active NVIDIA support

**Limitations**:
- Too large for Pi 5 real-time use
- GPU-oriented optimization
- No ARM64 CPU benchmarks
- Requires NVIDIA infrastructure (Riva)

---

## 7. Moonshine ONNX Variants (September 2025)

**Status**: Community releases, September 2025
**Focus**: Ultra-low-resource deployment

### Available Models

**Specialized Language Variants**:
- `bh4/moonshine-tiny-vi-ONNX` (Vietnamese)
- `onnx-community/moonshine-tiny-ko-ONNX` (Korean)
- Other community-contributed languages

**Sherpa-ONNX INT8 Quantized**:
- 8-bit quantized ONNX builds
- Explicitly for constrained devices
- Official support via k2-fsa/sherpa-onnx

### Deployment Characteristics

**Target Hardware**: "Low-cost/resource-constrained hardware"

**Format Advantages**:
- ONNX Runtime optimizations
- Cross-platform deployment
- INT8 quantization for memory reduction
- Community-driven language expansion

**Usage** (sherpa-onnx):

```bash
pip install sherpa-onnx

# Example inference (exact API varies by language)
# See: https://k2-fsa.github.io/sherpa/onnx/moonshine/models.html
```

**Advantages**:
- Smallest memory footprint
- ONNX Runtime optimizations
- INT8 quantization
- Growing language support

**Limitations**:
- Community models (varying quality)
- Limited official benchmarks
- Requires ONNX Runtime setup

---

## 8. Vosk Models (Kaldi-Based)

**Status**: Mature, stable, Pi-optimized
**Official Site**: https://alphacephei.com/vosk/models

### Model Catalog

**Small Models** (Raspberry Pi Optimized):

| Model | Language | Size | LibriSpeech WER | TEDLIUM WER | Notes |
|-------|----------|------|-----------------|-------------|-------|
| vosk-model-small-en-us-0.15 | English (US) | 40MB | Published | Published | Pi-friendly |
| vosk-model-small-* | Various | ~40-50MB | Varies | Varies | Many languages |

**Characteristics**:
- Explicit Raspberry Pi compatibility
- Published WER scores per model
- Kaldi backend (mature, stable)
- Small memory footprint

### Pi 5 Benchmark (MDPI 2025)

**Vosk-small performance**:
- Included in Pi 5 accuracy/runtime study
- Compared against Whisper tiny/base/medium
- Memory: <0.5GB RSS (similar to Whisper tiny)

**Specific numbers**: See MDPI study for WER and runtime comparisons.

### Deployment

```python
from vosk import Model, KaldiRecognizer
import wave

model = Model("vosk-model-small-en-us-0.15")
wf = wave.open("audio.wav", "rb")
rec = KaldiRecognizer(model, wf.getframerate())

while True:
    data = wf.readframes(4000)
    if len(data) == 0:
        break
    if rec.AcceptWaveform(data):
        print(rec.Result())
```

**Advantages**:
- Smallest footprint (40MB)
- Proven Pi compatibility
- Published WERs
- Fast inference
- Mature ecosystem

**Limitations**:
- Lower accuracy than Whisper/Moonshine
- Kaldi architecture (older than transformers)
- Less active development than newer models

---

## 9. Sherpa-ONNX Zipformer (k2-fsa)

**Status**: Active, 2024-2025 releases
**Official Docs**: https://k2-fsa.github.io/sherpa/onnx/

### Model Architecture

**Zipformer-based Transducers**:
- Modern transformer variant
- Streaming and offline modes
- INT8 quantization support
- Designed for edge inference

### Available Models (2024-2025)

**Offline Transducer Models**:
- Multiple language support
- INT8 variants for lower-resource devices
- Documented on k2-fsa documentation

**Streaming Models** (sherpa-ncnn):
- Small streaming Zipformer models
- Intended for real-time edge inference
- NCNN backend for mobile/embedded

### Deployment

```bash
pip install sherpa-onnx

# See documentation for model download and usage
# https://k2-fsa.github.io/sherpa/onnx/pretrained_models/
```

**Advantages**:
- Modern transformer architecture
- Streaming support
- INT8 quantization
- Active development

**Limitations**:
- Less documented than Whisper/Vosk
- Smaller community
- No Pi-specific benchmarks found

---

## 10. ONNX-ASR Project (Multi-Model Benchmarking)

**Status**: Active, ongoing updates
**Repository**: https://github.com/istupakov/onnx-asr

### Supported Model Families

- Vosk
- Whisper
- NeMo (NVIDIA)
- Quantization support for select models

### ARM Benchmarks (Orange Pi Zero 3)

**RTFx (Real-Time Factor)** on ARM Cortex-A53:

Benchmark results published for:
- Vosk models (Russian/English)
- Whisper variants
- NeMo models

**Note**: Orange Pi Zero 3 is **lower-spec than Pi 5**, so results are conservative baseline.

### Deployment

```bash
pip install onnx-asr

# Supports multiple model formats
# See: https://istupakov.github.io/onnx-asr/
```

**Advantages**:
- Multi-model support
- ARM benchmarks included
- Quantization capabilities
- Unified inference API

**Limitations**:
- Not Pi 5-specific
- Benchmark hardware less powerful than Pi 5
- Smaller model selection than dedicated projects

---

## 11. Wav2Vec2 Quantized (ONNX/OpenVINO)

**Status**: Community conversions, 2025 updates
**Repository**: https://huggingface.co/darjusul/wav2vec2-ONNX-collection

### ONNX Conversions

**Performance** (desktop CPU reference):
- 2.2-2.3x speedup vs PyTorch (Intel CPU)
- Not ARM-specific, but indicative of ONNX gains

**Models Available**:
- Various wav2vec2 checkpoints in ONNX format
- Community-maintained

### OpenVINO Quantization Workflow

**INT8 Quantization**:
- OpenVINO provides workflow for wav2vec2
- Accuracy comparison steps documented
- Suitable for ARM64 deployment via OpenVINO Runtime

**Deployment Complexity**:
- Requires OpenVINO or ONNX Runtime setup
- Custom pipeline construction
- More complex than pre-packaged solutions

**Advantages**:
- Transformer-based (modern architecture)
- ONNX/OpenVINO optimizations
- Quantization support

**Limitations**:
- Requires custom integration
- No pre-built Pi packages
- Less mature than Whisper ecosystem
- No Pi benchmarks

---

## 12. SpeechBrain Models

**Status**: Active research toolkit, 100+ pretrained models
**Repository**: https://github.com/speechbrain/speechbrain

### Characteristics

**Model Hub**:
- 100+ pretrained models on Hugging Face
- Research-friendly toolkit
- Multiple ASR architectures

**Deployment Approach**:
- Not pre-optimized for edge
- Can be combined with ONNX/quantization
- Requires custom optimization pipeline

**Use Case**: Best for research, experimentation, and custom model development rather than production edge deployment.

**Advantages**:
- Large model variety
- Active research community
- Flexible architecture

**Limitations**:
- Not edge-optimized out-of-box
- Requires custom deployment pipeline
- No Pi-specific tooling
- Heavier than dedicated edge solutions

---

## Comparison Matrix: Best Options for Pi 5

### Speed-Optimized (Low Latency Priority)

| Model | Params | Est. RTF | Memory | Accuracy | Maturity | Pi 5 Data |
|-------|--------|----------|--------|----------|----------|-----------|
| Moonshine tiny | 27M | ~0.2-0.3* | ~190MB | 12.66% WER | New (2024-25) | None |
| Vosk small | ~10M | ~0.15-0.25* | ~40MB | Higher WER | Mature | Some |
| faster-whisper tiny int8 | 39M | 0.25-0.45 | <500MB | 12.81% WER | Mature | Yes (Pi 5) |

*Estimated based on claims/similar hardware

### Accuracy-Optimized (Quality Priority)

| Model | Params | Est. RTF | Memory | Accuracy | Maturity | Pi 5 Data |
|-------|--------|----------|--------|----------|----------|-----------|
| faster-whisper base int8 | 74M | ~0.68 | Unknown | 10.32% WER | Mature | Yes (Pi 5) |
| Moonshine base | 62M | ~0.3-0.5* | ~400MB | 10.07% WER | New (2024-25) | None |
| Hailo Whisper base | 74M | Unknown | Unknown | 10.32% WER† | Official | None |

*Estimated based on claims/similar hardware
†Assumes same as standard Whisper base (not verified for Hailo compilation)

### Balanced (Best All-Around)

**Recommendation**: Moonshine tiny or faster-whisper base int8

- Moonshine tiny: Best latency-accuracy tradeoff if claims hold on Pi 5
- faster-whisper base: Most proven with actual Pi 5 benchmarks

---

## Model Selection Guide

### For Your Payphone Project (3-5 second utterances)

**Primary Recommendation**: **Moonshine tiny (27M)**

**Rationale**:
- Short utterances (3-5s) are exactly where Moonshine excels (5-15x speedup vs Whisper)
- 27M parameters fits well in Pi 5 memory
- 12.66% WER competitive with Whisper tiny (12.81%)
- Variable-length encoding optimizes for short audio
- ONNX deployment well-supported

**Secondary Option**: **faster-whisper tiny int8**

**Rationale**:
- Proven Pi 5 performance (RTF 0.25-0.45 on 60s audio)
- Should be faster than realtime on 3-5s utterances
- Mature ecosystem
- CTranslate2 optimizations for ARM64

**NPU-Accelerated Option**: **Hailo Whisper base** (if using AI HAT+ 2)

**Rationale**:
- Offloads STT from CPU (frees resources for VAD/TTS/LLM)
- Base model accuracy (10.32% WER) with NPU acceleration
- Official support from Hailo
- Worth testing despite lack of published benchmarks

### NOT Recommended for Pi 5 Real-Time

- NVIDIA Canary/Parakeet (600M-1B params - too large)
- faster-whisper small/medium (RTF >1 on Pi 5)
- distil-whisper large variants (too large)
- Whisper.cpp without quantization (higher memory, no proven advantage)

---

## Missing Benchmarks & Research Gaps

### Critical Missing Data

1. **Moonshine Pi 5 benchmarks**
   - No published latency/RTF measurements
   - No memory profiling
   - No power consumption data

2. **Hailo Whisper WER/RTF**
   - TPS metric published, but not RTF
   - No WER comparison (pre vs post compilation)
   - No end-to-end latency measurements

3. **whisper.cpp Pi 5 quantization comparison**
   - No Q5_0 vs Q5_1 vs Q8_0 benchmarks
   - Quantization performance on ARM unpredictable (issue #3491)

4. **Streaming vs batch latency**
   - Most benchmarks are batch processing (full audio clip)
   - First-token latency critical for voice assistants
   - Limited streaming benchmark data

### Recommended Next Steps

1. **Benchmark Moonshine tiny on Pi 5**
   - Test with 3-5 second utterances
   - Measure end-to-end latency
   - Compare against current faster-whisper implementation

2. **Test Hailo Whisper base**
   - Measure RTF and first-token latency
   - Compare WER against CPU Whisper base
   - Assess CPU offload benefits

3. **Profile faster-whisper tiny/base int8**
   - Confirm Pi 5 performance on short utterances
   - Measure streaming latency (not just batch)
   - Compare int8 vs float16 quantization

---

## Implementation Priority

### Immediate (Week 1)

1. Benchmark **Moonshine tiny** on Pi 5
   - Install: `pip install useful-moonshine-onnx`
   - Test with your existing audio samples
   - Measure latency on 3-5s utterances

### Short-Term (Week 2-4)

2. Test **Hailo Whisper base** (if AI HAT+ 2 available)
   - Compare against Moonshine tiny
   - Measure CPU usage reduction
   - Validate WER on your use case

3. Benchmark **faster-whisper base int8** as fallback
   - Already proven on Pi 5
   - Test streaming mode
   - Compare against Moonshine

### Evaluation Criteria

| Criterion | Weight | Moonshine tiny | faster-whisper tiny | Hailo Whisper base |
|-----------|--------|----------------|---------------------|-------------------|
| Latency (5s audio) | 40% | TBD | ~0.4-1.0s* | TBD |
| Accuracy (WER) | 30% | 12.66% | 12.81% | 10.32% |
| Memory usage | 15% | ~190MB | <500MB | Unknown |
| Maturity/Stability | 10% | New | Mature | Official |
| Integration ease | 5% | Simple | Simple | Moderate |

*Extrapolated from 60s benchmark assuming linear scaling

### Success Criteria

**Acceptable Performance**:
- End-to-end latency <1.5s for 5s utterance
- WER <15% on telephony audio (may be higher than benchmarks due to audio quality)
- Memory <1GB
- CPU usage <50% average (to share with LLM/TTS)

**Optimal Performance**:
- End-to-end latency <1.0s for 5s utterance
- WER <12%
- Memory <500MB
- CPU usage <30% average

---

## Sources & References

### Primary Research

1. **Moonshine**: https://github.com/moonshine-ai/moonshine
   - Paper: arXiv 2410.15608 (Oct 2024)
   - Flavors paper: arXiv 2509.02523 (Sep 2025)
   - ONNX package: useful-moonshine-onnx (Nov 2025)

2. **Faster-Whisper/CTranslate2**:
   - https://github.com/SYSTRAN/faster-whisper
   - https://github.com/OpenNMT/CTranslate2
   - MDPI Study: https://www.mdpi.com/2227-9709/13/2/19 (2025)

3. **Hailo-10H**:
   - Model Explorer: https://hailo.ai/products/hailo-software/model-explorer/
   - hailo-whisper: https://github.com/hailocs/hailo-whisper
   - Release Notes: 2026-01 Software Suite

4. **whisper.cpp**:
   - https://github.com/ggml-org/whisper.cpp
   - Benchmark issue #89
   - Release v1.7.5+ (2025-2026)

5. **Alternative Models**:
   - Vosk: https://alphacephei.com/vosk/models
   - sherpa-onnx: https://k2-fsa.github.io/sherpa/onnx/
   - onnx-asr: https://github.com/istupakov/onnx-asr

### Benchmark Sources

- **Willow Inference Server** (Pi 4): https://heywillow.io/components/willow-inference-server/
- **OpenBenchmarking.org**: whisper.cpp aggregated results (Jan 31, 2026)
- **MDPI 2025**: Raspberry Pi 5 ASR comparison study

### Community Resources

- whisper.cpp issue tracker (quantization performance discussions)
- Hailo community forums (AI HAT+ 2 support)
- k2-fsa documentation (Zipformer models)

---

## Conclusion

The edge STT landscape in early 2026 offers several viable options for Raspberry Pi 5 deployment, with Moonshine emerging as a promising new entrant claiming significant speed improvements over Whisper. However, **lack of Pi 5-specific benchmarks** remains a critical gap.

**Key Takeaway**: Moonshine tiny offers the best theoretical latency-accuracy tradeoff for short-utterance use cases like your payphone project, but requires empirical validation on Pi 5 hardware before production deployment. Faster-whisper base int8 provides a proven fallback with documented Pi 5 performance.

**Next Steps**: Conduct local benchmarks comparing Moonshine tiny, faster-whisper tiny/base int8, and (if available) Hailo Whisper base on your specific hardware and audio samples.
