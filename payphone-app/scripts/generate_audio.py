#!/usr/bin/env python3
"""Generate telephone sound effect WAV files.

Produces authentic North American telephone network sounds based on
Bellcore GR-506 specifications. All output is 16-bit PCM WAV at 8000 Hz
mono, matching the voice pipeline's output_sample_rate.

Usage:
    cd payphone-app
    python3 scripts/generate_audio.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import soundfile as sf

# Output format constants
SAMPLE_RATE = 8000
DTYPE = np.float64
MAX_INT16 = 32767


def tone(freq: float, duration: float, amplitude: float = 0.8) -> np.ndarray:
    """Generate a sine wave.

    Args:
        freq: Frequency in Hz.
        duration: Duration in seconds.
        amplitude: Peak amplitude (0.0 - 1.0).
    """
    t = np.arange(int(SAMPLE_RATE * duration), dtype=DTYPE) / SAMPLE_RATE
    return amplitude * np.sin(2 * np.pi * freq * t)


def dual_tone(
    freq1: float, freq2: float, duration: float, amplitude: float = 0.7
) -> np.ndarray:
    """Generate a two-frequency combined tone (e.g. DTMF, dial tone).

    Each frequency is mixed at half the target amplitude so the sum
    doesn't clip.
    """
    t = np.arange(int(SAMPLE_RATE * duration), dtype=DTYPE) / SAMPLE_RATE
    half = amplitude / 2
    return half * np.sin(2 * np.pi * freq1 * t) + half * np.sin(2 * np.pi * freq2 * t)


def multi_tone(freqs: list[float], duration: float, amplitude: float = 0.7) -> np.ndarray:
    """Combine 3+ frequencies, each scaled so the sum stays within amplitude."""
    t = np.arange(int(SAMPLE_RATE * duration), dtype=DTYPE) / SAMPLE_RATE
    each = amplitude / len(freqs)
    return sum(each * np.sin(2 * np.pi * f * t) for f in freqs)


def cadenced(
    signal: np.ndarray, on_sec: float, off_sec: float, cycles: int
) -> np.ndarray:
    """Apply an on/off cadence pattern to a tone.

    The signal is looped/truncated to fill the on portion of each cycle.
    """
    on_samples = int(SAMPLE_RATE * on_sec)
    off_samples = int(SAMPLE_RATE * off_sec)
    silence = np.zeros(off_samples, dtype=DTYPE)

    parts: list[np.ndarray] = []
    for _ in range(cycles):
        # Loop signal to fill the on-time
        if len(signal) >= on_samples:
            chunk = signal[:on_samples]
        else:
            reps = (on_samples // len(signal)) + 1
            chunk = np.tile(signal, reps)[:on_samples]
        parts.append(chunk)
        parts.append(silence)

    return np.concatenate(parts)


def envelope(
    signal: np.ndarray, attack: float = 0.005, decay: float = 0.0
) -> np.ndarray:
    """Apply attack/decay amplitude envelope.

    Args:
        signal: Input audio.
        attack: Attack time in seconds.
        decay: Decay time in seconds (exponential). 0 = no decay.
    """
    out = signal.copy()
    attack_samples = int(SAMPLE_RATE * attack)
    if attack_samples > 0 and attack_samples < len(out):
        ramp = np.linspace(0, 1, attack_samples, dtype=DTYPE)
        out[:attack_samples] *= ramp

    if decay > 0:
        decay_env = np.exp(-np.arange(len(out), dtype=DTYPE) / (SAMPLE_RATE * decay))
        out *= decay_env

    return out


def noise_burst(duration: float, amplitude: float = 0.3) -> np.ndarray:
    """Generate filtered white noise burst."""
    rng = np.random.default_rng(42)
    n_samples = int(SAMPLE_RATE * duration)
    noise = rng.standard_normal(n_samples).astype(DTYPE)

    # Simple low-pass via moving average to make it less harsh
    kernel_size = 5
    kernel = np.ones(kernel_size, dtype=DTYPE) / kernel_size
    noise = np.convolve(noise, kernel, mode="same")

    # Normalize and scale
    peak = np.max(np.abs(noise))
    if peak > 0:
        noise = noise / peak * amplitude

    return noise


def save_wav(filename: str, audio: np.ndarray, output_dir: Path) -> int:
    """Write audio to 16-bit PCM WAV at 8000 Hz.

    Returns file size in bytes.
    """
    # Clip to [-1, 1] range
    audio = np.clip(audio, -1.0, 1.0)

    filepath = output_dir / filename
    sf.write(str(filepath), audio, SAMPLE_RATE, subtype="PCM_16")
    return filepath.stat().st_size


def generate_all(output_dir: Path) -> list[tuple[str, int]]:
    """Generate all telephone sound effects.

    Returns list of (filename, size_bytes) tuples.
    """
    results: list[tuple[str, int]] = []

    def save(name: str, audio: np.ndarray) -> None:
        size = save_wav(name, audio, output_dir)
        results.append((name, size))

    # 1. Dial tone: 350 Hz + 440 Hz, continuous, 3s
    save("dial_tone.wav", dual_tone(350, 440, 3.0))

    # 2. Busy signal: 480 Hz + 620 Hz, 0.5s on / 0.5s off, 4 cycles
    busy_base = dual_tone(480, 620, 0.5)
    save("busy_signal.wav", cadenced(busy_base, 0.5, 0.5, 4))

    # 3. Ring tone: 440 Hz + 480 Hz, 2s on / 4s off, 2 cycles
    ring_base = dual_tone(440, 480, 2.0)
    save("ring_tone.wav", cadenced(ring_base, 2.0, 4.0, 2))

    # 4. Off-hook warning: 1400+2060+2450+2600 Hz, 0.1s on / 0.1s off, 5 cycles
    offhook_base = multi_tone([1400, 2060, 2450, 2600], 0.1)
    save("off_hook.wav", cadenced(offhook_base, 0.1, 0.1, 5))

    # 5. Reorder tone (fast busy): 480+620 Hz, 0.25s on / 0.25s off, 6 cycles
    reorder_base = dual_tone(480, 620, 0.25)
    save("reorder_tone.wav", cadenced(reorder_base, 0.25, 0.25, 6))

    # 6. Coin deposit: metallic ping 1700+2200 Hz, 80ms with decay
    coin_tone = dual_tone(1700, 2200, 0.08, amplitude=0.8)
    save("coin_deposit.wav", envelope(coin_tone, attack=0.001, decay=0.03))

    # 7. Coin return: noise burst + low thunk, 150ms
    thunk = tone(200, 0.05, amplitude=0.5)
    thunk = envelope(thunk, attack=0.001, decay=0.02)
    click_noise = noise_burst(0.03, amplitude=0.4)
    # Combine: click then thunk with small gap
    gap = np.zeros(int(SAMPLE_RATE * 0.02), dtype=DTYPE)
    coin_return = np.concatenate([click_noise, gap, thunk])
    # Pad to ~150ms
    target_samples = int(SAMPLE_RATE * 0.15)
    if len(coin_return) < target_samples:
        coin_return = np.concatenate(
            [coin_return, np.zeros(target_samples - len(coin_return), dtype=DTYPE)]
        )
    save("coin_return.wav", coin_return)

    # 8. SIT intercept (number not in service): 913.8 → 1370.6 → 1776.7 Hz
    sit1 = tone(913.8, 0.380, amplitude=0.8)
    sit2 = tone(1370.6, 0.380, amplitude=0.8)
    sit3 = tone(1776.7, 0.380, amplitude=0.8)
    # Small gaps between tones (20ms)
    sit_gap = np.zeros(int(SAMPLE_RATE * 0.02), dtype=DTYPE)
    save("sit_intercept.wav", np.concatenate([sit1, sit_gap, sit2, sit_gap, sit3]))

    # 9. SIT reorder (all circuits busy): 985.2 → 1370.6 → 1776.7 Hz
    sit_r1 = tone(985.2, 0.380, amplitude=0.8)
    save("sit_reorder.wav", np.concatenate([sit_r1, sit_gap, sit2, sit_gap, sit3]))

    # 10. Connect click: short broadband noise burst, 20ms
    save("connect_click.wav", envelope(noise_burst(0.02, amplitude=0.5), attack=0.001))

    # 11. Disconnect click: slightly longer noise burst, 40ms
    save("disconnect_click.wav", envelope(noise_burst(0.04, amplitude=0.5), attack=0.001))

    # 12. DTMF star: 941 Hz + 1209 Hz, 100ms
    save("dtmf_star.wav", envelope(dual_tone(941, 1209, 0.1, amplitude=0.8), attack=0.002))

    # 13. DTMF pound: 941 Hz + 1477 Hz, 100ms
    save("dtmf_pound.wav", envelope(dual_tone(941, 1477, 0.1, amplitude=0.8), attack=0.002))

    # 14. Static burst: filtered white noise, 500ms with envelope
    static = noise_burst(0.5, amplitude=0.4)
    static = envelope(static, attack=0.01, decay=0.15)
    save("static_burst.wav", static)

    # 15. Line noise: 60 Hz hum + low-level noise, 2s
    hum = tone(60, 2.0, amplitude=0.15)
    bg_noise = noise_burst(2.0, amplitude=0.05)
    save("line_noise.wav", hum + bg_noise)

    # 16. Operator beep: 440 Hz, 100ms single beep
    save("operator_beep.wav", envelope(tone(440, 0.1, amplitude=0.7), attack=0.005))

    # 17. Recording beep: 1004 Hz, 200ms (standard test tone)
    save("recording_beep.wav", envelope(tone(1004, 0.2, amplitude=0.7), attack=0.005))

    return results


def main() -> None:
    """Generate all sounds and print summary."""
    # Resolve output directory relative to this script's location
    script_dir = Path(__file__).resolve().parent
    output_dir = script_dir.parent / "audio" / "sounds"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating telephone sound effects into {output_dir}/")
    print(f"Format: 16-bit PCM WAV, {SAMPLE_RATE} Hz, mono")
    print()

    results = generate_all(output_dir)

    total_size = 0
    for filename, size in results:
        print(f"  {filename:<24s}  {size:>6,d} bytes")
        total_size += size

    print()
    print(f"Generated {len(results)} files, {total_size:,d} bytes total")


if __name__ == "__main__":
    main()
