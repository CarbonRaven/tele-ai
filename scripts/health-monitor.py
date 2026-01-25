#!/usr/bin/env python3
"""
Health and capacity monitoring script for tele-ai Raspberry Pi 5 setup.

Monitors:
- CPU temperature and throttling status
- CPU/memory/disk usage
- Hailo NPU status (if available)
- Voice pipeline service health (Ollama, etc.)

Usage:
    ./health-monitor.py                    # One-shot console output
    ./health-monitor.py --watch            # Continuous monitoring (2s refresh)
    ./health-monitor.py --json             # JSON output for parsing
    ./health-monitor.py --log              # Append to log file
    ./health-monitor.py --watch --log      # Continuous logging
"""

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


# ANSI colors for terminal output
class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


@dataclass
class CPUMetrics:
    temperature_c: float
    throttled: bool
    throttle_flags: str
    usage_percent: float
    frequency_mhz: int
    core_count: int


@dataclass
class MemoryMetrics:
    total_mb: int
    used_mb: int
    available_mb: int
    percent_used: float


@dataclass
class DiskMetrics:
    total_gb: float
    used_gb: float
    free_gb: float
    percent_used: float
    mount_point: str


@dataclass
class HailoMetrics:
    available: bool
    device_id: Optional[str] = None
    fw_version: Optional[str] = None
    temperature_c: Optional[float] = None
    power_w: Optional[float] = None
    utilization_percent: Optional[float] = None
    error: Optional[str] = None


@dataclass
class ServiceStatus:
    name: str
    port: int
    healthy: bool
    response_time_ms: Optional[float] = None
    error: Optional[str] = None


@dataclass
class HealthReport:
    timestamp: str
    hostname: str
    uptime_seconds: int
    cpu: CPUMetrics
    memory: MemoryMetrics
    disk: DiskMetrics
    hailo: HailoMetrics
    services: list[ServiceStatus]


def run_cmd(cmd: list[str], timeout: int = 5) -> tuple[bool, str]:
    """Run a command and return (success, output)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode == 0, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except FileNotFoundError:
        return False, "command not found"
    except Exception as e:
        return False, str(e)


def get_cpu_metrics() -> CPUMetrics:
    """Gather CPU temperature, throttling, usage, and frequency."""
    # Temperature
    temp = 0.0
    success, output = run_cmd(["vcgencmd", "measure_temp"])
    if success:
        match = re.search(r"temp=([\d.]+)", output)
        if match:
            temp = float(match.group(1))
    else:
        # Fallback to thermal zone
        try:
            with open("/sys/class/thermal/thermal_zone0/temp") as f:
                temp = int(f.read().strip()) / 1000.0
        except:
            pass

    # Throttling
    throttled = False
    throttle_flags = "0x0"
    success, output = run_cmd(["vcgencmd", "get_throttled"])
    if success:
        match = re.search(r"throttled=(0x[0-9a-fA-F]+)", output)
        if match:
            throttle_flags = match.group(1)
            throttled = int(throttle_flags, 16) != 0

    # CPU frequency
    freq_mhz = 0
    success, output = run_cmd(["vcgencmd", "measure_clock", "arm"])
    if success:
        match = re.search(r"=(\d+)", output)
        if match:
            freq_mhz = int(match.group(1)) // 1_000_000
    else:
        # Fallback
        try:
            with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq") as f:
                freq_mhz = int(f.read().strip()) // 1000
        except:
            pass

    # CPU usage (1-second sample)
    usage = 0.0
    try:
        with open("/proc/stat") as f:
            line1 = f.readline()
        time.sleep(0.1)
        with open("/proc/stat") as f:
            line2 = f.readline()

        def parse_cpu(line):
            parts = line.split()[1:8]
            return [int(x) for x in parts]

        vals1 = parse_cpu(line1)
        vals2 = parse_cpu(line2)

        idle1, idle2 = vals1[3], vals2[3]
        total1, total2 = sum(vals1), sum(vals2)

        idle_delta = idle2 - idle1
        total_delta = total2 - total1

        if total_delta > 0:
            usage = 100.0 * (1.0 - idle_delta / total_delta)
    except:
        pass

    core_count = os.cpu_count() or 4

    return CPUMetrics(
        temperature_c=temp,
        throttled=throttled,
        throttle_flags=throttle_flags,
        usage_percent=round(usage, 1),
        frequency_mhz=freq_mhz,
        core_count=core_count
    )


def get_memory_metrics() -> MemoryMetrics:
    """Get memory usage from /proc/meminfo."""
    meminfo = {}
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    key = parts[0].rstrip(":")
                    value = int(parts[1])  # in kB
                    meminfo[key] = value
    except:
        pass

    total_kb = meminfo.get("MemTotal", 0)
    available_kb = meminfo.get("MemAvailable", 0)
    used_kb = total_kb - available_kb

    total_mb = total_kb // 1024
    used_mb = used_kb // 1024
    available_mb = available_kb // 1024
    percent = (used_kb / total_kb * 100) if total_kb > 0 else 0

    return MemoryMetrics(
        total_mb=total_mb,
        used_mb=used_mb,
        available_mb=available_mb,
        percent_used=round(percent, 1)
    )


def get_disk_metrics(mount_point: str = "/") -> DiskMetrics:
    """Get disk usage for a mount point."""
    try:
        usage = shutil.disk_usage(mount_point)
        total_gb = usage.total / (1024**3)
        used_gb = usage.used / (1024**3)
        free_gb = usage.free / (1024**3)
        percent = (usage.used / usage.total * 100) if usage.total > 0 else 0
    except:
        total_gb = used_gb = free_gb = percent = 0

    return DiskMetrics(
        total_gb=round(total_gb, 1),
        used_gb=round(used_gb, 1),
        free_gb=round(free_gb, 1),
        percent_used=round(percent, 1),
        mount_point=mount_point
    )


def get_hailo_metrics() -> HailoMetrics:
    """Get Hailo NPU status using hailortcli."""
    # Check if Hailo device exists
    success, output = run_cmd(["lspci"], timeout=2)
    if not success or "Hailo" not in output:
        return HailoMetrics(available=False, error="No Hailo device in lspci")

    # Get device identification
    success, output = run_cmd(["hailortcli", "fw-control", "identify"], timeout=5)
    if not success:
        return HailoMetrics(available=False, error=f"hailortcli failed: {output}")

    device_id = None
    fw_version = None

    for line in output.split("\n"):
        if "Device:" in line:
            device_id = line.split(":")[-1].strip()
        if "Firmware Version:" in line or "FW Version:" in line:
            fw_version = line.split(":")[-1].strip()

    # Try to get temperature/power from monitor (may not work in all setups)
    temp = None
    power = None
    utilization = None

    # hailortcli monitor runs interactively, so we try a quick query
    success, output = run_cmd(["hailortcli", "fw-control", "identify"], timeout=2)
    # Note: Full monitoring requires running `hailortcli monitor` interactively
    # or parsing hailo logs. For now we just confirm device is accessible.

    return HailoMetrics(
        available=True,
        device_id=device_id,
        fw_version=fw_version,
        temperature_c=temp,
        power_w=power,
        utilization_percent=utilization
    )


def check_service(name: str, host: str, port: int, timeout: float = 2.0) -> ServiceStatus:
    """Check if a TCP service is responding."""
    start = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        elapsed_ms = (time.time() - start) * 1000
        sock.close()

        if result == 0:
            return ServiceStatus(
                name=name,
                port=port,
                healthy=True,
                response_time_ms=round(elapsed_ms, 1)
            )
        else:
            return ServiceStatus(
                name=name,
                port=port,
                healthy=False,
                error=f"Connection refused (errno {result})"
            )
    except socket.timeout:
        return ServiceStatus(name=name, port=port, healthy=False, error="Timeout")
    except Exception as e:
        return ServiceStatus(name=name, port=port, healthy=False, error=str(e))


def check_http_service(name: str, url: str, timeout: float = 2.0) -> ServiceStatus:
    """Check if an HTTP service is responding."""
    import urllib.request
    import urllib.error

    # Extract port from URL for the ServiceStatus
    port = 80
    if ":" in url.split("//")[-1]:
        try:
            port = int(url.split(":")[-1].split("/")[0])
        except:
            pass

    start = time.time()
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as response:
            elapsed_ms = (time.time() - start) * 1000
            return ServiceStatus(
                name=name,
                port=port,
                healthy=response.status < 500,
                response_time_ms=round(elapsed_ms, 1)
            )
    except urllib.error.URLError as e:
        return ServiceStatus(name=name, port=port, healthy=False, error=str(e.reason))
    except Exception as e:
        return ServiceStatus(name=name, port=port, healthy=False, error=str(e))


def get_uptime() -> int:
    """Get system uptime in seconds."""
    try:
        with open("/proc/uptime") as f:
            return int(float(f.read().split()[0]))
    except:
        return 0


def collect_health_report() -> HealthReport:
    """Collect all health metrics into a report."""

    # Define services to check based on tele-ai architecture
    services = [
        check_http_service("Ollama", "http://localhost:11434/api/tags"),
        check_service("AudioSocket", "localhost", 9092),
        check_service("openWakeWord", "localhost", 10400),
        check_service("Whisper-Wyoming", "localhost", 10300),
        check_service("Piper-TTS", "localhost", 10200),
        check_http_service("hailo-ollama", "http://localhost:8000/api/tags"),
    ]

    return HealthReport(
        timestamp=datetime.now().isoformat(),
        hostname=socket.gethostname(),
        uptime_seconds=get_uptime(),
        cpu=get_cpu_metrics(),
        memory=get_memory_metrics(),
        disk=get_disk_metrics("/"),
        hailo=get_hailo_metrics(),
        services=services
    )


def format_uptime(seconds: int) -> str:
    """Format uptime as human-readable string."""
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


def print_report(report: HealthReport, use_color: bool = True) -> None:
    """Print health report to console with formatting."""
    c = Colors if use_color else type("NoColor", (), {k: "" for k in dir(Colors)})()

    print(f"\n{c.BOLD}═══════════════════════════════════════════════════════════════{c.RESET}")
    print(f"{c.BOLD}  tele-ai Health Monitor  │  {report.hostname}  │  up {format_uptime(report.uptime_seconds)}{c.RESET}")
    print(f"{c.BOLD}═══════════════════════════════════════════════════════════════{c.RESET}")
    print(f"  {c.CYAN}Timestamp:{c.RESET} {report.timestamp}")

    # CPU Section
    cpu = report.cpu
    temp_color = c.GREEN if cpu.temperature_c < 70 else (c.YELLOW if cpu.temperature_c < 80 else c.RED)
    throttle_color = c.RED if cpu.throttled else c.GREEN
    throttle_status = "YES" if cpu.throttled else "No"

    print(f"\n{c.BOLD}  CPU{c.RESET}")
    print(f"    Temperature:  {temp_color}{cpu.temperature_c:.1f}°C{c.RESET}")
    print(f"    Throttled:    {throttle_color}{throttle_status}{c.RESET} ({cpu.throttle_flags})")
    print(f"    Usage:        {cpu.usage_percent:.1f}%")
    print(f"    Frequency:    {cpu.frequency_mhz} MHz")
    print(f"    Cores:        {cpu.core_count}")

    # Memory Section
    mem = report.memory
    mem_color = c.GREEN if mem.percent_used < 70 else (c.YELLOW if mem.percent_used < 85 else c.RED)

    print(f"\n{c.BOLD}  Memory{c.RESET}")
    print(f"    Used:         {mem_color}{mem.used_mb} MB / {mem.total_mb} MB ({mem.percent_used:.1f}%){c.RESET}")
    print(f"    Available:    {mem.available_mb} MB")

    # Disk Section
    disk = report.disk
    disk_color = c.GREEN if disk.percent_used < 70 else (c.YELLOW if disk.percent_used < 85 else c.RED)

    print(f"\n{c.BOLD}  Disk ({disk.mount_point}){c.RESET}")
    print(f"    Used:         {disk_color}{disk.used_gb:.1f} GB / {disk.total_gb:.1f} GB ({disk.percent_used:.1f}%){c.RESET}")
    print(f"    Free:         {disk.free_gb:.1f} GB")

    # Hailo Section
    hailo = report.hailo
    hailo_status = c.GREEN + "Available" + c.RESET if hailo.available else c.YELLOW + "Not Available" + c.RESET

    print(f"\n{c.BOLD}  Hailo NPU{c.RESET}")
    print(f"    Status:       {hailo_status}")
    if hailo.available:
        if hailo.device_id:
            print(f"    Device:       {hailo.device_id}")
        if hailo.fw_version:
            print(f"    Firmware:     {hailo.fw_version}")
        if hailo.temperature_c:
            print(f"    Temperature:  {hailo.temperature_c:.1f}°C")
        if hailo.utilization_percent is not None:
            print(f"    Utilization:  {hailo.utilization_percent:.1f}%")
    elif hailo.error:
        print(f"    Error:        {c.YELLOW}{hailo.error}{c.RESET}")

    # Services Section
    print(f"\n{c.BOLD}  Services{c.RESET}")
    for svc in report.services:
        if svc.healthy:
            status = f"{c.GREEN}●{c.RESET} UP"
            latency = f"({svc.response_time_ms:.0f}ms)" if svc.response_time_ms else ""
        else:
            status = f"{c.RED}●{c.RESET} DOWN"
            latency = f"- {svc.error}" if svc.error else ""
        print(f"    {svc.name:18} :{svc.port:<5}  {status} {latency}")

    print(f"\n{c.BOLD}═══════════════════════════════════════════════════════════════{c.RESET}\n")


def log_report(report: HealthReport, log_file: Path) -> None:
    """Append report as JSON line to log file."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a") as f:
        f.write(json.dumps(asdict(report)) + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Health monitoring for tele-ai Raspberry Pi setup"
    )
    parser.add_argument(
        "--watch", "-w",
        action="store_true",
        help="Continuous monitoring mode (refresh every 2s)"
    )
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=2,
        help="Refresh interval in seconds for watch mode (default: 2)"
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output as JSON instead of formatted text"
    )
    parser.add_argument(
        "--log", "-l",
        action="store_true",
        help="Append JSON logs to file"
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=Path("/var/log/tele-ai/health.jsonl"),
        help="Log file path (default: /var/log/tele-ai/health.jsonl)"
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output"
    )

    args = parser.parse_args()
    use_color = not args.no_color and sys.stdout.isatty()

    try:
        while True:
            report = collect_health_report()

            if args.json:
                print(json.dumps(asdict(report), indent=2))
            else:
                if args.watch:
                    # Clear screen for watch mode
                    print("\033[2J\033[H", end="")
                print_report(report, use_color=use_color)

            if args.log:
                try:
                    log_report(report, args.log_file)
                except PermissionError:
                    # Fallback to user's home directory
                    fallback = Path.home() / ".tele-ai" / "health.jsonl"
                    log_report(report, fallback)
                    if not args.json:
                        print(f"  (Logging to {fallback} - no write access to {args.log_file})")

            if not args.watch:
                break

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\nMonitoring stopped.")
        sys.exit(0)


if __name__ == "__main__":
    main()
