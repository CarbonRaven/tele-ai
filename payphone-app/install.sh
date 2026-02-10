#!/bin/bash
#
# AI Payphone Installation Script
# For Pi #1 (pi-voice): Raspberry Pi 5 (16GB) with AI HAT+ 2
#
# This script sets up the voice pipeline on Pi #1:
#   - Hailo-accelerated Whisper STT (via Wyoming protocol)
#   - Kokoro TTS
#   - VAD (Voice Activity Detection)
#   - AudioSocket server for Asterisk integration
#
# LLM runs on Pi #2 (pi-ollama) - configure separately.
#
# Prerequisites:
#   - Debian Trixie (13)
#   - AI HAT+ 2 drivers installed (sudo apt install hailo-h10-all)
#   - Wyoming Hailo Whisper running (sudo apt install wyoming-hailo-whisper)
#   - Network configured (static IP: 10.10.10.10)
#
# Usage:
#   chmod +x install.sh
#   ./install.sh
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="${INSTALL_DIR}/.venv"
SERVICE_NAME="payphone"

# Default settings (can be overridden)
# Default to Pi #2 (pi-ollama) for LLM
OLLAMA_HOST="${OLLAMA_HOST:-http://10.10.10.11:11434}"
AUDIOSOCKET_PORT="${AUDIOSOCKET_PORT:-9092}"
WYOMING_WHISPER_PORT="${WYOMING_WHISPER_PORT:-10300}"

#------------------------------------------------------------------------------
# Helper Functions
#------------------------------------------------------------------------------

print_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_step() {
    echo -e "${GREEN}▶${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

#------------------------------------------------------------------------------
# Pre-flight Checks
#------------------------------------------------------------------------------

preflight_checks() {
    print_header "Pre-flight Checks"

    # Check if running on Raspberry Pi
    if [ -f /proc/device-tree/model ]; then
        MODEL=$(cat /proc/device-tree/model)
        print_step "Device: $MODEL"
    else
        print_warning "Could not detect Raspberry Pi model"
    fi

    # Check architecture
    ARCH=$(uname -m)
    if [ "$ARCH" != "aarch64" ]; then
        print_error "This script requires 64-bit ARM (aarch64). Detected: $ARCH"
        exit 1
    fi
    print_success "Architecture: $ARCH"

    # Check available memory
    TOTAL_MEM=$(free -g | awk '/^Mem:/{print $2}')
    if [ "$TOTAL_MEM" -lt 8 ]; then
        print_warning "Less than 8GB RAM detected. Performance may be limited."
    else
        print_success "Memory: ${TOTAL_MEM}GB"
    fi

    # Check available disk space
    AVAILABLE_SPACE=$(df -BG "$HOME" | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$AVAILABLE_SPACE" -lt 20 ]; then
        print_error "Less than 20GB free space. Need space for models."
        exit 1
    fi
    print_success "Available disk space: ${AVAILABLE_SPACE}GB"

    # Check Python version
    if check_command python3; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f1)
        PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f2)
        if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
            print_success "Python: $PYTHON_VERSION"
        else
            print_error "Python 3.10+ required. Found: $PYTHON_VERSION"
            exit 1
        fi
    else
        print_error "Python3 not found"
        exit 1
    fi

    # Check if we're in the right directory
    if [ ! -f "${INSTALL_DIR}/pyproject.toml" ]; then
        print_error "pyproject.toml not found in ${INSTALL_DIR}"
        print_error "Please run this script from the payphone-app directory"
        exit 1
    fi
    print_success "Found pyproject.toml"

    echo ""
}

#------------------------------------------------------------------------------
# System Dependencies
#------------------------------------------------------------------------------

install_system_deps() {
    print_header "Installing System Dependencies"

    print_step "Updating package lists..."
    sudo apt update

    print_step "Installing required packages..."
    sudo apt install -y \
        python3-pip \
        python3-venv \
        python3-dev \
        ffmpeg \
        libsndfile1 \
        libsndfile1-dev \
        portaudio19-dev \
        libffi-dev \
        libssl-dev \
        libopenblas-dev \
        libasound2-dev \
        git \
        curl \
        wget

    print_success "System dependencies installed"
}

#------------------------------------------------------------------------------
# Python Virtual Environment
#------------------------------------------------------------------------------

setup_python_env() {
    print_header "Setting Up Python Environment"

    # Create virtual environment if it doesn't exist
    if [ ! -d "$VENV_DIR" ]; then
        print_step "Creating virtual environment..."
        python3 -m venv "$VENV_DIR"
    else
        print_step "Virtual environment already exists"
    fi

    # Activate virtual environment
    print_step "Activating virtual environment..."
    source "${VENV_DIR}/bin/activate"

    # Upgrade pip
    print_step "Upgrading pip..."
    pip install --upgrade pip wheel setuptools

    # Install PyTorch (CPU version for Pi)
    print_step "Installing PyTorch (this may take a few minutes)..."
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu

    # Install project dependencies
    print_step "Installing project dependencies..."
    pip install -e "${INSTALL_DIR}"

    print_success "Python environment configured"
}

#------------------------------------------------------------------------------
# Download Models
#------------------------------------------------------------------------------

download_models() {
    print_header "Downloading AI Models"

    source "${VENV_DIR}/bin/activate"
    cd "$INSTALL_DIR"

    # Download Kokoro TTS models
    if [ ! -f "kokoro-v1.0.onnx" ]; then
        print_step "Downloading Kokoro TTS model (~200MB)..."
        wget -q --show-progress \
            https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
    else
        print_step "Kokoro TTS model already exists"
    fi

    if [ ! -f "voices-v1.0.bin" ]; then
        print_step "Downloading Kokoro voices (~50MB)..."
        wget -q --show-progress \
            https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
    else
        print_step "Kokoro voices already exist"
    fi

    # Pre-download Silero VAD (via torch.hub)
    print_step "Downloading Silero VAD model..."
    python3 -c "
import torch
torch.hub.load('snakers4/silero-vad', 'silero_vad', trust_repo=True)
print('Silero VAD downloaded')
"

    # Pre-download Whisper model
    print_step "Downloading Whisper model (this may take several minutes)..."
    python3 -c "
from faster_whisper import WhisperModel
import os

# Use smaller model for faster download, user can change later
model_name = os.environ.get('WHISPER_MODEL', 'base')
print(f'Downloading Whisper model: {model_name}')
model = WhisperModel(model_name, device='cpu', compute_type='int8')
print('Whisper model downloaded')
"

    print_success "All models downloaded"
}

#------------------------------------------------------------------------------
# Moonshine STT
#------------------------------------------------------------------------------

install_moonshine() {
    print_header "Installing Moonshine STT (Recommended)"

    source "${VENV_DIR}/bin/activate"

    print_step "Installing transformers for Moonshine..."
    pip install "transformers>=4.48"

    print_step "Pre-downloading Moonshine model..."
    python3 -c "
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
model_id = 'UsefulSensors/moonshine-tiny'
processor = AutoProcessor.from_pretrained(model_id)
model = AutoModelForSpeechSeq2Seq.from_pretrained(model_id)
print('Moonshine model downloaded')
"

    if [ $? -eq 0 ]; then
        print_success "Moonshine STT installed (5x faster than Whisper)"
    else
        print_warning "Moonshine install failed, will use Whisper fallback"
    fi
}

#------------------------------------------------------------------------------
# Configuration
#------------------------------------------------------------------------------

create_config() {
    print_header "Creating Configuration"

    cd "$INSTALL_DIR"

    if [ -f ".env" ]; then
        print_warning ".env file already exists, backing up to .env.backup"
        cp .env .env.backup
    fi

    # Prompt for Ollama host (default to Pi #2)
    echo ""
    echo -e "${YELLOW}Ollama Configuration${NC}"
    echo "In the recommended dual-Pi setup, Ollama runs on Pi #2 (10.10.10.11)."
    echo "Press Enter to use the default, or enter a different IP address."
    read -p "Ollama host [10.10.10.11]: " OLLAMA_INPUT

    if [ -n "$OLLAMA_INPUT" ]; then
        OLLAMA_HOST="http://${OLLAMA_INPUT}:11434"
    else
        OLLAMA_HOST="http://10.10.10.11:11434"
    fi

    # Check if Wyoming Hailo Whisper is running
    echo ""
    echo -e "${YELLOW}STT Configuration${NC}"
    if nc -zv localhost ${WYOMING_WHISPER_PORT} 2>/dev/null; then
        print_success "Wyoming Hailo Whisper detected on port ${WYOMING_WHISPER_PORT}"
        STT_BACKEND="hailo"
    else
        print_warning "Wyoming Hailo Whisper not detected on port ${WYOMING_WHISPER_PORT}"
        print_warning "Will use faster-whisper CPU fallback"
        STT_BACKEND="auto"
    fi

    # Create .env file
    print_step "Creating .env file..."
    cat > .env << EOF
# AI Payphone Configuration
# Generated by install.sh on $(date)
# Running on: Pi #1 (pi-voice) - Voice Pipeline

# Debug mode
DEBUG=false
LOG_LEVEL=INFO

# AudioSocket Server (entry point for Asterisk calls)
AUDIO_AUDIOSOCKET_HOST=0.0.0.0
AUDIO_AUDIOSOCKET_PORT=${AUDIOSOCKET_PORT}

# Speech-to-Text
# Primary: Hailo-accelerated Whisper via Wyoming protocol
# Fallback: faster-whisper on CPU if Wyoming unavailable
STT_BACKEND=${STT_BACKEND}
STT_MOONSHINE_MODEL=UsefulSensors/moonshine-tiny
STT_WYOMING_HOST=localhost
STT_WYOMING_PORT=${WYOMING_WHISPER_PORT}
# Fallback model settings (used if Wyoming/Hailo unavailable)
STT_WHISPER_MODEL=base
STT_COMPUTE_TYPE=int8
STT_LANGUAGE=en

# Language Model (Ollama on Pi #2)
LLM_HOST=${OLLAMA_HOST}
LLM_MODEL=qwen3:4b
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=150
LLM_TIMEOUT=10.0

# Text-to-Speech (Kokoro - runs locally on Pi #1)
TTS_MODEL_PATH=kokoro-v1.0.onnx
TTS_VOICES_PATH=voices-v1.0.bin
TTS_VOICE=af_bella
TTS_SPEED=1.0

# Voice Activity Detection
VAD_THRESHOLD=0.5
VAD_MIN_SPEECH_DURATION_MS=250
VAD_MIN_SILENCE_DURATION_MS=500

# Timeouts
TIMEOUT_SILENCE_PROMPT=10
TIMEOUT_SILENCE_GOODBYE=30
TIMEOUT_MAX_CALL_DURATION=1800
EOF

    print_success "Configuration file created"
}

#------------------------------------------------------------------------------
# Systemd Service
#------------------------------------------------------------------------------

setup_systemd() {
    print_header "Setting Up Systemd Service"

    SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

    print_step "Creating systemd service file..."
    sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=AI Payphone Voice Pipeline
After=network.target

[Service]
Type=simple
User=${USER}
WorkingDirectory=${INSTALL_DIR}
Environment=PATH=${VENV_DIR}/bin:/usr/bin:/bin
ExecStart=${VENV_DIR}/bin/python main.py
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=${SERVICE_NAME}

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=${INSTALL_DIR}

[Install]
WantedBy=multi-user.target
EOF

    print_step "Reloading systemd..."
    sudo systemctl daemon-reload

    print_step "Enabling service..."
    sudo systemctl enable "$SERVICE_NAME"

    print_success "Systemd service configured"
    echo ""
    echo "  Start:   sudo systemctl start $SERVICE_NAME"
    echo "  Stop:    sudo systemctl stop $SERVICE_NAME"
    echo "  Status:  sudo systemctl status $SERVICE_NAME"
    echo "  Logs:    journalctl -u $SERVICE_NAME -f"
}

#------------------------------------------------------------------------------
# Firewall Configuration
#------------------------------------------------------------------------------

setup_firewall() {
    print_header "Configuring Firewall"

    if check_command ufw; then
        print_step "Configuring UFW firewall..."
        sudo ufw allow ${AUDIOSOCKET_PORT}/tcp comment "AudioSocket"
        print_success "Firewall rule added for port ${AUDIOSOCKET_PORT}"
    else
        print_warning "UFW not installed. Please manually open port ${AUDIOSOCKET_PORT}/tcp"
    fi
}

#------------------------------------------------------------------------------
# Ollama Connectivity Check
#------------------------------------------------------------------------------

check_ollama() {
    print_header "Ollama Connectivity Check"

    echo ""
    echo "In the recommended setup, Ollama runs on Pi #2 (pi-ollama)."
    echo "Checking connectivity to: ${OLLAMA_HOST}"
    echo ""

    if curl -s "${OLLAMA_HOST}/api/tags" > /dev/null 2>&1; then
        print_success "Ollama is reachable at ${OLLAMA_HOST}"

        # Check if model exists
        if curl -s "${OLLAMA_HOST}/api/tags" | grep -q "qwen3:4b"; then
            print_success "Model qwen3:4b is available"
        else
            print_warning "Model qwen3:4b not found on remote Ollama"
            echo ""
            echo "On Pi #2 (pi-ollama), run:"
            echo "  ollama pull qwen3:4b"
        fi
    else
        print_warning "Cannot reach Ollama at ${OLLAMA_HOST}"
        echo ""
        echo "Make sure Ollama is installed and running on Pi #2:"
        echo "  1. SSH to Pi #2: ssh pi@10.10.10.11"
        echo "  2. Install Ollama: curl -fsSL https://ollama.com/install.sh | sh"
        echo "  3. Configure for network access:"
        echo "     sudo systemctl edit ollama"
        echo "     Add: Environment=\"OLLAMA_HOST=0.0.0.0\""
        echo "  4. Restart: sudo systemctl restart ollama"
        echo "  5. Pull model: ollama pull qwen3:4b"
        echo ""

        # Offer local installation as fallback for development
        read -p "Install Ollama locally for development? [y/N]: " INSTALL_LOCAL

        if [[ "$INSTALL_LOCAL" =~ ^[Yy]$ ]]; then
            print_step "Installing Ollama locally..."
            curl -fsSL https://ollama.com/install.sh | sh

            print_step "Pulling qwen3:4b model..."
            ollama pull qwen3:4b

            # Update .env to use localhost
            sed -i "s|LLM_HOST=.*|LLM_HOST=http://localhost:11434|" .env
            print_success "Ollama installed locally, .env updated"
            print_warning "For production, move Ollama to Pi #2 to free RAM for voice pipeline"
        fi
    fi
}

#------------------------------------------------------------------------------
# Verification
#------------------------------------------------------------------------------

verify_installation() {
    print_header "Verifying Installation"

    source "${VENV_DIR}/bin/activate"
    cd "$INSTALL_DIR"

    print_step "Testing imports..."
    python3 -c "
import sys
errors = []

try:
    import torch
    print('  ✓ torch')
except ImportError as e:
    errors.append(f'torch: {e}')
    print('  ✗ torch')

try:
    import faster_whisper
    print('  ✓ faster_whisper')
except ImportError as e:
    errors.append(f'faster_whisper: {e}')
    print('  ✗ faster_whisper')

try:
    import kokoro_onnx
    print('  ✓ kokoro_onnx')
except ImportError as e:
    errors.append(f'kokoro_onnx: {e}')
    print('  ✗ kokoro_onnx')

try:
    import ollama
    print('  ✓ ollama')
except ImportError as e:
    errors.append(f'ollama: {e}')
    print('  ✗ ollama')

try:
    import soundfile
    print('  ✓ soundfile')
except ImportError as e:
    errors.append(f'soundfile: {e}')
    print('  ✗ soundfile')

try:
    import scipy
    print('  ✓ scipy')
except ImportError as e:
    errors.append(f'scipy: {e}')
    print('  ✗ scipy')

try:
    import pydantic_settings
    print('  ✓ pydantic_settings')
except ImportError as e:
    errors.append(f'pydantic_settings: {e}')
    print('  ✗ pydantic_settings')

if errors:
    print()
    print('Errors:')
    for err in errors:
        print(f'  {err}')
    sys.exit(1)
"

    # Check model files
    print_step "Checking model files..."
    if [ -f "kokoro-v1.0.onnx" ]; then
        print_success "  kokoro-v1.0.onnx found"
    else
        print_error "  kokoro-v1.0.onnx missing"
    fi

    if [ -f "voices-v1.0.bin" ]; then
        print_success "  voices-v1.0.bin found"
    else
        print_error "  voices-v1.0.bin missing"
    fi

    # Check Wyoming Whisper (Hailo STT)
    print_step "Checking Wyoming Whisper (Hailo STT)..."
    if nc -zv localhost ${WYOMING_WHISPER_PORT} 2>/dev/null; then
        print_success "  Wyoming Whisper is running on port ${WYOMING_WHISPER_PORT}"
    else
        print_warning "  Wyoming Whisper not detected on port ${WYOMING_WHISPER_PORT}"
        print_warning "  STT will use faster-whisper CPU fallback"
    fi

    # Check Ollama connectivity
    print_step "Checking Ollama connectivity (Pi #2)..."
    source .env 2>/dev/null || true
    if curl -s "${LLM_HOST}/api/tags" > /dev/null 2>&1; then
        print_success "  Ollama is reachable at ${LLM_HOST}"
    else
        print_warning "  Cannot reach Ollama at ${LLM_HOST}"
        print_warning "  Make sure Ollama is running on Pi #2 before starting the service"
    fi

    print_success "Verification complete"
}

#------------------------------------------------------------------------------
# Main Installation Flow
#------------------------------------------------------------------------------

main() {
    clear
    echo ""
    echo -e "${BLUE}"
    echo "    _    ___   ____                  _                      "
    echo "   / \  |_ _| |  _ \ __ _ _   _ _ __ | |__   ___  _ __   ___ "
    echo "  / _ \  | |  | |_) / _\` | | | | '_ \| '_ \ / _ \| '_ \ / _ \\"
    echo " / ___ \ | |  |  __/ (_| | |_| | |_) | | | | (_) | | | |  __/"
    echo "/_/   \_\___| |_|   \__,_|\__, | .__/|_| |_|\___/|_| |_|\___|"
    echo "                         |___/|_|                           "
    echo -e "${NC}"
    echo "                    Installation Script"
    echo ""

    # Run installation steps
    preflight_checks
    install_system_deps
    setup_python_env
    download_models
    install_moonshine
    create_config
    check_ollama
    setup_firewall
    setup_systemd
    verify_installation

    # Final message
    print_header "Installation Complete!"

    echo ""
    echo "Pi #1 (pi-voice) voice pipeline is configured."
    echo ""
    echo "Architecture:"
    echo "  Pi #1 (this machine): Moonshine/Hailo Whisper STT + Kokoro TTS + VAD + AudioSocket"
    echo "  Pi #2 (10.10.10.11): Standard Ollama with qwen3:4b"
    echo ""
    echo "Next steps:"
    echo ""
    echo "  1. Ensure Pi #2 (pi-ollama) has Ollama running with qwen3:4b"
    echo "     ssh pi@10.10.10.11"
    echo "     ollama list  # should show qwen3:4b"
    echo ""
    echo "  2. Ensure Wyoming Hailo Whisper is running:"
    echo "     sudo systemctl status wyoming-hailo-whisper"
    echo ""
    echo "  3. Configure FreePBX AudioSocket dialplan"
    echo "     See SETUP.md for details"
    echo ""
    echo "  4. Start the voice pipeline service:"
    echo "     sudo systemctl start ${SERVICE_NAME}"
    echo ""
    echo "  5. Monitor logs:"
    echo "     journalctl -u ${SERVICE_NAME} -f"
    echo ""
    echo "  6. Test by dialing extension 2255 from your payphone"
    echo ""
    echo -e "${GREEN}Installation directory: ${INSTALL_DIR}${NC}"
    echo -e "${GREEN}Virtual environment: ${VENV_DIR}${NC}"
    echo ""
}

# Run main function
main "$@"
