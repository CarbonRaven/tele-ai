#!/bin/bash
#
# payphone-ops.sh - Unified operations script for Payphone-AI system
#
# Usage:
#   ./payphone-ops.sh status      # Full system health check
#   ./payphone-ops.sh verify      # Pre-flight verification (all services ready?)
#   ./payphone-ops.sh start       # Start all services in order
#   ./payphone-ops.sh stop        # Graceful shutdown sequence
#   ./payphone-ops.sh restart     # Stop then start
#   ./payphone-ops.sh ready-call  # Call payphone to announce system ready
#   ./payphone-ops.sh watch       # Live monitoring dashboard
#   ./payphone-ops.sh shutdown    # Full system shutdown (both Pis)
#
# Configuration is loaded from /etc/payphone/ops.conf or environment variables

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================

# Load config file if exists
CONFIG_FILE="${PAYPHONE_CONFIG:-/etc/payphone/ops.conf}"
[[ -f "$CONFIG_FILE" ]] && source "$CONFIG_FILE"

# Network Configuration
PI_VOICE_IP="${PI_VOICE_IP:-10.10.10.10}"
PI_OLLAMA_IP="${PI_OLLAMA_IP:-10.10.10.11}"
HT801_IP="${HT801_IP:-10.10.10.12}"
PI_USER="${PI_USER:-payphone}"

# Service Ports
AUDIOSOCKET_PORT="${AUDIOSOCKET_PORT:-9092}"
OLLAMA_PORT="${OLLAMA_PORT:-11434}"
WHISPER_WYOMING_PORT="${WHISPER_WYOMING_PORT:-10300}"
WAKEWORD_PORT="${WAKEWORD_PORT:-10400}"
TTS_SERVER_PORT="${TTS_SERVER_PORT:-10200}"
ASTERISK_SIP_PORT="${ASTERISK_SIP_PORT:-5060}"

# Ollama Model
OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.2:3b}"

# Ready Call Configuration
PAYPHONE_EXTENSION="${PAYPHONE_EXTENSION:-100}"
READY_CALL_CONTEXT="${READY_CALL_CONTEXT:-ready-announcement}"
READY_CALL_MAX_RETRIES="${READY_CALL_MAX_RETRIES:-3}"
READY_CALL_WAIT_TIME="${READY_CALL_WAIT_TIME:-45}"

# Timeouts
PING_TIMEOUT="${PING_TIMEOUT:-2}"
SERVICE_TIMEOUT="${SERVICE_TIMEOUT:-5}"
BOOT_WAIT_TIMEOUT="${BOOT_WAIT_TIMEOUT:-120}"

# Paths
ASTERISK_SPOOL="/var/spool/asterisk/outgoing"
ASTERISK_SOUNDS="/var/lib/asterisk/sounds/custom"
PAYPHONE_APP_DIR="${PAYPHONE_APP_DIR:-/home/payphone/tele-ai/payphone-app}"

# =============================================================================
# Colors and Formatting
# =============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m' # No Color

# Status indicators
OK="${GREEN}●${NC}"
FAIL="${RED}●${NC}"
WARN="${YELLOW}●${NC}"
WAIT="${BLUE}○${NC}"

# =============================================================================
# Utility Functions
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${CYAN}==>${NC} ${BOLD}$1${NC}"
}

# Check if running on Pi #1 (pi-voice)
is_pi_voice() {
    local current_ip
    current_ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    [[ "$current_ip" == "$PI_VOICE_IP" ]] || [[ "$(hostname)" == "pi-voice" ]]
}

# Check if a host is reachable
check_host() {
    local host=$1
    ping -c 1 -W "$PING_TIMEOUT" "$host" &>/dev/null
}

# Check if a TCP port is open
check_port() {
    local host=$1
    local port=$2
    timeout "$SERVICE_TIMEOUT" bash -c "echo >/dev/tcp/$host/$port" 2>/dev/null
}

# Check HTTP endpoint
check_http() {
    local url=$1
    local expected_code=${2:-200}
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout "$SERVICE_TIMEOUT" "$url" 2>/dev/null || echo "000")
    [[ "$code" == "$expected_code" ]] || [[ "$code" == "200" ]]
}

# Get service status with timing
check_service_timed() {
    local name=$1
    local host=$2
    local port=$3
    local start end elapsed

    start=$(date +%s%N)
    if check_port "$host" "$port"; then
        end=$(date +%s%N)
        elapsed=$(( (end - start) / 1000000 ))
        echo -e "  ${OK} ${name}:${port} ${DIM}(${elapsed}ms)${NC}"
        return 0
    else
        echo -e "  ${FAIL} ${name}:${port} ${RED}DOWN${NC}"
        return 1
    fi
}

# Wait for a service to become available
wait_for_service() {
    local name=$1
    local host=$2
    local port=$3
    local timeout=${4:-30}
    local elapsed=0

    echo -n "  Waiting for $name..."
    while ! check_port "$host" "$port" && [[ $elapsed -lt $timeout ]]; do
        echo -n "."
        sleep 1
        ((elapsed++))
    done

    if check_port "$host" "$port"; then
        echo -e " ${GREEN}ready${NC} (${elapsed}s)"
        return 0
    else
        echo -e " ${RED}timeout${NC}"
        return 1
    fi
}

# =============================================================================
# Status Command
# =============================================================================

cmd_status() {
    echo -e "\n${BOLD}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}  Payphone-AI System Status${NC}"
    echo -e "${BOLD}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "  ${DIM}$(date '+%Y-%m-%d %H:%M:%S')${NC}\n"

    local all_ok=true

    # --- Network ---
    echo -e "${BOLD}  Network${NC}"
    if check_host "$PI_VOICE_IP"; then
        echo -e "  ${OK} Pi #1 (pi-voice) ${DIM}$PI_VOICE_IP${NC}"
    else
        echo -e "  ${FAIL} Pi #1 (pi-voice) ${RED}unreachable${NC}"
        all_ok=false
    fi

    if check_host "$PI_OLLAMA_IP"; then
        echo -e "  ${OK} Pi #2 (pi-ollama) ${DIM}$PI_OLLAMA_IP${NC}"
    else
        echo -e "  ${FAIL} Pi #2 (pi-ollama) ${RED}unreachable${NC}"
        all_ok=false
    fi

    if check_host "$HT801_IP"; then
        echo -e "  ${OK} HT801 ATA ${DIM}$HT801_IP${NC}"
    else
        echo -e "  ${FAIL} HT801 ATA ${RED}unreachable${NC}"
        all_ok=false
    fi

    # --- Pi #1 Services ---
    echo -e "\n${BOLD}  Pi #1 Services (pi-voice)${NC}"

    check_service_timed "AudioSocket" "$PI_VOICE_IP" "$AUDIOSOCKET_PORT" || all_ok=false

    # Check Asterisk (SIP)
    if check_port "$PI_VOICE_IP" "$ASTERISK_SIP_PORT"; then
        echo -e "  ${OK} Asterisk/FreePBX:$ASTERISK_SIP_PORT"
    else
        echo -e "  ${WARN} Asterisk/FreePBX:$ASTERISK_SIP_PORT ${YELLOW}(may be filtered)${NC}"
    fi

    # Optional services
    if check_port "$PI_VOICE_IP" "$WHISPER_WYOMING_PORT"; then
        echo -e "  ${OK} Wyoming-Whisper:$WHISPER_WYOMING_PORT ${DIM}(optional)${NC}"
    else
        echo -e "  ${DIM}  ○ Wyoming-Whisper:$WHISPER_WYOMING_PORT (not running)${NC}"
    fi

    if check_port "$PI_VOICE_IP" "$WAKEWORD_PORT"; then
        echo -e "  ${OK} openWakeWord:$WAKEWORD_PORT ${DIM}(optional)${NC}"
    else
        echo -e "  ${DIM}  ○ openWakeWord:$WAKEWORD_PORT (not running)${NC}"
    fi

    # --- Pi #2 Services ---
    echo -e "\n${BOLD}  Pi #2 Services (pi-ollama)${NC}"

    if check_http "http://$PI_OLLAMA_IP:$OLLAMA_PORT/api/tags"; then
        # Get loaded model
        local models
        models=$(curl -s "http://$PI_OLLAMA_IP:$OLLAMA_PORT/api/tags" 2>/dev/null | grep -o '"name":"[^"]*"' | head -1 | cut -d'"' -f4)
        echo -e "  ${OK} Ollama:$OLLAMA_PORT ${DIM}($models)${NC}"
    else
        echo -e "  ${FAIL} Ollama:$OLLAMA_PORT ${RED}DOWN${NC}"
        all_ok=false
    fi

    if check_port "$PI_OLLAMA_IP" "$TTS_SERVER_PORT"; then
        echo -e "  ${OK} TTS-Server:$TTS_SERVER_PORT ${DIM}(optional)${NC}"
    else
        echo -e "  ${DIM}  ○ TTS-Server:$TTS_SERVER_PORT (not running)${NC}"
    fi

    # --- System Resources (if on Pi #1) ---
    if is_pi_voice; then
        echo -e "\n${BOLD}  System Resources (Pi #1)${NC}"

        # CPU Temperature
        local temp
        temp=$(vcgencmd measure_temp 2>/dev/null | grep -oP 'temp=\K[\d.]+' || echo "N/A")
        if [[ "$temp" != "N/A" ]]; then
            local temp_int=${temp%.*}
            if [[ $temp_int -lt 70 ]]; then
                echo -e "  ${OK} CPU Temperature: ${temp}°C"
            elif [[ $temp_int -lt 80 ]]; then
                echo -e "  ${WARN} CPU Temperature: ${YELLOW}${temp}°C${NC}"
            else
                echo -e "  ${FAIL} CPU Temperature: ${RED}${temp}°C${NC}"
            fi
        fi

        # Throttling
        local throttle
        throttle=$(vcgencmd get_throttled 2>/dev/null | grep -oP 'throttled=\K0x[0-9a-fA-F]+' || echo "N/A")
        if [[ "$throttle" == "0x0" ]]; then
            echo -e "  ${OK} Throttling: None"
        elif [[ "$throttle" != "N/A" ]]; then
            echo -e "  ${FAIL} Throttling: ${RED}$throttle${NC}"
            all_ok=false
        fi

        # Memory
        local mem_total mem_avail mem_pct
        mem_total=$(grep MemTotal /proc/meminfo | awk '{print int($2/1024)}')
        mem_avail=$(grep MemAvailable /proc/meminfo | awk '{print int($2/1024)}')
        mem_pct=$(( (mem_total - mem_avail) * 100 / mem_total ))
        if [[ $mem_pct -lt 80 ]]; then
            echo -e "  ${OK} Memory: ${mem_pct}% used (${mem_avail}MB available)"
        else
            echo -e "  ${WARN} Memory: ${YELLOW}${mem_pct}% used${NC} (${mem_avail}MB available)"
        fi

        # Hailo NPU
        if lspci 2>/dev/null | grep -q Hailo; then
            echo -e "  ${OK} Hailo NPU: Detected"
        else
            echo -e "  ${DIM}  ○ Hailo NPU: Not detected${NC}"
        fi
    fi

    # --- Summary ---
    echo -e "\n${BOLD}═══════════════════════════════════════════════════════════════${NC}"
    if $all_ok; then
        echo -e "  ${GREEN}${BOLD}System Status: OPERATIONAL${NC}"
    else
        echo -e "  ${RED}${BOLD}System Status: DEGRADED${NC}"
    fi
    echo -e "${BOLD}═══════════════════════════════════════════════════════════════${NC}\n"

    $all_ok
}

# =============================================================================
# Verify Command (Pre-flight Check)
# =============================================================================

cmd_verify() {
    echo -e "\n${BOLD}Pre-flight Verification${NC}"
    echo -e "${DIM}Checking all services required for operation...${NC}\n"

    local checks_passed=0
    local checks_failed=0

    run_check() {
        local name=$1
        local cmd=$2
        echo -n "  Checking $name... "
        if eval "$cmd" &>/dev/null; then
            echo -e "${GREEN}OK${NC}"
            ((checks_passed++))
            return 0
        else
            echo -e "${RED}FAILED${NC}"
            ((checks_failed++))
            return 1
        fi
    }

    # Network
    log_step "Network Connectivity"
    run_check "Pi #1 (pi-voice)" "check_host $PI_VOICE_IP"
    run_check "Pi #2 (pi-ollama)" "check_host $PI_OLLAMA_IP"
    run_check "HT801 ATA" "check_host $HT801_IP"

    # Core Services
    echo ""
    log_step "Core Services"
    run_check "AudioSocket server" "check_port $PI_VOICE_IP $AUDIOSOCKET_PORT"
    run_check "Ollama LLM" "check_http http://$PI_OLLAMA_IP:$OLLAMA_PORT/api/tags"

    # Ollama Model
    echo ""
    log_step "LLM Model"
    echo -n "  Checking model loaded... "
    local models_json
    models_json=$(curl -s "http://$PI_OLLAMA_IP:$OLLAMA_PORT/api/tags" 2>/dev/null)
    if echo "$models_json" | grep -q "$OLLAMA_MODEL"; then
        echo -e "${GREEN}OK${NC} ($OLLAMA_MODEL)"
        ((checks_passed++))
    elif echo "$models_json" | grep -q '"name"'; then
        local available
        available=$(echo "$models_json" | grep -o '"name":"[^"]*"' | head -1 | cut -d'"' -f4)
        echo -e "${YELLOW}WARN${NC} (found: $available)"
        ((checks_passed++))
    else
        echo -e "${RED}FAILED${NC} (no models)"
        ((checks_failed++))
    fi

    # Test LLM Response
    echo -n "  Testing LLM response... "
    local llm_test
    llm_test=$(curl -s --max-time 10 "http://$PI_OLLAMA_IP:$OLLAMA_PORT/api/generate" \
        -d "{\"model\":\"$OLLAMA_MODEL\",\"prompt\":\"Say OK\",\"stream\":false}" 2>/dev/null)
    if echo "$llm_test" | grep -q '"response"'; then
        echo -e "${GREEN}OK${NC}"
        ((checks_passed++))
    else
        echo -e "${RED}FAILED${NC}"
        ((checks_failed++))
    fi

    # Asterisk
    echo ""
    log_step "Telephony"
    if is_pi_voice; then
        echo -n "  Checking Asterisk running... "
        if systemctl is-active asterisk &>/dev/null; then
            echo -e "${GREEN}OK${NC}"
            ((checks_passed++))
        else
            echo -e "${RED}FAILED${NC}"
            ((checks_failed++))
        fi

        echo -n "  Checking AudioSocket module... "
        if asterisk -rx "module show like audiosocket" 2>/dev/null | grep -q "app_audiosocket"; then
            echo -e "${GREEN}OK${NC}"
            ((checks_passed++))
        else
            echo -e "${RED}FAILED${NC}"
            ((checks_failed++))
        fi

        echo -n "  Checking payphone extension... "
        if asterisk -rx "pjsip show endpoints" 2>/dev/null | grep -qi "avail\|online"; then
            echo -e "${GREEN}OK${NC}"
            ((checks_passed++))
        else
            echo -e "${YELLOW}WARN${NC} (no endpoints registered)"
        fi
    else
        run_check "Asterisk SIP port" "check_port $PI_VOICE_IP $ASTERISK_SIP_PORT"
    fi

    # Summary
    echo ""
    echo -e "${BOLD}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "  Checks passed: ${GREEN}$checks_passed${NC}"
    echo -e "  Checks failed: ${RED}$checks_failed${NC}"
    echo -e "${BOLD}═══════════════════════════════════════════════════════════════${NC}"

    if [[ $checks_failed -eq 0 ]]; then
        echo -e "\n  ${GREEN}${BOLD}VERIFICATION PASSED${NC} - System ready for operation\n"
        return 0
    else
        echo -e "\n  ${RED}${BOLD}VERIFICATION FAILED${NC} - Fix issues before proceeding\n"
        return 1
    fi
}

# =============================================================================
# Start Command
# =============================================================================

cmd_start() {
    log_step "Starting Payphone-AI System"

    if ! is_pi_voice; then
        log_error "This command must be run on Pi #1 (pi-voice)"
        exit 1
    fi

    # 1. Check Pi #2 is up and Ollama running
    log_info "Checking Pi #2 (pi-ollama)..."
    if ! check_host "$PI_OLLAMA_IP"; then
        log_error "Pi #2 is not reachable. Please ensure it's powered on."
        exit 1
    fi

    if ! check_http "http://$PI_OLLAMA_IP:$OLLAMA_PORT/api/tags"; then
        log_warn "Ollama not responding, waiting..."
        if ! wait_for_service "Ollama" "$PI_OLLAMA_IP" "$OLLAMA_PORT" 60; then
            log_error "Ollama failed to start on Pi #2"
            exit 1
        fi
    fi
    log_success "Ollama is ready"

    # 2. Start Asterisk/FreePBX if not running
    log_info "Checking Asterisk..."
    if ! systemctl is-active asterisk &>/dev/null; then
        log_info "Starting Asterisk..."
        sudo systemctl start asterisk
        sleep 2
    fi
    log_success "Asterisk is running"

    # 3. Start payphone service
    log_info "Starting payphone service..."
    if systemctl is-active payphone &>/dev/null; then
        log_warn "Payphone service already running"
    else
        sudo systemctl start payphone
        sleep 2
    fi

    if ! wait_for_service "AudioSocket" "$PI_VOICE_IP" "$AUDIOSOCKET_PORT" 30; then
        log_error "Payphone service failed to start"
        sudo journalctl -u payphone -n 20 --no-pager
        exit 1
    fi
    log_success "Payphone service is running"

    # 4. Verify system
    echo ""
    if cmd_verify; then
        log_success "System started successfully!"
        echo ""
        read -p "Trigger ready call to payphone? [y/N] " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cmd_ready_call
        fi
    else
        log_warn "System started with warnings"
    fi
}

# =============================================================================
# Stop Command
# =============================================================================

cmd_stop() {
    log_step "Stopping Payphone-AI Services"

    if ! is_pi_voice; then
        log_error "This command must be run on Pi #1 (pi-voice)"
        exit 1
    fi

    # 1. Stop payphone service
    log_info "Stopping payphone service..."
    if systemctl is-active payphone &>/dev/null; then
        sudo systemctl stop payphone
        log_success "Payphone service stopped"
    else
        log_info "Payphone service was not running"
    fi

    # Note: We don't stop Asterisk by default as other things may depend on it
    log_info "Asterisk left running (stop manually if needed: sudo fwconsole stop)"

    log_success "Services stopped"
}

# =============================================================================
# Restart Command
# =============================================================================

cmd_restart() {
    cmd_stop
    echo ""
    sleep 2
    cmd_start
}

# =============================================================================
# Ready Call Command
# =============================================================================

cmd_ready_call() {
    log_step "Triggering System Ready Call"

    if ! is_pi_voice; then
        log_error "This command must be run on Pi #1 (pi-voice)"
        exit 1
    fi

    # Verify system first
    log_info "Running pre-flight verification..."
    if ! cmd_verify; then
        log_error "System verification failed. Fix issues before triggering ready call."
        exit 1
    fi

    # Check if custom sound exists, if not we'll use AudioSocket
    local use_audiosocket=false
    if [[ ! -f "$ASTERISK_SOUNDS/system-ready.wav" ]] && [[ ! -f "$ASTERISK_SOUNDS/system-ready.sln" ]]; then
        log_info "No pre-recorded announcement found, will use live TTS"
        use_audiosocket=true
    fi

    # Create the call file
    local call_file
    call_file=$(mktemp)

    if $use_audiosocket; then
        # Use AudioSocket to play TTS announcement
        cat > "$call_file" << EOF
Channel: PJSIP/$PAYPHONE_EXTENSION
MaxRetries: $READY_CALL_MAX_RETRIES
RetryTime: 30
WaitTime: $READY_CALL_WAIT_TIME
Context: ready-announcement-tts
Extension: s
Priority: 1
Setvar: READY_MESSAGE=Payphone AI system is fully operational. All services verified and ready for use. Have a nice day!
EOF
    else
        # Use pre-recorded announcement
        cat > "$call_file" << EOF
Channel: PJSIP/$PAYPHONE_EXTENSION
MaxRetries: $READY_CALL_MAX_RETRIES
RetryTime: 30
WaitTime: $READY_CALL_WAIT_TIME
Context: ready-announcement
Extension: s
Priority: 1
EOF
    fi

    log_info "Call file contents:"
    cat "$call_file"
    echo ""

    # Ensure dialplan context exists
    log_info "Checking dialplan context..."
    if ! asterisk -rx "dialplan show $READY_CALL_CONTEXT" 2>/dev/null | grep -q "^'"; then
        log_warn "Dialplan context '$READY_CALL_CONTEXT' not found"
        log_info "Creating temporary dialplan..."

        # Add dialplan via CLI (temporary, survives until Asterisk reload)
        asterisk -rx "dialplan add extension s,1,Answer() into $READY_CALL_CONTEXT" 2>/dev/null || true
        asterisk -rx "dialplan add extension s,2,Wait(1) into $READY_CALL_CONTEXT" 2>/dev/null || true

        if $use_audiosocket; then
            # For TTS, connect to our AudioSocket handler
            asterisk -rx "dialplan add extension s,3,AudioSocket(\${READY_MESSAGE},127.0.0.1:$AUDIOSOCKET_PORT) into $READY_CALL_CONTEXT" 2>/dev/null || true
        else
            asterisk -rx "dialplan add extension s,3,Playback(custom/system-ready) into $READY_CALL_CONTEXT" 2>/dev/null || true
        fi

        asterisk -rx "dialplan add extension s,4,Wait(1) into $READY_CALL_CONTEXT" 2>/dev/null || true
        asterisk -rx "dialplan add extension s,5,Hangup() into $READY_CALL_CONTEXT" 2>/dev/null || true

        log_success "Dialplan context created"
    fi

    # Move call file to spool directory
    log_info "Initiating call to extension $PAYPHONE_EXTENSION..."

    # Ensure spool directory exists and is writable
    if [[ ! -d "$ASTERISK_SPOOL" ]]; then
        log_error "Asterisk spool directory not found: $ASTERISK_SPOOL"
        rm -f "$call_file"
        exit 1
    fi

    # Move with correct ownership
    sudo mv "$call_file" "$ASTERISK_SPOOL/ready-call.call"
    sudo chown asterisk:asterisk "$ASTERISK_SPOOL/ready-call.call"

    log_success "Call queued! Payphone should ring shortly..."
    log_info "Watch call progress: asterisk -rx 'core show channels'"
}

# =============================================================================
# Watch Command
# =============================================================================

cmd_watch() {
    log_info "Starting live monitoring (Ctrl+C to exit)"
    echo ""

    # Check if health-monitor.py exists
    local monitor_script
    monitor_script="$(dirname "$0")/health-monitor.py"

    if [[ -f "$monitor_script" ]]; then
        python3 "$monitor_script" --watch --interval 2
    else
        # Fallback to simple watch loop
        while true; do
            clear
            cmd_status
            echo -e "${DIM}Refreshing every 5 seconds... (Ctrl+C to exit)${NC}"
            sleep 5
        done
    fi
}

# =============================================================================
# Shutdown Command (Full System)
# =============================================================================

cmd_shutdown() {
    echo -e "\n${BOLD}${RED}FULL SYSTEM SHUTDOWN${NC}"
    echo -e "${DIM}This will shut down both Raspberry Pis${NC}\n"

    read -p "Are you sure you want to shut down the entire system? [y/N] " -n 1 -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Shutdown cancelled"
        exit 0
    fi

    log_step "Initiating graceful shutdown sequence"

    # 1. Stop payphone service
    if is_pi_voice; then
        log_info "Stopping payphone service..."
        sudo systemctl stop payphone 2>/dev/null || true
    fi

    # 2. Stop Asterisk
    if is_pi_voice; then
        log_info "Stopping Asterisk/FreePBX..."
        sudo fwconsole stop 2>/dev/null || sudo systemctl stop asterisk 2>/dev/null || true
    fi

    # 3. Shutdown Pi #2 first (LLM server)
    log_info "Shutting down Pi #2 (pi-ollama)..."
    if check_host "$PI_OLLAMA_IP"; then
        ssh -o ConnectTimeout=5 "$PI_USER@$PI_OLLAMA_IP" "sudo shutdown -h now" 2>/dev/null &
        sleep 2
        log_success "Pi #2 shutdown initiated"
    else
        log_warn "Pi #2 not reachable (may already be off)"
    fi

    # 4. Shutdown Pi #1 (this machine if running locally)
    if is_pi_voice; then
        log_info "Shutting down Pi #1 (this machine)..."
        log_warn "System will power off in 5 seconds..."
        sleep 5
        sudo shutdown -h now
    else
        log_info "Shutting down Pi #1 (pi-voice)..."
        if check_host "$PI_VOICE_IP"; then
            ssh -o ConnectTimeout=5 "$PI_USER@$PI_VOICE_IP" "sudo shutdown -h now" 2>/dev/null &
            log_success "Pi #1 shutdown initiated"
        else
            log_warn "Pi #1 not reachable"
        fi
    fi

    log_success "Shutdown sequence complete"
    log_info "Wait for LED activity to stop before turning off power supply"
}

# =============================================================================
# Help
# =============================================================================

cmd_help() {
    cat << 'EOF'

Payphone-AI Operations Script

Usage: payphone-ops.sh <command>

Commands:
  status      Show full system health status
  verify      Run pre-flight verification (checks all services)
  start       Start all services in correct order
  stop        Stop payphone services gracefully
  restart     Stop then start services
  ready-call  Call the payphone to announce system ready
  watch       Live monitoring dashboard
  shutdown    Full system shutdown (both Pis)
  help        Show this help message

Configuration:
  Set environment variables or edit /etc/payphone/ops.conf:
    PI_VOICE_IP        Pi #1 IP address (default: 10.10.10.10)
    PI_OLLAMA_IP       Pi #2 IP address (default: 10.10.10.11)
    HT801_IP           HT801 ATA IP address (default: 10.10.10.12)
    PAYPHONE_EXTENSION Extension to call for ready announcement (default: 100)
    OLLAMA_MODEL       LLM model name (default: llama3.2:3b)

Examples:
  ./payphone-ops.sh status          # Check system health
  ./payphone-ops.sh verify          # Verify all services ready
  ./payphone-ops.sh start           # Start services and optionally call
  ./payphone-ops.sh ready-call      # Call payphone with ready message
  ./payphone-ops.sh shutdown        # Graceful full shutdown

EOF
}

# =============================================================================
# Main
# =============================================================================

main() {
    local command="${1:-help}"

    case "$command" in
        status)
            cmd_status
            ;;
        verify)
            cmd_verify
            ;;
        start)
            cmd_start
            ;;
        stop)
            cmd_stop
            ;;
        restart)
            cmd_restart
            ;;
        ready-call|readycall|call)
            cmd_ready_call
            ;;
        watch|monitor)
            cmd_watch
            ;;
        shutdown|poweroff)
            cmd_shutdown
            ;;
        help|--help|-h)
            cmd_help
            ;;
        *)
            log_error "Unknown command: $command"
            cmd_help
            exit 1
            ;;
    esac
}

main "$@"
