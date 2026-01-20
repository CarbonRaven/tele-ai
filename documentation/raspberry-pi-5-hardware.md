# Raspberry Pi 5 Hardware Specifications

## Processor (CPU)

| Specification | Details |
|---------------|---------|
| SoC | Broadcom BCM2712 |
| CPU | Quad-core 64-bit Arm Cortex-A76 |
| Clock Speed | 2.4 GHz |
| L2 Cache | 512KB per core |
| L3 Cache | 2MB shared |
| Features | Cryptography extensions |
| Performance | 2-3x faster than Raspberry Pi 4 |

### Comparison with Pi 4

| Feature | Pi 4 | Pi 5 |
|---------|------|------|
| CPU Core | Cortex-A72 | Cortex-A76 |
| Clock Speed | 1.8 GHz | 2.4 GHz |

## Graphics (GPU)

| Specification | Details |
|---------------|---------|
| GPU | VideoCore VII |
| Clock Speed | 800 MHz |
| OpenGL | OpenGL ES 3.1 |
| Vulkan | Vulkan 1.2 |
| Video Decode | 4Kp60 HEVC decoder |
| Display Output | Dual 4Kp60 HDMI with HDR support |

### Comparison with Pi 4

| Feature | Pi 4 | Pi 5 |
|---------|------|------|
| GPU | VideoCore VI | VideoCore VII |
| Clock Speed | 500 MHz | 800 MHz |
| Max Resolution | 4K @ 30Hz | 4K @ 60Hz |

## Memory (RAM)

| Specification | Details |
|---------------|---------|
| Type | LPDDR4X-4267 SDRAM |
| Speed | 4267 MHz |
| Available Options | 4GB, 8GB, 16GB |

### Comparison with Pi 4

| Feature | Pi 4 | Pi 5 |
|---------|------|------|
| RAM Type | LPDDR4-3200 | LPDDR4X-4267 |
| Max Capacity | 8GB | 16GB |

## Storage

| Storage Type | Details |
|--------------|---------|
| Primary | MicroSD card slot (SDR104 mode) |
| Secondary | NVMe SSD via PCIe adapter |
| External | USB boot capability |
| SD Card Speed | ~2x faster than Pi 4 (SDR104) |

## Custom Silicon: RP1 Southbridge

The RP1 is Raspberry Pi's first custom I/O controller chip, providing:

- Bulk of I/O capabilities for the Pi 5
- Improved peripheral performance
- Enhanced GPIO functionality
- Better power management

## Power Requirements

| Specification | Details |
|---------------|---------|
| Input | USB-C PD (Power Delivery) |
| Voltage | 5V |
| Current | 5A (recommended) |
| Power Supply | 27W USB-C PD Power Supply |

### USB Power Budget

| PSU Type | USB Port Power Limit |
|----------|---------------------|
| Standard | 600mA total |
| USB-C PD PSU | 1.6A total |

## Thermal Management

- Built-in fan header on the board
- Fan mounting points included
- Active cooling recommended for sustained workloads
- Official Active Cooler available

## Real-Time Clock (RTC)

- New feature for Pi 5
- Requires external battery backup
- Maintains time when powered off
- Useful for time-critical applications

## Power Button

- New feature for Pi 5
- On-board power button
- Enables safe shutdown without unplugging
