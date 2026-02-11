# Project Status — AI Payphone

**Last updated**: 2026-02-11

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
| Pi #2 (pi-ollama) | Running | Ollama 0.15.5, qwen3:4b-instruct (~4.5 tok/s, MMLU 73.0) |
| HT801 ATA | Configured | PJSIP endpoint, ulaw, RFC4733 DTMF |
| Network (10.10.10.0/24) | Working | 5-port gigabit switch |
| AudioSocket protocol | Working | Binary UUID, end-to-end audio |
| systemd services | Running | `payphone` + `wyoming-whisper` on Pi #1, `ollama` on Pi #2 |
| Hailo-10H NPU | **Active** | Whisper-Base encoder+decoder running on NPU via Wyoming protocol |

---

## Voice Pipeline — COMPLETE

| Component | Status | Performance |
|-----------|--------|-------------|
| VAD (Silero v5) | Working | Model pool (3), barge-in threshold 0.8 |
| STT (Whisper-Base, Hailo) | **Working** | ~300-534ms on NPU (encoder ~80ms, decoder ~230-440ms) |
| STT (Moonshine tiny) | Fallback | Available if Hailo unavailable (`STT_BACKEND=moonshine`) |
| LLM (qwen3:4b-instruct) | Working | ~4.5 tok/s, MMLU 73.0, streaming with per-token timeout |
| TTS (Kokoro-82M) | Working | af_bella voice, 24kHz → 8kHz resampled |
| Streaming LLM → TTS | Working | SentenceBuffer chunks tokens, producer-consumer TTS |
| Telephone bandpass filter | Working | 300-3400 Hz applied to all output audio |
| Prompt warm-up | Working | Operator system prompt cached in Ollama KV at init |
| Whisper hallucination filter | Working | 16 known patterns filtered (e.g. `[BLANK_AUDIO]`, `Thank you.`) |

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
| Hailo decoder max 64 tokens | Info | HEF fixed at 64-token sequence; adequate for phone utterances |

---

## Session Log

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
