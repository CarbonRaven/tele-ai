# Raspberry Pi 5 GPIO Pinout Reference

## Overview

The Raspberry Pi 5 features a standard 40-pin GPIO (General Purpose Input/Output) header, maintaining backward compatibility with previous Pi models and HATs.

## RP1 GPIO Controller

The Pi 5 uses the new **RP1** I/O controller chip for GPIO management, which provides:

- 28 multi-functional GPIO pins on the 40-pin header
- Single electrical bank (VDDIO0)
- Can be powered at 1.8V or 3.3V (timings specified at 3.3V)
- 5V tolerant when RP1 is powered (3.63V when unpowered)

## Important Safety Notes

- **Logic Level**: 3.3V (connecting 5V signals can damage the Pi)
- **Per-pin current**: ~16mA maximum
- **Total GPIO current**: 50mA across all pins
- **3.3V regulator**: 500mA total capacity

## Complete 40-Pin Header Pinout

| Pin | GPIO | Function | | Pin | GPIO | Function |
|-----|------|----------|---|-----|------|----------|
| 1 | - | 3.3V Power | | 2 | - | 5V Power |
| 3 | GPIO2 | I2C SDA | | 4 | - | 5V Power |
| 5 | GPIO3 | I2C SCL | | 6 | - | Ground |
| 7 | GPIO4 | Digital I/O | | 8 | GPIO14 | UART TXD |
| 9 | - | Ground | | 10 | GPIO15 | UART RXD |
| 11 | GPIO17 | Digital I/O | | 12 | GPIO18 | PWM0 |
| 13 | GPIO27 | Digital I/O | | 14 | - | Ground |
| 15 | GPIO22 | Digital I/O | | 16 | GPIO23 | Digital I/O |
| 17 | - | 3.3V Power | | 18 | GPIO24 | Digital I/O |
| 19 | GPIO10 | SPI MOSI | | 20 | - | Ground |
| 21 | GPIO9 | SPI MISO | | 22 | GPIO25 | Digital I/O |
| 23 | GPIO11 | SPI SCLK | | 24 | GPIO8 | SPI CE0 |
| 25 | - | Ground | | 26 | GPIO7 | SPI CE1 |
| 27 | GPIO0 | ID EEPROM SDA | | 28 | GPIO1 | ID EEPROM SCL |
| 29 | GPIO5 | Digital I/O | | 30 | - | Ground |
| 31 | GPIO6 | Digital I/O | | 32 | GPIO12 | PWM0 |
| 33 | GPIO13 | PWM1 | | 34 | - | Ground |
| 35 | GPIO19 | PWM1 / SPI MISO | | 36 | GPIO16 | Digital I/O |
| 37 | GPIO26 | Digital I/O | | 38 | GPIO20 | SPI MOSI |
| 39 | - | Ground | | 40 | GPIO21 | SPI SCLK |

## Pin Categories

### Power Pins

| Pin | Voltage | Notes |
|-----|---------|-------|
| 1, 17 | 3.3V | Low current, for sensors |
| 2, 4 | 5V | Higher current capability |

### Ground Pins

Pins: **6, 9, 14, 20, 25, 30, 34, 39**

### Communication Protocols

#### I2C (Inter-Integrated Circuit)

| Pin | GPIO | Function |
|-----|------|----------|
| 3 | GPIO2 | SDA (Data) |
| 5 | GPIO3 | SCL (Clock) |

**Use Cases**: Sensors, displays, EEPROMs, ADCs/DACs

#### SPI (Serial Peripheral Interface)

| Pin | GPIO | Function |
|-----|------|----------|
| 19 | GPIO10 | MOSI (Master Out Slave In) |
| 21 | GPIO9 | MISO (Master In Slave Out) |
| 23 | GPIO11 | SCLK (Clock) |
| 24 | GPIO8 | CE0 (Chip Enable 0) |
| 26 | GPIO7 | CE1 (Chip Enable 1) |

**Use Cases**: High-speed data transfer, ADCs, displays, SD cards

#### UART (Serial)

| Pin | GPIO | Function |
|-----|------|----------|
| 8 | GPIO14 | TXD (Transmit) |
| 10 | GPIO15 | RXD (Receive) |

**Use Cases**: Serial communication, GPS modules, microcontrollers

### PWM (Pulse Width Modulation)

| Pin | GPIO | PWM Channel |
|-----|------|-------------|
| 12 | GPIO18 | PWM0 |
| 32 | GPIO12 | PWM0 |
| 33 | GPIO13 | PWM1 |
| 35 | GPIO19 | PWM1 |

**Use Cases**: Motor control, LED dimming, servo control

## Supported Interfaces (via RP1)

| Interface | Count |
|-----------|-------|
| UART | 5 |
| SPI | 6 |
| I2C | 4 |
| I2S | 2 |
| PWM | 4 channels |
| DPI | 24-bit output |
| GPCLK | General-purpose clock |
| eMMC/SDIO | 4-bit interface |

## Software Libraries

### Recommended Libraries for Pi 5

| Library | Level | Notes |
|---------|-------|-------|
| **GPIO Zero** | Beginner-friendly | High-level, object-oriented |
| **gpiod** | Intermediate/Advanced | Lower-level control |

### Deprecated Libraries

- **RPi.GPIO**: Not compatible with Pi 5 due to RP1 controller changes
- **WiringPi**: Deprecated

### Getting Pinout on the Pi

Open terminal and run:
```bash
pinout
```

## Additional Resources

- [pinout.xyz](https://pinout.xyz/) - Interactive GPIO pinout reference
- [pinout.ai/raspberry-pi-5](https://pinout.ai/raspberry-pi-5) - Pi 5 specific pinouts
- [Official Raspberry Pi Documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html)
