# HuggingFace Models Research for Raspberry Pi 5 Voice Assistant (2024-2025)

**Research Date**: January 27, 2026
**Target Hardware**: Raspberry Pi 5 (16GB) + Hailo-10H NPU (40 TOPS, 8GB LPDDR4X)
**Target Latency**: <2 seconds end-to-end
**Constraint**: Fully local (no cloud)

---

## 1. Speech-to-Text (STT) Models

### Current: Whisper (tiny/base) - Hailo NPU accelerated

### Alternative Models

#### 🌙 Moonshine-Tiny (RECOMMENDED for ultra-low latency)
- **HuggingFace**: [UsefulSensors/moonshine-tiny](https://huggingface.co/UsefulSensors/moonshine-tiny)
- **Parameters**: 27M (27.1M in safetensors)
- **Disk Size**: ~27MB
- **Released**: October 21, 2024
- **Architecture**: Encoder-decoder transformer with RoPE instead of absolute position embeddings
- **Performance**: 5x reduction in compute vs Whisper tiny.en with no increase in WER
- **Training**: Segments of various lengths without zero-padding for greater encoder efficiency

**Pros**:
- Extremely lightweight (27M vs 39M for Whisper tiny)
- 5x faster than Whisper tiny.en
- Designed specifically for resource-constrained edge devices
- No zero-padding = more efficient inference
- Available in Transformers (added January 10, 2025)

**Cons**:
- Newer model with less community adoption
- Limited language support (English-focused)
- No confirmed Hailo NPU support yet

**Hailo NPU**: Not yet confirmed, but ONNX export should be possible

---

#### 🔹 Distil-Whisper Small.en (RECOMMENDED for balanced performance)
- **HuggingFace**: [distil-whisper/distil-small.en](https://huggingface.co/distil-whisper/distil-small.en)
- **Parameters**: 166M
- **Disk Size**: ~200MB (0.2B params)
- **Released**: 2024 (updated to v3.5 in late 2024)
- **WER**: 12.1% short-form, 12.8% long-form (within 4% of Whisper large-v3)
- **Speed**: 5.6x faster than Whisper large-v2

**Benchmark Performance**:
- LibriSpeech validation.clean: 3.43% WER
- 4x faster than large-v2 on Mac M1
- 9x faster chunked long-form vs OpenAI's sequential algorithm

**Pros**:
- 6x faster than original Whisper
- 49% smaller than Whisper large
- Within 1% WER on out-of-distribution sets
- MIT licensed (commercial use)
- Can be used as assistant model with speculative decoding (2x speedup)

**Cons**:
- Larger than moonshine-tiny
- May cause thermal throttling on Raspberry Pi Zero 2 (small.en model reaches 80°C)
- 166M parameters still significant for lowest-end devices

**Hailo NPU**: Compatible (Whisper models supported by Hailo as of 2024)

**Pi 5 Suitability**: ✅ Excellent - Won't thermal throttle on Pi 5 (unlike Pi Zero 2)

---

#### 🔹 Distil-Whisper Large-v3.5 (For best accuracy)
- **HuggingFace**: [distil-whisper/distil-large-v3.5](https://huggingface.co/distil-whisper/distil-large-v3.5)
- **Released**: Late 2024
- **Training**: 98k hours (4x more diverse than v3)
- **Speed**: 1.5x faster than Whisper-Large-v3-Turbo
- **Features**: "Patient" teacher with extended training schedule and aggressive data augmentation

**Pros**:
- Best accuracy in distil-whisper family
- Faster than Turbo variant
- Trained on most diverse dataset

**Cons**:
- Larger model size than small.en
- May be overkill for payphone use case

---

### STT Recommendation

**Primary**: **Moonshine-Tiny** (27M, 5x faster than Whisper tiny)
**Backup**: **Distil-Whisper Small.en** (166M, proven Hailo support)

---

## 2. Language Models (LLM)

### Current: Qwen2.5:3b via Ollama

### Alternative Models

#### 🔸 Qwen2.5-3B-Instruct (CURRENT - Excellent choice)
- **HuggingFace**: [Qwen/Qwen2.5-3B-Instruct](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct)
- **Parameters**: 3.09B total, 2.77B non-embedding
- **Context Length**: 32,768 tokens (128K capable)
- **Max Generation**: 8,192 tokens
- **Tensor Type**: BF16
- **Architecture**: 36 layers, 16 attention heads (Q), 2 attention heads (KV) with GQA
- **Languages**: 29+
- **Quantization**: 176 quantized variants available

**RAM Requirements** (quantized):
- Q4_K_M (4-bit): 4GB RAM min, 8GB recommended
- Q5_K_M (5-bit): 6GB RAM min, 12GB recommended
- Q8_0 (8-bit): 8GB RAM min, 16GB recommended
- Optimized: 2.4GB (60% less than 7B models)

**Pros**:
- Already in use, proven on Pi 5
- Excellent coding and mathematics performance
- Long context support (32K-128K)
- Extensive multilingual support
- 176 quantized variants for optimization
- Outperforms Phi3.5-mini and MiniCPM3-4B despite fewer parameters

**Cons**:
- Requires separate Pi for optimal performance
- Larger than sub-1B alternatives

**Pi 5 Suitability**: ✅ Excellent (proven in current setup)

---

#### 🌟 SmolLM2-1.7B-Instruct (RECOMMENDED for single-Pi deployment)
- **HuggingFace**: [HuggingFaceTB/SmolLM2-1.7B-Instruct](https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct)
- **Parameters**: 1.7B
- **Disk Size**: ~2GB (BF16)
- **Pretraining**: 11 trillion tokens
- **License**: Apache 2.0
- **RAM**: 6GB minimum (runs on modern smartphones)

**Capabilities**:
- Text generation
- Instruction following
- Text rewriting & summarization
- Function calling (27% on BFCL Leaderboard)
- Conversational AI
- Browser deployment via Transformers.js

**Training**:
- Framework: nanotron
- Hardware: 256 H100 GPUs
- Approach: SFT + DPO alignment with UltraFeedback

**Pros**:
- Smaller than Qwen2.5-3B (1.7B vs 3.09B)
- Apache 2.0 license
- Optimized for on-device deployment
- Browser support via Transformers.js
- Competitive with 3B models in many tasks
- Lower RAM requirements

**Cons**:
- Slightly less capable than Qwen2.5-3B
- Smaller context window than Qwen
- Less multilingual support

**Pi 5 Suitability**: ✅✅ Excellent - Could run on Pi #1 alongside voice services

---

#### 🔹 SmolLM2-360M-Instruct (For ultra-lightweight deployment)
- **HuggingFace**: [HuggingFaceTB/SmolLM2-360M-Instruct](https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct)
- **Parameters**: 360M
- **RAM**: 720MB (bfloat16), 100-300MB quantized
- **Training**: 4 trillion tokens
- **Memory Footprint**: ~720MB

**Pros**:
- Extremely lightweight
- Runs on smartphones and edge devices
- INT8 quantization reduces to <300MB
- Part of SmolLM2 family (135M, 360M, 1.7B)

**Cons**:
- Significantly less capable than 1.7B or 3B models
- May struggle with complex conversations
- Limited function calling ability

**Pi 5 Suitability**: ✅ Good for basic conversations, limited for complex tasks

---

#### 🔹 SmolLM2-135M (For extreme resource constraints)
- **HuggingFace**: [HuggingFaceTB/SmolLM2-135M](https://huggingface.co/HuggingFaceTB/SmolLM2-135M)
- **Parameters**: 135M
- **Memory**: 723MB (bfloat16)
- **Training**: 2 trillion tokens
- **Benchmarks**: 48.2% GSM8K, 56.7% IFEval

**Pros**:
- Smallest SmolLM2 variant
- Fits in <1GB RAM
- Can run on mobile processors

**Cons**:
- Limited capabilities
- Not suitable for complex dialogue

**Pi 5 Suitability**: ⚠️ Usable but limited

---

#### 🔹 Phi-3.5-Mini (Microsoft)
- **Parameters**: 3.8B
- **Focus**: High reasoning performance in compute-constrained settings
- **License**: MIT
- **Formats**: HuggingFace, ONNX, Azure AI Studio

**Pros**:
- Strong reasoning, math, coding capabilities
- MIT licensed
- ONNX support

**Cons**:
- Larger than Qwen2.5-3B (3.8B vs 3.09B)
- Underperforms Qwen2.5-3B in math/coding despite more parameters
- Less extensive quantization ecosystem

---

#### 🔹 Gemma 2 (2B)
- **HuggingFace**: Google's lightweight model family
- **Parameters**: 2B+
- **Features**: Summarization, Q&A, reasoning
- **Integration**: Smooth HuggingFace ecosystem

**Pros**:
- Google backing
- Good HuggingFace integration
- Runs on consumer hardware

**Cons**:
- SmolLM2-1.7B outperforms in benchmarks
- Less context than Qwen2.5

---

### LLM Recommendation

**For dual-Pi (current setup)**: **Qwen2.5-3B-Instruct** (keep current - proven, excellent)
**For single-Pi consolidation**: **SmolLM2-1.7B-Instruct** (best balance of size/capability)
**For extreme efficiency**: **SmolLM2-360M-Instruct** (basic conversations only)

---

## 3. Text-to-Speech (TTS) Models

### Current: Kokoro-82M (82M params, 24kHz)

### Alternative Models

#### ✅ Kokoro-82M (CURRENT - Excellent choice)
- **HuggingFace**: [hexgrad/Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M)
- **Parameters**: 82M
- **Architecture**: StyleTTS 2 + ISTFTNet decoder (no encoder/diffusion)
- **License**: Apache 2.0
- **Languages**: 8 languages
- **Voices**: 54 voices (v1.0)
- **Sample Rate**: 24kHz
- **Release**: v0.19 (December 25, 2024) - #1 ranked in TTS Spaces Arena

**Performance**:
- Generated 30-second sample in <1 second
- High quality with minimal distortion
- API cost: <$1 per million characters (~$0.06/hour audio)

**Training**:
- Data: Few hundred hours permissive/non-copyrighted audio
- Cost: ~$1,000 USD (1000 A100 GPU hours)
- Sources: Public domain, Apache/MIT licensed, synthetic audio

**Pros**:
- Already in use, proven on Pi 5
- Extremely fast (30s audio in <1s)
- Lightweight 82M parameters
- Comparable quality to larger models
- Apache 2.0 license (commercial use)
- 54 voice options
- Actively maintained (v0.19 Dec 2024)

**Cons**:
- Relatively new (may have edge cases)
- Smaller voice dataset than commercial TTS

**Pi 5 Suitability**: ✅✅ Excellent (proven in current setup)

---

#### 🔸 StyleTTS2
- **HuggingFace**: [hexgrad/styletts2](https://huggingface.co/hexgrad/styletts2)
- **GitHub**: [yl4579/StyleTTS2](https://github.com/yl4579/StyleTTS2)
- **Architecture**: Style diffusion + adversarial training with large speech language models
- **Quality**: Surpasses human recordings on LJSpeech, matches on VCTK

**Note**: Kokoro v0.19 uses StyleTTS 2 architecture

**Pros**:
- Human-level synthesis quality
- Strong single and multi-speaker performance
- Kokoro is based on this architecture

**Cons**:
- Diffusion processes can be slower than Kokoro
- Requires more compute than feed-forward models
- May need encoder (Kokoro avoids this)

**Pi 5 Suitability**: ⚠️ Possible but slower than Kokoro

---

#### 🔸 Parler-TTS Mini
- **HuggingFace**: [parler-tts/parler-tts-mini-v1](https://huggingface.co/parler-tts/parler-tts-mini-v1)
- **Parameters**: 880M
- **Released**: August 8, 2024
- **Training**: 45k hours audiobook data
- **Features**: Controllable TTS via text prompts

**Variants**:
- Mini v1: 880M params
- Mini v0.1: 10.5k hours data
- Mini Expresso: 0.6B params (fine-tuned)
- Tiny v1: Smaller variant
- Large v1: 2.2B params

**Pros**:
- Controllable voice characteristics via prompts
- Large training dataset (45k hours)
- Multiple voice control options

**Cons**:
- 880M parameters (10.7x larger than Kokoro)
- Significantly slower inference than Kokoro
- Requires more RAM and compute
- May not meet <2s latency target

**Pi 5 Suitability**: ⚠️ Possible but likely too slow for real-time

---

#### 🔸 Piper TTS
- **HuggingFace**: [Piper TTS Collection](https://huggingface.co/collections/mukhortov/piper-tts)
- **Type**: VITS-based neural TTS
- **Focus**: Fast, lightweight inference
- **Deployment**: Commonly used in Home Assistant, edge devices

**Pros**:
- Proven edge device performance
- Multiple voice models available
- Fast inference
- Active community

**Cons**:
- Quality may be lower than Kokoro/StyleTTS2
- Less natural-sounding than newer models
- Older architecture

**Pi 5 Suitability**: ✅ Good backup option

---

### TTS Recommendation

**Primary**: **Kokoro-82M** (keep current - proven, fastest, excellent quality)
**Backup**: **Piper TTS** (if more voice variety needed)
**Not Recommended**: Parler-TTS Mini (too large), StyleTTS2 (slower than Kokoro)

---

## 4. Voice Activity Detection (VAD)

### Current: Silero VAD (1.8MB)

### Alternative Models

#### 🔹 TEN VAD (RECOMMENDED upgrade)
- **HuggingFace**: [TEN-framework/ten-vad](https://huggingface.co/TEN-framework/ten-vad)
- **Released**: 2024-2025
- **Type**: Real-time VAD for enterprise use

**Performance**:
- Superior precision vs WebRTC VAD and Silero VAD
- Lower computational complexity than Silero VAD
- Reduced memory usage vs Silero VAD

**Pros**:
- Better precision than Silero
- Lower compute and memory than Silero
- Designed for real-time enterprise applications
- Recent release (2024-2025)

**Cons**:
- Newer, less proven in production
- Limited community adoption vs Silero

**Pi 5 Suitability**: ✅ Excellent - Better than Silero

---

#### 🔹 Cobra VAD (Picovoice)
- **Type**: Deep learning + lightweight performance
- **License**: Commercial (not open-source)

**Performance @ 5% False Positive Rate**:
- Cobra: 98.9% TPR (12x fewer errors than Silero, 50x fewer than WebRTC)
- Silero: 87.7% TPR
- WebRTC: 50% TPR

**Pros**:
- Best accuracy of all VAD options
- Production-ready, cross-platform
- Significantly better than Silero/WebRTC

**Cons**:
- Commercial license (not free/open-source)
- Not suitable for open-source project
- Vendor lock-in

**Pi 5 Suitability**: ❌ Not recommended (commercial license)

---

#### 🔹 WebRTC VAD
- **Type**: Gaussian Mixture Model (GMM)
- **Size**: 158 KB
- **Speed**: Exceptional (fastest option)

**Performance @ 5% False Positive Rate**:
- True Positive Rate: 50%

**Pros**:
- Extremely lightweight (158 KB vs 1.8MB Silero)
- Exceptionally fast
- Excellent at silence/noise detection

**Cons**:
- Lower accuracy differentiating speech from background noise
- 50x more errors than Cobra
- May cause false negatives in noisy environments

**Pi 5 Suitability**: ✅ Good for clean environments only

---

#### 🔹 Yamnet VAD
- **Type**: DNN-based (Mobilenet_v1 architecture)
- **Runtime**: TensorFlow Lite
- **Classes**: 521 audio event classes

**Pros**:
- Can classify many audio events beyond speech
- Mobilenet architecture optimized for mobile

**Cons**:
- Overkill for simple VAD task
- Requires TensorFlow Lite runtime
- Larger and slower than dedicated VAD

**Pi 5 Suitability**: ⚠️ Usable but overkill

---

#### ✅ Silero VAD (CURRENT - Good choice)
- **GitHub**: [snakers4/silero-vad](https://github.com/snakers4/silero-vad)
- **Size**: 1.8MB
- **Type**: Enterprise-grade DNN

**Performance**:
- Processes 30+ ms chunk in <1ms on single CPU thread
- ONNX can run 4-5x faster
- 87.7% TPR @ 5% FPR

**Pros**:
- Proven in production
- Fast (<1ms per chunk)
- Good accuracy/performance balance
- ONNX optimization available
- Active maintenance

**Cons**:
- TEN VAD may be more accurate
- Not as accurate as Cobra (but Cobra is commercial)

**Pi 5 Suitability**: ✅ Excellent (proven)

---

### VAD Recommendation

**Primary**: **Silero VAD** (keep current - proven, good balance)
**Upgrade Option**: **TEN VAD** (better precision, lower compute)
**Lightweight Option**: **WebRTC VAD** (if CPU is critical bottleneck)
**Not Recommended**: Cobra VAD (commercial), Yamnet VAD (overkill)

---

## 5. Wake Word Detection

### Current: openWakeWord

### Alternative Models

#### ✅ openWakeWord (CURRENT - Excellent choice)
- **HuggingFace**: [davidscripka/openwakeword](https://huggingface.co/davidscripka/openwakeword)
- **GitHub**: [dscripka/openWakeWord](https://github.com/dscripka/openWakeWord)
- **PyPI**: [openwakeword](https://pypi.org/project/openwakeword/)
- **License**: Creative Commons BY-NC-SA 4.0 (non-commercial)

**Performance**:
- Raspberry Pi 3 (single core): 15-20 models simultaneously in real-time
- Frame rate: 80ms frames
- Output: Confidence score 0-1 per frame
- False-accept rate: <0.5 per hour
- False-reject rate: <5%

**Training**:
- 100% synthetic speech from TTS models
- Google Colab notebook for custom training in <1 hour
- Automatic training pipeline available

**Features**:
- Pre-trained models available on HuggingFace
- Demo available on HuggingFace Spaces
- Focus on performance and simplicity
- Custom wake word training support

**Pros**:
- Proven on Raspberry Pi (15-20 models on Pi 3!)
- Easy custom training (<1 hour)
- Low false-accept/reject rates
- Active development
- HuggingFace integration
- Can run many models simultaneously

**Cons**:
- Non-commercial license (CC BY-NC-SA 4.0)
- Synthetic training data (not real speech)
- May not perform as well with strong accents/noise

**Pi 5 Suitability**: ✅✅ Excellent (proven on Pi 3, will be even better on Pi 5)

---

### Wake Word Alternatives

No strong HuggingFace alternatives found. Other options:

- **Porcupine** (Picovoice): Commercial, not on HuggingFace
- **Snowboy** (archived): No longer maintained
- **Precise** (Mycroft): Less active development

### Wake Word Recommendation

**Primary**: **openWakeWord** (keep current - proven, excellent Pi performance)
**No change needed** - openWakeWord is the best open-source option

---

## Summary & Recommendations

### Quick Wins (Easy Upgrades)

1. **STT**: Switch to **Moonshine-Tiny** (27M) - 5x faster than Whisper tiny, ultra-lightweight
2. **VAD**: Test **TEN VAD** - Better precision and lower compute than Silero

### Keep Current (Already Optimal)

1. **TTS**: **Kokoro-82M** - Best combination of speed, quality, size
2. **Wake Word**: **openWakeWord** - Proven Pi performance (15-20 models on Pi 3!)
3. **LLM** (Dual-Pi): **Qwen2.5-3B-Instruct** - Excellent performance, proven

### Consolidation Option (Single Pi #1)

If you want to consolidate to a single Pi:

1. **LLM**: Switch to **SmolLM2-1.7B-Instruct** (1.7B vs 3.09B)
   - 6GB RAM requirement (fits on Pi #1 with 16GB)
   - Frees up Pi #2 for other uses
   - Competitive performance with Qwen2.5-3B
   - Apache 2.0 license

### Performance Estimates

**Current Setup** (estimated):
- Wake Word: <50ms (openWakeWord on Pi 3 does 15-20 models)
- VAD: <1ms per chunk (Silero)
- STT: ~200-500ms (Whisper tiny on Hailo)
- LLM: ~500-1000ms (Qwen2.5-3B on Pi #2)
- TTS: ~100-200ms (Kokoro-82M, 30s in <1s)
- **Total**: ~800-1700ms ✅

**With Moonshine-Tiny** (estimated):
- STT: ~40-100ms (5x faster than Whisper tiny)
- **Total**: ~640-1400ms ✅ (20-30% improvement)

**Single Pi with SmolLM2-1.7B** (estimated):
- LLM: ~600-800ms (smaller model, same hardware)
- **Total**: ~740-1500ms ✅

---

## Hailo NPU Compatibility

### Confirmed Compatible:
- ✅ Whisper models (official Hailo support)
- ✅ Distil-Whisper (uses Whisper architecture)

### Likely Compatible (ONNX export possible):
- 🟡 Moonshine (encoder-decoder transformer, should export to ONNX)
- 🟡 LLM models (but Hailo primarily for vision/speech, not transformers)

### Not Compatible:
- ❌ TTS models (Hailo focused on ASR, not TTS - confirmed by community)
- ❌ LLM inference (Hailo NPU designed for vision/speech, not large transformers)

**Note**: TTS models will run on Pi CPU - Kokoro is already fast enough (<1s for 30s audio)

---

## Implementation Priority

### Phase 1: Low-Risk Improvements (Test on dev branch)
1. Test **Moonshine-Tiny** for STT (easy swap, 5x faster)
2. Test **TEN VAD** (drop-in Silero replacement)

### Phase 2: Single-Pi Consolidation (If needed)
1. Test **SmolLM2-1.7B-Instruct** on Pi #1
2. Benchmark end-to-end latency
3. Compare quality with Qwen2.5-3B
4. If acceptable, repurpose Pi #2

### Phase 3: Custom Training (Optional)
1. Train custom openWakeWord model for payphone-specific wake phrase
2. Fine-tune Moonshine/Distil-Whisper on telephone audio (if needed)

---

## Sources

### STT
- [Distil-Whisper GitHub](https://github.com/huggingface/distil-whisper)
- [Moonshine HuggingFace](https://huggingface.co/UsefulSensors/moonshine-tiny)
- [Moonshine Paper](https://huggingface.co/papers/2410.15608)
- [Distil-Whisper distil-small.en](https://huggingface.co/distil-whisper/distil-small.en)

### LLM
- [Best Open-Source LLMs 2025](https://huggingface.co/blog/daya-shankar/open-source-llms)
- [Qwen2.5-3B-Instruct](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct)
- [SmolLM2-1.7B-Instruct](https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct)
- [Best Small Language Models 2026](https://www.bentoml.com/blog/the-best-open-source-small-language-models)

### TTS
- [Kokoro-82M HuggingFace](https://huggingface.co/hexgrad/Kokoro-82M)
- [StyleTTS2 GitHub](https://github.com/yl4579/StyleTTS2)
- [Parler-TTS Mini](https://huggingface.co/parler-tts/parler-tts-mini-v1)
- [Best TTS Models 2026](https://www.bentoml.com/blog/exploring-the-world-of-open-source-text-to-speech-models)

### VAD
- [Best VAD 2025 Comparison](https://picovoice.ai/blog/best-voice-activity-detection-vad-2025/)
- [TEN VAD HuggingFace](https://huggingface.co/TEN-framework/ten-vad)
- [Silero VAD GitHub](https://github.com/snakers4/silero-vad)

### Wake Word
- [openWakeWord GitHub](https://github.com/dscripka/openWakeWord)
- [openWakeWord HuggingFace](https://huggingface.co/davidscripka/openwakeword)

### Hailo
- [Hailo Whisper Release](https://community.hailo.ai/t/whisper-full-release-now-available/16228)
- [Hailo TTS Discussion](https://community.hailo.ai/t/has-anyone-successfully-converted-any-text-to-speech-tts-models-to-run-on-the-hailo-8-hailo-8l/2526)
