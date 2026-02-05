# Network Configuration

Complete network topology and IP assignments for the Payphone-AI system.

## Network Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PAYPHONE-AI NETWORK                                 │
│                        Subnet: 10.10.10.0/24                               │
│                        Gateway: 10.10.10.1                                 │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────┐
                              │   Router/   │
                              │   Gateway   │
                              │ 10.10.10.1 │
                              └──────┬──────┘
                                     │
                              ┌──────┴──────┐
                              │  5-Port     │
                              │  Gigabit    │
                              │  Switch     │
                              └──────┬──────┘
                                     │
            ┌────────────────────────┼────────────────────────┐
            │                        │                        │
     ┌──────┴──────┐          ┌──────┴──────┐          ┌──────┴──────┐
     │   Pi #1     │          │   Pi #2     │          │   HT801     │
     │  pi-voice   │          │  pi-ollama  │          │    ATA      │
     │10.10.10.10 │          │10.10.10.11 │          │10.10.10.12 │
     │             │          │             │          │             │
     │ + AI HAT+ 2 │          │  (standard) │          │     FXS     │
     └─────────────┘          └─────────────┘          └──────┬──────┘
                                                              │
                                                       ┌──────┴──────┐
                                                       │  Payphone   │
                                                       │  (Analog)   │
                                                       └─────────────┘
```

## IP Address Assignments

| IP Address | Device | Hostname | MAC Address | Notes |
|------------|--------|----------|-------------|-------|
| 10.10.10.1 | Router/Gateway | — | — | Upstream network |
| 10.10.10.10 | Raspberry Pi 5 #1 | pi-voice | — | Voice pipeline, FreePBX |
| 10.10.10.11 | Raspberry Pi 5 #2 | pi-ollama | — | LLM server |
| 10.10.10.12 | Grandstream HT801 v2 | ht801 | — | ATA for payphone |
| 10.10.10.13-99 | Reserved | — | — | Future expansion |

## Device Details

### Pi #1 (pi-voice) - 10.10.10.10

**Role:** Voice processing hub, telephony server

| Component | Details |
|-----------|---------|
| Hardware | Raspberry Pi 5 (16GB) + AI HAT+ 2 (Hailo-10H) |
| OS | Raspberry Pi OS Lite (64-bit) |
| Hostname | pi-voice |
| Static IP | 10.10.10.10 |

**Services:**

| Service | Port | Protocol | Description |
|---------|------|----------|-------------|
| SSH | 22 | TCP | Remote administration |
| HTTP (FreePBX) | 80 | TCP | Web GUI |
| HTTPS (FreePBX) | 443 | TCP | Secure web GUI |
| Asterisk SIP | 5060 | UDP/TCP | SIP signaling |
| Asterisk RTP | 10000-20000 | UDP | Media (voice) |
| AudioSocket | 9092 | TCP | AI voice pipeline |
| Wyoming-Whisper | 10300 | TCP | Speech-to-text (optional) |
| openWakeWord | 10400 | TCP | Wake word detection (optional) |

**Static IP Configuration** (`/etc/dhcpcd.conf`):

```
interface eth0
static ip_address=10.10.10.10/24
static routers=10.10.10.1
static domain_name_servers=10.10.10.1 8.8.8.8
```

Or with NetworkManager (`/etc/NetworkManager/system-connections/eth0.nmconnection`):

```ini
[connection]
id=eth0
type=ethernet
interface-name=eth0

[ipv4]
method=manual
address1=10.10.10.10/24,10.10.10.1
dns=10.10.10.1;8.8.8.8;

[ipv6]
method=disabled
```

---

### Pi #2 (pi-ollama) - 10.10.10.11

**Role:** LLM inference server

| Component | Details |
|-----------|---------|
| Hardware | Raspberry Pi 5 (16GB) - standard, no HAT |
| OS | Raspberry Pi OS Lite (64-bit) |
| Hostname | pi-ollama |
| Static IP | 10.10.10.11 |

**Services:**

| Service | Port | Protocol | Description |
|---------|------|----------|-------------|
| SSH | 22 | TCP | Remote administration |
| Ollama API | 11434 | TCP | LLM inference |
| TTS Server | 10200 | TCP | Remote TTS (optional) |

**Ollama Network Binding** (`/etc/systemd/system/ollama.service.d/override.conf`):

```ini
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
```

**Static IP Configuration** (`/etc/dhcpcd.conf`):

```
interface eth0
static ip_address=10.10.10.11/24
static routers=10.10.10.1
static domain_name_servers=10.10.10.1 8.8.8.8
```

---

### HT801 ATA - 10.10.10.12

**Role:** Analog Telephone Adapter - connects physical payphone to SIP

| Component | Details |
|-----------|---------|
| Hardware | Grandstream HT801 v2 |
| Static IP | 10.10.10.12 |
| Web GUI | http://10.10.10.12 |
| Default Password | admin |

**Services:**

| Service | Port | Protocol | Description |
|---------|------|----------|-------------|
| HTTP (Admin) | 80 | TCP | Web configuration |
| SIP | 5060 | UDP | SIP client to FreePBX |
| RTP | 5004+ | UDP | Media (voice) |

**Key Configuration Settings:**

| Setting | Location | Value |
|---------|----------|-------|
| IP Mode | Basic Settings > IPv4 | Static |
| IP Address | Basic Settings > IPv4 | 10.10.10.12 |
| Subnet Mask | Basic Settings > IPv4 | 255.255.255.0 |
| Gateway | Basic Settings > IPv4 | 10.10.10.1 |
| DNS Server | Basic Settings > IPv4 | 10.10.10.1 |
| SIP Server | FXS Port > Account | 10.10.10.10 |
| SIP User ID | FXS Port > Account | 100 |
| Auth ID | FXS Port > Account | 100 |
| Auth Password | FXS Port > Account | (from FreePBX extension) |
| Primary Codec | FXS Port > Audio | PCMU (G.711 u-law) |
| NAT Traversal | FXS Port > Account | No (same LAN) |

**HT801 Web GUI Access:**

```
URL: http://10.10.10.12
Default User: admin
Default Password: admin (change after setup!)
```

**Factory Reset:** Press and hold RESET button for 10 seconds

---

### Payphone (Analog)

**Role:** User interface - vintage payphone handset

| Component | Details |
|-----------|---------|
| Connection | RJ-11 to HT801 FXS port |
| Type | Standard analog telephone |
| Power | Line-powered via HT801 |

No IP configuration required - purely analog connection to HT801.

---

## Network Diagram (Physical)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PHYSICAL LAYOUT                                   │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────┐
    │                         ENCLOSURE                                   │
    │  ┌──────────────────────────────────────────────────────────────┐   │
    │  │                    SINGLE POWER SUPPLY                       │   │
    │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐          │   │
    │  │  │ Pi #1   │  │ Pi #2   │  │ HT801   │  │ Switch  │          │   │
    │  │  │ 5V/5A   │  │ 5V/5A   │  │ 5V/1A   │  │ 5V/1A   │          │   │
    │  │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘          │   │
    │  │       │            │            │            │                │   │
    │  └───────┼────────────┼────────────┼────────────┼────────────────┘   │
    │          │            │            │            │                    │
    │          └────────────┴─────┬──────┴────────────┘                    │
    │                             │                                        │
    │                      ┌──────┴──────┐                                 │
    │                      │   5-Port    │                                 │
    │                      │   Switch    │                                 │
    │                      │   (GbE)     │                                 │
    │                      └──────┬──────┘                                 │
    │                             │                                        │
    │                       To Router/LAN                                  │
    │                                                                      │
    │  ┌──────────────────────────────────────────────────────────────┐   │
    │  │                      HT801 FXS Port                          │   │
    │  │                           │                                  │   │
    │  │                     ┌─────┴─────┐                            │   │
    │  │                     │  RJ-11    │                            │   │
    │  │                     │  Cable    │                            │   │
    │  │                     └─────┬─────┘                            │   │
    │  │                           │                                  │   │
    │  │                     ┌─────┴─────┐                            │   │
    │  │                     │ PAYPHONE  │                            │   │
    │  │                     │ (Analog)  │                            │   │
    │  │                     └───────────┘                            │   │
    │  └──────────────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────────────┘
```

---

## Network Traffic Flow

### Inbound Call (Payphone to AI)

```
Payphone (analog)
    │
    │ Audio signal
    ▼
HT801 (10.10.10.12)
    │
    │ SIP INVITE + RTP
    ▼
Pi #1 FreePBX (10.10.10.10:5060)
    │
    │ AudioSocket
    ▼
Pi #1 payphone-app (10.10.10.10:9092)
    │
    │ HTTP API
    ▼
Pi #2 Ollama (10.10.10.11:11434)
    │
    │ Response
    ▼
Pi #1 payphone-app → TTS → AudioSocket → FreePBX → HT801 → Payphone
```

### Service Communication Matrix

| From | To | Port | Protocol | Purpose |
|------|-----|------|----------|---------|
| HT801 | Pi #1 | 5060/UDP | SIP | Call signaling |
| HT801 | Pi #1 | 10000-20000/UDP | RTP | Voice media |
| Pi #1 (FreePBX) | Pi #1 (payphone-app) | 9092/TCP | AudioSocket | AI processing |
| Pi #1 (payphone-app) | Pi #2 (Ollama) | 11434/TCP | HTTP | LLM inference |
| Pi #1 (payphone-app) | Pi #2 (TTS) | 10200/TCP | HTTP | Remote TTS (optional) |
| Admin | Pi #1 | 22/TCP | SSH | Management |
| Admin | Pi #2 | 22/TCP | SSH | Management |
| Admin | Pi #1 | 443/TCP | HTTPS | FreePBX GUI |
| Admin | HT801 | 80/TCP | HTTP | ATA config |

---

## Firewall Rules

### Pi #1 (pi-voice)

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow FreePBX Web
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow SIP
sudo ufw allow 5060/udp

# Allow RTP
sudo ufw allow 10000:20000/udp

# Allow AudioSocket (local only recommended)
sudo ufw allow from 10.10.10.0/24 to any port 9092

# Enable firewall
sudo ufw enable
```

### Pi #2 (pi-ollama)

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow Ollama from Pi #1 only
sudo ufw allow from 10.10.10.10 to any port 11434

# Allow TTS server from Pi #1 only (if used)
sudo ufw allow from 10.10.10.10 to any port 10200

# Enable firewall
sudo ufw enable
```

---

## DNS / Hostname Resolution

Add to `/etc/hosts` on each Pi for reliable name resolution:

```
# Payphone-AI Network
10.10.10.10    pi-voice
10.10.10.11    pi-ollama
10.10.10.12    ht801
```

---

## DHCP Reservations (Alternative to Static)

If using DHCP with reservations on your router, configure:

| Hostname | MAC Address | Reserved IP |
|----------|-------------|-------------|
| pi-voice | (from Pi #1) | 10.10.10.10 |
| pi-ollama | (from Pi #2) | 10.10.10.11 |
| ht801 | (from HT801) | 10.10.10.12 |

Get MAC addresses:

```bash
# On each Pi
ip link show eth0 | grep ether

# On HT801: Check Status page in web GUI
```

---

## Troubleshooting

### Connectivity Tests

```bash
# From Pi #1, verify all devices reachable
ping -c 1 10.10.10.11    # Pi #2
ping -c 1 10.10.10.12    # HT801
ping -c 1 10.10.10.1     # Gateway

# Check Ollama accessible
curl -s http://10.10.10.11:11434/api/tags | jq '.models[].name'

# Check HT801 web interface
curl -s -o /dev/null -w "%{http_code}" http://10.10.10.12

# Check SIP registration from FreePBX
asterisk -rx "pjsip show endpoints"
```

### Common Issues

| Issue | Check | Fix |
|-------|-------|-----|
| Pi not reachable | Cable, switch port LEDs | Reseat cable, check switch |
| HT801 not registering | SIP credentials, IP | Verify settings in HT801 GUI |
| Ollama connection refused | Firewall, OLLAMA_HOST | Check binding and ufw rules |
| No audio | RTP ports, NAT | Verify RTP range open |

---

## Expansion Notes

Reserved IP ranges for future use:

| Range | Purpose |
|-------|---------|
| 10.10.10.13-19 | Additional Pis |
| 10.10.10.20-29 | Additional ATAs/phones |
| 10.10.10.30-39 | IoT/sensors |
| 10.10.10.100-199 | DHCP pool |
| 10.10.10.200-254 | Infrastructure |
