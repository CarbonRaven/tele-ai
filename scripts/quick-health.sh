#!/bin/bash
# Quick one-liner health check for tele-ai
# For Pi #1 (pi-voice) with AI HAT+ 2
# Usage: ./quick-health.sh

set -e

echo "=== tele-ai Quick Health Check ==="
echo ""

# Temperature
TEMP=$(vcgencmd measure_temp 2>/dev/null | grep -oP 'temp=\K[\d.]+' || echo "N/A")
echo "CPU Temp:    ${TEMP}°C"

# Throttling
THROTTLE=$(vcgencmd get_throttled 2>/dev/null | grep -oP 'throttled=\K0x[0-9a-fA-F]+' || echo "N/A")
if [ "$THROTTLE" = "0x0" ]; then
    echo "Throttled:   No"
else
    echo "Throttled:   YES ($THROTTLE)"
fi

# Memory
MEM_TOTAL=$(grep MemTotal /proc/meminfo | awk '{print int($2/1024)}')
MEM_AVAIL=$(grep MemAvailable /proc/meminfo | awk '{print int($2/1024)}')
MEM_USED=$((MEM_TOTAL - MEM_AVAIL))
MEM_PCT=$((MEM_USED * 100 / MEM_TOTAL))
echo "Memory:      ${MEM_USED}MB / ${MEM_TOTAL}MB (${MEM_PCT}%)"

# Disk
DISK_INFO=$(df -h / | tail -1 | awk '{print $3 " / " $2 " (" $5 ")"}')
echo "Disk (/):    $DISK_INFO"

# Hailo
if lspci 2>/dev/null | grep -q Hailo; then
    HAILO_STATUS="Available"
    if command -v hailortcli &>/dev/null; then
        HAILO_ID=$(hailortcli fw-control identify 2>/dev/null | grep -oP 'Device: \K.*' || echo "")
        [ -n "$HAILO_ID" ] && HAILO_STATUS="$HAILO_ID"
    fi
else
    HAILO_STATUS="Not detected"
fi
echo "Hailo NPU:   $HAILO_STATUS"

echo ""
echo "=== Services ==="

check_port() {
    local name=$1
    local port=$2
    if timeout 1 bash -c "echo >/dev/tcp/localhost/$port" 2>/dev/null; then
        echo "  $name (:$port): UP"
    else
        echo "  $name (:$port): DOWN"
    fi
}

check_port "Ollama" 11434
check_port "AudioSocket" 9092
check_port "openWakeWord" 10400
check_port "Whisper" 10300
check_port "Piper TTS" 10200
check_port "hailo-ollama" 8000

echo ""
