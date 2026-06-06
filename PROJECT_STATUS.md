# Project Status — AI Payphone

**Last updated**: 2026-06-05

---

## Phase 0: MVP — COMPLETE

End-to-end voice pipeline verified on hardware.

| Item | Status | Notes |
|------|--------|-------|
| Call answer/hangup detection | Done | AudioSocket protocol, binary UUID handling |
| Greeting playback | Done | TTS greeting on call connect |
| DTMF digit detection | Done | RFC4733 via HT801, single-digit shortcuts + multi-digit dialing |
| Operator mode (STT → LLM → TTS) | Done | Full pipeline working end-to-end |
| Graceful hang-up with goodbye | Done | "Goodbye"/"bye" voice trigger + timeout auto-hangup |
| Streaming LLM → TTS | Done | First audio in ~4-7s (was ~5-10s sequential) |

---

## Phase 1: Core Experience — MOSTLY COMPLETE

| Item | Status | Notes |
|------|--------|-------|
| Main menu with DTMF navigation | Done | 10 single-digit shortcuts (0-9), star returns to menu |
| Multi-digit phone number dialing | Done | 44 numbers in directory, area code stripping, pound to confirm |
| Time & Temperature (767-2676) | Done | LLM-based (no real-time data), prompt implemented |
| Dial-A-Joke (555-5653) | Done | Prompt + feature module implemented |
| Weather Forecast (555-9328) | Done | LLM-based (no real-time data), prompt implemented |
| Return to menu with * key | Done | Works from any feature/persona |
| SIT tri-tone for invalid numbers | Done | Bellcore GR-506 compliant, plays before "not in service" TTS |
| Voice barge-in | Done | VAD threshold 0.8 during TTS, audio pre-buffered for STT |
| Silence timeout handling | Done | 10s prompt, 30s additional → auto-hangup |
| **External API integration** | **Not started** | Weather/news/sports are LLM-generated, not real data |

---

## Phase 2: Entertainment Expansion — COMPLETE (prompts only)

All features have system prompts and phone directory entries. They work via LLM prompt-switching — no custom feature logic beyond the prompt.

| Feature | Number | Prompt | Custom Logic | Hardware Tested |
|---------|--------|--------|--------------|-----------------|
| Trivia Challenge | 555-8748 | Done | No (LLM only) | No |
| Fortune Teller | 555-3678 | Done | No | No |
| Story Time | 555-7867 | Done | No | No |
| Moviefone | 777-3456 | Done | No | No |
| Horoscope | 555-4676 | Done | No | No |
| Mad Libs | 555-6235 | Done | No | No |
| Would You Rather | 555-9687 | Done | No | No |
| 20 Questions | 555-2090 | Done | No | No |

---

## Phase 3: Interactive Features — COMPLETE (prompts only)

| Feature | Number | Prompt | Custom Logic | Hardware Tested |
|---------|--------|--------|--------------|-----------------|
| Advice Line | 555-2384 | Done | No | No |
| Compliment Line | 555-2667 | Done | No | No |
| Roast Line | 555-7627 | Done | No | No |
| Life Coach | 555-5433 | Done | No | No |
| Confession Line | 555-2663 | Done | No | No |
| Vent Line | 555-8368 | Done | No | No |
| Debate Partner | 555-3322 | Done | No | No |
| Interview Mode | 555-4688 | Done | No | No |
| Collect Call Simulator | 555-2655 | Done | No | No |
| Nintendo Tip Line | 555-8477 | Done | No | No |
| Time Traveler | 555-8463 | Done | No | No |
| Calculator | 555-2252 | Done | No | No |
| Translator | 555-8726 | Done | No | No |
| Spelling Bee | 555-7735 | Done | No | No |
| Dictionary | 555-3428 | Done | No | No |
| Recipe Line | 555-7324 | Done | No | No |
| News Headlines | 555-6397 | Done | No | No |
| Sports Scores | 555-7767 | Done | No | No |

### Personas — COMPLETE (prompts only)

| Persona | Number | Prompt | Hardware Tested |
|---------|--------|--------|-----------------|
| Wise Sage | 555-7243 | Done | No |
| Comedian | 555-5264 | Done | No |
| Noir Detective | 555-3383 | Done | No |
| Southern Grandma | 555-4726 | Done | No |
| Robot from Future | 555-2687 | Done | No |
| Valley Girl | 555-8255 | Done | No |
| Beatnik Poet | 555-7638 | Done | No |
| Game Show Host | 555-4263 | Done | No |
| Conspiracy Theorist | 555-9427 | Done | No |

### Easter Eggs — COMPLETE (prompts only)

| Easter Egg | Number | Prompt | Hardware Tested |
|------------|--------|--------|-----------------|
| Jenny (867-5309) | 867-5309 | Done | No |
| Phone Phreaker | 555-2600 | Done | No |
| Hacker Mode | 555-1337 | Done | No |
| Joe's Pizza | 555-7492 | Done | No |
| Haunted Booth | 555-1313 | Done | No |
| Birthday (regex) | 555-MMDD | Done | No |

---

## Phase 4: Polish & Easter Eggs — NOT STARTED

| Item | Status | Notes |
|------|--------|-------|
| Secret codes / Konami code | Not started | Planned: hidden dial codes unlock content |
| Achievements system | Not started | Track caller milestones, verbal badges |
| Holiday modes | Not started | Seasonal content (Halloween, Christmas, etc.) |
| Daily special | Not started | Rotate featured service each day |
| Late night mode | Not started | Different tone after midnight |
| Hold music (Muzak) | Not started | Royalty-free 80s/90s style hold music |
| Vintage recordings | Not started | Hidden codes play actual vintage phone recordings |
| Full sound design | Partial | 17 Bellcore sounds generated; only SIT tri-tone wired in |

---

## Infrastructure — COMPLETE

| Component | Status | Details |
|-----------|--------|---------|
| Pi #1 (pi-voice) | Running | Asterisk 22.8.2, Hailo Whisper STT, Kokoro TTS, Silero VAD |
| Pi #2 (pi-ollama) | Running | Ollama 0.16.3, qwen3:4b-instruct (~4.5 tok/s, MMLU 73.0) |
| HT801 ATA | Configured | PJSIP endpoint, ulaw, RFC4733 DTMF |
| Network (10.10.10.0/24) | Working | 5-port gigabit switch |
| AudioSocket protocol | Working | Binary UUID, end-to-end audio |
| systemd services | Running | `payphone` + `wyoming-whisper` on Pi #1, `ollama` on Pi #2 |
| Persistent journal | Active | `/etc/systemd/journald.conf.d/99-persistent.conf` overrides RPi volatile default; captures boot logs for crash diagnosis |
| Hailo-10H NPU | **Active** | Whisper-Base encoder+decoder running on NPU via Wyoming protocol |

---

## Voice Pipeline — COMPLETE

| Component | Status | Performance |
|-----------|--------|-------------|
| VAD (Silero v5) | Working | Model pool (3), barge-in threshold 0.8 |
| STT (Whisper-Base, Hailo) | **Primary** | ~300-534ms on NPU (encoder ~80ms, decoder ~230-440ms), most accurate on telephone audio |
| STT (Moonshine Tiny) | **Fallback** | Installed on Pi #1, auto-activates when Wyoming unavailable (e.g., after reboot) |
| LLM (qwen3:4b-instruct) | Working | ~4.5 tok/s, MMLU 73.0, streaming with per-token timeout |
| TTS (Kokoro-82M) | Working | af_bella voice, 24kHz → 8kHz resampled |
| Streaming LLM → TTS | Working | SentenceBuffer chunks tokens, producer-consumer TTS |
| Greeting audio cache (Phase A3) | **Working (2026-06-05)** | Persistent PCM cache keyed sha256(text+voice+speed+model); operator greeting primed at init. Measured: first audio +0.0s after call start (was +12s) |
| Directory retrieval (Phase A1) | **Working (2026-06-05)** | 44-number directory removed from operator prompt (~2,000 prefill tokens); stdlib fuzzy lookup injects top-3 matches per turn, ephemeral (never accumulates). App warm-up 2-3min → ~5s |
| Telephone bandpass filter | Working | 300-3400 Hz applied to all output audio |
| Prompt warm-up | Working | Operator system prompt cached in Ollama KV at init |
| Whisper hallucination filter | Working | 20 known patterns filtered; prefix-matching for truncated Hailo tokens (e.g. `[BLANK_AUDIO` without `]`) |
| Voice-initiated feature transfer | **Hardware-verified 2026-06-05** | Live call: garbled STT, operator inferred intent, emitted `[TRANSFER:jokes]`, switched feature, caller heard the joke |

---

## Hardware Test Plan Progress (138 tests)

| Phase | Tests | Tested | Notes |
|-------|-------|--------|-------|
| 1. Infrastructure | 8 | ~8 | All services verified during bring-up |
| 2. Basic Call Flow | 7 | ~5 | Greeting, speech, multi-turn, hangup tested |
| 3. Phone Directory (44 numbers) | 51 | ~2 | Operator and Jokes tested on hardware |
| 4. DTMF Navigation | 9 | ~1 | Star key tested |
| 5. Voice Pipeline Quality | 10 | ~4 | Latency, barge-in, streaming tested |
| 6. Timeout Behavior | 7 | ~2 | Silence timeout tested |
| 7. Stress Testing | 36 | 0 | Not started |
| 8. Sound Effects | 5 | ~1 | SIT tri-tone verified through handset |
| 9. Endurance | 5 | 0 | Not started |
| **Total** | **138** | **~23** | **~17% complete** |

---

## What's Left to Do

### High Priority (functional gaps)

0. **Finish Phase A2 (llama.cpp runtime)** — llama-server built + Qwen3-4B GGUF staged on pi-ollama; remaining: smoke test, env-gated client adapter in `services/llm.py` (LLM_RUNTIME setting), B2 benchmark vs Ollama. Then Phase B model bench per `research/edge-llm-decision-2026-06.md` (Qwen3-1.7B / Gemma3-1B; B6-gate the 30B MoE on measured TTFT).
0b. **VAD pre-roll + STT ceiling** (ISA ISC-48/49) — the "operator couldn't hear me" pair.
1. **Hardware test all 44 phone numbers** — Only operator and jokes have been tested on the actual payphone. All prompts exist but need hardware verification (Phase 3 of test plan).
2. **DTMF navigation testing** — Single-digit shortcuts, star key, pound confirm, feature switching during calls (Phase 4).
3. **Stress testing** — Rapid input, network failures, hangup during various states, concurrent calls (Phase 7).
4. **Endurance testing** — 30-min calls, repeated calls, overnight stability (Phase 9).

### Medium Priority (quality improvements)

5. **Custom feature logic** — All 35 features currently use LLM prompt-switching only. Features like Trivia (scoring), Mad Libs (word collection), and 20 Questions (state tracking) would benefit from dedicated game logic in `features/`.
6. **Wire remaining sound effects** — 17 Bellcore sounds are generated but only `sit_intercept.wav` is used. Could add: dial tone simulation, busy signal, ring tone, coin deposit sounds.
7. **Real-time data integration** — Weather, news, sports, time/temperature are all LLM-generated fiction. Could integrate APIs for actual data.
8. **STT accuracy tuning** — Whisper-Base on Hailo is working but may benefit from prompt tuning, language forcing, or audio preprocessing for telephone-quality audio.

### Lower Priority (polish)

9. **Phone book design** — Physical phone book with white/yellow/blue pages and fake classified ads (detailed design exists in `planning/phone-book-content.md`).
10. **Achievements system** — Track caller milestones, progressive unlocks.
11. **Holiday modes** — Seasonal content variations.
12. **Hold music** — Muzak-style audio during processing waits.
13. **Secret codes** — Hidden dial sequences for easter egg content.
14. **Late night mode** — Different persona/tone after midnight.
15. **Vintage audio processing** — Presence EQ boost, soft saturation, mu-law artifacts for more authentic telephone sound.

### Known Bugs / Limitations

| Issue | Severity | Notes |
|-------|----------|-------|
| Navigation false positives | Low | "menu", "go back", "goodbye" substring matching triggers unintended navigation |
| No concurrent call limit | Low | Memory-bounded only; 4th+ call blocks waiting for VAD model |
| Birthday dates not validated | Low | 555-0230 (Feb 30) accepted as valid birthday |
| max_call_duration not enforced | Low | State machine checks it but was marked as "not enforced" in test plan |
| Extension not passed from Asterisk | Info | AudioSocket sends binary UUID only; all calls show `extension: None` |
| Hailo decoder max 64 tokens | Info | HEF fixed at 64-token sequence; adequate for phone utterances. Can truncate hallucination tokens (e.g. `[BLANK_AUDIO` without `]`); handled by prefix-matching filter. |
| Hailo Whisper decoder stale after reboot | Medium | After pi-voice reboots, Wyoming Whisper decoder can produce 1-token garbage (`-`, `and`). Restarting `wyoming-whisper.service` fixes it. (The companion app-hang was the busy-loop bug, FIXED 2026-06-05.) Automate via self-test/restart hook — ISA ISC-5. |
| TTS echo triggers false VAD | Low | 20ms audio captures immediately after TTS playback (acoustic echo through phone line). Hallucination filter catches the noise but root cause is HT801 ATA echo cancellation settings. |
| Short utterance STT accuracy | Medium | Whisper mishears short words like "yes" → garbled output. May need minimum audio duration threshold or VAD sensitivity tuning. |
| SD card filesystem corruption (round 2) | **RESOLVED 2026-06-05** | Root cause was never the cards: PSU undervoltage under load (kernel: `Undervoltage detected!` 2026-06-05 14:50 under 100%-CPU). Official Pi 5 27W PSU installed 2026-06-05; validated under all-core load (`throttled=0x0`). |
| Busy-loop on remote hangup (call goes deaf) | **FIXED 2026-06-05** | After hangup/TCP-close, conversation loop re-entered LISTENING in a zero-await spin (100% CPU, event loop starved, all later calls unserviced). Fix: honor `protocol.is_active` in loop + state machine (`6d3944e`). Verified: 3 sequential calls on one process. |
| VAD start-clipping | Medium | Live captures show utterance fronts cut (capture began mid-sentence). Tune speech_pad / pre-roll buffer — ISA ISC-48. |
| Whisper-base accuracy ceiling on telephone audio | Medium | A/B 2026-06-05: Hailo AND CPU whisper-base both garble healthy-level 8kHz captures equally — model-class limit, not hardware. Candidates: whisper-small on Hailo, Moonshine telephone fine-tune — ISA ISC-49. |
| Sustained LAN transfers >~80MB stall | Low (infra) | NOT the Pis: both fail sustained TX at variable points; MTU clean. Path Mac→opnsense→192.168.1.22→10.10.10.0/24 (double routed hop) — suspect conn-track/flow-offload on a router. Workaround: chunked transfers. |

---

## Session Log

### 2026-06-05: Restart, Rescue, Phase A, Live Transfer Verification (full-day session)

**The restart session.** Project dormant since 2026-02-23; both Pis powered on fresh.

1. **Access + review** — repo cloned to `~/Documents/project/tele-ai`, both Pis verified, all services survived cold boot. Project ISA seeded (`ISA.md`, now system of record; this file remains the session journal).
2. **Rescue** — Feb-23 uncommitted experiments (SmolLM3 + TEN-VAD + int8-Kokoro, 11 files / 970 lines) found ONLY on pi-voice's SD card; checksummed archive + full diff secured off-Pi; preserved on branch `feb23-experiments`. Working tree reconciled to origin/main.
3. **Live-call debugging** — "dialed 0, nothing happened" traced through three layers: (a) experimental code never sent greeting audio; (b) busy-loop on remote hangup spun the event loop at 100% CPU making the phone deaf to later calls (the February ghost — root-caused and FIXED, `6d3944e`); (c) PSU undervoltage under load (kernel evidence) = the real cause of February's "failing SD cards" — **official 27W PSU installed and validated same day**.
4. **June research refresh** (`research/edge-llm-decision-2026-06.md`) — key reframe: TTFT/prefill of the 2,000-token operator prompt dominated perceived latency, not decode tok/s. Feb's SmolLM3 bet obsolete (dead-zone decode). Hailo-10H confirmed NOT viable for LLM (measured ≈ CPU). CPU speculative decoding: skip.
5. **Phase A shipped to main** (branch `phase-a`, fast-forwarded):
   - A3 greeting cache: first audio **+0.0s** after call start (was +12s)
   - A1 directory out of prompt: app warm-up **~5s** (was 2-3 min); RAG-lite per-turn lookup, ephemeral injection; TRANSFER instructions preserved
   - Busy-loop fix verified: 3 sequential calls serviced by one process
   - DEBUG_SAVE_CAPTURES diagnostic (per-utterance STT input WAVs; note systemd PrivateTmp puts them in the service namespace)
   - Test suite: **216/216 green** (first all-green; 3 stale Feb assertions fixed)
6. **🏆 Voice transfer LIVE-VERIFIED** — the Feb-22 feature worked on a real call: garbled transcripts ("and number for the job"), operator inferred intent, `[TRANSFER:jokes]` fired, caller got the joke.
7. **STT A/B diagnosis** — captures healthy (RMS 0.06, full length) but Hailo AND CPU whisper-base garble equally → model-class ceiling (ISC-49); VAD clips utterance fronts (ISC-48).
8. **Infra** — Ollama upgraded 0.16.3 → 0.30.5 (phone path verified); llama.cpp + llama-bench built on pi-ollama, Qwen3-4B GGUF staged; LAN bulk-transfer stalls localized to the inter-VLAN routing path (opnsense → 192.168.1.22), not the Pis.

**Key discoveries:**
- systemd PrivateTmp=true hides service /tmp writes from login shells (`/tmp/systemd-private-*-payphone.service-*/tmp/`).
- HF `resolve/main` URLs 401 on nonexistent repos; official Qwen GGUF repo absent — use `unsloth/Qwen3-4B-Instruct-2507-GGUF`.
- Deploys are git-pull only now (cat-pipe deploys stranded the Feb experiments).

**Current state:** Phone on main = best version ever. Next: A2 smoke + adapter, ISC-48/49, Phase B bench (PSU gate now open).

---

### 2026-02-22 (Evening): Voice Transfer + Hallucination Filter Fixes

**What was accomplished:**

1. **Fixed Whisper hallucination filter for truncated Hailo tokens** — Hailo's 64-token decoder limit truncates `[BLANK_AUDIO]` to `[BLANK_AUDIO` (no closing bracket), bypassing the exact-match frozenset filter. Split filter into `_HALLUCINATION_EXACT` (text patterns, frozenset) and `_HALLUCINATION_PREFIXES` (bracket patterns, `startswith()` tuple). Also added `[Inaudible` patterns seen in call logs. Committed as `3350caf`.

2. **Implemented voice-initiated feature transfer** — The operator could tell callers about services but had no mechanism to actually *connect* them. When the caller says "yes" to being connected:
   - Operator LLM now emits `[TRANSFER:feature_name]` signal (added transfer instructions + valid feature list to operator prompt)
   - State machine `_check_transfer_signal()` parses the signal with regex, validates against known features
   - `_voice_transfer()` switches the feature, clears conversation history, plays the target greeting
   - Streaming token filter in `pipeline.py` suppresses `[TRANSFER:]` from TTS output
   - Files changed: `config/prompts.py`, `core/state_machine.py`, `core/pipeline.py`, `services/stt.py`

3. **Deployed to Pi #1** — All files transferred via `cat | ssh` (SCP was timing out after reboot). Service restarted and running.

**Known issue from testing:** After first operator response, subsequent speech wasn't captured (process at 72% CPU with no log output). Occurred once after a Pi reboot — likely related to the known "Hailo Whisper decoder stale after reboot" bug. Service restart resolved it. Voice transfer feature not yet verified with a successful end-to-end call.

**Current state:** Voice transfer code deployed but needs live verification. Hallucination filter improved. All services running.

---

### 2026-02-22: Full Software Rebuild (SD Card Replacement)

**What was accomplished:**

1. **Replaced Pi #1 SD card and rebuilt from scratch** — Previous 512GB SD card had recurring filesystem corruption (2026-02-11, 2026-02-19). Fresh Debian Trixie install on new card.

2. **Full software stack installed on Pi #1:**
   - System packages: `apt upgrade`, build-essential, Python 3.13.5, git, ffmpeg, libsndfile1, etc.
   - `hailo-h10-all` 5.1.1 (464 packages): Hailo-10H NPU drivers, firmware, runtime
   - PCIe Gen 3 configured in `/boot/firmware/config.txt`
   - Python venv with PyTorch, faster-whisper, kokoro-onnx, ollama, pydantic-settings
   - `transformers` 5.2.0 + `sentencepiece` + `safetensors` for Moonshine STT
   - Kokoro TTS models: `kokoro-v1.0.onnx` (311MB) + `voices-v1.0.bin` (27MB)
   - Asterisk 22.8.2 built from source (not in Debian Trixie arm64 repos)
   - PJSIP + AudioSocket dialplan configured
   - Persistent journaling (`99-persistent.conf`, 100M cap)

3. **Hailo-10H NPU activated and Wyoming Whisper deployed:**
   - `hailo-apps` installed from GitHub (provides `hailo-download-resources`)
   - `Whisper-Base.hef` (137MB) downloaded via `hailo-download-resources --group whisper_chat --arch hailo10h`
   - NPY embedding files downloaded via `download_hailo_models.py --variant base`
   - `hailo_platform` symlinked into venv
   - `wyoming-whisper.service` installed and running on port 10300
   - Encoder + decoder running on NPU (fw 5.1.1)

4. **Moonshine STT installed as CPU fallback:**
   - `moonshine-onnx` unavailable on arm64 — using HuggingFace transformers v1 path
   - `UsefulSensors/moonshine-tiny` model auto-downloads from HuggingFace on first load
   - Payphone app auto-selects Moonshine when Wyoming is unavailable

5. **Pi #2 (pi-ollama) verified intact:**
   - Ollama 0.16.3 running on `0.0.0.0:11434`
   - `qwen3:4b-instruct` model cached and responsive
   - Cross-Pi connectivity confirmed from Pi #1

6. **All services verified running post-reboot:**
   - `wyoming-whisper` (active, :10300)
   - `payphone` (active, :9092, STT: Hailo Wyoming primary)
   - `asterisk` (active, PJSIP endpoints configured)
   - `/dev/hailo0` present (after `apt reinstall h10-hailort-pcie-driver` for new kernel)

**Key discoveries:**
- `hailo-apps-infra` pip package does NOT exist on arm64. Use `hailo-apps` GitHub repo with `./install.sh` instead.
- `wyoming-hailo-whisper` apt package does NOT exist. The Wyoming server is `services/wyoming_whisper_server.py` in the payphone-app repo.
- `moonshine-onnx` pip package not available on arm64. Moonshine works via `transformers` (v1 path).
- After kernel upgrade, Hailo driver must be rebuilt: `sudo apt reinstall h10-hailort-pcie-driver && sudo depmod -a && sudo modprobe hailo1x_pci`
- Kokoro downloads with `wget -q` produce 0-byte files (GitHub redirect issue). Use `wget -v`.

**Current state:** Full voice pipeline operational. Hailo Whisper-Base is primary STT (NPU-accelerated). Moonshine tiny is CPU fallback. All systemd services enabled and running. HT801 ATA not yet configured (next step).

---

### 2026-02-19: SD Card Corruption Recurrence

**What happened:**

1. **SD card corrupt again on pi-voice** — Second corruption event in 8 days (previous: 2026-02-11). The recurrence strongly suggests the 512GB SD card is failing rather than a one-time corruption event.

**Next steps when resuming:**
- Consider replacing the 512GB SD card entirely with a fresh card
- Image the current card (if readable) to preserve the configured system
- Alternative: try `fsck.mode=force` again, but if it recurs a third time, the card is definitely bad
- Check `smartctl` or `mmc` health data if available on Pi
- Consider moving to USB SSD boot for better reliability

---

### 2026-02-11: SD Card Filesystem Repair + Persistent Journal

**What was accomplished:**

1. **Diagnosed SD card filesystem corruption as reboot cause** — Pi #1's 512GB SD card had significant EXT4 corruption: corrupt inode bitmap (block_group 80), cross-linked inodes (a `.pyc` file linked to a systemd private directory), deleted inode references, block/inode count mismatches. The BCM2835 hardware watchdog (1-min timeout) was resetting the Pi when the kernel hung on corrupt blocks.

2. **Repaired filesystem with forced fsck** — Added `fsck.mode=force` to `/boot/firmware/cmdline.txt` (alongside existing `fsck.repair=yes`). The initramfs ran `fsck -y` during boot and fixed the major corruption. A second pass cleaned up remaining block/inode count bookkeeping errors. Filesystem state went from `clean with errors` → `clean`. Removed `fsck.mode=force` after repair.

3. **Fixed persistent journaling** — Previous attempt failed because RPi OS ships a drop-in config `/usr/lib/systemd/journald.conf.d/40-rpi-volatile-storage.conf` that sets `Storage=volatile`, overriding our `Storage=persistent` in the main `journald.conf`. Created `/etc/systemd/journald.conf.d/99-persistent.conf` with `[Journal]\nStorage=persistent` to override the RPi default. After `journalctl --flush`, both `system.journal` and `user-1000.journal` are now persisted in `/var/log/journal/<machine-id>/`.

**Key discovery:** On Raspberry Pi OS, persistent journal requires a drop-in in `/etc/systemd/journald.conf.d/` — editing `/etc/systemd/journald.conf` alone is insufficient because the RPi-specific `40-rpi-volatile-storage.conf` drop-in takes precedence.

**Current state:** Filesystem clean, persistent journal active. Pi was stable for 2.5 hours after fsck repair (no reboots, 0 ext4 errors, load 0.00). Both Pis cleanly shut down at end of session. If Pi reboots unexpectedly in future, previous boot logs will be available via `journalctl -b -1`.

---

### 2026-02-11: Moonshine STT Installed + STT Priority Flip

**What was accomplished:**

1. **Installed Moonshine Tiny on Pi #1** — `transformers` and `torch` were already installed; downloaded and verified the `UsefulSensors/moonshine-tiny` model. Provides automatic CPU-based STT fallback when Wyoming/Hailo is unavailable.

2. **Discovered Moonshine accuracy issue on telephone audio** — Moonshine Tiny mistranscribed "give me the number for jokes" as "One of her jokes." (confidence 0.90). Hailo Whisper-Base produces accurate transcriptions on 8kHz telephone audio.

3. **Flipped STT backend priority** — Changed auto-detection order from Moonshine → Hailo → faster-whisper to **Hailo → Moonshine → faster-whisper**. Hailo Whisper-Base is now primary (most accurate on telephone audio), Moonshine serves as automatic CPU fallback when Wyoming is down (e.g., after reboots).

4. **Removed llama3.2:3b from Pi #2** — Freed ~2GB disk space. Only qwen3:4b-instruct remains on Ollama.

5. **Enabled persistent journaling on Pi #1** — Created `/var/log/journal` so boot logs survive reboots, enabling investigation of the reboot issue.

6. **Investigated Pi reboot issue** — Pi #1 keeps rebooting. No undervoltage (`throttled=0x0`), no thermal issues (36.7°C), no kernel panics, no failed services. Previous boot logs were unavailable (no persistent journal before this session). Persistent journal now enabled for next reboot.

**Current state:** Hailo Whisper primary STT, Moonshine Tiny installed as fallback. Pi rebooting intermittently — cause still unknown, persistent journal now enabled to capture it.

---

### 2026-02-11: LLM Switch to qwen3:4b-instruct + Whisper Hallucination Filter

**What was accomplished:**

1. **Switched LLM from llama3.2:3b to qwen3:4b-instruct** — Researched small LLM candidates (phi4-mini, gemma3, qwen3 variants, SmolLM3, etc.) for Pi 5 CPU-only. The `-instruct` variant of qwen3:4b has no thinking mode (unlike the default `qwen3:4b` which was previously rejected). Benchmarked side-by-side on Pi #2: ~4.5 tok/s generation (vs ~5.9 for llama3.2:3b), but MMLU 73.0 vs 63.4 and better instruction following (shorter responses, accurate directory lookups).

2. **Added Whisper hallucination filter** — Whisper-Base outputs hallucination tokens like `[BLANK_AUDIO]`, `Thank you.`, and `you` on silence or noise. These were passing through as real user messages, causing the LLM to respond with repeated greetings. Added a frozenset of 16 known hallucination patterns to `TranscriptionResult.is_empty` in `stt.py`.

3. **Tightened operator phone directory prompt** — LLM was hallucinating phone numbers for services that don't exist (e.g. "555-3678" for a non-existent job line). Added explicit instructions: "NEVER invent or guess phone numbers" and "suggest the closest match from this list". Verified: now correctly says "Sorry, we don't have that service" for unknown requests and gives accurate numbers from the directory.

4. **Added audio duration logging** — `pipeline.py` now logs captured speech duration and sample count at INFO level before sending to STT, plus logs discarded hallucination transcriptions. Helps diagnose STT accuracy issues.

**Key discovery:** The `.env` file on pi-voice overrides `settings.py` defaults via Pydantic Settings. Changing the default in `settings.py` alone is not sufficient — must also update `LLM_MODEL` in `.env`.

**Current state:** System running with qwen3:4b-instruct. End-to-end verified: asked for non-existent service (correctly refused), asked for joke line number (correctly gave 555-5653). Hallucination filter catching `[BLANK_AUDIO]` on silence between utterances.

**Next session priorities:**
- Fine-tune operator and feature prompts for qwen3:4b-instruct response style
- Hardware test more phone numbers
- DTMF navigation testing
- Wire more sound effects

---

### 2026-02-10: Initial Hardware Bring-Up + Hailo STT Deployment

**What was accomplished:**

1. **End-to-end voice pipeline verified** — Payphone → HT801 → Asterisk → AudioSocket → VAD → STT → LLM → TTS → audio response all working through the physical payphone handset.

2. **Hailo-10H NPU activated for Whisper STT** — Wrote a custom Wyoming protocol server (`wyoming_whisper_server.py`) that runs Whisper-Base inference on the Hailo-10H NPU. Encoder runs entirely on NPU (~80ms), decoder runs on NPU with CPU-side token embedding lookup (~230-440ms). Total STT latency 300-534ms for typical phone utterances.

3. **Key technical discoveries:**
   - Multi-NG HEFs require `create_infer_model(hef_path, name=ng_name)` — the lower-level `VDevice.configure()` returns `HAILO_NOT_IMPLEMENTED`
   - The `onnx_add_input_base.npy` file (24x512) is NOT positional embeddings — positional embeddings are baked into the HEF. Adding this file to token embeddings corrupts the decoder, causing immediate EOT with 0 tokens transcribed
   - Wyoming server uses one-shot connections (closes after each transcription) — client must reconnect per request
   - `hailo_platform` system package must be symlinked into the venv: `ln -s /usr/lib/python3/dist-packages/hailo_platform .venv/lib/python3.13/site-packages/`

4. **Streaming LLM→TTS pipeline tested** — First audio response in ~4-7s with Ollama KV cache warm, vs ~5-10s without streaming.

5. **Phone number readback fixed** — LLM now says each digit individually ("five five five, five six five three") instead of grouping ("five hundred fifty-five").

6. **8 bugs fixed** across three hardware test sessions (see CLAUDE.md for full tables).

**Current state:** System is fully operational with Hailo-accelerated STT. Operator (dial 0) and Jokes tested on hardware. All 44 phone numbers have prompts but only 2 have been hardware tested.

**Next session priorities:**
- Hardware test more phone numbers (especially features with complex interactions like Trivia, Mad Libs, 20 Questions)
- DTMF navigation testing (shortcuts, star key, feature switching mid-call)
- Wire more sound effects (dial tone, busy signal, ring tone, coin deposit)
- Consider custom game logic for interactive features (scoring, state tracking)
