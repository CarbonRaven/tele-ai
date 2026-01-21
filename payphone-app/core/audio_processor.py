"""Audio processing utilities for the voice pipeline.

Handles:
- Sample rate conversion (8kHz <-> 16kHz <-> 24kHz)
- Telephone bandpass filter (300-3400 Hz)
- Audio format conversions
"""

import numpy as np
from numpy.typing import NDArray
from scipy import signal
from scipy.signal import resample_poly
from typing import Literal

from config.settings import AudioSettings


class AudioProcessor:
    """Audio processing utilities for the voice pipeline."""

    def __init__(self, settings: AudioSettings | None = None):
        if settings is None:
            settings = AudioSettings()
        self.settings = settings

        # Pre-compute filter coefficients for telephone bandpass
        self._telephone_filter = self._create_telephone_filter()

    def _create_telephone_filter(self) -> tuple[NDArray, NDArray]:
        """Create Butterworth bandpass filter for telephone audio (300-3400 Hz).

        Returns:
            Tuple of (b, a) filter coefficients.
        """
        nyquist = self.settings.output_sample_rate / 2
        low = self.settings.telephone_lowcut / nyquist
        high = self.settings.telephone_highcut / nyquist

        # Clamp to valid range
        low = max(0.001, min(low, 0.99))
        high = max(low + 0.001, min(high, 0.99))

        # 4th order Butterworth bandpass
        b, a = signal.butter(4, [low, high], btype="band")
        return b, a

    def bytes_to_samples(self, audio_bytes: bytes) -> NDArray[np.int16]:
        """Convert raw audio bytes to numpy array.

        Args:
            audio_bytes: Raw audio bytes (signed 16-bit PCM)

        Returns:
            Numpy array of int16 samples.
        """
        return np.frombuffer(audio_bytes, dtype=np.int16)

    def samples_to_bytes(self, samples: NDArray) -> bytes:
        """Convert numpy array to raw audio bytes.

        Args:
            samples: Numpy array of audio samples.

        Returns:
            Raw audio bytes (signed 16-bit PCM).
        """
        # Ensure int16 range
        samples = np.clip(samples, -32768, 32767).astype(np.int16)
        return samples.tobytes()

    def normalize_samples(self, samples: NDArray) -> NDArray[np.float32]:
        """Normalize int16 samples to float32 range [-1.0, 1.0].

        Args:
            samples: Int16 audio samples.

        Returns:
            Float32 normalized samples.
        """
        return samples.astype(np.float32) / 32768.0

    def denormalize_samples(self, samples: NDArray[np.float32]) -> NDArray[np.int16]:
        """Convert float32 [-1.0, 1.0] samples to int16.

        Args:
            samples: Float32 normalized samples.

        Returns:
            Int16 audio samples.
        """
        return (samples * 32767.0).clip(-32768, 32767).astype(np.int16)

    def resample(
        self,
        samples: NDArray,
        from_rate: int,
        to_rate: int,
    ) -> NDArray:
        """Resample audio to a different sample rate.

        Uses polyphase resampling for efficient, high-quality conversion.

        Args:
            samples: Input audio samples.
            from_rate: Original sample rate.
            to_rate: Target sample rate.

        Returns:
            Resampled audio samples.
        """
        if from_rate == to_rate:
            return samples

        # Find GCD for rational resampling
        from math import gcd

        g = gcd(from_rate, to_rate)
        up = to_rate // g
        down = from_rate // g

        # Use polyphase resampling
        resampled = resample_poly(samples.astype(np.float64), up, down)

        # Preserve dtype
        if samples.dtype == np.int16:
            return resampled.clip(-32768, 32767).astype(np.int16)
        elif samples.dtype == np.float32:
            return resampled.astype(np.float32)
        return resampled

    def resample_8k_to_16k(self, samples: NDArray) -> NDArray:
        """Resample from 8kHz (Asterisk) to 16kHz (STT).

        Args:
            samples: Audio samples at 8kHz.

        Returns:
            Audio samples at 16kHz.
        """
        return self.resample(samples, 8000, 16000)

    def resample_16k_to_8k(self, samples: NDArray) -> NDArray:
        """Resample from 16kHz to 8kHz (Asterisk).

        Args:
            samples: Audio samples at 16kHz.

        Returns:
            Audio samples at 8kHz.
        """
        return self.resample(samples, 16000, 8000)

    def resample_24k_to_8k(self, samples: NDArray) -> NDArray:
        """Resample from 24kHz (Kokoro TTS) to 8kHz (Asterisk).

        Args:
            samples: Audio samples at 24kHz.

        Returns:
            Audio samples at 8kHz.
        """
        return self.resample(samples, 24000, 8000)

    def apply_telephone_filter(self, samples: NDArray) -> NDArray:
        """Apply telephone bandpass filter (300-3400 Hz).

        Simulates the frequency response of the PSTN for authentic telephone audio.

        Args:
            samples: Audio samples (should be at output sample rate, e.g., 8kHz).

        Returns:
            Filtered audio samples.
        """
        b, a = self._telephone_filter

        # Convert to float for filtering
        float_samples = samples.astype(np.float64)

        # Apply filter
        filtered = signal.filtfilt(b, a, float_samples)

        # Preserve original dtype
        if samples.dtype == np.int16:
            return filtered.clip(-32768, 32767).astype(np.int16)
        return filtered.astype(samples.dtype)

    def process_for_stt(self, audio_bytes: bytes) -> NDArray[np.float32]:
        """Process raw 8kHz audio for STT (Whisper expects 16kHz float32).

        Args:
            audio_bytes: Raw audio bytes from Asterisk (8kHz, 16-bit PCM).

        Returns:
            Processed audio as float32 array at 16kHz.
        """
        # Convert bytes to samples
        samples = self.bytes_to_samples(audio_bytes)

        # Resample 8kHz -> 16kHz
        resampled = self.resample_8k_to_16k(samples)

        # Normalize to float32 [-1.0, 1.0]
        return self.normalize_samples(resampled)

    def process_for_output(self, samples: NDArray, from_rate: int = 24000) -> bytes:
        """Process TTS audio for output to Asterisk.

        Args:
            samples: Audio samples from TTS.
            from_rate: Sample rate of input (default 24kHz for Kokoro).

        Returns:
            Processed audio bytes (8kHz, 16-bit PCM) ready for Asterisk.
        """
        # Ensure float for processing
        if samples.dtype == np.int16:
            float_samples = samples.astype(np.float32)
        else:
            float_samples = samples.astype(np.float32)

        # Resample to 8kHz
        resampled = self.resample(float_samples, from_rate, 8000)

        # Apply telephone filter for authentic sound
        filtered = self.apply_telephone_filter(resampled)

        # Convert to int16
        if filtered.dtype != np.int16:
            int_samples = (filtered * 32767.0).clip(-32768, 32767).astype(np.int16)
        else:
            int_samples = filtered

        return self.samples_to_bytes(int_samples)

    def chunk_audio(
        self,
        audio_bytes: bytes,
        chunk_size: int | None = None,
    ) -> list[bytes]:
        """Split audio into chunks for streaming.

        Args:
            audio_bytes: Audio data to chunk.
            chunk_size: Size of each chunk in bytes. Defaults to settings.chunk_size.

        Returns:
            List of audio chunks.
        """
        if chunk_size is None:
            chunk_size = self.settings.chunk_size

        chunks = []
        for i in range(0, len(audio_bytes), chunk_size):
            chunks.append(audio_bytes[i : i + chunk_size])

        return chunks


class AudioBuffer:
    """Buffer for accumulating audio chunks."""

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self._buffer: list[NDArray[np.float32]] = []
        self._total_samples = 0

    def add(self, samples: NDArray[np.float32]) -> None:
        """Add audio samples to the buffer.

        Args:
            samples: Float32 audio samples to add.
        """
        self._buffer.append(samples)
        self._total_samples += len(samples)

    def get_all(self) -> NDArray[np.float32]:
        """Get all buffered audio as a single array.

        Returns:
            Concatenated audio samples.
        """
        if not self._buffer:
            return np.array([], dtype=np.float32)
        return np.concatenate(self._buffer)

    def get_duration_ms(self) -> float:
        """Get duration of buffered audio in milliseconds.

        Returns:
            Duration in milliseconds.
        """
        return (self._total_samples / self.sample_rate) * 1000

    def clear(self) -> None:
        """Clear the buffer."""
        self._buffer = []
        self._total_samples = 0

    @property
    def is_empty(self) -> bool:
        """Check if buffer is empty."""
        return self._total_samples == 0

    @property
    def num_samples(self) -> int:
        """Get number of samples in buffer."""
        return self._total_samples
