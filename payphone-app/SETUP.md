# AI Payphone Setup Guide

Complete setup guide for the AI Payphone voice pipeline.

## Quick Start (Automated Install)

For Raspberry Pi 5 with OS and AI HAT already configured:

```bash
# Clone the repository
git clone <repo-url> ~/tele-ai
cd ~/tele-ai/payphone-app

# Run the install script
chmod +x install.sh
./install.sh

# Start the service
sudo systemctl start payphone
```

The install script handles everything: system dependencies, Python environment, model downloads, configuration, and systemd service setup.

For manual installation or customization, follow the detailed steps below.

---

## Table of Contents

1. [Quick Start](#quick-start-automated-install)
2. [Hardware Overview](#hardware-overview)
3. [Network Architecture](#network-architecture)
4. [Raspberry Pi Setup](#raspberry-pi-setup)
5. [Python Environment](#python-environment)
6. [Model Downloads](#model-downloads)
7. [Ollama Setup](#ollama-setup)
8. [FreePBX Configuration](#freepbx-configuration)
9. [HT801 ATA Configuration](#ht801-ata-configuration)
10. [Running the Application](#running-the-application)
11. [Testing](#testing)
12. [Troubleshooting](#troubleshooting)

---

## Hardware Overview

### Required Components

| Component | Model | Purpose |
|-----------|-------|---------|
| Pi #1 (pi-voice) | Raspberry Pi 5 (16GB) + **AI HAT+ 2** | Voice pipeline: Moonshine/Whisper STT, Kokoro TTS, VAD, Asterisk |
| Pi #2 (pi-ollama) | Raspberry Pi 5 (16GB) | LLM server: Standard Ollama with qwen3:4b |
| AI Accelerator | Raspberry Pi AI HAT+ 2 (Hailo-10H, 40 TOPS) | Whisper STT acceleration on Pi #1 |
| Network Switch | 5-port Gigabit | Internal network |
| ATA | Grandstream HT801 v2 | Converts analog phone to SIP |
| Phone | Payphone | User interface |

**Architecture Note**: The AI HAT+ 2 is used exclusively for Whisper STT acceleration on Pi #1. Standard Ollama runs on Pi #2 for access to larger (3B+) models with better response quality.

### Physical Connections

```
┌─────────────┐     ┌─────────────┐
│  Payphone   │────▶│   HT801     │
│  (Analog)   │ RJ11│   (ATA)     │
└─────────────┘     └──────┬──────┘
                           │ Ethernet
                    ┌──────▼──────┐
                    │   Switch    │
                    │  (5-port)   │
                    └──────┬──────┘
            ┌──────────────┼──────────────┐
            │              │              │
     ┌──────▼──────┐ ┌─────▼─────┐ ┌──────▼──────┐
     │   Pi 5 #1   │ │  Pi 5 #2  │ │   Router    │
     │  pi-voice   │ │ pi-ollama │ │ (Optional)  │
     │ + AI HAT+2  │ │           │ │             │
     │ 10.10.10.10│ │10.10.10.11│ │             │
     └─────────────┘ └───────────┘ └─────────────┘
```

---

## Network Architecture

### IP Address Assignments

| Device | Hostname | IP Address | Role |
|--------|----------|------------|------|
| Pi 5 #1 | pi-voice | 10.10.10.10 | Voice pipeline + Hailo Whisper STT |
| Pi 5 #2 | pi-ollama | 10.10.10.11 | LLM server (standard Ollama) |
| HT801 ATA | ata | 10.10.10.20 | Payphone SIP adapter |

### Port Reference

| Port | Protocol | Host | Service |
|------|----------|------|---------|
| 9092 | TCP | pi-voice | AudioSocket (voice pipeline entry) |
| 10300 | TCP | pi-voice | Wyoming Whisper (Hailo-accelerated) |
| 10200 | TCP | pi-voice | Kokoro TTS (remote mode) |
| 10400 | TCP | pi-voice | Wyoming openWakeWord |
| 5060 | UDP | pi-voice | SIP signaling (Asterisk) |
| 10000-20000 | UDP | pi-voice | RTP media |
| 11434 | HTTP | pi-ollama | Ollama API (qwen3:4b) |

---

## Raspberry Pi Setup

### Initial OS Setup (Both Pi 5s)

1. **Flash Raspberry Pi OS Lite (64-bit)**

   ```bash
   # Use Raspberry Pi Imager
   # Select: Raspberry Pi OS Lite (64-bit) - Bookworm
   # Note: Use Lite (no desktop) for both Pis - saves ~300MB RAM
   # Enable SSH, set hostname, configure WiFi if needed
   ```

2. **First Boot Configuration**

   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y

   # Install essential packages
   sudo apt install -y \
       git \
       python3-pip \
       python3-venv \
       ffmpeg \
       libsndfile1 \
       portaudio19-dev \
       libffi-dev \
       libssl-dev
   ```

3. **Set Static IP (NetworkManager - default on Bookworm)**

   ```bash
   # For Pi 5 #1 (Pipeline)
   sudo nmcli con mod "Wired connection 1" \
     ipv4.method manual \
     ipv4.addresses 10.10.10.10/24 \
     ipv4.gateway 10.10.10.1 \
     ipv4.dns "8.8.8.8"
   sudo nmcli con up "Wired connection 1"

   # For Pi 5 #2 (Ollama)
   sudo nmcli con mod "Wired connection 1" \
     ipv4.method manual \
     ipv4.addresses 10.10.10.11/24 \
     ipv4.gateway 10.10.10.1 \
     ipv4.dns "8.8.8.8"
   sudo nmcli con up "Wired connection 1"
   ```

   > **Note**: Raspberry Pi OS Bookworm uses NetworkManager, not `dhcpcd`.
   > Run `nmcli con show` to see the exact connection name for your setup.

4. **Reboot**

   ```bash
   sudo reboot
   ```

### AI HAT+ 2 Setup (Required - Pi 5 #1 only)

The AI HAT+ 2 provides Hailo-10H NPU acceleration for Whisper STT on Pi #1. This frees the CPU for TTS and audio processing.

```bash
# Enable PCIe Gen 3 for best performance
sudo raspi-config
# Advanced Options → PCIe Speed → Gen 3
# Reboot when prompted

# Install Hailo runtime and drivers
sudo apt update
sudo apt install -y hailo-all

# Verify Hailo device is detected
lspci | grep Hailo
hailortcli fw-control identify

# Install Wyoming Hailo Whisper server
# (This provides the Hailo-accelerated Whisper endpoint on port 10300)
sudo apt install -y wyoming-hailo-whisper

# Enable and start the service
sudo systemctl enable wyoming-hailo-whisper
sudo systemctl start wyoming-hailo-whisper

# Verify Wyoming Whisper is running
systemctl status wyoming-hailo-whisper
nc -zv localhost 10300  # Should connect
```

**Note**: Pi #2 (pi-ollama) does not need the AI HAT+ 2 - it runs standard Ollama on CPU.

---

## Python Environment

### On Pi 5 #1 (Voice Pipeline)

1. **Clone Repository**

   ```bash
   cd ~
   git clone <your-repo-url> tele-ai
   cd tele-ai/payphone-app
   ```

2. **Create Virtual Environment**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Dependencies**

   ```bash
   # Install PyTorch (CPU version for Pi)
   pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu

   # Install project dependencies
   pip install -e .
   ```

4. **Verify Installation**

   ```bash
   python -c "import faster_whisper; print('faster-whisper OK')"
   python -c "import torch; print('torch OK')"
   python -c "import kokoro_onnx; print('kokoro-onnx OK')"
   python -c "import ollama; print('ollama OK')"
   ```

---

## Model Downloads

### Speech-to-Text (STT) - Pi #1

The application supports three STT backends with automatic fallback:

#### 1. Moonshine (Recommended - 5x faster than Whisper tiny)

Moonshine is a lightweight STT model optimized for edge devices:

```bash
source ~/tele-ai/payphone-app/.venv/bin/activate

# Install transformers (required for Moonshine)
pip install "transformers>=4.48"

# Pre-download Moonshine model (~27MB)
python -c "
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
model_id = 'UsefulSensors/moonshine-tiny'
processor = AutoProcessor.from_pretrained(model_id)
model = AutoModelForSpeechSeq2Seq.from_pretrained(model_id)
print('Moonshine model downloaded')
"
```

Moonshine models:
| Model | Size | Latency | Notes |
|-------|------|---------|-------|
| moonshine-tiny | 27MB | <100ms | **Recommended** - fastest |
| moonshine-base | 61MB | ~150ms | Better accuracy |

#### 2. Hailo-accelerated Whisper (Wyoming)

The Hailo NPU provides hardware-accelerated Whisper. The model is managed by the `wyoming-hailo-whisper` service installed above.

#### 3. faster-whisper (CPU Fallback)

If neither Moonshine nor Wyoming/Hailo is available:

```bash
source ~/tele-ai/payphone-app/.venv/bin/activate

# Pre-download fallback model
python -c "
from faster_whisper import WhisperModel
model = WhisperModel('tiny', device='cpu', compute_type='int8')
print('Whisper fallback model downloaded')
"
```

Whisper model sizes:
| Model | Size | RAM Required | Notes |
|-------|------|--------------|-------|
| tiny | ~75MB | ~1GB | Fastest Whisper option |
| base | ~145MB | ~1GB | Good balance |
| small | ~465MB | ~2GB | Better accuracy, slower |

### Silero VAD

Downloads automatically via torch.hub on first use:

```bash
python -c "
import torch
model, utils = torch.hub.load('snakers4/silero-vad', 'silero_vad', trust_repo=True)
print('Silero VAD downloaded')
"
```

### Kokoro TTS

Download model files manually:

```bash
cd ~/tele-ai/payphone-app

# Download ONNX model (~200MB)
wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx

# Download voices file (~50MB)
wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin

# Verify downloads
ls -la kokoro-v1.0.onnx voices-v1.0.bin
```

---

## Ollama Setup

### On Pi 5 #2 (LLM Server)

1. **Install Ollama**

   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```

2. **Pull the LLM Model**

   ```bash
   # Recommended: Qwen3 4B (best balance of speed and quality)
   ollama pull qwen3:4b

   # Alternative models:
   # ollama pull llama3.2:3b      # Fallback, good latency
   # ollama pull ministral:8b    # Best conversational quality
   ```

3. **Configure for Network Access**

   Edit `/etc/systemd/system/ollama.service`:

   ```ini
   [Service]
   Environment="OLLAMA_HOST=0.0.0.0"
   ```

   Reload and restart:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart ollama
   ```

4. **Verify Ollama is Accessible**

   From Pi 5 #1:

   ```bash
   curl http://10.10.10.11:11434/api/tags
   ```

5. **Test Generation**

   ```bash
   curl http://10.10.10.11:11434/api/generate -d '{
     "model": "qwen3:4b",
     "prompt": "Hello, how are you?",
     "stream": false
   }'
   ```

---

## FreePBX Configuration

### Step 1: Verify AudioSocket Module

SSH into your FreePBX server and verify the AudioSocket module is available:

```bash
# Check if module is loaded
asterisk -rx "module show like audiosocket"

# If not loaded, load it
asterisk -rx "module load app_audiosocket"

# Verify it loaded
asterisk -rx "module show like audiosocket"
# Should show: app_audiosocket.so
```

If the module doesn't exist, you may need Asterisk 16+ (AudioSocket was added in Asterisk 16). FreePBX 16/17 includes it by default.

### Step 2: Create Custom Dialplan

**Via SSH** - Add to `/etc/asterisk/extensions_custom.conf`:

```ini
[from-internal-custom]
; ============================================
; AI Payphone Voice Pipeline
; Routes calls to the AudioSocket server
; ============================================

; Direct dial to AI (extension 2255 = "CALL")
exten => 2255,1,NoOp(AI Payphone - Direct)
 same => n,Answer()
 same => n,Wait(0.5)
 same => n,Set(CHANNEL(audioreadformat)=slin16)
 same => n,Set(CHANNEL(audiowriteformat)=slin16)
 same => n,AudioSocket(${UNIQUEID},10.10.10.10:9092)
 same => n,Hangup()

; Dial-A-Joke shortcut (extension 5653 = "JOKE")
exten => 5653,1,NoOp(AI Payphone - Jokes)
 same => n,Answer()
 same => n,Wait(0.5)
 same => n,Set(CHANNEL(audioreadformat)=slin16)
 same => n,Set(CHANNEL(audiowriteformat)=slin16)
 same => n,Set(AI_FEATURE=jokes)
 same => n,AudioSocket(${UNIQUEID},10.10.10.10:9092)
 same => n,Hangup()

; Catch-all: Route ANY call from payphone extension (100) to AI
; Uncomment if you want the payphone to always connect to AI
;exten => _X.,1,GotoIf($["${CALLERID(num)}" = "100"]?ai-route,1)
; same => n,Goto(from-internal,${EXTEN},1)
;exten => _X.(ai-route),1,NoOp(Routing payphone to AI)
; same => n,Goto(2255,1)
```

**Reload the dialplan:**

```bash
asterisk -rx "dialplan reload"

# Verify it loaded
asterisk -rx "dialplan show 2255@from-internal-custom"
```

### Step 3: Create Payphone Extension (GUI)

1. **Navigate to Extensions**
   ```
   Applications → Extensions → Add Extension → Add New PJSIP Extension
   ```

2. **Extension Settings**

   | Field | Value |
   |-------|-------|
   | User Extension | 100 |
   | Display Name | Payphone |
   | Secret | (click Generate) - save this! |

3. **Advanced Tab**

   | Field | Value |
   |-------|-------|
   | DTMF Signaling | RFC 4733 |

4. **Click Submit, then Apply Config**

### Step 4: Create Custom Destination (Optional)

To make the AI accessible from IVR menus:

1. **Navigate to Admin → Custom Destinations**

2. **Add Custom Destination**

   | Field | Value |
   |-------|-------|
   | Target | 2255@from-internal-custom |
   | Description | AI Payphone |

3. **Now you can select "AI Payphone" as a destination in IVRs, Ring Groups, etc.**

### Step 5: Create Inbound Route for Payphone

If you want external callers to reach the AI:

1. **Navigate to Connectivity → Inbound Routes**

2. **Add Inbound Route**

   | Field | Value |
   |-------|-------|
   | Description | AI Payphone Inbound |
   | DID Number | (your DID or leave blank for catch-all) |
   | Set Destination | Custom Destinations → AI Payphone |

### Step 6: Firewall Configuration

Allow the AudioSocket connection from FreePBX to the Pi:

**On FreePBX (if firewall enabled):**
```
Connectivity → Firewall → Networks → Add Network
```

| Field | Value |
|-------|-------|
| Network | 10.10.10.10/32 |
| Zone | Trusted |
| Description | AI Payphone Server |

**On Pi #1 (voice pipeline):**
```bash
sudo ufw allow 9092/tcp comment "AudioSocket"
```

### Step 7: Test the Configuration

1. **Check AudioSocket is reachable from FreePBX:**
   ```bash
   # From FreePBX server
   nc -zv 10.10.10.10 9092
   ```

2. **Make a test call:**
   - Pick up payphone (or use softphone registered as ext 100)
   - Dial 2255
   - You should hear the AI greeting

3. **Monitor Asterisk logs:**
   ```bash
   # On FreePBX
   asterisk -rvvv

   # When call connects, you'll see:
   # -- AudioSocket(uuid,10.10.10.10:9092)
   ```

### Troubleshooting FreePBX

| Issue | Solution |
|-------|----------|
| "AudioSocket: Could not connect" | Check Pi is running, firewall allows 9092 |
| No audio | Ensure `slin16` format settings, check codecs |
| Call drops immediately | Check dialplan syntax with `dialplan show` |
| Extension not registering | Verify HT801 credentials match FreePBX |

**Useful Commands:**

```bash
# Check PJSIP registrations
asterisk -rx "pjsip show endpoints"

# Check active channels
asterisk -rx "core show channels"

# Debug AudioSocket
asterisk -rx "core set verbose 5"
asterisk -rx "core set debug 5"

# Reload after changes
fwconsole reload
```

---

## HT801 ATA Configuration

1. **Access Web Interface**

   Default: http://10.10.10.20 (admin/admin)

2. **SIP Settings (FXS Port)**

   | Setting | Value |
   |---------|-------|
   | SIP Server | 10.10.10.10 (FreePBX/Asterisk on Pi #1) |
   | SIP User ID | 100 |
   | Authenticate ID | 100 |
   | Authenticate Password | (set in FreePBX) |
   | Preferred Vocoder | PCMU (G.711 μ-law) |

3. **Audio Settings**

   | Setting | Value |
   |---------|-------|
   | Preferred Vocoder | PCMU |
   | Silence Suppression | No |
   | Echo Cancellation | Yes |
   | Jitter Buffer | Fixed, 60ms |

4. **Create Extension in FreePBX**

   - Extensions → Add Extension → PJSIP
   - Extension: 100
   - Display Name: Payphone
   - Secret: (generate password)

---

## Running the Application

### Configuration

1. **Create Environment File**

   ```bash
   cd ~/tele-ai/payphone-app
   cp .env.example .env
   ```

2. **Edit .env**

   ```bash
   # Debug mode
   DEBUG=false
   LOG_LEVEL=INFO

   # AudioSocket Server (Pi #1 voice pipeline entry point)
   AUDIO_AUDIOSOCKET_HOST=0.0.0.0
   AUDIO_AUDIOSOCKET_PORT=9092

   # Speech-to-Text
   # Backend: "moonshine" (fastest), "hailo", "whisper", or "auto" (tries all)
   STT_BACKEND=auto
   # Moonshine settings (recommended - 5x faster than Whisper tiny)
   STT_MOONSHINE_MODEL=UsefulSensors/moonshine-tiny
   # Wyoming/Hailo settings (fallback if Moonshine unavailable)
   STT_WYOMING_HOST=localhost
   STT_WYOMING_PORT=10300
   # faster-whisper settings (CPU fallback)
   STT_WHISPER_MODEL=tiny
   STT_COMPUTE_TYPE=int8

   # LLM (Standard Ollama on Pi #2)
   LLM_HOST=http://10.10.10.11:11434
   LLM_MODEL=qwen3:4b
   LLM_TEMPERATURE=0.7
   LLM_MAX_TOKENS=150

   # TTS (Kokoro on Pi #1)
   TTS_MODEL_PATH=kokoro-v1.0.onnx
   TTS_VOICES_PATH=voices-v1.0.bin
   TTS_VOICE=af_bella
   ```

### Start the Application

```bash
cd ~/tele-ai/payphone-app
source venv/bin/activate
python main.py
```

Expected output (with Moonshine - recommended):

```
2026-01-20 10:00:00 - INFO - Starting AI Payphone application...
2026-01-20 10:00:00 - INFO - Registered features: ['operator', 'jokes']
2026-01-20 10:00:01 - INFO - Loading Silero VAD...
2026-01-20 10:00:02 - INFO - Silero VAD model loaded successfully
2026-01-20 10:00:02 - INFO - Loading Moonshine model: UsefulSensors/moonshine-tiny
2026-01-20 10:00:04 - INFO - Using Moonshine STT (UsefulSensors/moonshine-tiny) on cpu - 5x faster than Whisper tiny
2026-01-20 10:00:04 - INFO - Connecting to Ollama at http://10.10.10.11:11434...
2026-01-20 10:00:05 - INFO - Ollama client initialized (model: qwen3:4b)
2026-01-20 10:00:05 - INFO - Loading Kokoro TTS...
2026-01-20 10:00:07 - INFO - Kokoro TTS model loaded successfully
2026-01-20 10:00:07 - INFO - All services initialized successfully
2026-01-20 10:00:07 - INFO - AudioSocket server listening on 0.0.0.0:9092
```

If Moonshine unavailable, falls back to Wyoming/Hailo:

```
2026-01-20 10:00:02 - WARNING - Moonshine unavailable (install transformers>=4.48): No module named 'transformers'
2026-01-20 10:00:02 - INFO - Connected to Wyoming Whisper at localhost:10300
2026-01-20 10:00:02 - INFO - Using Hailo-accelerated Whisper via Wyoming at localhost:10300
```

If both unavailable, falls back to faster-whisper:

```
2026-01-20 10:00:02 - WARNING - Moonshine unavailable...
2026-01-20 10:00:02 - WARNING - Hailo Wyoming unavailable: Cannot connect...
2026-01-20 10:00:02 - INFO - Loading faster-whisper model: tiny...
2026-01-20 10:00:10 - INFO - Using faster-whisper (tiny) on cpu
```

### Run as Systemd Service

Create `/etc/systemd/system/payphone.service`:

```ini
[Unit]
Description=AI Payphone Voice Pipeline
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/tele-ai/payphone-app
Environment=PATH=/home/pi/tele-ai/payphone-app/.venv/bin
ExecStart=/home/pi/tele-ai/payphone-app/.venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable payphone
sudo systemctl start payphone

# Check status
sudo systemctl status payphone

# View logs
journalctl -u payphone -f
```

---

## Testing

### Test AudioSocket Connection

```bash
# From another machine, test TCP connection
nc -zv 10.10.10.10 9092
```

### Test with SIP Client

Use a softphone (Zoiper, Linphone) to call extension 2255.

### Test Individual Components

```python
# test_components.py
import asyncio
from services.vad import SileroVAD
from services.stt import WhisperSTT
from services.llm import OllamaClient
from services.tts import KokoroTTS

async def test():
    # Test VAD
    vad = SileroVAD()
    await vad.initialize()
    print("✓ VAD initialized")

    # Test STT
    stt = WhisperSTT()
    await stt.initialize()
    print("✓ STT initialized")

    # Test LLM
    llm = OllamaClient()
    await llm.initialize()
    response = await llm.generate("Say hello in one word")
    print(f"✓ LLM response: {response.text}")

    # Test TTS
    tts = KokoroTTS()
    await tts.initialize()
    audio = await tts.synthesize("Hello world")
    print(f"✓ TTS generated {len(audio)} samples")

asyncio.run(test())
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "AudioSocket connection refused" | Check firewall: `sudo ufw allow 9092/tcp` |
| "Ollama connection refused" | Verify OLLAMA_HOST=0.0.0.0 and restart |
| "Model not found" | Run `ollama pull qwen3:4b` |
| "Out of memory" | Use smaller model or add swap |
| "No audio from payphone" | Check HT801 SIP registration |
| "Slow response" | Check network latency, consider smaller models |
| "Wyoming connection retry" | Normal behavior - auto-reconnects with exponential backoff (0.5s → 4s) |
| "LLM streaming timeout" | Check Ollama health; timeout auto-recovers with graceful message |

### Debug Commands

```bash
# Check AudioSocket server
netstat -tlnp | grep 9092

# Check Ollama
curl http://localhost:11434/api/tags

# Check Asterisk AudioSocket module
asterisk -rx "module show like audiosocket"

# Test dialplan
asterisk -rx "dialplan show 2255@from-internal-custom"

# View live Asterisk logs
asterisk -rvvv
```

### Performance Tuning

For Raspberry Pi 5:

```bash
# Add swap if needed (Pi 5 dynamically allocates GPU memory - no gpu_mem setting needed)
sudo dphys-swapfile swapoff
sudo sed -i 's/CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# Optimize for headless operation
sudo systemctl disable bluetooth
sudo systemctl disable avahi-daemon
```

---

## Quick Start Checklist

### Pi #1 (pi-voice) - Voice Pipeline + AI HAT+ 2
- [ ] Flash Pi OS Lite (64-bit Bookworm)
- [ ] Set static IP: 10.10.10.10
- [ ] Enable PCIe Gen 3 (raspi-config)
- [ ] Install Hailo drivers (`sudo apt install hailo-all`) - optional if using Moonshine
- [ ] Install Wyoming Hailo Whisper (`sudo apt install wyoming-hailo-whisper`) - optional
- [ ] Clone repo and run `install.sh`
- [ ] Install Moonshine: `pip install "transformers>=4.48"` (recommended)
- [ ] Download Kokoro model files
- [ ] Configure .env (STT_BACKEND=auto, points to Pi #2 for LLM)
- [ ] Install/configure Asterisk with AudioSocket dialplan
- [ ] Start payphone service

### Pi #2 (pi-ollama) - LLM Server
- [ ] Flash Pi OS Lite (64-bit Bookworm)
- [ ] Set static IP: 10.10.10.11
- [ ] Install Ollama (`curl -fsSL https://ollama.com/install.sh | sh`)
- [ ] Configure Ollama for network access (OLLAMA_HOST=0.0.0.0)
- [ ] Pull qwen3:4b model

### Network & Telephony
- [ ] Configure HT801 ATA (10.10.10.20)
- [ ] Test from Pi #1: `curl http://10.10.10.11:11434/api/tags`
- [ ] Test with phone call to extension 2255
