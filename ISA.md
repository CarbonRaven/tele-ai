---
project: tele-ai
task: AI Payphone — system of record
effort: E3
phase: active
mode: project
started: 2026-02-10
updated: 2026-06-05
---

# ISA — tele-ai (AI Payphone)

> Project ISA, seeded 2026-06-05 from PROJECT_STATUS.md, the restart review, and live hardware inspection. This file is the system of record; PROJECT_STATUS.md remains the detailed session journal.

## Problem

A real 1990s payphone is a dead object. The craft problem: make it a fully-working telephone portal to local AI — dialable services, real personas, vintage telco behavior — with zero cloud dependence, on hardware that fits inside/beside the phone (two Raspberry Pi 5s).

## Vision

Someone picks up the handset, gets a dial tone, dials 867-5309 — and something delightful answers. Every number in the phone book works. Latency feels like a phone call, not a chatbot. The illusion holds: SIT tones, operator transfers, hold behavior. Euphoric surprise is a guest laughing at the Roast Line and then trying ten more numbers.

## Out of Scope

Cloud APIs for core voice path (LLM/STT/TTS stay local). Multi-line/concurrent-trunk support. Public/internet exposure. Mobile apps. Replacing Asterisk.

## Principles

- Local-first: the phone works with the WAN unplugged.
- The telephone illusion outranks technical purity — Bellcore-accurate behavior over feature count.
- Verify on the physical handset; lab tests gate, hardware tests prove.
- Latency budget is experiential: first audio ≤ a few seconds or the illusion breaks.

## Constraints

- Hardware: 2× Pi 5 (16GB), Hailo-10H NPU on pi-voice, HT801 ATA, isolated 10.10.10.0/24 segment.
- Telephone audio: 8kHz ulaw end-to-end; bandpass 300-3400Hz.
- LLM runs on pi-ollama CPU only (~4.5 tok/s class models).
- SD-card fragility history: anything irreplaceable must be committed/pushed or backed up off-Pi.

## Goal

All 44 directory numbers hardware-verified on the physical payphone with the full local pipeline (VAD → Hailo STT → Ollama LLM → Kokoro TTS) at conversational latency, surviving reboots unattended.

## Criteria

### Infrastructure (verified 2026-06-05)
- [x] ISC-1: Both Pis reachable via SSH (pi-voice 10.10.10.10, pi-ollama 10.10.10.11)
- [x] ISC-2: All services auto-start and survive cold boot (asterisk, payphone, wyoming-whisper, ollama)
- [x] ISC-3: NTP syncs after boot (verified post-boot 2026-06-05)
- [x] ISC-4: STT loopback sane post-restart (Kokoro→Wyoming→verbatim transcript)
- [ ] ISC-5: wyoming-whisper stale-decoder bug has an automated mitigation (self-test or restart hook), not a manual ritual
- [ ] ISC-6: Unattended 7-day uptime without SD corruption or watchdog reset

### Voice pipeline
- [x] ISC-7: End-to-end call flow works (handset → Asterisk → AudioSocket → pipeline → audio reply)
- [x] ISC-8: Hailo STT primary at 300-534ms; Moonshine CPU fallback auto-activates
- [x] ISC-9: Streaming LLM→TTS first-audio ~4-7s warm
- [x] ISC-10: Voice barge-in works (threshold 0.8 during TTS)
- [x] ISC-11: Hallucination filter catches known Whisper artifacts incl. truncated Hailo tokens
- [ ] ISC-12: Short-utterance accuracy acceptable ("yes"/"no" reliably transcribed)
- [ ] ISC-13: TTS-echo false-VAD root-caused (HT801 echo cancellation) not just filtered

### Directory & features (2/44 hardware-verified)
- [x] ISC-14: 44 numbers routed with prompts; area-code stripping; pound-confirm
- [x] ISC-15: Operator (0) hardware-verified multi-turn
- [x] ISC-16: Dial-A-Joke hardware-verified
- [x] ISC-17: Voice-initiated transfer ([TRANSFER:feature]) verified on a live call — deployed 2026-02-22, NEVER live-tested
- [ ] ISC-18: All 35 feature lines hardware-verified (batch through test plan Phase 3)
- [ ] ISC-19: All 9 personas hardware-verified
- [ ] ISC-20: All 6 easter eggs hardware-verified (incl. 555-MMDD birthday regex)
- [ ] ISC-21: DTMF navigation verified (single-digit shortcuts, star, pound, mid-call switching)
- [ ] ISC-22: SIT tri-tone + "not in service" on invalid numbers (verified through handset once; re-verify after changes)

### Game logic (currently prompt-only)
- [ ] ISC-23: Trivia keeps real score across turns
- [ ] ISC-24: Mad Libs collects words before reveal
- [ ] ISC-25: 20 Questions tracks question count and state

### Resilience
- [ ] ISC-26: Stress: rapid DTMF, hangup mid-state, network drop to pi-ollama — no hung sessions
- [ ] ISC-27: Endurance: 30-min call + overnight idle stability
- [ ] ISC-28: max_call_duration actually enforced
- [ ] ISC-29: Concurrent-call behavior defined and tested (VAD pool exhaustion path)
- [ ] ISC-30: Anti: no call ever reaches a cloud endpoint (network egress audit)
- [x] ISC-31: Anti: a Pi reboot never requires manual intervention to restore service (2026-06-06: 4 reboots across both Pis — kernel + EEPROM — all auto-recovered to full verified service)
- [ ] ISC-32: Antecedent: phone book artifact exists so guests can discover numbers (planning/phone-book-content.md)

### Phase A — latency (added 2026-06-05, branch `phase-a`)
- [x] ISC-37: Operator greeting served from persistent audio cache; first audio frame <1s after call start (synthetic probe)
- [x] ISC-38: Greeting cache keyed on text+voice+speed+model; config change = natural miss; miss falls back to live synth
- [x] ISC-39: Directory block removed from OPERATOR_PROMPT; prompt token count materially reduced (measure before/after)
- [x] ISC-40: Per-turn directory retrieval injects top-3 matches ephemerally (operator only); never accumulates in history
- [x] ISC-41: [TRANSFER:feature] voice-transfer still works with the slimmed prompt (live or synthetic verification)
- [ ] ISC-42: No hallucinated directory numbers with retrieval in place (B5-style check)
- [ ] ISC-43: LLM_RUNTIME setting gates ollama (default) vs llamacpp client; ollama path byte-identical behavior
- [ ] ISC-44: llama-server built + smoke-tested on pi-ollama (/v1/chat/completions returns valid stream)
- [x] ISC-45: phase-a deployed to pi-voice via git pull (never cat-pipe); main untouched until verified
- [x] ISC-46: Anti: phone never left in a broken state — known-good main restorable in one command
- [x] ISC-47: Full pytest suite green on phase-a (skips for hardware-gated tests acceptable)

### Hygiene
- [x] ISC-33: No secrets committed (audited 2026-06-05)
- [ ] ISC-34: Pi working tree clean against origin (PENDING — Feb-23 experiments: SmolLM3 + TEN-VAD + int8 Kokoro across 11 files, diff secured at tele-ai-backups/pi-experiments-20260605.diff; decide merge/branch/discard)
- [x] ISC-35: Deploy is git-pull based, not cat-pipe (repeatable deploys)
- [ ] ISC-36: Off-Pi backup automated (manual rescue 2026-06-05; FULL verified backup completed 2026-06-06 — 433M md5-verified via 32MB-chunk workaround; automation still open)

### STT quality (added 2026-06-05 from live-call A/B diagnosis)
- [ ] ISC-48: VAD pre-roll captures utterance starts (capture #2 began mid-sentence; tune speech_pad/pre-buffer)
- [ ] ISC-49: Telephone-audio transcription accuracy improved beyond whisper-base ceiling (both Hailo and CPU base garble equally at healthy RMS — model-class limit, candidates: whisper-small on Hailo, Moonshine telephone fine-tune per Feb research)

### Phase B — model bench (added 2026-06-08; gated by Gemma 4 research, PSU gate OPEN)
> Candidate: **Gemma 4 E2B QAT Q4_0** (NOT 12B = laptop model; NOT E4B = swap-bound 3–5 tok/s on Pi 5). Question the bench answers: does E2B beat qwen3:4b-instruct on the two axes that matter — long-prompt TTFT and tag/tool-call fidelity — without regressing. Research: `obsidian/Core/Research/2026-06-08 Gemma 4 12B and Quantization.md`.
- [ ] ISC-50: Official Gemma 4 E2B QAT Q4_0 GGUF (Google, shipped 2026-06-05) on pi-ollama; loads in llama-server/ollama; /v1/chat/completions returns valid stream
- [ ] ISC-51: Gemma 4 chat/turn template correct for the operator prompt (Gemma format, not Qwen) — verified BEFORE any quality comparison
- [ ] ISC-52: Baseline captured — qwen3:4b-instruct on pi-ollama: TTFT on the REAL ~2000-token operator prompt, decode tok/s, RAM use (3-run median)
- [ ] ISC-53: E2B measured on identical harness/prompt: TTFT, decode tok/s, RAM, swap watched (3-run median)
- [ ] ISC-54: [TRANSFER:feature] tag fidelity — ≥20 scripted turns that should emit a transfer tag; count malformed/missed per model
- [ ] ISC-55: Directory tool-call fidelity — ≥20 lookups; count hallucinated numbers / wrong routing per model (B5-style)
- [ ] ISC-56: Decision recorded WITH the numbers: E2B adopt / reject / escalate-to-E4B — gated on TTFT delta + zero tag-fidelity regression vs baseline
- [ ] ISC-57: Anti: bench runs in a throwaway model slot; qwen3:4b-instruct stays live default until a model is explicitly promoted — phone never points at an unvetted model mid-bench
- [ ] ISC-58: Anti: swap-thrash not masked — if E2B exceeds Pi RAM under real prompt+KV, recorded as a FAIL, not smoothed over

## Test Strategy

| area | check | tool |
|------|-------|------|
| infra | systemctl states post-boot, NTP, SSH | ssh + journalctl |
| model bench TTFT | qwen3:4b vs E2B: TTFT on real ~2000-tok operator prompt + decode tok/s, 3-run median | curl timing + /usr/bin/time on pi-ollama; llama-bench |
| model bench RAM | RSS + swap during real prompt+KV; fail if swap engaged | ssh free/vmstat during run |
| tag fidelity | ≥20 scripted [TRANSFER:]/directory turns, count malformed per model | pytest-style harness on pi-ollama |
| STT sanity | /tmp/stt_sanity.py loopback (Kokoro→Wyoming) | venv python — keep as scripts/stt-sanity.py |
| pipeline | live handset calls per 138-test plan in PROJECT_STATUS.md | human + journalctl -f |
| drift | md5/git status Pi vs origin | ssh + git |
| egress | tcpdump/nftables counters during calls | ssh (read-only) |

## Features

| name | satisfies | depends_on | parallelizable |
|------|-----------|------------|----------------|
| reconcile-feb-experiments | ISC-34 | live-verify-transfer | no |
| live-verify-transfer | ISC-17 | handset session | no (needs Tom) |
| stale-decoder-mitigation | ISC-5, ISC-31 | — | yes |
| hardware-test-campaign | ISC-18..22 | transfer verified | batched |
| game-logic | ISC-23..25 | — | yes |
| stress-endurance | ISC-26..29 | campaign | no |
| phone-book | ISC-32 | — | yes |
| phase-b-model-bench | ISC-50..58 | llama-server smoke (ISC-44), live-verify-transfer (ISC-17 ✓) | partly (download + baseline parallel; tag/RAM tests serial) |

## Decisions

- 2026-02-11: LLM = qwen3:4b-instruct over llama3.2:3b (MMLU 73 vs 63, better instruction-following; accepts ~4.5 tok/s).
- 2026-02-11: STT priority Hailo → Moonshine → faster-whisper (Hailo most accurate on 8kHz telephone audio).
- 2026-02-22: SD card replaced after two corruption events; full rebuild on fresh card.
- 2026-06-05: Restart review — backup-before-reconcile ordering adopted; critical archive + full diff secured off-Pi before any git operation.
- 2026-06-05: Feb-23 uncommitted experiment scope identified: SmolLM3-3B (LLM), TEN-VAD (replacing Silero, 281-line vad.py rework), int8 Kokoro. Disposition pending live-verify of current code.
- 2026-06-05 (RESOLVED to root-cause level): bulk-transfer stalls are NOT the Pis — both pi-voice and pi-ollama fail sustained TX at variable points (87-240MB); MTU clean (1500 DF passes); NIC counters clean. Path: Mac(192.168.1.111) -> opnsense(.254) -> 192.168.1.22 -> 10.10.10.0/24 = double routing hop. Suspect conn-track/flow-offload state handling on opnsense or the .22 device. Tom to investigate router config. Workaround stands: small/chunked transfers. Benchmarks unaffected (Pi-local).

- 2026-06-05: Edge-LLM research refreshed (June 2026, Extensive mode + intern evaluation + rubric verification) → `research/edge-llm-decision-2026-06.md`. Key reframe: TTFT/prefill of the 2,000-token operator prompt is the latency bottleneck, not decode tok/s. Decisions adopted as candidate work: Phase A (directory→tool-call, llama.cpp migration, canned instant greeting), Phase B (bench Qwen3-1.7B / Gemma3-1B; B6-gate the 30B MoE on measured TTFT), Phase C (Supertonic TTS bench, full STT offload). ISC-34 disposition informed: SmolLM3 confirmed dead-zone — do not resurrect branch wholesale. Hard no: Hailo LLM, CPU speculative decoding. PSU REPLACED 2026-06-05 (~15:06 — the 15:06 'reboot' was the swap itself, not a crash; 14:50 undervoltage on old PSU was real). Validated: 2h+ heavy load + all-core stress, throttled=0x0. Phase B gate OPEN.

- 2026-06-06: Test-readiness pass (task ISA 20260606-tele-ai-test-readiness, 34/34). Both Pis: full apt upgrade (231+109 pkgs), kernel 6.12.62→6.18.33, bootloader EEPROM Aug2025→May2026 flashed+verified, dkms installed + hailo1x_pci registered (kernel bumps now self-healing). feb23-experiments + scripts/stt-sanity.py (8a24623) pushed to origin. Post-everything: 216/216 pytest, STT fox verbatim on Hailo, SIP registered, cross-Pi API 200, throttled=0x0 both. Phone verified BETTER than starting state. Residual: full off-Pi backup still partial (6/5); ISC-36 open.

- 2026-06-06 (config audit, read-only): Asterisk verified correct — thin-funnel design ([payphone] in /etc/asterisk/extensions_custom.conf routes ALL patterns → AudioSocket :9092; pjsip ulaw; 30min app + 3h dialplan timeouts). Directory verified: 44 = 30 features + 5 easter-egg numbers + 9 personas; all resolve (FEATURE_PROMPTS=35 exact, PERSONA_PROMPTS covers all 9); birthday regex sane; 180 routing tests green. ⚠️ FOOTGUN FOUND: repo scripts/asterisk/*.conf are STALE pre-deploy iterations ([payphone-incoming]) — redeploying them would clobber the working live dialplan. Live /etc/asterisk captured complete to tele-ai-backups/etc-asterisk-full-20260606.tgz (109 files incl. modules.conf). Follow-up (post-first-smoke-dial, repo-only, no Pi deploy): commit live configs into repo + retire stale ones to archive/. Operational note for campaign: no dialplan fallback if payphone app dies (thin-funnel) — watch service liveness; HT801 is NonQual (no proactive drop detection).

- 2026-06-08: Phase B bench scoped from Gemma 4 research (Standard-mode, 2 passes, URL-verified; full note in obsidian Research). Candidate = **Gemma 4 E2B QAT Q4_0**, explicitly NOT the 12B (a 16GB-*laptop* model; on Pi 5 ~1.5–3 tok/s + 30–90s TTFT = breaks the voice loop) and NOT E4B (~5GB → swap-bound 3–5 tok/s on Pi 5). E2B measured 8–12 tok/s ≈ **2× qwen3:4b-instruct's ~4.5**, ~3.1GB Q4 footprint survives Pi RAM. Two UNMEASURED gates drive the bench: (a) ~2000-tok operator-prompt prefill/TTFT on Pi 5 — published nowhere; (b) [TRANSFER:] tag + directory tool-call fidelity for Gemma — unverified. Use official QAT Q4_0 (shipped 2026-06-05), not vanilla community Q4_K_M. **No published head-to-head vs qwen3:4b-instruct exists** (the web compares Qwen *3.5*) — self-bench is the only valid data, hence ISC-52/53 capture our own baseline. MatFormer escape hatch: E2B is a nested submodel of E4B, so escalating to E4B needs no re-architecture if tag fidelity fails. PSU gate is OPEN (replaced 2026-06-05), so Phase B is unblocked.

## Changelog

- conjectured: The cat-pipe deploy of 2026-02-22 left the Pi matching origin once commits were pushed.
- refuted_by: md5 cross-check 2026-06-05 — 6+ files differ from BOTH Pi HEAD and origin; an entire un-pushed experiment (SmolLM3/TEN-VAD/int8-Kokoro) existed only on the corruption-prone SD card.
- learned: Ad-hoc transfer deploys hide unpushed work; the Pi must be treated as a deploy target, never the only home of source.
- criterion_now: ISC-34 (tree clean vs origin) + ISC-35 (git-pull deploys) + ISC-36 (automated off-Pi backup).

- conjectured: apt full-upgrade would carry the Hailo PCIe driver forward across a kernel major bump (6.12→6.18).
- refuted_by: pre-reboot probe 2026-06-06 — /lib/modules/6.18.33*/ contained no hailo module; h10-hailort-pcie-driver compiles at install-time against the RUNNING kernel only, and dkms was not installed, so the upgrade silently staged a kernel that would boot without STT.
- learned: install-time-compiled vendor drivers are invisible to apt's dependency model; the module-for-target-kernel probe must run BEFORE reboot, and DKMS registration is the structural fix that makes the failure class impossible.
- criterion_now: ISC-31 strengthened and verified — dkms status must list hailo1x_pci for every installed kernel; 4 reboots (kernel + EEPROM × 2 Pis) auto-recovered with zero manual intervention.

## Verification

- 2026-06-05: Access — gh repo view; ssh both Pis (hostname/uptime/OS); services all active post-cold-boot; zero failed units.
- 2026-06-05: Rescue — critical archive md5-verified on Mac (f3a10a78…); 970-line experiment diff secured; full archive via resumable rsync (in progress).
- 2026-06-05: STT loopback — Kokoro "quick brown fox" → Hailo Whisper → verbatim transcript after service restart (ISC-4 evidence).
