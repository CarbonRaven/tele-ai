# FreePBX Documentation & Best Practices

## Overview

FreePBX is an open-source web-based GUI that manages Asterisk, the most widely deployed open-source telephony platform. It provides an intuitive interface for configuring extensions, trunks, IVRs, and other PBX features.

**Current Version**: FreePBX 17 (GA as of August 2, 2024)

## FreePBX 17 Key Features

| Feature | Details |
|---------|---------|
| Operating System | Debian 12 "Bookworm" (exclusively) |
| PHP Version | PHP 8.2 (supported until December 2026) |
| Asterisk Support | Asterisk 21 (default), 20, 18 |
| NodeJS | v18.16 |
| Installation | Bash script or ISO |
| EOL Policy | Matches Debian EOL date |

### Major Changes in FreePBX 17

- **Debian-only**: No longer CentOS/RHEL based
- **Script installation**: Cloud-friendly, no physical console needed
- **Asterisk 21**: First version to support it
- **No chan_sip**: Asterisk 21 dropped chan_sip support entirely
- **Updated libraries**: jQuery, Bootstrap, security improvements

## System Requirements

### Hardware Sizing Guide

| Deployment Size | Concurrent Calls | CPU | RAM | Storage |
|-----------------|------------------|-----|-----|---------|
| Small | Up to 20 | Dual-core 2.0GHz | 4GB | 80GB |
| Medium | 20-50 | Quad-core | 8GB | 160GB |
| Large | 50-100 | 8-core | 16GB | 250GB+ |
| Enterprise | 100+ | Multi-socket | 32GB+ | 500GB+ |

### Recommended Specifications

- **CPU**: Modern x86_64 processor (Intel/AMD)
- **RAM**: 4GB minimum, 8GB+ recommended
- **Storage**: SSD strongly recommended for database performance
- **Network**: Dedicated NIC, gigabit ethernet

### Raspberry Pi Considerations

FreePBX can run on Raspberry Pi 4/5 for small deployments:

| Pi Model | Max Extensions | Max Concurrent Calls | Notes |
|----------|----------------|----------------------|-------|
| Pi 4 (4GB) | ~20 | ~5-10 | Use NVMe for storage |
| Pi 5 (8GB) | ~30-40 | ~10-15 | Better performance |

**Limitations**:
- Not officially supported by Sangoma
- Community guides available (RasPBX project)
- Use 64-bit Raspberry Pi OS
- NVMe storage strongly recommended

## Installation

### Method 1: Debian Script (Recommended)

```bash
# Start with fresh Debian 12 minimal install

# Download and run installer
wget https://github.com/FreePBX/sng_freepbx_debian_install/raw/master/sng_freepbx_debian_install.sh
chmod +x sng_freepbx_debian_install.sh
./sng_freepbx_debian_install.sh

# Follow prompts
# Access GUI at https://<server-ip>/admin
```

### Method 2: ISO Installation

Download from [freepbx.org/downloads](https://www.freepbx.org/downloads/) and boot from ISO.

### Post-Installation

1. Access web GUI at `https://<server-ip>/admin`
2. Complete initial setup wizard
3. Set admin password
4. Configure firewall
5. Update all modules

## Security Best Practices

### Critical Security Checklist

| Priority | Action | Status |
|----------|--------|--------|
| **Critical** | Set Firewall zone to "Internet" for untrusted interfaces | Required |
| **Critical** | Enable Fail2ban/Intrusion Detection | Required |
| **Critical** | Use strong extension passwords | Required |
| **High** | Disable anonymous SIP calls | Required |
| **High** | Block international calling (if not needed) | Recommended |
| **High** | Keep system updated | Required |
| **Medium** | Enable TLS/SRTP encryption | Recommended |
| **Medium** | Change default SIP port (5060) | Recommended |

### Firewall Configuration

```
Connectivity → Firewall → Interfaces
- Set external/untrusted interfaces to "Internet" zone
- Set internal/trusted interfaces to "Local" or "Trusted" zone
```

**Key Settings**:
- **Responsive Firewall**: Enable for unknown SIP sources
- **Intrusion Detection**: Enable and whitelist known IPs
- **Sync Firewall**: Enable to sync trusted IPs to whitelist

### Fail2ban / Intrusion Detection

```
Connectivity → Firewall → Intrusion Detection
- Enable Intrusion Detection
- Set ban time (default: 1800 seconds)
- Whitelist trusted IP addresses
- Enable email notifications
```

### SIP Security Settings

```
Settings → Asterisk SIP Settings
```

| Setting | Recommended Value |
|---------|-------------------|
| Allow Anonymous Inbound SIP Calls | NO |
| Allow SIP Guests | NO |
| SIP Port | Non-standard (e.g., 5160) |
| NAT | Configure properly for your network |

### TLS/SRTP Encryption

```
Settings → Asterisk SIP Settings → SIP Settings [chan_pjsip] → TLS/SSL/SRTP
```

1. Generate or import SSL certificate
2. Enable TLS transport on port 5061
3. Configure trunks and extensions to use TLS
4. Set Media Encryption to "SRTP via IN-SDP"

### Additional Security Measures

- **VPN**: Use for remote administration
- **SSH**: Disable password auth, use key-based only
- **Provisioning**: Never expose TFTP/HTTP provisioning to Internet
- **International calls**: Disable or restrict via outbound routes
- **CDR monitoring**: Watch for unusual call patterns

## SIP Trunk Configuration (PJSIP)

### Creating a PJSIP Trunk

```
Connectivity → Trunks → Add Trunk → Add SIP (chan_pjsip) Trunk
```

### General Settings

| Field | Description |
|-------|-------------|
| Trunk Name | Descriptive name |
| Outbound CallerID | Your DID number |
| Maximum Channels | Leave blank for unlimited |

### PJSIP Settings Tab

| Field | Value |
|-------|-------|
| Username | From provider |
| Secret | Password from provider |
| SIP Server | Provider's SIP server |
| SIP Server Port | 5060 (or 5061 for TLS) |
| Context | from-internal |
| Transport | UDP (or TLS for encryption) |
| Send RPID/PAI | Yes |
| RTP Symmetric | Yes |

### Codecs

Enable (in order of preference):
1. G.722 (HD voice)
2. ulaw (G.711μ)
3. alaw (G.711a)

### Firewall Whitelist

```
Connectivity → Firewall → Networks
- Add provider's SIP server IPs to Trusted zone
- Add to Intrusion Detection whitelist
```

### Outbound Routes

```
Connectivity → Outbound Routes → Add Route
```

| Field | Value |
|-------|-------|
| Route Name | Descriptive name |
| Trunk Sequence | Select your trunk |
| Dial Patterns | Configure based on dialing needs |

**Common Dial Patterns**:

| Pattern | Description |
|---------|-------------|
| `NXXNXXXXXX` | 10-digit US number |
| `1NXXNXXXXXX` | 11-digit US number with 1 |
| `011.` | International calls |
| `.` | Match all (catch-all) |

## Extension Configuration

### Creating Extensions

```
Applications → Extensions → Add Extension → Add New SIP [chan_pjsip] Extension
```

### Extension Settings

| Field | Recommendation |
|-------|----------------|
| User Extension | 3-5 digits, don't start with 1 |
| Display Name | User's name |
| Secret | Use auto-generated complex password |
| Voicemail | Enable and set PIN |

### Extension Best Practices

- Use strong, unique passwords (auto-generated)
- Enable voicemail with PIN
- Set appropriate outbound route permissions
- Configure Follow Me for remote workers
- Set up call recording if needed (compliance)

## IVR Configuration

### Creating an IVR

```
Applications → IVR → Add IVR
```

### IVR Settings

| Field | Description |
|-------|-------------|
| IVR Name | Descriptive name |
| Announcement | Main greeting recording |
| Direct Dial | Enable extension dialing (optional) |
| Timeout | Seconds before timeout action |
| Invalid Destination | Where to route invalid input |
| Timeout Destination | Where to route on timeout |

### IVR Best Practices

- Keep menus simple (3-5 options max)
- Most common option should be first
- Always provide "0 for operator" option
- Use professional recordings
- Test thoroughly before deployment

### Recording Announcements

```
Admin → System Recordings
```

- Use .wav format (8kHz, 16-bit, mono)
- Keep recordings concise
- Speak clearly and professionally
- Include after-hours announcements

## Ring Groups & Queues

### Ring Groups

```
Applications → Ring Groups → Add Ring Group
```

| Setting | Description |
|---------|-------------|
| Ring Strategy | ringall, hunt, memoryhunt, etc. |
| Ring Time | Seconds before moving to next |
| Extension List | Extensions to ring |
| Destination if no answer | Voicemail, IVR, etc. |

### Call Queues

```
Applications → Queues → Add Queue
```

For more complex call distribution with hold music, position announcements, and agent management.

## Backup & Restore

### Creating Backups

```
Admin → Backup & Restore → Add Backup
```

### Recommended Backup Contents

| Item | Include | Notes |
|------|---------|-------|
| Full Backup | Yes | Core configuration |
| System Audio | Yes | Custom recordings |
| CDR | Optional | Can be large |
| Voicemail | Yes | User messages |

### Backup Schedule

| Environment | Frequency | Retention |
|-------------|-----------|-----------|
| Production | Daily | 30 days |
| Critical | Hourly | 7 days |
| Development | Weekly | 4 weeks |

### Backup Storage

| Location | Pros | Cons |
|----------|------|------|
| Local | Fast | No disaster recovery |
| FTP/SFTP | Off-site | Requires setup |
| Cloud (S3, etc.) | Highly available | Cost |

### Restore Process

```
Admin → Backup & Restore → Restore
1. Click Browse
2. Select .tgz backup file
3. Wait for processing (may take several minutes)
4. Apply configuration
```

## Maintenance

### Regular Maintenance Tasks

| Task | Frequency |
|------|-----------|
| Update FreePBX modules | Weekly |
| Review security logs | Daily |
| Check disk space | Weekly |
| Test backups | Monthly |
| Review CDR for anomalies | Weekly |
| Update Asterisk (minor) | Monthly |

### Module Updates

```bash
# CLI method
fwconsole ma upgradeall
fwconsole reload

# Or via GUI
Admin → Module Admin → Check Online → Upgrade All
```

### Monitoring

- **Asterisk Info**: Reports → Asterisk Info
- **System Status**: Dashboard
- **CDR Reports**: Reports → CDR Reports
- **Asterisk Logs**: Reports → Asterisk Logfiles

### Database Maintenance

```bash
# Optimize MySQL tables
mysqlcheck -o --all-databases -u root -p

# Clean old CDR records (optional)
mysql asteriskcdrdb -e "DELETE FROM cdr WHERE calldate < DATE_SUB(NOW(), INTERVAL 6 MONTH);"
```

## Useful Commercial Modules

| Module | Price | Features |
|--------|-------|----------|
| SysAdmin Pro | $30 | DDNS, Email, UPS, VPN, Updates |
| Endpoint Manager | $150 | Phone provisioning |
| Call Recording Reports | $50 | Recording management |
| Paging Pro | $25 | Advanced paging |
| Parking Lot | $25 | Advanced call parking |

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Calls dropping | Check NAT settings, RTP ports |
| One-way audio | Enable RTP Symmetric, check firewall |
| Registration failures | Verify credentials, check firewall |
| Poor call quality | Check bandwidth, QoS settings |
| GUI not loading | Clear browser cache, check Apache |

### Diagnostic Commands

```bash
# Asterisk CLI
asterisk -rvvvv

# Check SIP registrations
asterisk -rx "pjsip show registrations"

# Check active channels
asterisk -rx "core show channels"

# FreePBX module status
fwconsole ma list

# Restart FreePBX
fwconsole restart
```

### Log Locations

| Log | Path |
|-----|------|
| Asterisk | /var/log/asterisk/full |
| FreePBX | /var/log/asterisk/freepbx.log |
| Apache | /var/log/apache2/ |
| Fail2ban | /var/log/fail2ban.log |

## Resources

### Official Documentation
- [FreePBX Wiki](https://sangomakb.atlassian.net/wiki/spaces/FP/)
- [FreePBX 17 Docs](https://sangomakb.atlassian.net/wiki/spaces/FP/pages/222101505/FreePBX+17)
- [FreePBX Community Forums](https://community.freepbx.org/)
- [FreePBX Downloads](https://www.freepbx.org/downloads/)

### Guides & Tutorials
- [FreePBX Getting Started](https://www.freepbx.org/get-started/)
- [Security Best Practices](https://sangomakb.atlassian.net/wiki/spaces/FCD/pages/9699445/FreePBX+Security+Best+Practices)
- [Voxtelesys FreePBX Tutorials](https://voxtelesys.com/tutorials)

### Community Resources
- [Incredible PBX](http://nerdvittles.com/) - Community distribution
- [RasPBX GitHub](https://github.com/playfultechnology/RasPBX) - Raspberry Pi guide
- [FreePBX GitHub](https://github.com/freepbx)

### Support
- [FreePBX Support Portal](https://www.freepbx.org/support/)
- [Sangoma AI Help](https://help.sangoma.com/)
