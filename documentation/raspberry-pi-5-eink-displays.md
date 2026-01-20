# Raspberry Pi 5 E-Ink Display Options & Accessories

## Overview

E-ink (electronic ink) displays replicate the appearance of ink on paper. Unlike traditional displays, e-paper screens:

- **Hold images indefinitely** without power
- **Require no backlight** - readable in direct sunlight
- **Ultra-low power consumption** - only draw power during refresh
- **Wide viewing angles** - typically >170°
- **Eye-friendly** - no flicker or blue light

**Trade-offs**: Slow refresh rates (5-30 seconds), limited color options, higher cost per inch.

## Display Technologies

### Black & White (Dual-Color)

| Feature | Details |
|---------|---------|
| Colors | Black, White |
| Refresh Time | ~5 seconds |
| Best For | Text, simple graphics |
| Cost | Lowest |

### Three-Color (B/W/Red or B/W/Yellow)

| Feature | Details |
|---------|---------|
| Colors | Black, White, Red or Yellow |
| Refresh Time | ~15 seconds |
| Best For | Highlighted information, labels |
| Cost | Medium |

### ACeP 7-Color (Gallery Palette)

| Feature | Details |
|---------|---------|
| Colors | Black, White, Red, Green, Blue, Yellow, Orange |
| Refresh Time | ~30 seconds |
| Best For | Full-color images, art displays |
| Cost | Higher |

### Spectra 6 (Latest Generation)

| Feature | Details |
|---------|---------|
| Colors | Black, White, Red, Green, Blue, Yellow |
| Refresh Time | ~12-25 seconds |
| Color Gamut | 64% wider than previous gen |
| Best For | Vibrant color displays |
| Cost | Premium |

## Major Manufacturers

### Waveshare

The most extensive selection of e-paper displays for Raspberry Pi.

#### Black & White Displays

| Size | Resolution | Refresh | Price |
|------|------------|---------|-------|
| 2.13" | 250 × 122 | ~2s (partial) | ~$15 |
| 2.7" | 264 × 176 | ~5s | ~$20 |
| 2.9" | 296 × 128 | ~2s (partial) | ~$18 |
| 4.2" | 400 × 300 | ~4s | ~$30 |
| 5.83" | 648 × 480 | ~5s | ~$40 |
| 7.5" | 800 × 480 | ~5s | ~$50 |
| 7.5" HD | 880 × 528 | ~5s | ~$55 |
| 10.3" | 1872 × 1404 | ~6s | ~$150 |

#### Three-Color Displays

| Size | Resolution | Colors | Price |
|------|------------|--------|-------|
| 2.13" (B) | 250 × 122 | B/W/Red | ~$20 |
| 2.7" (B) | 264 × 176 | B/W/Red | ~$25 |
| 4.2" (B) | 400 × 300 | B/W/Red | ~$40 |
| 7.5" (B) | 800 × 480 | B/W/Red | ~$65 |

#### Color Displays (ACeP/Spectra 6)

| Size | Resolution | Technology | Price |
|------|------------|------------|-------|
| 4" | 600 × 400 | Spectra 6 | ~$50 |
| 5.65" | 600 × 448 | ACeP 7-color | ~$70 |
| 7.3" | 800 × 480 | Spectra 6 | ~$75 |
| 13.3" | 1600 × 1200 | Spectra 6 | ~$200 |

#### Touch-Enabled Displays

| Size | Resolution | Touch Points | Price |
|------|------------|--------------|-------|
| 2.13" | 250 × 122 | 5-point capacitive | ~$25 |
| 2.9" | 296 × 128 | 5-point capacitive | ~$30 |

#### Key Waveshare Specifications

| Spec | Value |
|------|-------|
| Interface | SPI (3-wire or 4-wire) |
| Operating Voltage | 3.3V / 5V |
| Standby Current | <0.01μA |
| Viewing Angle | >170° |
| Connector | 40-pin GPIO header |

### Pimoroni Inky

Premium displays with excellent software support and build quality.

#### Inky Impression Series (7-Color)

| Model | Size | Resolution | Refresh | Price |
|-------|------|------------|---------|-------|
| Inky Impression 4" | 4" | 640 × 400 | ~30s | ~$50 |
| Inky Impression 5.7" | 5.7" | 600 × 448 | ~30s | ~$65 |
| Inky Impression 7.3" | 7.3" | 800 × 480 | ~30s | ~$80 |
| Inky Impression 7.3" (2025) | 7.3" | 800 × 480 | ~12s | ~$85 |
| Inky Impression 13.3" | 13.3" | 1600 × 1200 | ~30s | ~$180 |

**2025 Edition Features**:
- Uses Spectra 6 technology
- Faster refresh (~12 seconds vs ~30 seconds)
- More saturated colors

#### Inky wHAT (Three-Color)

| Colors | Resolution | Price |
|--------|------------|-------|
| Red/Black/White | 400 × 300 | ~$40 |
| Yellow/Black/White | 400 × 300 | ~$40 |

#### Inky Features

- **Auto-configuration**: Display type detected automatically
- **Four tactile buttons**: Side-mounted for wall mounting
- **Qwiic/STEMMA QT connectors**: Easy I2C expansion
- **No soldering required**: Fully assembled HAT
- **Frame-friendly sizes**: 7.3" fits IKEA 180×130mm frames

### Good Display

Industrial-grade e-paper panels, often used as OEM components.

- SPI E-Paper Adapter with touch panel support
- Front light function available
- Compatible with displays up to 7.5"

## Connection Interface

### SPI Pinout (Standard)

| Pin | GPIO | Function |
|-----|------|----------|
| VCC | - | 3.3V/5V Power |
| GND | - | Ground |
| DIN | GPIO10 | SPI MOSI (Data In) |
| CLK | GPIO11 | SPI Clock |
| CS | GPIO8 | Chip Select |
| DC | GPIO25 | Data/Command |
| RST | GPIO17 | Reset |
| BUSY | GPIO24 | Busy Status |

**Note**: Pin assignments may vary by display model. Check documentation.

### Enable SPI on Pi 5

```bash
sudo raspi-config
# Navigate to: Interface Options → SPI → Enable
```

## Software & Libraries

### Pimoroni Inky Library

The recommended library for Inky displays with automatic detection.

```bash
# Installation
pip install inky

# Or from source
git clone https://github.com/pimoroni/inky
cd inky
pip install .
```

```python
from inky.auto import auto
from PIL import Image

# Auto-detect display
display = auto()

# Load and display image
image = Image.open("image.png")
display.set_image(image)
display.show()
```

### Waveshare EPD Library

```bash
# Install dependencies
sudo apt-get update
sudo apt-get install python3-pip python3-pil python3-numpy
pip install RPi.GPIO spidev

# Clone library
git clone https://github.com/waveshare/e-Paper.git
cd e-Paper/RaspberryPi_JetsonNano/python
pip install .
```

```python
import epaper

# Initialize specific display model
epd = epaper.epaper('epd7in5').EPD()
epd.init()
epd.Clear()

# Display image
from PIL import Image
image = Image.open('image.bmp')
epd.display(epd.getbuffer(image))
epd.sleep()
```

### PyPI Package

```bash
pip install waveshare-epaper
```

### InkyPi (Multi-Display Support)

Web-based management for both Inky and Waveshare displays.

```bash
git clone https://github.com/fatihak/InkyPi.git
cd InkyPi

# For Inky displays
./install.sh

# For Waveshare displays (specify model)
./install.sh -W epd7in3f
```

**Features**:
- Web interface for display management
- Plugin system (weather, calendar, news, photos)
- Scheduled automatic refreshes
- HTML/CSS rendering with Chromium

### PaperTTY

Mirror terminal/console to e-paper display.

```bash
pip install papertty
```

## Popular Projects & Use Cases

### Weather Dashboard

| Component | Details |
|-----------|---------|
| Display | 7.3" or 7.5" color e-paper |
| Data Source | OpenWeatherMap API |
| Pi Model | Pi Zero 2 W (low power) |
| Refresh | Every 15-60 minutes |

### Calendar/Schedule Display

| Component | Details |
|-----------|---------|
| Display | 5.7" - 7.3" e-paper |
| Data Source | Google Calendar, iCal, Outlook |
| Features | Week view, event list, reminders |

### Home Dashboard

| Component | Details |
|-----------|---------|
| Display | 7.3" - 13.3" color e-paper |
| Data Sources | Weather, calendar, news, photos |
| Software | InkyPi, custom Python |
| Frame | IKEA RIBBA or similar |

### Smart Label / Price Tag

| Component | Details |
|-----------|---------|
| Display | 2.13" - 2.9" B/W or 3-color |
| Use Case | Shelf labels, name tags |
| Features | Battery powered, wireless update |

### E-Reader / Document Display

| Component | Details |
|-----------|---------|
| Display | 10.3" or 13.3" |
| Resolution | 1872×1404 or higher |
| Use Case | PDF viewer, book reader |

## Hardware Recommendations

### By Use Case

| Use Case | Recommended Display | Size |
|----------|---------------------|------|
| Minimal dashboard | Waveshare B/W | 2.7" - 4.2" |
| Weather station | Waveshare/Inky 3-color | 4.2" - 7.5" |
| Photo frame | Inky Impression (color) | 5.7" - 7.3" |
| Document display | Waveshare HD | 10.3"+ |
| Interactive | Waveshare Touch | 2.13" - 2.9" |
| Wall calendar | Inky Impression 2025 | 7.3" |

### By Budget

| Budget | Option |
|--------|--------|
| <$25 | Waveshare 2.13" - 2.9" B/W |
| $25-50 | Waveshare 4.2" - 5.83" or 3-color |
| $50-100 | Inky Impression 5.7" - 7.3" |
| $100+ | Large format (10.3"+) |

### Pi Model Pairing

| Pi Model | Best For |
|----------|----------|
| Pi Zero 2 W | Low-power, battery projects |
| Pi 5 | Fast updates, complex rendering |
| Pi 4 | General purpose |

## Limitations & Considerations

### Refresh Rates

| Display Type | Typical Refresh |
|--------------|-----------------|
| B/W (partial) | 0.3-2 seconds |
| B/W (full) | 3-5 seconds |
| 3-color | 10-15 seconds |
| 7-color ACeP | 25-35 seconds |
| Spectra 6 | 12-25 seconds |

### Temperature Sensitivity

| Condition | Effect |
|-----------|--------|
| <0°C | Slower refresh, possible damage |
| 0-10°C | Slower refresh |
| 10-40°C | Optimal performance |
| >40°C | Faster refresh, reduced lifespan |

### Ghosting

Faint remnants of previous images may appear. Mitigate with:
- Full refresh cycles periodically
- Proper sleep mode usage
- Manufacturer-recommended refresh sequences

### Not Suitable For

- Video playback
- Real-time updates (<5 second intervals)
- High frame rate content
- Touch-heavy interfaces (limited touch options)

## Resources

### Official Documentation
- [Waveshare E-Paper Wiki](https://www.waveshare.com/wiki/Main_Page#e-Paper)
- [Pimoroni Inky Guide](https://learn.pimoroni.com/article/getting-started-with-inky-impression)
- [Raspberry Pi E-Ink Blog Post](https://www.raspberrypi.com/news/using-e-ink-raspberry-pi/)

### GitHub Projects
- [Waveshare e-Paper](https://github.com/waveshare/e-Paper)
- [Pimoroni Inky](https://github.com/pimoroni/inky)
- [InkyPi Dashboard](https://github.com/fatihak/InkyPi)
- [PaperTTY](https://github.com/joukos/PaperTTY)
- [E-Paper Weather Display](https://github.com/AbnormalDistributions/e_paper_weather_display)

### Retailers
- [Waveshare](https://www.waveshare.com/product/raspberry-pi/displays/e-paper.htm)
- [Pimoroni](https://shop.pimoroni.com/)
- [The Pi Hut](https://thepihut.com/collections/epaper-displays-for-raspberry-pi)
- [Adafruit](https://www.adafruit.com/)
