# AI Payphone Project - Plan Improvements

**Research Date:** January 21, 2026
**Based on:** Codex deep research analysis of technical architecture, features/UX, similar projects, and audio authenticity

---

## Table of Contents

1. [Technical Architecture Improvements](#technical-architecture-improvements)
2. [Voice Pipeline Optimizations](#voice-pipeline-optimizations)
3. [Hardware Alternatives](#hardware-alternatives)
4. [Features & UX Improvements](#features--ux-improvements)
5. [Similar Projects & Inspiration](#similar-projects--inspiration)
6. [Audio Authenticity Techniques](#audio-authenticity-techniques)
7. [Implementation Priorities](#implementation-priorities)

---

## Technical Architecture Improvements

### Current Target vs Achievable Performance

| Metric | Current Target | Achievable (Optimized) | Notes |
|--------|---------------|------------------------|-------|
| End-to-end latency | <2.5s | **1.5-2.0s** | With optimizations below |
| STT latency | ~500ms | **150-300ms** | faster-whisper + distil-whisper |
| LLM TTFT | ~800ms | **200-400ms** | Qwen2.5-3B GPTQ |
| TTS latency | ~400ms | **<300ms** | Kokoro-82M replaces Piper |

### Critical Architecture Changes

#### 1. STT: Replace Whisper with faster-whisper + distil-whisper

**Current:** Standard Whisper
**Recommended:** faster-whisper + distil-whisper-large-v3

**Benefits:**
- **4-6x speedup** over baseline Whisper
- Same accuracy, less memory
- 8-bit quantization available for further speedup
- distil-whisper: 49% smaller (756M vs 1.55B params), within 1% WER

**Implementation:**
```bash
pip install faster-whisper
# Use distil-whisper models with faster-whisper backend
```

#### 2. TTS: Replace Piper with Kokoro-82M

**Current:** Piper TTS (VITS + ONNX)
**Recommended:** Kokoro-82M

**Why Kokoro:**
- **Sub-300ms latency consistently** (vs Piper's ~400ms)
- Only 82M parameters (~150-200MB model)
- Built on StyleTTS2 + ISTFTNet (no encoders/diffusion)
- Apache 2.0 license
- CPU-friendly, runs on embedded devices

**Trade-offs:**
- No voice cloning (not needed for payphone)
- Audio quality slightly less natural than XTTS

#### 3. LLM: Optimize Model Selection

**Primary Recommendation:** Qwen2.5-3B-Instruct (GPTQ 4-bit)

| Model | Size | Latency | Best For |
|-------|------|---------|----------|
| **Qwen2.5-3B-Instruct** | 1.93GB (4-bit) | Fast | Best overall conversational |
| SmolLM3-3B-Instruct | ~6GB | Moderate | Best reasoning, 64K context |
| Llama-3.2-3B-Instruct | ~6GB | Moderate | Best ecosystem support |
| TinyLlama 1.1B | 2.2GB | Fastest | Ultra-low resource fallback |

**Fallback Strategy:** Start with Qwen2.5-3B, fall back to TinyLlama if latency exceeds target.

#### 4. Add Voice Activity Detection (VAD)

**Recommended:** Silero VAD

- 1.8MB model size
- **Processes 30ms chunks in ~1ms**
- Trained on 6,000+ languages
- 95% accuracy in noisy environments
- MIT License (free commercial use)

**Benefits:**
- Better turn detection (knows when user finished speaking)
- Reduces unnecessary processing
- Optimizes resource usage
- Enables natural turn-taking

#### 5. Streaming Architecture

**Key Techniques:**
1. **Chunked Audio Processing:** 100-200ms frames for smooth streaming
2. **Progressive Streaming:** STT → partial transcripts → LLM → streaming tokens → TTS
3. **Chunked Playback Masking:** User hears audio after ~600ms (TTFT + TTS startup)
4. **Latency reduction:** 800-1500ms vs batch processing

**Expected First Audio:** 550-1000ms (optimistic) to 1.5-2.0s (realistic)

---

## Hardware Alternatives

### Current Setup Analysis

**Raspberry Pi 5 (16GB) + AI HAT+ 2 (Hailo-10H)**

| Component | Spec | Issue |
|-----------|------|-------|
| Hailo-10H NPU | 40 TOPS (INT4) | **Underperforms for LLMs** |
| HAT RAM | 8GB LPDDR4X | Limits model sizes |
| Cold Start | 25-40 seconds | Delay when accelerator reloads |
| Total Cost | ~$210 | ($80 RPi5 + $130 HAT) |

**Critical Finding:** Research shows the Pi's CPU actually outperforms the Hailo-10H for LLM inference. The HAT is better for computer vision (YOLOv8) than conversational AI.

### Recommended Alternative: NVIDIA Jetson Orin Nano Super

| Spec | Value |
|------|-------|
| AI Performance | **67 TOPS** |
| GPU | 1,024 CUDA cores + 32 Tensor Cores |
| RAM | 8GB LPDDR5 |
| Power | 7-15W (configurable) |
| Cost | **$249** |

**Advantages:**
- Superior LLM inference performance
- Better software ecosystem (NVIDIA Riva, TensorRT)
- Optimized for real-time voice AI
- Better thermal management

### Budget Alternative: Orange Pi 5 Plus (RK3588)

| Spec | Value |
|------|-------|
| NPU | 6 TOPS |
| CPU | Octa-core (4x A76 + 4x A55) |
| RAM | Up to 32GB |
| Power | 5-6W |
| Cost | **$180** |

**Performance:**
- TinyLlama 1.1B: 10-15 tokens/second
- 5X NPU speedup vs ARM CPU
- Best price-to-performance ratio

### Hardware Decision Matrix

| Platform | AI Perf | LLM Perf | Power | Cost | Recommendation |
|----------|---------|----------|-------|------|----------------|
| RPi5 + Hailo-10H | 40 TOPS | Poor | 5-6W | $210 | Good for CV, poor for LLM |
| **Jetson Orin Nano** | 67 TOPS | Excellent | 7-15W | $249 | **Best for voice AI** |
| Orange Pi 5+ | 6 TOPS | Good | 5-6W | $180 | **Best price/performance** |

**Recommendation:**
- **Production quality:** Jetson Orin Nano Super ($249)
- **Budget-conscious:** Orange Pi 5 Plus ($180)
- **Keep current:** RPi5 + Hailo works but use CPU for LLM, not NPU

---

## Voice Pipeline Optimizations

### Optimized Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    OPTIMIZED VOICE PIPELINE                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Payphone → ATA → Asterisk → AudioSocket                    │
│                       ↓                                     │
│              ┌───────────────┐                              │
│              │  Silero VAD   │ ← NEW: Turn detection        │
│              │   (~1ms)      │                              │
│              └───────────────┘                              │
│                       ↓                                     │
│              ┌───────────────┐                              │
│              │ faster-whisper│ ← UPGRADED: 4-6x faster      │
│              │ + distil-v3   │   150-300ms                  │
│              └───────────────┘                              │
│                       ↓ (streaming partial transcripts)     │
│              ┌───────────────┐                              │
│              │ Qwen2.5-3B    │ ← UPGRADED: Best edge LLM    │
│              │ GPTQ 4-bit    │   200-400ms TTFT             │
│              └───────────────┘                              │
│                       ↓ (streaming tokens)                  │
│              ┌───────────────┐                              │
│              │  Kokoro-82M   │ ← UPGRADED: Sub-300ms        │
│              │               │   replaces Piper             │
│              └───────────────┘                              │
│                       ↓                                     │
│              AudioSocket → Asterisk → ATA → Payphone        │
│                                                             │
│  TOTAL LATENCY: 1.5-2.0s (down from 2.5s target)           │
└─────────────────────────────────────────────────────────────┘
```

### Audio Quality Consideration: 8kHz vs 16kHz

**Current Limitation:** Grandstream HT801 uses G.711 codec (8kHz sampling)

**Impact:**
- Degrades STT accuracy
- Reduces TTS naturalness
- Consonants/fricatives most affected (3-8kHz range)

**Solutions:**
1. **Accept 8kHz** - Still viable, matches vintage authenticity
2. **Upgrade ATA** - Wideband-capable ATA with G.722 (16kHz)
3. **WebRTC Bridge** - Analog → ATA → SIP → WebRTC gateway

**Recommendation:** Accept 8kHz limitation - it actually enhances vintage telephone authenticity!

### Telephony: Keep Asterisk + AudioSocket

**Verdict:** For a single payphone, Asterisk's simplicity outweighs FreeSWITCH's features.

**If scaling to 5+ phones:** Consider FreeSWITCH for:
- Native WebRTC support
- Multi-threaded performance
- Better scripting flexibility

---

## Features & UX Improvements

### Missing 1980s-90s Services to Add

Based on research into historical telephone services:

#### Premium Rate Services (1-900 Numbers)

| Service Type | Implementation Ideas |
|--------------|---------------------|
| **Sports Phone** | Real-time scores, replays of historic games |
| **Joke Lines** | Daily joke, comedy segments |
| **Horoscope Lines** | Daily horoscope readings |
| **Soap Opera Updates** | Dramatic story updates |
| **Santa/Holiday Lines** | Seasonal character interactions |

#### Party Lines / Chat Services

- **Teen Party Line** - Multi-caller social simulation
- **Dating Hotline** - "Quest" style interaction
- **Confession Line** - Anonymous message recording

#### Information Services

| Service | Historical Accuracy |
|---------|---------------------|
| **Time & Temperature** | Jane Barbe voice style |
| **Directory Assistance** | "What city please?" flow |
| **Dial-A-Poem** | Poetry reading service |
| **Dial-A-Prayer** | Religious message service |
| **Consumer Hotlines** | Product info, recalls |

### Gamification Strategies

Based on voice-first UX research:

#### Achievement System
- **First Call** - Complete your first interaction
- **Time Traveler** - Use services from 5 different eras
- **Collector** - Unlock all operator personas
- **Power User** - Make 100 calls
- **Night Owl** - Call after midnight

#### Progressive Unlocks
1. **Phase 0:** Basic services (time, weather, operator)
2. **Phase 1:** Entertainment unlocks after 10 calls
3. **Phase 2:** Easter eggs unlock after 50 calls
4. **Phase 3:** Secret numbers revealed gradually

#### Easter Egg Discovery
- Dial specific numbers to unlock hidden content
- "Wrong numbers" that lead to surprises
- Holiday-specific content (Santa line at Christmas)
- Movie/TV reference numbers from our research

### Voice UI Best Practices

Based on modern conversational AI research:

#### Error Recovery
- **Graceful fallback:** "I didn't catch that. You can say..."
- **Progressive disclosure:** Start simple, offer more options
- **Escape hatch:** "Press 0 for operator" always works

#### Turn-Taking
- Use Silero VAD for natural conversation flow
- Implement barge-in (interrupt long responses)
- Add "listening" audio cues (subtle tone/click)

#### Menu Navigation
- Maximum 3-4 options per menu
- Always provide "repeat" and "go back" options
- Use consistent structure across services

### Accessibility Considerations

- Voice-only interface is inherently accessible
- Slower speech rate option for elderly users
- Repeat/slow-down commands
- Clear pronunciation of numbers and addresses

---

## Similar Projects & Inspiration

### Payphone Art Installations

| Project | Creator | Description | Tech |
|---------|---------|-------------|------|
| **Futel** | Portland, OR | Free public payphones, anti-surveillance | Raspberry Pi, VoIP |
| **Good Phone Project** | Rochester, NY | Free VoIP payphones for underserved communities | Solar-powered, RPi |
| **Montana Phone Booth Project** | Jim Dolan | Mental health awareness booths | Symbolic (non-functional) |
| **Wind Phone** | Japan | Grief processing phone (not connected) | Purely symbolic |
| **Goodbye Line** | Various | Leave goodbye messages for loved ones | RPi, recording |
| **970-HA-JOKES** | SparkFun | Fully functional VoIP payphone with Easter eggs | Arduino, VoIP module |
| **AlexaPhone** | Martin Manders | 1970s Trimphone with Alexa | Raspberry Pi, AlexaPi |
| **PHONEBOOTH** | Sara Keen | Satirical corporate phone tree installation | RPi, AI-generated ads |

### Key Takeaways

1. **Futel's philosophy:** Free, anti-surveillance, community-focused
2. **Good Phone Project:** 650 calls/month at single location, 20% to social services
3. **SparkFun project:** Easter eggs via specific number sequences - great model for gamification
4. **PHONEBOOTH:** Satirical AI-generated content shows creative possibilities

### Technical Approaches from Similar Projects

| Project | Audio Handling | Unique Feature |
|---------|---------------|----------------|
| **PiPhone Kit** | VoIP over WiFi | Modular design for replication |
| **Rotary Radio** | RPi + Arduino hybrid | Each processor for different tasks |
| **ArduPhony** | GSM cellular module | Mobile network via vintage handset |
| **Ocean Listening Booth** | HTML5 streaming | Underwater microphone feeds |

---

## Audio Authenticity Techniques

### Telephone Audio Simulation

#### The PSTN Sound (300-3400 Hz)

**Technical Specifications:**
- Highpass filter: 300 Hz
- Lowpass filter: 3,400 Hz (effective 4,000 Hz Nyquist at 8kHz sampling)
- Presence peak: 2,000-3,000 Hz boost (3-8 dB, Q: 1.5-3.0)

**Processing Chain:**
1. **Bandpass filter** - 300-3400 Hz restriction
2. **Presence EQ** - 2-3kHz boost for "telephone clarity"
3. **Dynamic compression** - 4:1 to 8:1 ratio, fast attack
4. **μ-law encoding** - Logarithmic compression (optional, for extreme authenticity)
5. **Soft saturation** - Subtle harmonic distortion

#### Implementation Options

**Simple (Plugin-based):**
```
EQ: Highpass 300Hz → Lowpass 3400Hz → Peak 2.5kHz +6dB Q:2.0
Compressor: 4:1 ratio, 10ms attack, 100ms release
Saturation: Light drive (2-4 dB)
```

**Advanced (Convolution):**
- Capture impulse response from actual payphone handset
- Apply via convolution reverb for complete acoustic character
- Includes microphone and speaker characteristics

### Text-to-Speech Voice Quality

#### Historical TTS Systems

| Era | Technology | Character |
|-----|-----------|-----------|
| **1970s-80s** | Votrax, DECtalk | Robotic, distinctive |
| **1980s-90s** | Concatenative TTS | Chunky, recognizable joins |
| **Jane Barbe era** | Human recordings with splicing | Smooth but detectable edits |
| **Moviefone** | Human voice (Russ Leatherman) | Natural but processed |

#### Creating Vintage TTS Sound

1. **Use Kokoro-82M** for speed, then process
2. **Apply telephone filter chain** (above)
3. **Add subtle artifacts:**
   - Gentle sample rate reduction
   - Micro-pauses between phrases
   - Slight pitch inconsistencies

### Authentic Sound Effect Sources

#### Recommended Archives (from audio-sources-archive.md)

| Resource | Content |
|----------|---------|
| **Telephone World** | Premier source for all telephone sounds |
| **ElmerCat.org** | Jane Barbe collection, vintage sounds |
| **Evan Doorbell** | 95+ narrated phone trips (1970s-80s) |
| **PhreakNet** | Phone phreak history, operator recordings |
| **Internet Archive** | Evan Doorbell tapes, vintage commercials |

#### Essential Sounds to Include

- Dial tone (350 + 440 Hz)
- Busy signal (480 + 620 Hz, 0.5s on/off)
- Ring tone (440 + 480 Hz, 2s on/4s off)
- DTMF tones (authentic frequencies)
- Coin deposit sounds
- Operator interjections
- "Please deposit 25 cents" recordings
- Hold music (Muzak style)

### Muzak / Hold Music

**Sources:**
- Internet Archive muzak collections
- Retrowave/synthwave for 80s vibe
- Jazz/easy listening for 90s feel

**Processing:** Apply telephone filter chain to all hold music for consistency.

---

## Implementation Priorities

### Phase 1: Voice Pipeline Optimization (Highest Impact)

1. **Replace STT:** Install faster-whisper + distil-whisper
2. **Add VAD:** Implement Silero VAD for turn detection
3. **Test latency:** Benchmark current vs optimized pipeline
4. **Iterate:** Fine-tune chunk sizes and streaming

**Expected Result:** 30-50% latency reduction

### Phase 2: TTS Upgrade

1. **Install Kokoro-82M:** Replace Piper
2. **Apply audio filters:** Telephone simulation chain
3. **Test voices:** Ensure consistent quality
4. **Create presets:** Different personas (operator, time lady, etc.)

**Expected Result:** 100-200ms TTS improvement

### Phase 3: LLM Optimization

1. **Deploy Qwen2.5-3B:** GPTQ 4-bit quantized
2. **Enable streaming:** Token-by-token output
3. **Optimize prompts:** Persona-specific system prompts
4. **Test fallback:** TinyLlama 1.1B for latency spikes

**Expected Result:** Consistent sub-500ms TTFT

### Phase 4: Content & Features

1. **Implement missing services:** Party lines, horoscopes, etc.
2. **Add gamification:** Achievements, unlocks
3. **Easter eggs:** Hidden numbers, pop culture references
4. **Audio authenticity:** Apply full processing chain

### Phase 5: Hardware Decision (If Needed)

1. **Benchmark optimized stack** on current RPi5
2. **If latency >2.5s:** Migrate to Jetson Orin Nano
3. **If budget constrained:** Orange Pi 5 Plus alternative

---

## Summary of Key Recommendations

### Must-Do (High Impact, Low Effort)

| Change | Impact | Effort |
|--------|--------|--------|
| faster-whisper + distil-whisper | 4-6x STT speedup | Medium |
| Silero VAD | Better turn detection | Low |
| Qwen2.5-3B GPTQ | Best edge LLM | Medium |
| Kokoro-82M | 100-200ms TTS improvement | Medium |

### Should-Do (Medium Impact)

| Change | Impact | Effort |
|--------|--------|--------|
| Streaming architecture | 800-1500ms latency reduction | High |
| Telephone audio filters | Authentic sound | Medium |
| Gamification system | User engagement | Medium |
| Missing 90s services | Content completeness | Medium |

### Consider (Lower Priority)

| Change | Impact | Effort |
|--------|--------|--------|
| Hardware upgrade to Jetson | Best performance | High (cost) |
| Wideband ATA upgrade | Better audio quality | Medium |
| FreeSWITCH migration | Better scalability | High |

---

## Sources

### Technical Architecture
- [Toward Low-Latency End-to-End Voice Agents](https://arxiv.org/abs/2508.04721)
- [Raspberry Pi AI HAT+ 2 Review](https://www.tomshardware.com/raspberry-pi/raspberry-pi-ai-hat-plus-2-review)
- [Jeff Geerling's AI HAT+ 2 Analysis](https://www.jeffgeerling.com/blog/2026/raspberry-pi-ai-hat-2/)
- [SmolLM3 Blog](https://huggingface.co/blog/smollm3)
- [faster-whisper GitHub](https://github.com/SYSTRAN/faster-whisper)
- [distil-whisper GitHub](https://github.com/huggingface/distil-whisper)
- [Silero VAD GitHub](https://github.com/snakers4/silero-vad)
- [Kokoro-82M](https://www.inferless.com/learn/comparing-different-text-to-speech---tts--models-part-2)

### Voice AI Frameworks
- [Pipecat vs LiveKit Comparison](https://medium.com/@ggarciabernardo/realtime-ai-agents-frameworks-bb466ccb2a09)
- [Voice AI Latency Guide](https://deepgram.com/learn/low-latency-voice-ai)
- [Twilio Voice Agent Best Practices](https://www.twilio.com/en-us/blog/developers/best-practices/guide-core-latency-ai-voice-agents)

### Similar Projects
- [Futel](http://futel.net/)
- [Good Phone Project](https://rochesterbeacon.com/2026/01/06/the-good-phone-project-adds-more-free-payphones/)
- [SparkFun 970-HA-JOKES](https://learn.sparkfun.com/tutorials/the-970-ha-jokes-payphone-project/all)
- [Wind Phone](https://en.wikipedia.org/wiki/Wind_phone)

### Audio Processing
- [G.711 Codec Specification](https://en.wikipedia.org/wiki/G.711)
- [μ-law Algorithm](https://en.wikipedia.org/wiki/Mu-law_algorithm)
- [Telephone Audio Simulation](https://gearspace.com/board/so-much-gear-so-little-time/1337854-best-way-eq-telephone-vocal-effect.html)
