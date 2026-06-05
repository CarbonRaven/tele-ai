# tele-ai Edge LLM — June 2026 Decision Report

> Intern evaluation of the June 2026 Extensive research against project reality (verified 2026-06-05). Live call answered slowly; synthetic test put first greeting audio at +12s warm. This report says what to do about that. Rubric math verified/corrected by MoneyPenny 2026-06-05.

## 1. TL;DR

- **The bottleneck is TTFT/prefill, not decode speed.** A ~2,000-token operator prompt prefilled at ~30-60 tok/s on Pi 5 CPU = 30-60s of prefill before a single output token. No model swap fixes this; **pulling the 44-number directory out of the system prompt is the single highest-leverage change** and requires zero model change.
- **Do the zero-cost wins first:** directory→tool-call/RAG, llama.cpp (or llamafile) instead of Ollama, strict streaming discipline + a canned instant greeting clip. Expect the biggest felt latency drop here.
- **February's SmolLM3 bet is obsolete as the headline move.** Reasonable Feb call (best IFEval in class) but it's ~2-5 tok/s on Pi — the same dead zone as the current model. June's swap targets: **Qwen3-1.7B** (balance) or **Gemma3-1B** (speed).
- **Qwen3-30B-A3B MoE is the dark horse** (~8 tok/s decode, ~94% quality on this exact 16GB hardware) but its **Pi prefill TTFT is unpublished** — and TTFT is exactly our bottleneck. Bench before believing.
- **Hard "do not": Hailo for the LLM** (measured 2.6-9 tok/s ≈ or slower than CPU), **CPU speculative decoding** (~1x), and adopting any model on an off-Pi benchmark.

## 2. What changed since February

**Still holds (Feb got it right):**
- llama.cpp > Ollama on Pi 5 (~10-20%). June adds **llamafile** (claimed 3-4x throughput, 30-40% lower power — single arXiv source, bench it).
- Keep Hailo on Whisper STT, not the LLM — June confirms with measured LLM numbers.
- Conversational band is ~10-20 tok/s; current 4.5 tok/s is the dead zone.
- Streaming TTS (token→audio chunks) is the right architecture.

**Obsolete / changed:**
- **SmolLM3-3B as "the upgrade" is dead.** Feb ranked it #1 on IFEval (76.7) and *estimated* ~5-5.5 tok/s; reality is the ~2-5 tok/s 3B band. The broken Feb-23 branch is the empirical refutation. Feb's instinct (instruction-following > world knowledge) remains correct — the model that delivers it at speed changed.
- **Decode speed was the wrong frame.** February optimized tok/s. June's key insight — which Feb missed entirely — is that **TTFT (prefill of the giant prompt) dominates perceived phone latency** when TTS streams. This reframes the whole problem.
- **STT:** Feb pushed Moonshine v2 Small (off an M3 benchmark). June: no STT breakthrough; the working Hailo + Moonshine-fallback stack is already right. Don't chase STT now.

**Newly possible (June only):**
- **Qwen3-30B-A3B MoE** on a 16GB Pi at all (Q3_K_S, 2.7bpw) — not an option in Feb.
- **Supertonic 3 TTS** (May 2026) — faster RTF than Kokoro (benchmarked on EPYC, not Pi).
- **Directory→tool-call architecture** as a named TTFT lever.

**Where June is oversold (intern flags):**
- The 30B MoE's "8 tok/s, 94%" headline buries that **its TTFT on Pi is unpublished** — the deciding number for a phone.
- llamafile's "3-4x" is a single arXiv claim — hypothesis, not fact.
- Every MED/LOW Pi tok/s row (Qwen3-1.7B, Phi-4-mini, SmolLM3, LFM2) needs local confirmation.

## 3. Evaluation matrix

Rubric: TTFT impact 40% · Decode ≥10 tok/s 20% · Persona/instruction quality 20% · Integration effort 10% · Evidence confidence 10%. Scores 1-5. *(Weighted column recomputed and verified 2026-06-05.)*

| Candidate | TTFT (40%) | Decode (20%) | Persona (20%) | Integ (10%) | Evidence (10%) | **Weighted** |
|---|---|---|---|---|---|---|
| **Qwen3-0.6B** | 5 | 5 (~21) | 2 | 4 | 5 | **4.30** |
| **Gemma3-1B** | 4 | 5 (~15.5) | 3 | 4 | 5 | **4.10** |
| **Qwen3-1.7B** | 4 | 4 (~10-13) | 4 | 4 | 3 | **3.90** |
| **LFM2-1.2B** | 4 | 4 (est) | 3 | 3 | 2 | **3.50** |
| **qwen3:4b-instruct (baseline)** | 2 | 1 (~4.5) | 5 | 5 | 5 | **3.00** |
| **Qwen3-30B-A3B MoE** | 2 (unknown) | 3 (~8) | 5 | 2 | 3 | **2.90** |
| **SmolLM3-3B** | 2 | 2 (~2-5) | 5 | 3 | 3 | **2.80** |
| **Phi-4-mini** | 2 | 2 (~2-4) | 4 | 2 | 2 | **2.40** |

**Read:** Qwen3-0.6B tops the raw math — but that's a rubric artifact: for a product whose entire job is persona + accurate directory behavior, a persona score of 2 is closer to disqualifying than the 10%-of-rubric it costs. **Qwen3-1.7B remains the bench-first pick** (best speed/persona balance); Gemma3-1B is the speed alternative. The 30B MoE sits low *only* because its TTFT is unknown — if B6 measures well, it jumps to the top on quality. Baseline (3.00) outscores SmolLM3 (2.80): the Feb experiment wasn't even a lateral move. And all of these still lose to fixing the prompt — Phase A.

## 4. Use-case mapping — three phases

### Phase A — zero model change (do first, this week)
1. **Directory → tool-call / RAG lookup.** Pull all 44 numbers out of the system prompt; give the operator `lookup_directory(query)` or a tiny retrieval step. Prompt drops from ~2,000 tokens toward a few hundred. *Gain: largest single TTFT cut available — seconds off first-audio. Effort: medium. Risk: medium — the model must reliably call the tool; re-verify the no-hallucinated-numbers behavior (it was prompt-enforced in Feb).*
2. **Ollama → llama.cpp** (then trial llamafile). *Gain: 10-20%+, possibly more. Effort: low-medium. Risk: low — current stack stays as fallback.*
3. **Streaming discipline + instant canned greeting.** First clause → TTS immediately; greeting can be a cached audio clip that plays at answer while the LLM spins up. *Gain: kills the +12s dead-air problem outright. Effort: low. Risk: low.*

> Phase A target: warm first-greeting audio from +12s to **<3s** *before changing any model.*

### Phase B — model swap (after Phase A, measured)
- **Bench first: Qwen3-1.7B and Gemma3-1B.** With a stripped prompt, 10-15 tok/s + streaming should feel like a phone call (first-audio ~2-4s warm). *Effort: low once llama.cpp is in. Risk: persona/9-voice fidelity at 1-1.7B must be ears-tested (B5) — this is where SmolLM3's IFEval edge mattered.*
- **Stretch bench: Qwen3-30B-A3B Q3_K_S.** Only if measured Pi TTFT passes (B6). Best persona experience if it does. *Risk: high on TTFT; never deploy on decode numbers alone.*

### Phase C — pipeline rework (horizon)
- **Supertonic 3 TTS** (5-step) vs Kokoro for first-chunk latency — local bench, ears-on (2-step is robotic).
- **Full STT offload to Hailo** so CPU is 100% free during user speech — frees CPU exactly when TTFT needs it; pairs well with the MoE if pursued.
- Watch sub-3B full-duplex (Moshi/PersonaPlex family) — still not Pi-viable per both Feb and June.

## 5. Bench plan (on the real Pis; pass thresholds tied to <3s first-audio)

| # | Test | Measure | Pass |
|---|---|---|---|
| B1 | Prefill: current vs directory-stripped prompt | TTFT ms per prompt size, same model | stripped TTFT < 1.5s warm |
| B2 | Ollama vs llama.cpp vs llamafile (same model/quant) | decode tok/s, TTFT, temp | llama.cpp ≥ Ollama; fastest stable wins |
| B3 | Decode sweep: baseline, Qwen3-1.7B, Gemma3-1B, Qwen3-0.6B | tok/s | ≥10 to advance |
| B4 | End-to-end first-greeting audio per candidate | s from call-start to first audio, warm+cold | **<3s warm**, <5s cold |
| B5 | Persona fidelity at 1-1.7B | directory accuracy, hallucinated-number check, 9-persona distinguishability | zero hallucinated numbers |
| B6 | Qwen3-30B-A3B Q3_K_S | **TTFT (the deciding number)**, decode, sustained temp | TTFT <3s warm or it's out |
| B7 | Thermal: 10-min sustained call | °C, throttle events | no throttle (active cooling, SSD boot) |
| B8 | Egress audit during benches | tcpdump/nftables | zero cloud egress (ISC-30) |

**Bench only after the suspect PSU is replaced** — undervoltage poisons every number.

## 6. Do NOT do

- **LLM on the Hailo-10H** — measured ≈ or slower than CPU; keep it on Whisper STT.
- **CPU speculative decoding** — ~0.89-1.06x, often slower on MoE (llama.cpp #21453 unfinished).
- **Adopt the 30B MoE on decode numbers alone** — TTFT unmeasured, TTFT is the bottleneck.
- **Swap models before stripping the directory** — you'll credit the model with the prompt's win.
- **Trust off-Pi benchmarks** (Supertonic/EPYC, Moonshine/M3, llamafile claims) for deployment decisions.
- **Resurrect the Feb-23 branch wholesale** — SmolLM3 is in the dead zone; cherry-pick only what benches (ISC-34 disposition).
- **Bench on the suspect power supply** — replace PSU first.
- **Chase a new STT model now** — no breakthrough; ISC-8 stack is right.

## 7. Sources (confidence per claim — all live June 2026)

- Hailo LLM ≈/slower than CPU [HIGH]: codesota.com/embedded-ai/hailo-10h-llms · schwab.sh/blog/hailo-ai-hat-benchmarks · hardware-corner.net/local-llms-raspberry-pi-ai-hat-plus-2
- Hailo marketing vs reality [HIGH, conflict resolved]: hailo.ai/blog/bringing-on-device-generative-ai-to-the-pi
- Qwen3-30B-A3B ~8 tok/s @ Q3_K_S, ~94% [HIGH decode; TTFT NONE]: byteshape.com/blogs/Qwen3-30B-A3B-Instruct-2507
- llamafile 3-4x claim [MED, single source]: arxiv.org/html/2511.07425v1
- Pi decode benchmarks [HIGH/MED per row]: pocketclaw.dev/guides/raspberry-pi-5-self-hosted-ai-90-day-benchmark · stratosphereips.org (Jun 2025)
- Small-LM landscape [MED]: bentoml.com/blog/the-best-open-source-small-language-models
- LFM2 CPU-edge design [LOW, no Pi bench]: arxiv.org/pdf/2511.23404
- Supertonic 3 vs Kokoro [MED, EPYC not Pi]: heyneo.com/blog/kokoro-tts-vs-supertonic-3-tts · mikeesto.com/posts/kokoro-82m-pi (Pi4, older) · wiki.agentvoiceresponse.com/en/kokoro-tts
- CPU spec-decode unviable [HIGH]: github.com/ggml-org/llama.cpp/issues/21453
- Quant quality refs [MED]: arXiv 2601.14277 · arXiv 2511.07425
- Feb sources carried: SmolLM3 card (Pi-speed estimate REFUTED) · Moonshine v2 arXiv (Pi latency still estimated) · Kokoro HF card [HIGH]

**Bottom line:** June's real contribution isn't a new model — it's the reframe: *prefill of the giant prompt, not decode tok/s, is what makes the operator feel slow.* Fix the prompt, switch runtimes, then swap to ~1.7B and bench the 30B MoE's TTFT before believing the hype.

---
*Cross-links: [[2026-06-05 tele-ai restart]] · repo `research/voice-pipeline-models-2026.md` (Feb, superseded in part) · `tele-ai/ISA.md` ISC-34, Phase A→B→C candidates.*
*Provenance: Research skill Extensive mode (multi-angle, 14/14 URLs verified) → intern evaluation vs Feb research + ISA → MoneyPenny rubric-math verification (5 of 8 weighted scores corrected; ranking analysis updated).*
