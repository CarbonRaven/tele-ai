# Raspberry Pi 5 Power Requirements & Cooling

## Power Supply Requirements

### Official 27W USB-C PD Power Supply

The recommended power supply for the Raspberry Pi 5.

| Specification | Details |
|---------------|---------|
| Output | 5.1V / 5A (27W max) |
| Connector | USB Type-C |
| Cable Length | 1.2m (18AWG wire) |
| Input Voltage | 100-240VAC |
| Efficiency | >91% |
| Price | ~$12 |

### USB Power Delivery Modes

| Mode | Voltage | Current | Power |
|------|---------|---------|-------|
| Custom (Pi 5) | 5V | 5A | 25W |
| Standard PD | 5V | 3A | 15W |
| Standard PD | 9V | 3A | 27W |
| Standard PD | 12V | 2.25A | 27W |
| Standard PD | 15V | 1.8A | 27W |

### USB Port Power Budget

| Power Supply | USB-A Port Limit |
|--------------|------------------|
| Standard 5V/3A | 600mA total |
| Official 27W PD | 1.6A total |

**Note**: The Pi 5 auto-detects the official PSU and increases USB power budget accordingly.

### Minimum Requirements

| Use Case | Minimum PSU |
|----------|-------------|
| Basic use (no peripherals) | 5V / 3A (15W) |
| USB peripherals attached | 5V / 5A (27W) recommended |
| NVMe SSD + peripherals | 5V / 5A (27W) required |

### Third-Party PSU Warning

5A @ 5V is rare in third-party power supplies. Standard USB-C chargers (e.g., 45W laptop chargers) often only provide 5V/3A at the 5V rail, which can cause:
- Random system crashes
- USB device disconnections
- Instability under load

**Recommendation**: Use the official 27W PSU or a verified 5V/5A capable supply.

## Power Consumption

### Measured Power Draw

| State | Power (Watts) | Temperature | Notes |
|-------|---------------|-------------|-------|
| Standby | 0.05W | - | Optimized low-power mode |
| Standby (default) | 1.3W | - | RTC + wake capability |
| Idle | 2.6-3.5W | 39-50°C | Varies by stepping (D0 vs C1) |
| Light load | 4-5W | 50-60°C | Desktop use |
| Stress test (CPU) | 6.8-8.8W | 59-87°C | `stress -c 4` |
| Heavy load + USB | 10-11W | 70-85°C | With peripherals |
| Maximum | 15-17W | 85°C+ | Extreme workload |

### Comparison with Pi 4

| Metric | Pi 4 | Pi 5 | Difference |
|--------|------|------|------------|
| Idle | 1.0W | 2.7W | +1.7W |
| Under load | 6.2W | 7-8W | +1W |
| Performance | Baseline | 2-3x faster | Worth the extra watt |

### 2GB Model (D0 Stepping)

The newer 2GB Pi 5 uses D0 stepping silicon with ~30% lower idle power consumption compared to the original C1 stepping.

## Power Button

The Pi 5 includes an on-board power button (new feature).

### Functions

| Action | Result |
|--------|--------|
| Short press (off) | Power on |
| Short press (on) | Safe shutdown |
| Long press (10s) | Force power off |
| Double press | Reboot |

### Low-Power Mode

- Wake alarm can be set via RTC
- Very low power state: ~3mA (~0.015W)
- Useful for battery-powered or scheduled applications

## Real-Time Clock (RTC)

### Specifications

| Feature | Details |
|---------|---------|
| Crystal | External 32kHz |
| Accuracy | 50ppm typical |
| Connector | J5 (BAT) - 2-pin JST |
| Location | Right of USB-C power connector |
| Battery life | ~6 months (no external power) |

### Battery

| Specification | Details |
|---------------|---------|
| Recommended | Panasonic ML-2020 |
| Type | Lithium Manganese Dioxide |
| Charging | Built-in 3mA constant-current charger |
| Charging default | Disabled (enable in config.txt) |

**Note**: RTC is functional without battery; battery only needed to maintain time when unpowered.

### Enable Battery Charging

Add to `/boot/firmware/config.txt`:
```
dtparam=rtc_bbat_vchg=3000000
```

## Power over Ethernet (PoE)

### Requirements

- PoE+ HAT required (sold separately)
- PoE connector location changed from Pi 4
- Pi 4 PoE HATs not compatible

### PoE HAT Specifications (Third-Party Example)

| Feature | Details |
|---------|---------|
| Standard | 802.3af/at |
| Output | 5V up to 4.5A |
| Max Power | 25W (12V + 5V combined) |
| Cooling | Often includes fan/heatsink |

## Thermal Throttling

### Throttling Thresholds

| Temperature | Behavior |
|-------------|----------|
| < 80°C | Full speed (2.4 GHz) |
| 80-85°C | Throttled (reduced clock) |
| > 85°C | Heavy throttling |

### Without Cooling

Under sustained heavy load without cooling:
- Temperature reaches 85°C+ within ~200 seconds
- CPU throttles from 2.4 GHz down to ~1.5 GHz
- **No permanent damage** - throttling protects the SoC
- Even throttled Pi 5 is faster than unthrottled Pi 4

## Cooling Solutions

### Official Active Cooler

The recommended cooling solution for most users.

| Specification | Details |
|---------------|---------|
| Type | Aluminium heatsink + blower fan |
| Mounting | Spring-loaded push pins |
| Connection | 4-pin JST fan header |
| Thermal interface | Pre-applied thermal pads |
| Noise | 35-40 dB under load |
| Price | ~$5 |

#### Fan Speed Control (Automatic)

| Temperature | Fan Speed |
|-------------|-----------|
| < 60°C | Off |
| 60°C | Low speed |
| 67.5°C | Medium speed |
| 75°C+ | Full speed |

#### Thermal Performance

| State | Temperature |
|-------|-------------|
| Idle | ~45°C |
| Under load | 60-63°C |
| With 3GHz overclock | < 85°C (no throttling) |

**Warning**: Removing the Active Cooler damages the push pins and thermal pads. Do not reuse after removal.

### Official Case with Fan

| Feature | Details |
|---------|---------|
| Includes | Case + small radial fan |
| Performance | Keeps below thermal throttle |
| Compatibility | Works with Active Cooler |

### Passive Cooling Options

#### Aluminium Heatsink Cases

| Product | Notes |
|---------|-------|
| FLIRC Case | Minimalist, silent, proven design |
| 52Pi Armour Case | Rugged, full-metal sandwich |
| Argon ONE | Popular, includes power button |

**Performance**: Can prevent throttling for typical workloads, but may throttle under sustained heavy load (200+ seconds).

#### When Passive Cooling Suffices

- Typical desktop use
- Light server workloads
- Ambient temperature < 35°C
- No overclocking

### Active vs Passive Comparison

| Factor | Active Cooler | Passive Case |
|--------|---------------|--------------|
| Max sustained temp | 60-63°C | 80-85°C |
| Noise | Low (35-40 dB) | Silent |
| Throttling risk | None | Possible under heavy load |
| Overclocking support | Yes (up to 3GHz) | Limited |
| Price | ~$5 | $15-40 |

### Cooling Recommendations

| Use Case | Recommended Solution |
|----------|---------------------|
| Desktop/general use | Active Cooler or passive case |
| Server (light load) | Passive aluminium case |
| Server (heavy load) | Active Cooler |
| Overclocking | Active Cooler required |
| Silent operation | Passive case (accept throttling) |
| High ambient temp (>35°C) | Active Cooler |
| NVMe SSD use | Active cooling recommended |

## Operating Specifications

| Specification | Details |
|---------------|---------|
| Operating temp | 0°C to 60°C (ambient) |
| Storage temp | -20°C to 70°C |
| Production lifetime | Until at least January 2036 |

## Resources

- [Official 27W PSU Product Page](https://www.raspberrypi.com/products/27w-power-supply/)
- [27W PSU Product Brief (PDF)](https://datasheets.raspberrypi.com/power-supply/27w-usb-c-power-supply-product-brief.pdf)
- [Active Cooler Product Page](https://www.raspberrypi.com/products/active-cooler/)
- [Heating and Cooling Pi 5 (Official Blog)](https://www.raspberrypi.com/news/heating-and-cooling-raspberry-pi-5/)
- [Jeff Geerling Power Benchmarks](https://www.jeffgeerling.com/blog/2024/new-2gb-pi-5-has-33-smaller-die-30-idle-power-savings)
- [Pi Dramble Power Consumption](https://pidramble.com/wiki/benchmarks/power-consumption)
