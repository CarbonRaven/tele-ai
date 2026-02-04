# Payphone-AI Operations Scripts

Scripts for managing, monitoring, and troubleshooting the Payphone-AI system.

## Quick Start

```bash
# On Pi #1 (pi-voice), install the operations tools
sudo ./install-ops.sh

# Check system status
payphone-ops status

# Verify all services are ready
payphone-ops verify

# Start services and call payphone when ready
payphone-ops start
```

## Scripts

### payphone-ops.sh

**Unified operations script** for managing the entire Payphone-AI system.

| Command | Description |
|---------|-------------|
| `status` | Full system health check (network, services, resources) |
| `verify` | Pre-flight verification (checks all required services) |
| `start` | Start all services in correct dependency order |
| `stop` | Graceful shutdown of payphone services |
| `restart` | Stop then start services |
| `ready-call` | Call the payphone to announce system is ready |
| `watch` | Live monitoring dashboard (refreshes every 2s) |
| `shutdown` | Full system shutdown (both Raspberry Pis) |

**Examples:**

```bash
# Check if everything is working
payphone-ops status

# Verify before going live
payphone-ops verify

# Start services and optionally call payphone
payphone-ops start

# Just trigger the ready call
payphone-ops ready-call

# Watch system health live
payphone-ops watch

# Graceful full shutdown
payphone-ops shutdown
```

### health-monitor.py

**Detailed health monitoring** with JSON logging support.

```bash
# One-shot console output
./health-monitor.py

# Continuous monitoring (2s refresh)
./health-monitor.py --watch

# JSON output for parsing
./health-monitor.py --json

# Log to file
./health-monitor.py --log

# Combined: watch and log
./health-monitor.py --watch --log --interval 30
```

### quick-health.sh

**Quick one-liner health check** for terminal use.

```bash
./quick-health.sh
```

## Installation

### On Pi #1 (pi-voice)

```bash
cd /home/payphone/tele-ai/scripts
sudo ./install-ops.sh
```

This installs:
- `payphone-ops` command (and `pops` alias)
- Configuration file at `/etc/payphone/ops.conf`
- Asterisk dialplan for ready-call feature
- Pre-recorded announcement (if TTS tools available)

### Manual Installation

```bash
# Copy ops script
sudo cp payphone-ops.sh /usr/local/bin/payphone-ops
sudo chmod +x /usr/local/bin/payphone-ops

# Create config
sudo mkdir -p /etc/payphone
sudo cp ops.conf.example /etc/payphone/ops.conf

# Install Asterisk dialplan (append to existing)
sudo cat asterisk/extensions_ready.conf >> /etc/asterisk/extensions_custom.conf
sudo asterisk -rx "dialplan reload"
```

## Configuration

Edit `/etc/payphone/ops.conf`:

```bash
# Network
PI_VOICE_IP=192.168.1.10
PI_OLLAMA_IP=192.168.1.11

# Payphone extension (HT801)
PAYPHONE_EXTENSION=100

# LLM model to verify
OLLAMA_MODEL=llama3.2:3b-instruct-q4_K_M
```

Or use environment variables:

```bash
PI_OLLAMA_IP=192.168.1.20 payphone-ops status
```

## Ready Call Feature

When the system boots and all services are verified, it can call the payphone to announce readiness.

### How it works

1. `payphone-ops start` runs verification checks
2. If all checks pass, prompts to trigger ready call
3. Creates an Asterisk call file in `/var/spool/asterisk/outgoing/`
4. Asterisk dials the payphone extension
5. When answered, plays announcement via:
   - Pre-recorded audio (`/var/lib/asterisk/sounds/custom/system-ready.wav`)
   - Or live TTS via AudioSocket

### Custom Announcement

Record your own announcement:

```bash
# Record (8kHz mono WAV for Asterisk)
arecord -f S16_LE -r 8000 -c 1 /var/lib/asterisk/sounds/custom/system-ready.wav

# Or convert existing audio
sox input.mp3 -r 8000 -c 1 /var/lib/asterisk/sounds/custom/system-ready.wav

# Set permissions
sudo chown asterisk:asterisk /var/lib/asterisk/sounds/custom/system-ready.wav
```

## Systemd Integration

### health-monitor as a service

```bash
sudo cp health-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable health-monitor
sudo systemctl start health-monitor
```

Logs to `/var/log/tele-ai/health.jsonl` (JSON lines format).

## Troubleshooting

### Common Issues

| Issue | Check | Fix |
|-------|-------|-----|
| "Pi #2 unreachable" | Network cable, switch | `ping 192.168.1.11` |
| "Ollama DOWN" | Service status on Pi #2 | `ssh pi-ollama "systemctl status ollama"` |
| "AudioSocket DOWN" | payphone service | `sudo systemctl restart payphone` |
| Ready call not ringing | Extension config | Check `PAYPHONE_EXTENSION` matches HT801 |
| No announcement audio | Sound file missing | Run `install-ops.sh` or create manually |

### Debug Commands

```bash
# Check Asterisk channels during call
asterisk -rx "core show channels"

# View call file processing
tail -f /var/log/asterisk/full

# Check dialplan context exists
asterisk -rx "dialplan show ready-announcement"

# Test AudioSocket connectivity
nc -zv 127.0.0.1 9092

# Test Ollama from Pi #1
curl http://192.168.1.11:11434/api/tags
```

## File Structure

```
scripts/
├── README.md                    # This file
├── payphone-ops.sh              # Main operations script
├── install-ops.sh               # Installer for Pi #1
├── ops.conf.example             # Configuration template
├── health-monitor.py            # Detailed health monitoring
├── health-monitor.service       # Systemd unit for monitoring
├── quick-health.sh              # Quick health check
└── asterisk/
    └── extensions_ready.conf    # Dialplan for ready-call
```
