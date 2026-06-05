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
- [ ] ISC-31: Anti: a Pi reboot never requires manual intervention to restore service
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
- [ ] ISC-36: Off-Pi backup automated (manual rescue taken 2026-06-05)

### STT quality (added 2026-06-05 from live-call A/B diagnosis)
- [ ] ISC-48: VAD pre-roll captures utterance starts (capture #2 began mid-sentence; tune speech_pad/pre-buffer)
- [ ] ISC-49: Telephone-audio transcription accuracy improved beyond whisper-base ceiling (both Hailo and CPU base garble equally at healthy RMS — model-class limit, candidates: whisper-small on Hailo, Moonshine telephone fine-tune per Feb research)

## Test Strategy

| area | check | tool |
|------|-------|------|
| infra | systemctl states post-boot, NTP, SSH | ssh + journalctl |
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

## Decisions

- 2026-02-11: LLM = qwen3:4b-instruct over llama3.2:3b (MMLU 73 vs 63, better instruction-following; accepts ~4.5 tok/s).
- 2026-02-11: STT priority Hailo → Moonshine → faster-whisper (Hailo most accurate on 8kHz telephone audio).
- 2026-02-22: SD card replaced after two corruption events; full rebuild on fresh card.
- 2026-06-05: Restart review — backup-before-reconcile ordering adopted; critical archive + full diff secured off-Pi before any git operation.
- 2026-06-05: Feb-23 uncommitted experiment scope identified: SmolLM3-3B (LLM), TEN-VAD (replacing Silero, 281-line vad.py rework), int8 Kokoro. Disposition pending live-verify of current code.
- 2026-06-05: GOTCHA — bulk transfers (scp/rsync >~100MB) to/from pi-voice stall and die; small files + SSH commands fine. Same symptom as 2026-02-22 ("SCP timing out"). Suspect NIC power-save or MTU on the 10.10.10.0/24 segment. Workaround: keep critical archives small; full archive persisted on-Pi at ~/tele-ai-rescue-20260605.tgz. Diagnose when resuming hardware work.

- 2026-06-05: Edge-LLM research refreshed (June 2026, Extensive mode + intern evaluation + rubric verification) → `research/edge-llm-decision-2026-06.md`. Key reframe: TTFT/prefill of the 2,000-token operator prompt is the latency bottleneck, not decode tok/s. Decisions adopted as candidate work: Phase A (directory→tool-call, llama.cpp migration, canned instant greeting), Phase B (bench Qwen3-1.7B / Gemma3-1B; B6-gate the 30B MoE on measured TTFT), Phase C (Supertonic TTS bench, full STT offload). ISC-34 disposition informed: SmolLM3 confirmed dead-zone — do not resurrect branch wholesale. Hard no: Hailo LLM, CPU speculative decoding. PSU REPLACED 2026-06-05 (~15:06 — the 15:06 'reboot' was the swap itself, not a crash; 14:50 undervoltage on old PSU was real). Validated: 2h+ heavy load + all-core stress, throttled=0x0. Phase B gate OPEN.

## Changelog

- conjectured: The cat-pipe deploy of 2026-02-22 left the Pi matching origin once commits were pushed.
- refuted_by: md5 cross-check 2026-06-05 — 6+ files differ from BOTH Pi HEAD and origin; an entire un-pushed experiment (SmolLM3/TEN-VAD/int8-Kokoro) existed only on the corruption-prone SD card.
- learned: Ad-hoc transfer deploys hide unpushed work; the Pi must be treated as a deploy target, never the only home of source.
- criterion_now: ISC-34 (tree clean vs origin) + ISC-35 (git-pull deploys) + ISC-36 (automated off-Pi backup).

## Verification

- 2026-06-05: Access — gh repo view; ssh both Pis (hostname/uptime/OS); services all active post-cold-boot; zero failed units.
- 2026-06-05: Rescue — critical archive md5-verified on Mac (f3a10a78…); 970-line experiment diff secured; full archive via resumable rsync (in progress).
- 2026-06-05: STT loopback — Kokoro "quick brown fox" → Hailo Whisper → verbatim transcript after service restart (ISC-4 evidence).
