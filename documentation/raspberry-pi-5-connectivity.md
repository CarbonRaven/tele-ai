# Raspberry Pi 5 Connectivity & Interfaces

## Wireless Connectivity

### Wi-Fi

| Specification | Details |
|---------------|---------|
| Standard | 802.11ac (Wi-Fi 5) |
| Frequencies | 2.4 GHz and 5.0 GHz dual-band |
| Features | High-speed wireless, good for streaming and IoT |

### Bluetooth

| Specification | Details |
|---------------|---------|
| Version | Bluetooth 5.0 |
| Features | Bluetooth Low Energy (BLE) |
| Use Cases | IoT peripherals, keyboards, mice |

## Wired Networking

### Ethernet

| Specification | Details |
|---------------|---------|
| Speed | Gigabit Ethernet |
| PoE Support | Yes (requires PoE+ HAT) |
| Use Cases | Servers, NAS, reliable networking |

## USB Ports

| Port Type | Count | Speed | Use Cases |
|-----------|-------|-------|-----------|
| USB 3.0 | 2 | 5 Gbps (simultaneous) | External storage, cameras, fast peripherals |
| USB 2.0 | 2 | 480 Mbps | Keyboards, mice, basic peripherals |

**Note**: Both USB 3.0 ports can operate at full 5Gbps simultaneously (improved from Pi 4).

## Display Interfaces

### HDMI

| Specification | Details |
|---------------|---------|
| Ports | 2x Micro-HDMI 2.1 |
| Resolution | Dual 4K @ 60Hz |
| Features | HDR support, 10-bit color depth |
| Use Cases | Dual monitor setup, media centers |

## Camera/Display Connectors

| Specification | Details |
|---------------|---------|
| Type | MIPI CSI-2 / DSI |
| Count | 2x 4-lane connectors |
| Features | Can connect 2 cameras or 2 displays simultaneously |
| Use Cases | Stereo vision, depth mapping, computer vision |

### Comparison with Pi 4

| Feature | Pi 4 | Pi 5 |
|---------|------|------|
| Camera Connectors | 1 | 2 |
| Display Connectors | 1 | 2 |
| Lane Configuration | 2-lane | 4-lane |

## PCIe Interface (New in Pi 5)

| Specification | Details |
|---------------|---------|
| Version | PCIe 2.0 x1 |
| Use Cases | NVMe SSDs, network cards, other PCIe peripherals |
| Speed | Up to 5 GT/s |

**Note**: This is a new feature exclusive to Pi 5, enabling high-speed peripheral connections.

## Audio

| Output Type | Details |
|-------------|---------|
| HDMI | Digital audio via HDMI |
| PWM | Stereo PWM audio output via GPIO |
| I2S | Digital audio interface for DACs/ADCs |

## Communication Protocols Supported

| Protocol | Availability |
|----------|--------------|
| I2C | 4x interfaces |
| SPI | 6x interfaces |
| UART | 5x interfaces |
| I2S | 2x interfaces |
| PWM | 4-channel output |

## Power Input

| Specification | Details |
|---------------|---------|
| Connector | USB-C |
| Voltage | 5V |
| Current | 5A recommended |
| PD Support | USB Power Delivery enabled |
| Official PSU | 27W USB-C PD Power Supply |
