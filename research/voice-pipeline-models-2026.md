# Voice Pipeline Model Landscape — February 2026

> Research conducted 2026-02-16 by PAI for the tele-ai AI payphone project.
> Covers LLM, STT, and TTS model alternatives for Raspberry Pi 5 deployment.

---

## Current Stack

| Component | Model | Performance | Notes |
|-----------|-------|-------------|-------|
| **LLM** | Qwen3-4B (Ollama) | ~4.5 tok/s | Pi #2 via Ollama |
| **STT** | Whisper-Base (Hailo-10H) | ~300-534ms | NPU-accelerated |
| **TTS** | Kokoro-82M v0.82 | Marginal real-time | Pi #1 CPU |
| **VAD** | Silero VAD v5 | 61% utterance accuracy | Pre-STT gate |

---

## 1. LLM Alternatives (Pi 5 CPU-Only, 3-4B Class)

### Benchmark Comparison

| Model | Params | Pi 5 tok/s | IFEval | MMLU (5-shot) | GSM8K | BFCL (Tool Call) |
|-------|--------|-----------|--------|---------------|-------|-----------------|
| **SmolLM3-3B** | 3.0B | ~5-5.5 (est.) | **76.7** | 53.5 | 72.8 | 92.3 |
| **Qwen3-4B** (current) | 4.0B | ~4.5 | 68.9 | **65.1** | **82.1** | **95.0** |
| **Gemma 3 4B QAT** | 4.0B | ~3.9 | N/R | 57.0 | N/R | N/R |
| **Phi-4-mini** | 3.8B | ~3.1 | N/R | 67.3 | 88.6 | N/R |
| **Ministral-3-3B** | 3.0B | ~4.5-5.5 (est.) | N/R | N/R | N/R | N/R |
| **Gemma 3 1B** | 1.0B | ~11.6 | N/R | N/R | N/R | N/R |
| **Llama 3.2 3B** | 3.0B | ~4.5 (est.) | 71.6 | 63.4 | 59.2 | 92.3 |

### Top Recommendation: SmolLM3-3B

**Why:** Highest IFEval score (76.7) in this class — 8 points above Qwen3-4B. For a phone operator that must precisely follow persona instructions and not hallucinate phone numbers, instruction-following > general knowledge. Being 3B vs 4B, estimated 10-20% faster.

**Tradeoff:** Lower MMLU (53.5 vs Qwen3's 65.1) — less general knowledge, but phone operator doesn't need broad world knowledge.

**How to try:** `ollama run alibayram/smollm3` or pull `ggml-org/SmolLM3-3B-GGUF` Q5_K_M.

**Fallback:** Keep Qwen3-4B for edge cases needing reasoning depth.

### Speed Optimization Tips

1. **llama.cpp over Ollama** — 10-20% speed gain
2. **Q5_K_M quantization** — best quality/speed balance with 16GB RAM headroom
3. **Short context window** (2048-4096) — phone calls don't need 128K
4. **Overclock Pi 5** to 2.6-2.8GHz with adequate cooling

### Sources

- [SmolLM3-3B Model Card](https://huggingface.co/HuggingFaceTB/SmolLM3-3B)
- [SmolLM3 Blog Post](https://huggingface.co/blog/smollm3)
- [LLM Benchmarks on Pi CM5](https://blackdevice.com/installing-local-llms-raspberry-pi-cm5-benchmarking-performance/)
- [LLM Performance on Pi 5 (Stratosphere Lab)](https://www.stratosphereips.org/blog/2025/6/5/how-well-do-llms-perform-on-a-raspberry-pi-5)
- [Ollama vs llama.cpp on Pi 5](https://medium.com/@omkar121212/ollama-vs-llama-cpp-on-raspberry-pi-5-8e7fbeb310de)
- [SmolLM3 on Ollama (community)](https://ollama.com/alibayram/smollm3)

---

## 2. STT Alternatives (Pi 5 + Hailo-10H)

### Model Comparison

| Model | Params | Pi 5 Latency (est.) | WER (avg) | Streaming | Deployment |
|-------|--------|---------------------|-----------|-----------|------------|
| **Moonshine v2 Small** | 123M | **250-450ms** | **7.84%** | Yes (native) | ONNX on CPU |
| **Moonshine v2 Tiny** | 34M | **80-150ms** | 12.01% | Yes | ONNX on CPU |
| Whisper-Base (current) | 74M | 300-534ms | ~15%+ | No | Hailo NPU |
| Whisper-Small | 244M | N/A | ~9-11% | No | Hailo (buggy) |
| Moonshine v2 Medium | 245M | 450-800ms | 6.65% | Yes | ONNX on CPU |

### Top Recommendation: Moonshine v2 Small

**Released February 12, 2026** — [arxiv.org/abs/2602.12241](https://arxiv.org/abs/2602.12241)

**Why:** 7.84% WER (nearly 2x better than Whisper-Base) at comparable or better latency. Runs on Pi 5 CPU via ONNX — no Hailo NPU needed. Native streaming architecture = no 30-second padding = no hallucination on short phone commands.

**Architecture:** Ergodic streaming encoder with sliding-window self-attention. 80ms lookahead at boundary layers, 320ms finalization buffer.

**Latency on Apple M3 CPU:** 148ms (13.1x faster than Whisper Small). Estimated 250-450ms on Pi 5 ARM.

### Fine-Tuning Opportunity: Flavors of Moonshine

[arxiv.org/abs/2509.02523](https://arxiv.org/abs/2509.02523) — Monolingual fine-tuning of Moonshine achieves 48% lower error rates than Whisper Tiny. Training requires as little as 15-94 hours of labeled data, 1-3 days on 8xH100. Could create an **English telephone-audio specialist** Moonshine model.

### Hailo-10H HEF Compatibility

| Model | HEF Available | Status |
|-------|--------------|--------|
| Whisper-Base | Yes (GenAI Zoo v5.2.0) | Working |
| Whisper-Small | Yes (GenAI Zoo v5.2.0) | Buggy — language token issues |
| Whisper-Large-v3-Turbo | No | Too large |
| Distil-Whisper | No | Requires custom compilation |
| Moonshine v2 | No | ONNX-only (CPU) |

### Whisper Hallucination Mitigation

**Calm-Whisper** ([arxiv.org/abs/2505.12969](https://arxiv.org/abs/2505.12969)) — Fine-tunes only 3 of 20 decoder attention heads. 80%+ reduction in non-speech hallucination with <0.1% WER degradation.

### Sources

- [Moonshine v2 Paper](https://arxiv.org/abs/2602.12241)
- [Flavors of Moonshine](https://arxiv.org/abs/2509.02523)
- [Calm-Whisper](https://arxiv.org/abs/2505.12969)
- [Hailo Whisper Community Thread](https://community.hailo.ai/t/automatic-speech-recognition-pipeline-with-whisper-model/13127)
- [Moonshine GitHub](https://github.com/moonshine-ai/moonshine)
- [Best Open Source STT 2026 (Northflank)](https://northflank.com/blog/best-open-source-speech-to-text-stt-model-in-2026-benchmarks)

---

## 3. TTS Alternatives (Pi 5 CPU)

### Model Comparison

| Model | Params | Pi 5 RTF (est.) | Voices | Emotion Control | Pi 5 Viable? |
|-------|--------|-----------------|--------|-----------------|--------------|
| **Kokoro v1.0** | 82M | ~1-3x | **54** + blending | Voice palette only | YES |
| **Piper v1.4.1** | 15-60M | **10-20x** | 100+ downloadable | None | YES (speed king) |
| Marvis TTS | 250M | ~0.5-1x | Voice cloning (10s) | Limited | Maybe |
| NeuTTS Air | 748M | <0.5x | Clone from 3s audio | Limited | Unlikely |
| Kani-TTS-2 | 400M | <1x | Zero-shot cloning | Independent control | Unlikely |
| Orpheus | 3B | <0.2x | 8 + emotion tags | **Best** | NO (GPU only) |
| Qwen3-TTS | 0.6B+ | <0.5x | Text-prompt design | **Excellent** | NO (GPU only) |

### Top Recommendation: Upgrade Kokoro to v1.0

**Changes from v0.82 to v1.0:**
- **54 voices** across 8 languages (up from ~10)
- **Voice blending** — create unique personas by mixing voices (e.g., 70% af_bella + 30% af_sarah)
- **ONNX optimized** — mixed-precision weights, ~half the size
- Still 82M params, Apache 2.0 licensed

**Persona mapping for 9+ phone personas:**
- Operator: `af_nova` (clean, professional)
- Grandma: `af_sarah` blended with slower speed
- Detective: `am_adam` or `am_echo` (deeper male)
- Comedian: `af_bella` with punchy pacing

**Speed fallback:** Piper v1.4.1 for ultra-responsive moments (10-20x real-time). New ARM64 pip wheel support.

### Emotion Control Gap

Best emotion models (Orpheus `<laugh>`/`<sigh>` tags, Qwen3-TTS text prompts, OpenAudio S1) all require GPU. On Pi 5, use Kokoro's voice palette and speaking rate to imply emotional tones.

### Sources

- [Kokoro-82M on HuggingFace](https://huggingface.co/hexgrad/Kokoro-82M)
- [Kokoro Voices List](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md)
- [Kokoro on Raspberry Pi](https://mikeesto.com/posts/kokoro-82m-pi/)
- [Piper TTS](https://github.com/rhasspy/piper)
- [Orpheus TTS](https://github.com/canopyai/Orpheus-TTS)
- [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS)
- [Kani-TTS-2 (Feb 15, 2026)](https://www.marktechpost.com/2026/02/15/meet-kani-tts-2-a-400m-param-open-source-text-to-speech-model-that-runs-in-3gb-vram-with-voice-cloning-support/)

---

## 4. PersonaPlex-7B (NVIDIA) — Full-Duplex Speech-to-Speech

> [huggingface.co/nvidia/personaplex-7b-v1](https://huggingface.co/nvidia/personaplex-7b-v1) | Released January 15, 2026

### What It Does

PersonaPlex is NVIDIA's **real-time full-duplex speech-to-speech conversational AI**. It replaces the entire STT → LLM → TTS pipeline with a single 7B model that:

- Takes audio in, produces audio out (no intermediate text)
- Handles full-duplex conversation (simultaneous listen + speak)
- Supports persona control via text prompts AND voice reference audio
- Manages interruptions, barge-ins, and natural turn-taking

### Architecture

Based on **Moshi** (Moshiko weights). Stack:
```
Input Audio (24kHz) → Mimi Speech Encoder (ConvNet + Transformer)
                    → Moshi Temporal + Depth Transformer (7B)
                    → Mimi Speech Decoder → Output Audio (24kHz)
```

### Benchmark Performance (FullDuplexBench)

| Metric | Score |
|--------|-------|
| Smooth Turn-Taking Success | 90.8% |
| Turn-Taking Latency | 170ms |
| User Interruption Success | 95.0% |
| Interruption Response Latency | 240ms |
| Speaker Similarity (SSIM) | 0.650 |

### Pi 5 Feasibility: NOT VIABLE

- **Requires:** NVIDIA A100/H100 GPU (tested on A100 80GB)
- **No edge formats:** No GGUF, ONNX, or quantized variants available
- **7B params:** Even if GGUF existed, ~2 tok/s on Pi 5 — far too slow for real-time speech generation

### Relevance to Tele-AI

PersonaPlex represents the **architectural future** of what tele-ai does with discrete components. Key insights:

1. **Full-duplex is the goal** — PersonaPlex handles interruptions and barge-ins natively. Our STT→LLM→TTS pipeline cannot do true full-duplex without significant orchestration.
2. **Persona conditioning** — Their approach (text prompt + voice reference audio) is exactly what we'd want for payphone personas.
3. **When to revisit:** When similar models reach 1-3B parameters with GGUF support, they could replace our entire pipeline. Watch for smaller Moshi-family models.

### Paper

[PersonaPlex: Voice and Role Control for Full Duplex Conversational Speech Models](https://arxiv.org/abs/2602.06053) — Roy et al., 2026

---

## 5. Recommended Upgrade Path

### Immediate (drop-in)

| Component | Current | Upgrade To | Key Gain |
|-----------|---------|------------|----------|
| **LLM** | Qwen3-4B (Ollama) | SmolLM3-3B (llama.cpp, Q5_K_M) | +8 IFEval points, ~20% faster |
| **STT** | Whisper-Base (Hailo) | Moonshine v2 Small (ONNX, CPU) | ~2x better WER, native streaming |
| **TTS** | Kokoro v0.82 | Kokoro v1.0 (ONNX) | 54 voices, voice blending |

### Medium-term (1-2 weeks)

- Fine-tune Moonshine v2 on actual payphone audio (Flavors recipe)
- Benchmark SmolLM3 vs Qwen3 on actual persona prompts
- Test Marvis TTS and NeuTTS Air on Pi 5

### Longer-term

- Watch for smaller PersonaPlex/Moshi-family models (<3B)
- Watch for Hailo GenAI Model Zoo updates (Whisper-Small fix, Moonshine support)
- Consider hybrid: GPU server for emotion-heavy TTS (Orpheus), Pi for telephony I/O
