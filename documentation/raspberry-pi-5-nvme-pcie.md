# Raspberry Pi 5 NVMe Storage & PCIe Options

## PCIe Interface Overview

The Raspberry Pi 5 introduces an external PCIe interface for the first time on a consumer Pi board.

### Specifications

| Specification | Details |
|---------------|---------|
| Interface | PCIe 2.0 x1 (single lane) |
| Connector | 16-pin, 0.5mm pitch FPC |
| Official Speed | Gen 2.0 (5 GT/s) |
| Unofficial Speed | Gen 3.0 (8 GT/s) - works but unsupported |
| Theoretical Bandwidth | 500 MB/s (Gen 2), ~900 MB/s (Gen 3) |

### PCIe Lane Allocation

The Pi 5 has 5 active PCIe lanes total:
- **4 lanes** → RP1 chip (USB, Ethernet, GPIO, MIPI)
- **1 lane** → External PCIe connector (for NVMe, etc.)

### Gen 3 Mode (Unofficial)

Gen 3 can be enabled for ~2x speed improvement, though it's not officially supported.

```bash
# Add to /boot/firmware/config.txt
dtparam=pciex1_gen=3
```

**Performance difference**:
| Mode | Read Speed | Write Speed |
|------|------------|-------------|
| Gen 2 (default) | ~450 MB/s | ~380 MB/s |
| Gen 3 (unofficial) | ~850 MB/s | ~720 MB/s |

## NVMe Adapter Options

### Official: Raspberry Pi M.2 HAT+

The official adapter for connecting M.2 NVMe drives.

| Specification | Details |
|---------------|---------|
| Supported Sizes | M.2 2230, 2242 |
| Key Type | M-key |
| Interface | PCIe 2.0 x1 |
| Max Speed | 500 MB/s |
| SUSCLK | Built-in 32.768 kHz oscillator |
| Price | ~$12 |

**Features**:
- HAT+ compliant (auto-detection, no config needed)
- Mounts on top of Pi 5
- Compatible with Active Cooler
- Includes mounting hardware and stacking header

### Official: Raspberry Pi SSD Kit

Bundle of M.2 HAT+ with official Raspberry Pi NVMe SSD.

| Capacity | SSD Price | Kit Price |
|----------|-----------|-----------|
| 256GB | $30 | $40 |
| 512GB | $45 | $55 |

**SSD Specifications**:
| Spec | Details |
|------|---------|
| Form Factor | M.2 2230 |
| Interface | PCIe Gen 3, NVMe 1.4 |
| 4K Random Read | 40,000 IOPS |
| 4K Random Write | 70,000 IOPS |
| Operating Temp | 0°C to 50°C |
| Production Lifetime | Until January 2032 |

### Pimoroni NVMe Base

Budget-friendly option that mounts underneath the Pi.

| Specification | Details |
|---------------|---------|
| Supported Sizes | M.2 2230 to 2280 |
| Key Type | M-key |
| Mounting | Under the Pi 5 |
| GPIO Access | Full access preserved |
| Price | ~$14 |

**Advantages**:
- Supports larger 2280 drives
- Leaves top of Pi free for other HATs
- Follows Raspberry Pi PIP design guidelines
- Very affordable

### Pimoroni NVMe Base Duo

Dual-drive version for redundancy or expanded storage.

| Specification | Details |
|---------------|---------|
| Drive Slots | 2x M.2 (M-key) |
| Supported Sizes | 2230 to 2280 |
| Bandwidth | ~450 MB/s total (~220 MB/s per drive) |
| Use Cases | RAID, NAS, backup |
| Price | ~$25 |

**Note**: Drives share bandwidth via PCIe switch.

### Pineberry Pi HatDrive

| Model | Form Factor | Price |
|-------|-------------|-------|
| HatDrive! Top | 2230/2242 | ~$22 |
| HatDrive! Bottom | Up to 2280 | ~$28 |

### Third-Party Options

| Manufacturer | Notable Products |
|--------------|------------------|
| Geekworm | X1001, X1003, X1004 |
| GeeekPi | Various with case integration |
| 52Pi | Multiple form factors |
| Waveshare | PCIe to M.2 adapters |

## NVMe Compatibility

### Important Limitations

- **NVMe only**: M.2 SATA drives do NOT work
- **M-key required**: Most adapters use M-key slot
- **Some drives incompatible**: See list below

### Known Problematic Drives

| Drive | Issue |
|-------|-------|
| WD Green/Blue/SN350/SN550/SN850/X | Controller incompatibility |
| WD SN530 (especially 2242) | Boot issues |
| Drives with MAP1202 controller | Not Gen 2 compatible |
| Drives with Polaris controller | General issues |
| Corsair MP600 | Phison controller issues |
| Lexar NM620 | May need Gen 2 mode only |
| Any M.2 SATA drive | Not supported at all |

### Known Working Drives

| Drive | Notes |
|-------|-------|
| Samsung 980 / 980 Pro | Reliable |
| Samsung 990 EVO | Good performance |
| Crucial P310 | Works well |
| WD Black SN750 SE | Has Phison controller (OK) |
| Intel Optane | Excellent random I/O |
| Raspberry Pi Official SSD | Guaranteed compatible |
| Kioxia Exceria G2 | Tested working |

### Troubleshooting Incompatible Drives

1. **Update bootloader firmware**:
   ```bash
   sudo rpi-eeprom-update -a
   sudo reboot
   ```

2. **Try forcing Gen 3** (some drives need it):
   ```bash
   # Add to /boot/firmware/config.txt
   dtparam=pciex1_gen=3
   ```

3. **Check drive firmware**: Some WD drives fixed via firmware update

## Performance Benchmarks

### Speed Comparison

| Storage Type | Read | Write |
|--------------|------|-------|
| microSD (good) | ~90 MB/s | ~30 MB/s |
| USB 3.0 SSD | ~360 MB/s | ~250 MB/s |
| NVMe (Gen 2) | ~450 MB/s | ~380 MB/s |
| NVMe (Gen 3) | ~850 MB/s | ~720 MB/s |

**NVMe is up to 30x faster than microSD for writes.**

### Real-World Benchmarks (Pimoroni NVMe Base)

| Test | Gen 2 | Gen 3 |
|------|-------|-------|
| dd read | 443 MB/s | 837 MB/s |
| dd write | 384 MB/s | 723 MB/s |
| fio 4K random read | ~40K IOPS | ~60K IOPS |

### Best Performers

**Intel Optane drives** show exceptional random I/O performance due to their unique memory technology - they're often the fastest drives on Pi 5 despite being older.

### Benchmark Resources

- [pibenchmarks.com](https://pibenchmarks.com/) - 100,000+ community benchmarks
- [Jeff Geerling's PCIe Testing](https://www.jeffgeerling.com/blog/2023/testing-pcie-on-raspberry-pi-5)

## Boot from NVMe

### Prerequisites

1. **Updated firmware**: Run `sudo rpi-eeprom-update -a`
2. **HAT+ adapter**: Official M.2 HAT+ auto-enables PCIe
3. **Non-HAT+ adapter**: May need `PCIE_PROBE=1` in EEPROM

### Boot Order Configuration

```bash
# Edit EEPROM config
sudo rpi-eeprom-config --edit

# Set boot order (6 = NVMe first)
BOOT_ORDER=0xf416
```

Boot order codes:
| Code | Device |
|------|--------|
| 1 | SD Card |
| 2 | Network |
| 4 | USB |
| 6 | NVMe |
| f | Loop/retry |

### Config.txt Settings

```bash
# /boot/firmware/config.txt

# Enable PCIe (not needed if booting from NVMe)
dtparam=pciex1

# Force Gen 3 speed (optional, unofficial)
dtparam=pciex1_gen=3

# For non-HAT+ adapters (Pineberry, etc.)
# Add to EEPROM, not config.txt:
# PCIE_PROBE=1
```

### Cloning SD to NVMe

```bash
# Using SD Card Copier (GUI)
# Main Menu → Accessories → SD Card Copier

# Or using dd
sudo dd if=/dev/mmcblk0 of=/dev/nvme0n1 bs=4M status=progress
```

## Other PCIe Accessories

### Coral TPU (M.2)

AI accelerator via PCIe instead of USB.

| Specification | Details |
|---------------|---------|
| Performance | ~2.6ms inference (vs 5-7ms USB) |
| Adapter | Pineboards Hat AI! or similar |
| Requirements | 4K page size kernel, Python 3.8 |

**Setup challenges**:
- Needs kernel with 4K page size
- Disable PCIe ASPM
- Modify device tree for MSI-X interrupts
- Install Python 3.8 (Coral needs 3.6-3.9)

### PCIe Switches

Allow multiple PCIe devices (e.g., NVMe + Coral TPU).

**Limitation**: Pi firmware cannot boot from NVMe behind a PCIe switch.

### Network Cards

10GbE and other network cards can work via PCIe, but:
- Limited by single PCIe lane bandwidth
- Built-in 1GbE may be sufficient for most uses

### GPUs

External GPUs are technically possible but:
- Limited to single PCIe lane
- No official driver support
- Power requirements challenging
- Generally not practical

## Recommended Configurations

### Budget Setup
| Component | Price |
|-----------|-------|
| Pimoroni NVMe Base | $14 |
| Budget 256GB NVMe | $25 |
| **Total** | ~$40 |

### Official Setup
| Component | Price |
|-----------|-------|
| Raspberry Pi SSD Kit (256GB) | $40 |
| **Total** | $40 |

### Performance Setup
| Component | Price |
|-----------|-------|
| Pimoroni NVMe Base | $14 |
| Samsung 980 Pro 500GB | $50 |
| **Total** | ~$65 |

### NAS/Server Setup
| Component | Price |
|-----------|-------|
| Pimoroni NVMe Base Duo | $25 |
| 2x 1TB NVMe drives | $100 |
| **Total** | ~$125 |

## Resources

### Official Documentation
- [M.2 HAT+ Documentation](https://www.raspberrypi.com/documentation/accessories/m2-hat-plus.html)
- [Raspberry Pi SSD Product Brief](https://datasheets.raspberrypi.com/ssd/raspberry-pi-ssd-product-brief.pdf)

### Compatibility Lists
- [Pineberry Pi NVMe Compatibility](https://docs.pineberrypi.com/nvme-compatibility-list)
- [Raspberry Pi PCIe Database](https://pipci.jeffgeerling.com/)

### Guides & Benchmarks
- [Jeff Geerling - NVMe Boot](https://www.jeffgeerling.com/blog/2023/nvme-ssd-boot-raspberry-pi-5/)
- [Jeff Geerling - PCIe Gen 3](https://www.jeffgeerling.com/blog/2023/forcing-pci-express-gen-30-speeds-on-pi-5/)
- [Pi Benchmarks](https://pibenchmarks.com/)
- [Tom's Hardware - NVMe Guide](https://www.tomshardware.com/raspberry-pi/how-to-turbo-charge-your-raspberry-pi-5-with-an-nvme-boot-drive)

### Retailers
- [Raspberry Pi Official Store](https://www.raspberrypi.com/products/)
- [Pimoroni](https://shop.pimoroni.com/)
- [Pineboards](https://pineboards.io/)
- [The Pi Hut](https://thepihut.com/)
