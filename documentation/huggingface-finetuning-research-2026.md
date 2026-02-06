# HuggingFace Models and Fine-Tuning Research for Payphone-AI

**Date:** February 2026
**Purpose:** Research whether HuggingFace models or training can improve the payphone-ai project
**Status:** Research only — no code changes

---

## Executive Summary

Fine-tuning a small LLM (1B-4B parameters) via HuggingFace tools is a practical and high-impact improvement path for this project. The primary benefits are: shorter, more natural phone-style responses; consistent persona maintenance; and reduced latency through trained conciseness. The recommended workflow is to fine-tune Qwen3-4B (or a comparable model) using QLoRA on a cloud GPU via Unsloth/TRL, export to GGUF, and deploy on Ollama. A dataset of 500-1,000 curated conversation examples is sufficient for LoRA-based persona and style fine-tuning. Several newer model alternatives (Gemma-3n E2B, Phi-4-mini, Qwen3-4B-Instruct-2507) also warrant evaluation as potential upgrades to the current stack.

---

## 1. Fine-Tuning Small LLMs via HuggingFace

### 1.1 Why Fine-Tune for This Project

The current system uses `qwen3:4b` on Ollama with system prompts defined in `payphone-app/config/prompts.py`. System prompts instruct the model to "Keep responses brief and phone-appropriate (under 100 words)" and define personas like the Operator, Detective Jones, Grandma Mae, and COMP-U-TRON 3000.

System prompts work, but have inherent limitations:

1. **Verbosity**: General-purpose models are trained on web text where longer answers score higher in RLHF. Even with "keep it brief" instructions, models drift toward longer responses.
2. **Persona drift**: Over multi-turn conversations, models can break character. System prompt adherence degrades as context length grows.
3. **Token waste**: Every call burns tokens re-processing the same lengthy system prompt. A fine-tuned model internalizes these instructions.
4. **Latency**: Shorter, trained-in response patterns generate fewer tokens, directly reducing TTS wait time.

Fine-tuning addresses all four issues by baking the desired behavior directly into the model weights.

### 1.2 Available Tools and Libraries

| Tool | Purpose | Key Feature |
|------|---------|-------------|
| [Transformers](https://huggingface.co/docs/transformers) | Model loading and training | Supports all major model architectures |
| [PEFT](https://huggingface.co/docs/peft) | Parameter-efficient fine-tuning | LoRA, QLoRA adapter training |
| [TRL](https://huggingface.co/docs/trl) | SFTTrainer for supervised fine-tuning | Handles chat templates, dataset formatting |
| [BitsAndBytes](https://github.com/bitsandbytes-foundation/bitsandbytes) | 4-bit/8-bit quantization during training | Enables QLoRA on consumer GPUs |
| [Unsloth](https://unsloth.ai/) | 2x faster LoRA training, 70% less VRAM | Direct GGUF and Ollama export |
| [Datasets](https://huggingface.co/docs/datasets) | Data loading and processing | Streaming, HF Hub integration |

**Unsloth** simplifies the entire pipeline from training through export. It wraps TRL's SFTTrainer with kernel-level optimizations and provides a single `save_pretrained_gguf()` method that outputs GGUF files ready for Ollama, including auto-generating the Modelfile.

### 1.3 LoRA vs QLoRA vs Full Fine-Tuning

For a 4B parameter model and a dataset of hundreds to low thousands of examples, LoRA or QLoRA is the correct choice:

| Method | VRAM Needed (4B model) | Trainable Params | Quality | Cost |
|--------|----------------------|-----------------|---------|------|
| Full fine-tune | 32-48 GB | 100% (~4B) | Best | High |
| LoRA (16-bit) | 16-24 GB | ~0.1-1% (~4-40M) | Very good | Medium |
| QLoRA (4-bit) | 8-12 GB | ~0.1-1% (~4-40M) | Good | Low |

Key findings:

- For datasets with fewer than 1,000 examples, LoRA often **outperforms** full fine-tuning by preventing overfitting
- QLoRA reduces the base model to 4-bit precision during training while keeping adapter weights in 16-bit, enabling training of 4B models on a single 24GB GPU (RTX 4090 or A10G)
- Full fine-tuning only becomes favorable with million-scale datasets

**Recommended configuration for Qwen3-4B QLoRA:**

```
load_in_4bit: true
lora_target_modules: "all-linear"
lora_r: 16
lora_alpha: 16
learning_rate: 2.0e-4
per_device_train_batch_size: 4-8
max_seq_length: 2048
num_train_epochs: 3-5
```

### 1.4 Practical Workflow: Fine-Tune, Export, Deploy

**Stage 1: Prepare Training Data**

Create a dataset of conversations in the chat template format that Qwen3 expects. Each example should be a multi-turn conversation demonstrating the desired behavior.

```json
{
  "messages": [
    {"role": "system", "content": "You are a friendly 1990s telephone operator. Keep responses under 50 words. Stay in character."},
    {"role": "user", "content": "Hey, what services do you have?"},
    {"role": "assistant", "content": "Well hello there, caller! Welcome to the line. You can press 1 for jokes, 2 for your fortune, or 3 for trivia. I can also help you with just about anything. What sounds good?"}
  ]
}
```

**Stage 2: Fine-Tune on Cloud GPU**

| Platform | GPU | Cost Estimate | Time for 1K examples |
|----------|-----|---------------|---------------------|
| Google Colab (free tier) | T4 (16GB) | Free | 30-60 min with QLoRA |
| HuggingFace Jobs | A10G (24GB) | ~$15-40 total | 20-40 min |
| RunPod | A10G (24GB) | ~$0.50-0.75/hr | 20-40 min |
| Lambda Labs | A10G (24GB) | ~$0.60/hr | 20-40 min |

A free Google Colab T4 is sufficient for QLoRA fine-tuning of a 4B model with 1,000 examples.

**Stage 3: Merge and Export to GGUF**

With Unsloth:

```python
model.save_pretrained_gguf(
    "payphone-qwen3-4b",
    tokenizer,
    quantization_method="q4_k_m"
)
```

Without Unsloth (manual):

1. Merge LoRA adapter into base model weights
2. Save as safetensors
3. Convert with `llama.cpp/convert_hf_to_gguf.py`
4. Quantize with `llama-quantize` to Q4_K_M

**Stage 4: Import to Ollama**

```bash
# If using Unsloth's auto-generated Modelfile:
ollama create payphone-operator -f Modelfile

# Or from a GGUF on HuggingFace:
ollama run hf.co/your-username/payphone-qwen3-4b-GGUF:Q4_K_M
```

**Stage 5: Deploy on Pi #2**

Replace the model name in settings — the system prompt in `prompts.py` can then be significantly shortened or eliminated, since the behavior is baked into the model weights.

### 1.5 Training Data Requirements

| Goal | Minimum Examples | Recommended | Notes |
|------|-----------------|-------------|-------|
| Response length control | 200-300 | 500+ | Teach concise phone answers |
| Single persona (operator) | 300-500 | 800+ | Consistent character voice |
| Multiple personas | 500-1,000 | 1,500+ | 200-300 per persona |
| Domain vocabulary (90s phone) | 300-500 | 700+ | Period-appropriate language |
| Combined (all above) | 800-1,500 | 2,000-3,000 | Full payphone style |

Key guidance:

- With fewer than 1,000 examples, LoRA is preferred over full fine-tuning
- Training for 3-5 epochs with early stopping is standard for small datasets
- Learning rate of 2e-4 to 2e-5 works well across popular models
- For extremely small datasets (under 500), training up to 20-25 epochs can help with early stopping

### 1.6 Relevant HuggingFace Datasets

**Telephone and Call Center Datasets:**

| Dataset | Size | Description |
|---------|------|-------------|
| [AIxBlock/92k-real-world-call-center-scripts-english](https://huggingface.co/datasets/AIxBlock/92k-real-world-call-center-scripts-english) | 91,706 transcripts | Real call center conversations across industries |
| [AxonData/english-contact-center-audio-dataset](https://huggingface.co/datasets/AxonData/english-contact-center-audio-dataset) | 1,000+ hours | Real English call center audio with transcripts |
| [talkmap/telecom-conversation-corpus](https://huggingface.co/datasets/talkmap/telecom-conversation-corpus) | 200,000 conversations | Synthetic telecom customer service dialogs |
| [knkarthick/dialogsum](https://huggingface.co/datasets/knkarthick/dialogsum) | 13,460 dialogues | Service provider and customer conversations |

**Customer Service and Dialog Datasets:**

| Dataset | Size | Description |
|---------|------|-------------|
| [bitext/Bitext-customer-support-llm-chatbot-training-dataset](https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset) | Large | Curated by computational linguists |
| [syncora/customer_support_conversations_dataset](https://huggingface.co/datasets/syncora/customer_support_conversations_dataset) | Large | LLM training for dialogue generation |
| [google/air_dialogue](https://huggingface.co/datasets/google/air_dialogue) | Large | Structured conversation between agent and customer |

**Practical approach:** The most impactful training data will be custom-authored examples demonstrating the exact persona voices, response lengths, and conversational patterns desired. Use existing datasets for:

1. Mining realistic phone conversation structures and turn-taking patterns
2. Extracting examples of concise, natural phone responses
3. Augmenting hand-written persona examples with phone-style dialog patterns
4. Creating "rejected" examples for DPO training (verbose responses as negatives)

---

## 2. HuggingFace Model Alternatives for Pi 5

### 2.1 Current Baseline: Qwen3-4B

The project currently runs `qwen3:4b` on Pi #2 (Raspberry Pi 5, 16GB, no GPU). On Pi 5, 3B-4B models generally achieve 4-7 tokens per second at Q4_K_M quantization.

### 2.2 Candidate Replacement Models

**Tier 1: Strong Candidates (test first)**

| Model | Params | Est. TPS on Pi 5 | RAM | Strengths |
|-------|--------|-------------------|-----|-----------|
| [Gemma-3n-E2B-IT](https://huggingface.co/unsloth/gemma-3n-E2B-it-GGUF) | 5B raw / 2B effective | 8-12 | ~2 GB | Fastest option, huge RAM headroom |
| [Gemma-3n-E4B-IT](https://ollama.com/library/gemma3n:e4b) | 8B raw / 4B effective | 5-8 | ~3 GB | Better quality than E2B, still light |
| [Phi-4-mini-instruct](https://huggingface.co/microsoft/Phi-4-mini-instruct) | 3.8B | 5-8 | ~3.2 GB | Strong reasoning, dialog-focused |
| [Qwen3-4B-Instruct-2507](https://huggingface.co/Qwen/Qwen3-4B-GGUF) | 4B | 4-7 | ~3.5 GB | Latest instruct tune |

**Tier 2: Worth Testing**

| Model | Params | Est. TPS on Pi 5 | RAM | Strengths |
|-------|--------|-------------------|-----|-----------|
| [SmolLM2-1.7B-Instruct](https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct) | 1.7B | 10-15 | ~1.5 GB | Maximum speed option |
| [Llama-3.2-3B-Instruct](https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct) | 3B | 5-8 | ~2.5 GB | Well-tested community support |
| Granite-4.0-Micro | Small | TBD | TBD | IBM's edge-optimized model |

**Gemma-3n-E2B-IT analysis:** Google's parameter-skipping and PLE caching techniques mean it operates with an effective memory load of only 1.91B parameters, requiring ~2GB RAM. On the 16GB Pi #2, this leaves vast headroom. Estimated throughput could be 2-3x faster than Qwen3-4B, directly translating to lower latency. Trade-off: lower effective parameter count may reduce quality for complex reasoning, but for short phone conversations this is unlikely to matter.

### 2.3 Quantization Formats

| Format | Ollama Support | Best For |
|--------|---------------|----------|
| GGUF (Q4_K_M) | Native | Best balance of quality and speed (recommended) |
| GGUF (Q3_K_M) | Native | Maximum speed, slight quality loss |
| GGUF (Q5_K_M) | Native | Better quality, 15-20% more RAM |
| GGUF (Q8_0) | Native | Near-FP16 quality, 2x RAM vs Q4 |
| AWQ / GPTQ | Via conversion | GPU-optimized, not relevant for Pi |

**Q4_K_M is the recommended quantization for Pi 5 deployment.**

Trusted sources for pre-quantized GGUF models:
- [bartowski](https://huggingface.co/bartowski) — extensive GGUF library with imatrix quantization
- [unsloth](https://huggingface.co/unsloth) — official Unsloth quantizations
- [Qwen (official)](https://huggingface.co/Qwen) — official GGUF releases

---

## 3. Practical Fine-Tuning Benefits

### 3.1 Shorter, More Natural Phone Responses

**Highest-impact benefit.** The current `max_tokens: 150` is a hard cutoff, not stylistic control. Fine-tuning with 200-300 examples where assistant responses are consistently 20-60 words teaches the model that short output is expected.

**Expected impact:**
- Average response length drops from 80-120 tokens to 30-60 tokens
- TTS generation time cuts roughly in half
- End-to-end latency reduction of 500-1000ms per exchange

### 3.2 Consistent Persona Maintenance

For each persona, create 200-300 multi-turn conversation examples (5-10 turns each) that demonstrate consistent character voice. Include examples where the user tries to break character and the model stays in role.

A single fine-tuned model can support multiple personas using a system prompt tag like `[PERSONA: detective]` during training.

**Expected impact:**
- Near-zero persona drift across 10+ turn conversations
- Shorter system prompts needed (reduces prompt processing time)

### 3.3 Latency Reduction

Three mechanisms:

1. **Fewer output tokens**: 30-word answers = 30-40 tokens vs 100-150. At 5 TPS, that's 6-8s vs 20-30s
2. **Shorter system prompts**: Fine-tuned model needs only a brief persona tag, saving 100-250 tokens of prompt processing per turn
3. **More predictable generation**: Fine-tuned models have lower entropy for in-domain tasks

**Expected total latency improvement:** 1-3 seconds per exchange.

### 3.4 Custom Vocabulary and Style

Training data can include:
- Period-appropriate slang ("groovy," "radical," "talk to the hand")
- Telephone phrases ("please hold," "your call is important to us," "at the tone")
- 90s pop culture references
- Phone etiquette ("May I ask who's calling?", "One moment please")
- DTMF menu phrasing ("Press 1 for... or press star to return")

---

## 4. Recommended Implementation Plan

### Phase 1: Dataset Creation (1-2 weeks)

1. Author 200-300 "gold standard" examples for the Operator persona
2. Author 100-150 examples per additional persona (Detective, Grandma, Robot)
3. Mine existing HF datasets for phone conversation patterns
4. Create "rejected" examples for potential DPO training
5. Target total: 1,500-2,500 examples across all personas

### Phase 2: Fine-Tuning (1 day)

1. Use Unsloth on Google Colab (free T4) or HuggingFace Jobs (~$20)
2. Base model: Qwen3-4B or Gemma-3n-E4B (whichever wins evaluation)
3. Config: QLoRA with lora_r=16, learning_rate=2e-4, 3-5 epochs
4. Export: GGUF Q4_K_M via `save_pretrained_gguf()`
5. Upload to HuggingFace Hub for versioning

### Phase 3: Evaluation (2-3 days)

1. A/B test fine-tuned model against base model with system prompts
2. Measure: response length, persona consistency, latency, subjective quality
3. Test on Pi 5 to confirm inference speed matches or exceeds current model
4. Iterate on training data if needed

### Phase 4: Model Alternatives Evaluation (parallel with Phases 1-2)

1. Test Gemma-3n-E2B-IT: `ollama run gemma3n:e2b`
2. Test Phi-4-mini: `ollama run phi4-mini`
3. Test SmolLM2-1.7B for speed comparison
4. Benchmark all: tokens/second, response quality, memory usage
5. Select best base model for fine-tuning

---

## 5. Challenges and Limitations

### Technical

1. **Chat template consistency**: Template used during fine-tuning must exactly match inference in Ollama. Unsloth auto-generates the correct Modelfile.
2. **Evaluation difficulty**: No standard benchmark for "phone conversation quality." Evaluation will be largely subjective.
3. **Catastrophic forgetting**: Aggressive fine-tuning on narrow data can lose general capabilities. LoRA mitigates this by only training adapter weights.
4. **Audio domain mismatch**: Training data should include realistic transcription errors characteristic of telephone audio through STT.

### Practical

1. **Pi 5 inference ceiling**: CPU-only inference is limited to ~5-12 TPS for 2B-4B models at Q4_K_M regardless of fine-tuning.
2. **No local fine-tuning**: Pi 5 lacks compute for training. Cloud GPU required.
3. **Ongoing maintenance**: As personas evolve, model needs retraining. Less agile than editing system prompts.
4. **Quantization quality loss**: Fine-tuned behaviors should be tested post-quantization, not just at FP16.

---

## 6. Key Recommendations

### Highest Priority

1. **Evaluate Gemma-3n-E2B-IT** on Pi #2 immediately — `ollama run gemma3n:e2b`. Its 2GB footprint and native Ollama support make it the most promising latency improvement with zero fine-tuning effort.

2. **Begin authoring training data** for the Operator persona. Even 300 high-quality examples of short, in-character phone conversations will produce measurable improvement via LoRA.

### Medium Priority

3. **Fine-tune Qwen3-4B (or evaluation winner) using Unsloth on free Colab T4.** Complete workflow from fine-tuning to GGUF export to Ollama deployment can be done in a single session.

4. **Consider DPO (Direct Preference Optimization)** as a follow-up to SFT. Create pairs of good/bad responses (concise vs verbose, in-character vs out-of-character) to further refine behavior.

### Lower Priority

5. **Explore Qwen3-30B-A3B MoE** as an advanced option. Uses only 3B active parameters (fits Pi 5) but has 30B total for broader knowledge. Benchmarks show 8.03 TPS on Pi 5. Fine-tuning MoE models is more complex.

---

## Sources

- [How to fine-tune open LLMs in 2025 with Hugging Face](https://www.philschmid.de/fine-tune-llms-in-2025)
- [Unsloth Qwen3 Fine-Tuning Guide](https://docs.unsloth.ai/models/qwen3-how-to-run-and-fine-tune)
- [Unsloth Saving to Ollama](https://unsloth.ai/docs/basics/inference-and-deployment/saving-to-ollama)
- [Unsloth Saving to GGUF](https://unsloth.ai/docs/basics/inference-and-deployment/saving-to-gguf)
- [Qwen3-4B-GGUF (Official)](https://huggingface.co/Qwen/Qwen3-4B-GGUF)
- [Gemma-3n-E2B-IT GGUF (Unsloth)](https://huggingface.co/unsloth/gemma-3n-E2B-it-GGUF)
- [Gemma 3n on Ollama](https://ollama.com/library/gemma3n)
- [Gemma 3n Developer Guide](https://developers.googleblog.com/en/introducing-gemma-3n-developer-guide/)
- [How Well Do LLMs Perform on a Raspberry Pi 5?](https://www.stratosphereips.org/blog/2025/6/5/how-well-do-llms-perform-on-a-raspberry-pi-5)
- [7 Tiny AI Models for Raspberry Pi](https://www.kdnuggets.com/7-tiny-ai-models-for-raspberry-pi)
- [Top Small Language Models for 2026](https://www.datacamp.com/blog/top-small-language-models)
- [Best Open-Source SLMs in 2026](https://www.bentoml.com/blog/the-best-open-source-small-language-models)
- [Practical Tips for Finetuning LLMs Using LoRA](https://magazine.sebastianraschka.com/p/practical-tips-for-finetuning-llms)
- [HuggingFace PEFT LoRA Conceptual Guide](https://huggingface.co/docs/peft/main/en/conceptual_guides/lora)
- [Importing a Model to Ollama](https://docs.ollama.com/import)
- [HuggingFace Hub GGUF Ollama Integration](https://huggingface.co/docs/hub/en/ollama)
- [Consistently Simulating Human Personas with Multi-Turn RL](https://arxiv.org/html/2511.00222v1)
- [We Got Claude to Fine-Tune an Open Source LLM](https://huggingface.co/blog/hf-skills-training)
