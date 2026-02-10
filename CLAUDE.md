# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**payphone-ai** is an AI-powered payphone project. The goal is a self-contained 90s-style payphone running a fully local AI that users can interact with for information, jokes, and services styled after 1990s telephone services.

**Repository**: https://github.com/CarbonRaven/payphone-ai

### Target Hardware
- **Pi #1 (pi-voice)**: Raspberry Pi 5 (16GB) + AI HAT+ 2 (Hailo-10H)
- **Pi #2 (pi-ollama)**: Raspberry Pi 5 (16GB) - standard, no HAT
- Grandstream HT801 v2 (ATA for payphone interface)
- 5-port gigabit switch
- Physical payphone

### Dual-Pi Architecture
```
Payphone → HT801 ATA (SIP) → Asterisk 22.8.2
                                     │
                                AudioSocket :9092
                                     │
┌────────────────────────────────────┼────────────────────────────────────┐
│ Pi #1 (pi-voice) 10.10.10.10      │         + AI HAT+ 2               │
│                                    ▼                                    │
│              Silero VAD → Whisper (STT) ──────────→ Kokoro (TTS)       │
│               (CPU)       :10300 (Hailo)               (CPU)           │
│                                │                         ▲              │
│                                ▼                         │              │
└────────────────────────────────┼─────────────────────────┼──────────────┘
                                 │ HTTP                     │
                                 ▼                          │
┌────────────────────────────────────────────────────────────┼─────────────┐
│ Pi #2 (pi-ollama) 10.10.10.11                             │             │
│                     Ollama (LLM) ─────────────────────────┘             │
│                       :11434 / llama3.2:3b                               │
└─────────────────────────────────────────────────────────────────────────┘
```

**AI HAT+ 2 Usage**: The Hailo-10H NPU accelerates Whisper STT on Pi #1, freeing the CPU for audio processing. Standard Ollama runs on Pi #2 for better model flexibility (3B+ models).

**Important**: The AI HAT+ 2 requires the `hailo-h10-all` package (not `hailo-all` which is for Hailo-8). The correct package installs the `hailo1x_pci` driver, Hailo-10H firmware, and `h10-hailort` runtime. The Pi's `/boot/firmware/config.txt` must include `dtparam=pciex1` and `dtparam=pciex1_gen=3` under `[all]`.

## Repository Structure

- `payphone-app/` - Main Python application (see Code Architecture below)
- `documentation/` - Technical documentation (26 files)
  - `project-overview.md` - Architecture and service catalog
  - `local-voice-assistant-pipeline.md` - End-to-end voice pipeline guide
  - `raspberry-pi-5-ai-hat-2-*.md` - Hailo AI HAT+ 2 documentation
  - `raspberry-pi-5-openwakeword.md` - Wake word detection
  - `freepbx-*.md` - FreePBX/Asterisk telephony integration
  - `network-configuration.md` - Dual-Pi network setup
  - `*-research*.md` - LLM, STT, and model research
- `planning/` - Design and feature planning
  - `system-architecture.md` - System design document
  - `features-list.md` - Full feature roadmap with phone numbers
  - `phone-book-content.md` - Physical phone book content draft
- `scripts/` - Operational tooling
  - `asterisk/` - Asterisk/FreePBX configuration
  - `health-monitor.py` - System health monitoring
  - `payphone-ops.sh` - Operations management script
- `research/` - Reference materials and model research
- `hardware.txt` - Hardware inventory

## Key Technologies

| Component | Technology | Location | Notes |
|-----------|------------|----------|-------|
| Wake Word | openWakeWord | Pi #1 | Wyoming protocol, port 10400 |
| STT | Whisper-Base (Hailo) | Pi #1 | Hailo-10H NPU via Wyoming protocol, Moonshine fallback |
| LLM | Ollama | Pi #2 | Standard Ollama, llama3.2:3b, port 11434 |
| TTS | Kokoro-82M | Pi #1 | Fast neural TTS, 24kHz output |
| VAD | Silero VAD | Pi #1 | CPU-based, model pool (3) for concurrent calls |
| Telephony | Asterisk 22.8.2 | Pi #1 | Built from source, AudioSocket protocol |
| Protocol | Wyoming | Pi #1 | Home Assistant voice service integration |

## Code Architecture

### Voice Pipeline (`payphone-app/`)

```
main.py                    # Application entry point, service initialization
pyproject.toml             # Package config, dependencies, optional extras
install.sh                 # Automated installer
tts_server.py              # Standalone TTS server (for Pi #2 offloading)
├── config/
│   ├── settings.py        # Pydantic Settings v2 with env var support
│   ├── phone_directory.py # 44 phone numbers → features/personas (TypedDict entries)
│   └── prompts.py         # LLM system prompts (35 features, 9 personas, conditional directory)
├── core/
│   ├── audiosocket.py     # Asterisk AudioSocket protocol handler
│   ├── audio_processor.py # Sample rate conversion, telephone filter
│   ├── phone_router.py    # Number dialed → feature routing, DTMF shortcuts
│   ├── pipeline.py        # VAD → STT → LLM → TTS orchestration (streaming + sequential)
│   ├── session.py         # Per-call state (VAD model, barge-in audio buffer)
│   └── state_machine.py   # Conversation flow control
├── services/
│   ├── vad.py             # Silero VAD v5 with model pool + voice barge-in
│   ├── stt.py             # Moonshine (5x faster) + Wyoming/Hailo + faster-whisper
│   ├── wyoming_whisper_server.py  # Standalone Wyoming STT server for Hailo-10H NPU
│   ├── llm.py             # Ollama client with streaming timeout
│   └── tts.py             # Kokoro-82M synthesis
├── features/
│   ├── base.py            # Feature base classes
│   ├── registry.py        # Auto-discovery decorator pattern
│   ├── operator.py        # Default operator persona
│   └── jokes.py           # Dial-A-Joke feature
├── tests/
│   └── test_phone_routing.py  # Phone directory and routing tests
├── scripts/
│   ├── generate_audio.py  # Generates 17 telephone sound effects (Bellcore GR-506)
│   └── download_hailo_models.py  # Downloads Hailo Whisper HEF + NPY model files
├── models/                # Hailo Whisper model files (HEF + NPY, not committed)
└── audio/                 # Audio assets (music/, prompts/, sounds/)
    └── sounds/            # 17 generated WAV files (8kHz 16-bit PCM mono)
```

### Key Patterns

| Pattern | Location | Purpose |
|---------|----------|---------|
| Pydantic Settings | `config/settings.py` | Type-safe config with env var support |
| Phone Directory | `config/phone_directory.py` | 44-number TypedDict registry with greetings |
| Phone Router | `core/phone_router.py` | Number lookup, DTMF shortcuts, birthday regex |
| Feature Registry | `features/registry.py` | `@FeatureRegistry.register()` decorator |
| Wyoming Protocol | `services/stt.py` | Binary framing for audio, JSON for events |
| Sentence Buffer | `services/llm.py` | Regex-based streaming TTS chunking |
| Audio Buffer | `core/audio_processor.py` | Memory-bounded sample accumulation |
| VAD Model Pool | `services/vad.py` | `VADModelPool` gives each session an exclusive `VADModel` — no lock contention |
| Voice Barge-In | `core/pipeline.py` | `_monitor_barge_in()` runs VAD on incoming audio during TTS playback (both `speak()` and `speak_streaming()`) |
| Streaming LLM→TTS | `core/pipeline.py` | `generate_and_speak_streaming()` overlaps token generation with TTS synthesis via producer-consumer pattern |
| Conditional Prompts | `config/prompts.py` | `PHONE_DIRECTORY_BLOCK` only included for operator feature (~100 token savings) |
| SIT Tri-tone | `core/state_machine.py` | Plays `sit_intercept.wav` before "not in service" TTS |

### Performance Optimizations

- **Streaming LLM→TTS pipeline**: `generate_and_speak_streaming()` overlaps LLM token generation with TTS synthesis — first sentence plays while LLM is still generating, reducing perceived latency from ~5-10s to ~2-3s. Toggle via `LLM_STREAMING_ENABLED` env var with sequential fallback.
- **Conditional prompt inclusion**: Phone directory block (~100 tokens) only included for operator feature, not for jokes/trivia/personas — reduces LLM prompt processing time
- **Wyoming binary protocol**: Audio sent as binary frames (not base64) for 33% less overhead
- **Exponential backoff**: Wyoming reconnection with 0.5s → 4s backoff
- **VAD model pool**: 3 pre-loaded models via `asyncio.Queue` — each session gets exclusive access, no lock on hot path
- **Voice barge-in**: Detects speech during TTS playback (threshold 0.8), buffers triggering audio for seamless handoff to STT. Works in both `speak()` and `speak_streaming()` paths.
- **Thread-safe VAD**: Legacy `reset_async()` acquires lock for single-model path (backwards compat)
- **Per-token streaming timeout**: Each `__anext__()` wrapped in `asyncio.wait_for()` with `first_token_timeout` (25s) and `inter_token_timeout` (5s) — the `async for` pattern blocks indefinitely so manual iteration is required
- **Dynamic pacing**: Audio playback paced by actual chunk duration
- **Mid-sentence interrupt**: `_send_sentence()` passes `should_stop` callback to `send_audio()` for immediate barge-in response during streaming playback
- **O(n) string building**: LLM streaming uses list + join instead of O(n²) concatenation
- **Incremental sentence detection**: Regex searches only new content, not entire buffer
- **Pre-allocated audio arrays**: Streaming STT uses doubling strategy for O(n) total copies
- **Batched Wyoming writes**: Audio chunks written without drain, single flush at end
- **Lazy dtype conversion**: TTS/resampling skip copy when dtype already matches
- **Ollama prompt warm-up**: `initialize()` chats with the operator system prompt so Ollama's KV cache is hot for the first real call (~20s → ~1s prompt eval)
- **Moonshine min audio guard**: Audio <100ms (1600 samples) returns empty result instead of crashing `conv1d` kernel

## Build & Test

```bash
cd payphone-app
pip install -e ".[dev]"       # Install with dev dependencies
pytest tests/                 # Run tests
python3 -c "import ast; ast.parse(open('config/prompts.py').read())"  # Quick syntax check
python3 scripts/generate_audio.py   # Regenerate telephone sound effects
```

The app requires Python 3.10+ and uses `pydantic-settings` for configuration via environment variables (see `config/settings.py` and `.env.example`).

## Audio Assets

`payphone-app/audio/sounds/` contains 17 programmatically generated telephone sound effects based on Bellcore GR-506 specs. All files are 8kHz 16-bit PCM WAV mono, matching the pipeline's `output_sample_rate`.

To regenerate: `cd payphone-app && python3 scripts/generate_audio.py`

The `play_sound()` method in `core/pipeline.py` loads these files, resamples if needed, applies the telephone bandpass filter (300-3400 Hz), and sends via AudioSocket. Currently the SIT intercept tri-tone (`sit_intercept.wav`) is wired into both invalid-number paths in `state_machine.py`.

## Hardware Testing

`payphone-app/HARDWARE_TEST_PLAN.md` contains a 138-test plan across 9 phases for validating the system on hardware, including stress tests and adversarial scenarios to break features. See that file for the full plan and results template.

### First Hardware Test Results (2026-02-10)

End-to-end pipeline verified: Payphone → HT801 → Asterisk → AudioSocket → VAD → Moonshine STT → Ollama LLM → Kokoro TTS → audio response. Issues discovered and fixed during hardware bring-up:

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| Asterisk rejected AudioSocket calls | `app_audiosocket.c` requires strict UUID format | Generate UUIDs via `/proc/sys/kernel/random/uuid` in dialplan |
| `UnicodeDecodeError` on connect | Asterisk sends UUID as 16 raw bytes (binary), not 36-char ASCII | `uuid.UUID(bytes=payload)` in `audiosocket.py` |
| Silero VAD `ValueError: chunk too short` | AudioSocket 20ms frames = 320 samples at 16kHz, Silero needs exactly 512 | Accumulator buffer in `VADModel` feeds exact 512-sample windows |
| Moonshine STT `AttributeError` | Moonshine preprocessor returns `input_values`, not `input_features` (Whisper-style) | Fixed key in `stt.py` |
| `.env` settings ignored | Pydantic sub-settings classes didn't load `.env` file | Added `env_file=".env"` + `extra="ignore"` to all `SettingsConfigDict` |
| LLM timeout / empty responses | qwen3:4b spends all tokens on thinking mode, ~3.3 tok/s on Pi CPU | Switched to llama3.2:3b (~6 tok/s, no thinking mode) |
| LLM doesn't know phone directory | No directory data in system prompt | Added 15 key numbers as `PHONE_DIRECTORY_BLOCK` (included for operator only) |
| HT801 config not saving | "Account Active" must be enabled first | Documented gotcha in SETUP.md |

### Second Hardware Test Results (2026-02-10)

Streaming LLM→TTS pipeline tested end-to-end. Issues discovered and fixed:

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| Streaming timeout never fires | `async for part in stream:` blocks indefinitely on `__anext__()` — timeout check inside loop body never reached before first token | Manual `asyncio.wait_for(stream_iter.__anext__(), timeout=...)` iteration |
| First call always times out (~25s) | Ollama cold-start prompt eval for 223-token system prompt takes ~20s on Pi 5 CPU | Warm up with operator system prompt during `initialize()` so Ollama KV cache is hot |
| Moonshine STT crash on short audio | `conv1d` kernel_size=7 > padded input size when audio < ~100ms | Minimum audio length guard (1600 samples / 100ms) returns empty result |
| TTS reads `*chuckles*` literally | LLM outputs asterisk actions that TTS speaks as words | Added prompt rule: "Never use asterisk actions" |
| Phone numbers spoken as "five hundred fifty-five" | LLM says numbers naturally instead of digit-by-digit | Added prompt rule: "Say phone numbers one digit at a time" |

### Third Hardware Test Results (2026-02-10)

Hailo-10H NPU Whisper STT deployed and tested end-to-end. Issues discovered and fixed:

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| `Input base-whisper-encoder-10s/input_layer1 not found!` | `create_infer_model` defaulted to decoder (first NG alphabetically) | Use `name=ng_name` parameter to select specific network group |
| `HAILO_NOT_IMPLEMENTED` from `VDevice.configure(hef)` | Multi-NG HEFs not supported via lower-level configure API | Use `create_infer_model(hef_path, name=ng_name)` InferModel API instead |
| Wyoming `Broken pipe` / `Connection lost` | Client held persistent connection from startup; server closes after each transcription | Per-transcription reconnect in `stt.py`: `disconnect()` then `connect()` each time |
| Decoder returns 0 tokens (immediate EOT) for real speech | `onnx_add_input_base.npy` (24x512) is NOT positional embeddings — adding it corrupted decoder input. HEF has positional embeddings baked in | Removed positional embedding addition; pass only token embeddings to decoder |

### Ollama Prompt Caching

Ollama caches the KV state of prompt prefixes. The first call with a new system prompt pays full prompt eval cost (~20s for 223 tokens on Pi 5 CPU). Subsequent calls with the same system prompt prefix complete prompt eval in ~1s. The `initialize()` warm-up now runs a chat with the operator system prompt to pre-populate this cache, so the first real call benefits from cached eval.

### Hailo Whisper Wyoming Server

`services/wyoming_whisper_server.py` is a standalone async TCP server that speaks the Wyoming protocol for Hailo-accelerated Whisper STT. It runs as a separate systemd service (`wyoming-whisper.service`) on Pi #1.

**Architecture** (hybrid inference — encoder on NPU, decoder on NPU + CPU):
```
Audio (16kHz PCM) → Mel Spectrogram (CPU) → Encoder (Hailo NPU) → Decoder (Hailo NPU + CPU embed) → Text
```

- Encoder runs entirely on Hailo-10H NPU (10-second input chunks)
- Decoder runs on NPU with CPU-side token embedding lookup (large vocab table cannot be compiled into HEF)
- Mel spectrogram computed with pure numpy (no torch dependency)
- Inference serialized via asyncio.Lock for NPU access

**Model files**:
- `Whisper-Base.hef` — single HEF with encoder + decoder network groups (131 MB, from `hailo-apps`)
  - Located at `/usr/local/hailo/resources/models/hailo10h/Whisper-Base.hef`
  - Encoder: `base-whisper-encoder-10s` (1,1000,80) → (1,500,512)
  - Decoder: `base-whisper-decoder-10s-out-seq-64` (1,500,512)+(1,64,512) → 4 split outputs → (1,64,51865)
- `token_embedding_weight_base.npy` — CPU-side vocab embeddings (51865, 512), in `models/`
- `onnx_add_input_base.npy` — externalized ONNX constant (24, 512), in `models/` — **NOT used at runtime** (see note below)

**HailoRT API pattern**: Multi-NG HEFs require `create_infer_model(hef_path, name=ng_name)` to select individual network groups. `VDevice.configure(hef)` returns `HAILO_NOT_IMPLEMENTED`.

**Deployment** (already done on Pi #1):
```bash
# Download NPY embeddings
python scripts/download_hailo_models.py --variant base
# HEF obtained via hailo-apps: hailo-download-resources --arch hailo10h
sudo cp wyoming-whisper.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now wyoming-whisper
# Symlink hailo_platform into venv:
ln -s /usr/lib/python3/dist-packages/hailo_platform .venv/lib/python3.13/site-packages/
```

**Important: positional embeddings are baked into the HEF**. The `onnx_add_input_base.npy` file is an externalized ONNX constant that is NOT positional embeddings (shape 24x512 doesn't match any Whisper dimension). Adding it to token embeddings corrupts the decoder input, causing immediate EOT with 0 tokens. Only `token_embedding_weight_base.npy` is needed at runtime for CPU-side vocab lookup.

**Wyoming client connection model**: The server closes the TCP connection after each transcription response (one-shot per connection). The client in `stt.py` reconnects fresh for each `transcribe()` call — do not hold a persistent connection.

**Performance** (measured on Pi 5 + Hailo-10H with real speech):
- Encoder: ~73-95ms on NPU
- Decoder: ~228-439ms on NPU (varies with token count, up to 64 steps)
- Total for 5-token utterance: ~534ms
- Total for 2-token utterance: ~301ms

The app auto-detects the Wyoming server at localhost:10300 when `STT_BACKEND=auto` or `STT_BACKEND=hailo`.

### Known Limitations

- **Whisper-Base only**: Only Whisper-Base HEF is available from `hailo-apps` for Hailo-10H. Tiny model would require DFC compilation.
- **Max 64 tokens per transcription**: Decoder sequence length is fixed at 64 in the HEF. Adequate for phone utterances.

## Infrastructure Status

Both Pis run Debian Trixie (13.3) aarch64 with kernel 6.12.62+rpt-rpi-2712.

### Pi #1 (pi-voice) — 10.10.10.10

| Service | Version | Status | Notes |
|---------|---------|--------|-------|
| Hailo-10H NPU | FW 5.1.1, driver `hailo1x_pci` | `/dev/hailo0` active | `hailo-h10-all` package, Whisper-Base HEF running |
| Wyoming Whisper | Whisper-Base via Hailo-10H | Running (systemd) :10300 | Encoder 69ms, decoder 213ms on NPU |
| Asterisk | 22.8.2 | Running (systemd) | Built from source, PJSIP + AudioSocket configured |
| AudioSocket | `res_audiosocket.so` + `app_` + `chan_` | 3 modules loaded | Working end-to-end with voice pipeline |
| Payphone App | Python 3.13 | Running (systemd) | VAD pool (3), Hailo Whisper STT via Wyoming, Kokoro TTS |
| HT801 ATA | v2, 10.10.10.12 | Registered (NonQual) | PJSIP endpoint, ulaw, RFC4733 DTMF |

### Pi #2 (pi-ollama) — 10.10.10.11

| Service | Version | Status | Notes |
|---------|---------|--------|-------|
| Ollama | 0.15.5 | Running on `0.0.0.0:11434` | CPU-only mode, systemd override for network binding |
| Model | llama3.2:3b (2.0GB) | Active, ~6 tok/s | Replaced qwen3:4b (thinking mode unusable) |

### Model Selection Notes

- **qwen3:4b**: Not suitable — mandatory thinking mode consumes all tokens before generating a response. At ~3.3 tok/s on Pi 5 CPU, it cannot produce useful output within phone-appropriate timeouts.
- **llama3.2:3b**: Current choice — no thinking mode, ~6 tok/s, natural stop tokens, good conversational quality. With streaming LLM→TTS, first audio in ~4-7s (cached prompt) vs ~5-10s sequential.

### Asterisk Source Build

The `asterisk` package is not available in Debian Trixie arm64 repos. Built from source:
```bash
cd /usr/src/asterisk-22.8.2
sudo ./configure --with-jansson-bundled
sudo make -j4
sudo make install && sudo make samples && sudo make config
```

## Documentation Standards

All documentation uses Markdown with:
- Tables for specifications and comparisons
- Code blocks with language hints for commands/configs
- Consistent heading hierarchy
- Links between related documents via relative paths
