#!/bin/bash
#
# install-ops.sh - Install payphone-ops.sh and ready-call dialplan
#
# Run this on Pi #1 (pi-voice) to set up operations tooling
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="/usr/local/bin"
CONFIG_DIR="/etc/payphone"
ASTERISK_CUSTOM="/etc/asterisk/extensions_custom.conf"
SOUNDS_DIR="/var/lib/asterisk/sounds/custom"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo ""
echo "=========================================="
echo "  Payphone-AI Operations Setup"
echo "=========================================="
echo ""

# Check if running as root or with sudo
if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run with sudo"
    exit 1
fi

# 1. Install payphone-ops.sh
log_info "Installing payphone-ops.sh..."
cp "$SCRIPT_DIR/payphone-ops.sh" "$INSTALL_DIR/payphone-ops"
chmod +x "$INSTALL_DIR/payphone-ops"
log_success "Installed to $INSTALL_DIR/payphone-ops"

# 2. Create config directory and install config
log_info "Setting up configuration..."
mkdir -p "$CONFIG_DIR"
if [[ ! -f "$CONFIG_DIR/ops.conf" ]]; then
    cp "$SCRIPT_DIR/ops.conf.example" "$CONFIG_DIR/ops.conf"
    log_success "Created $CONFIG_DIR/ops.conf (edit to customize)"
else
    log_warn "$CONFIG_DIR/ops.conf already exists, skipping"
fi

# 3. Create custom sounds directory
log_info "Creating custom sounds directory..."
mkdir -p "$SOUNDS_DIR"
chown asterisk:asterisk "$SOUNDS_DIR"
log_success "Created $SOUNDS_DIR"

# 4. Install Asterisk dialplan
log_info "Installing Asterisk dialplan for ready-call..."

# Check if extensions_custom.conf exists
if [[ -f "$ASTERISK_CUSTOM" ]]; then
    # Check if our context already exists
    if grep -q "ready-announcement" "$ASTERISK_CUSTOM"; then
        log_warn "Ready-call dialplan already in extensions_custom.conf"
    else
        log_info "Appending ready-call dialplan to extensions_custom.conf..."
        echo "" >> "$ASTERISK_CUSTOM"
        echo "; === Payphone-AI Ready Call (added by install-ops.sh) ===" >> "$ASTERISK_CUSTOM"
        cat "$SCRIPT_DIR/asterisk/extensions_ready.conf" >> "$ASTERISK_CUSTOM"
        log_success "Dialplan added"

        # Reload Asterisk dialplan
        log_info "Reloading Asterisk dialplan..."
        asterisk -rx "dialplan reload" 2>/dev/null || true
        log_success "Dialplan reloaded"
    fi
else
    log_warn "extensions_custom.conf not found at $ASTERISK_CUSTOM"
    log_info "Creating new file..."
    cp "$SCRIPT_DIR/asterisk/extensions_ready.conf" "$ASTERISK_CUSTOM"
    chown asterisk:asterisk "$ASTERISK_CUSTOM"
    asterisk -rx "dialplan reload" 2>/dev/null || true
    log_success "Dialplan installed"
fi

# 5. Create symlink for convenience
log_info "Creating convenience symlink..."
ln -sf "$INSTALL_DIR/payphone-ops" "$INSTALL_DIR/pops" 2>/dev/null || true
log_success "Created symlink: pops -> payphone-ops"

# 6. Generate a simple ready announcement using espeak/pico2wave if available
log_info "Checking for TTS tools to generate announcement..."

ANNOUNCEMENT_TEXT="Payphone A I system is fully operational. All services verified and ready for use. Have a nice day!"

if command -v pico2wave &>/dev/null; then
    log_info "Generating announcement with pico2wave..."
    pico2wave -w "$SOUNDS_DIR/system-ready.wav" "$ANNOUNCEMENT_TEXT"
    # Convert to Asterisk-compatible format (8kHz mono)
    if command -v sox &>/dev/null; then
        sox "$SOUNDS_DIR/system-ready.wav" -r 8000 -c 1 "$SOUNDS_DIR/system-ready-8k.wav"
        mv "$SOUNDS_DIR/system-ready-8k.wav" "$SOUNDS_DIR/system-ready.wav"
    fi
    chown asterisk:asterisk "$SOUNDS_DIR/system-ready.wav"
    log_success "Created $SOUNDS_DIR/system-ready.wav"
elif command -v espeak &>/dev/null; then
    log_info "Generating announcement with espeak..."
    espeak -w "$SOUNDS_DIR/system-ready.wav" "$ANNOUNCEMENT_TEXT"
    chown asterisk:asterisk "$SOUNDS_DIR/system-ready.wav"
    log_success "Created $SOUNDS_DIR/system-ready.wav"
else
    log_warn "No TTS tool found (pico2wave or espeak)"
    log_info "Ready-call will use live TTS via AudioSocket instead"
    log_info "Or install: sudo apt install libttspico-utils"
fi

# Summary
echo ""
echo "=========================================="
echo "  Installation Complete"
echo "=========================================="
echo ""
echo "Commands available:"
echo "  payphone-ops status      # Check system health"
echo "  payphone-ops verify      # Pre-flight verification"
echo "  payphone-ops start       # Start services"
echo "  payphone-ops stop        # Stop services"
echo "  payphone-ops ready-call  # Call payphone with ready message"
echo "  payphone-ops watch       # Live monitoring"
echo "  payphone-ops shutdown    # Full system shutdown"
echo ""
echo "Short alias: pops (e.g., 'pops status')"
echo ""
echo "Configuration: $CONFIG_DIR/ops.conf"
echo ""
echo "Next steps:"
echo "  1. Edit $CONFIG_DIR/ops.conf to match your setup"
echo "  2. Run: payphone-ops verify"
echo "  3. Test: payphone-ops ready-call"
echo ""
