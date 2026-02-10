#!/usr/bin/env python3
"""Wyoming protocol STT server using Hailo-10H accelerated Whisper.

Standalone async TCP server that speaks the Wyoming protocol, wrapping
Hailo NPU inference for Whisper speech-to-text. Designed to run as a
systemd service on Pi #1 (pi-voice) with the AI HAT+ 2 (Hailo-10H).

Architecture (hybrid inference):
    Audio (16kHz PCM) -> Mel Spectrogram -> Encoder (Hailo NPU) -> Decoder (Hailo NPU + CPU) -> Text

The encoder runs entirely on the Hailo-10H NPU. The decoder runs on the
NPU with CPU-side token embedding lookup (large vocab table indexing
cannot be compiled into the HEF).

Wyoming protocol events:
    Receive: audio-start, audio-chunk (binary payload), audio-stop
    Send: transcript (with text in data)

Usage:
    python services/wyoming_whisper_server.py --model-dir ../models --port 10300

Dependencies (Pi #1):
    - hailo_platform (system package: python3-h10-hailort 5.1.1)
    - numpy, scipy (pip, already in venv)
    - transformers (pip, already in venv for Moonshine — provides WhisperTokenizer)
"""

import argparse
import asyncio
import json
import logging
import signal
import sys
import time
from pathlib import Path

import numpy as np

logger = logging.getLogger("wyoming_whisper")

# ---------------------------------------------------------------------------
# Whisper audio constants
# ---------------------------------------------------------------------------
SAMPLE_RATE = 16000
N_FFT = 400           # 25ms window at 16kHz
HOP_LENGTH = 160      # 10ms hop at 16kHz
N_MELS = 80
CHUNK_LENGTH_S = 10   # Hailo-10H encoder accepts 10s (not standard 30s)
N_SAMPLES = CHUNK_LENGTH_S * SAMPLE_RATE  # 160,000 samples

# Whisper special token IDs (multilingual vocab)
SOT_TOKEN = 50258              # <|startoftranscript|>
EN_TOKEN = 50259               # <|en|>
TRANSCRIBE_TOKEN = 50360       # <|transcribe|>
NO_TIMESTAMPS_TOKEN = 50363    # <|notimestamps|>
EOT_TOKEN = 50257              # <|endoftext|>

# Repetition penalty for decoder (prevents looping)
REPETITION_PENALTY = 1.5


# ---------------------------------------------------------------------------
# Mel spectrogram (pure numpy — no torch or librosa dependency)
# ---------------------------------------------------------------------------
class MelSpectrogram:
    """Compute log-mel spectrograms compatible with OpenAI Whisper.

    Replicates Whisper's preprocessing using numpy FFT and a mel filterbank
    computed from the HTK mel scale with Slaney normalization.
    """

    def __init__(self):
        self._filterbank = self._make_filterbank()
        # Periodic Hann window matching torch.hann_window(N_FFT)
        self._window = (0.5 - 0.5 * np.cos(
            2.0 * np.pi * np.arange(N_FFT) / N_FFT
        )).astype(np.float32)

    @staticmethod
    def _make_filterbank() -> np.ndarray:
        """Compute 80-bin mel filterbank, shape (80, 201).

        Matches librosa.filters.mel(sr=16000, n_fft=400, n_mels=80) with
        Slaney normalization (the default used by OpenAI Whisper).
        """
        n_freqs = N_FFT // 2 + 1  # 201

        fftfreqs = np.linspace(0, SAMPLE_RATE / 2, n_freqs)

        def hz_to_mel(f):
            return 2595.0 * np.log10(1.0 + f / 700.0)

        def mel_to_hz(m):
            return 700.0 * (10.0 ** (m / 2595.0) - 1.0)

        mels = np.linspace(hz_to_mel(0), hz_to_mel(SAMPLE_RATE / 2), N_MELS + 2)
        hz = mel_to_hz(mels)

        fb = np.zeros((N_MELS, n_freqs), dtype=np.float32)
        for i in range(N_MELS):
            lo, mid, hi = hz[i], hz[i + 1], hz[i + 2]
            # Rising slope
            rise = (fftfreqs >= lo) & (fftfreqs <= mid)
            if mid > lo:
                fb[i, rise] = (fftfreqs[rise] - lo) / (mid - lo)
            # Falling slope
            fall = (fftfreqs >= mid) & (fftfreqs <= hi)
            if hi > mid:
                fb[i, fall] = (hi - fftfreqs[fall]) / (hi - mid)

        # Slaney normalization
        enorm = 2.0 / (hz[2 : N_MELS + 2] - hz[:N_MELS])
        fb *= enorm[:, np.newaxis]

        return fb

    def __call__(self, audio: np.ndarray) -> np.ndarray:
        """Convert audio to log-mel spectrogram.

        Args:
            audio: Float32 samples at 16kHz.

        Returns:
            Log-mel spectrogram of shape (N_MELS, n_frames) where
            n_frames = N_SAMPLES // HOP_LENGTH (1000 for 10s).
        """
        # Pad or trim to exactly CHUNK_LENGTH_S seconds
        if len(audio) > N_SAMPLES:
            audio = audio[:N_SAMPLES]
        else:
            audio = np.pad(audio, (0, max(0, N_SAMPLES - len(audio))))

        audio = audio.astype(np.float32)

        # Reflect-pad signal (matching torch.stft center=True)
        pad_len = N_FFT // 2  # 200
        audio_padded = np.pad(audio, (pad_len, pad_len), mode="reflect")

        # Frame the signal
        n_frames = 1 + (len(audio_padded) - N_FFT) // HOP_LENGTH
        frames = np.lib.stride_tricks.as_strided(
            audio_padded,
            shape=(n_frames, N_FFT),
            strides=(audio_padded.strides[0] * HOP_LENGTH, audio_padded.strides[0]),
        ).copy()  # copy to avoid stride issues with FFT

        # Apply window and compute FFT
        windowed = frames * self._window
        spectrum = np.fft.rfft(windowed, n=N_FFT)  # (n_frames, n_freqs)

        # Power spectrogram — drop last time frame to match Whisper
        magnitudes = np.abs(spectrum[:-1]) ** 2  # (n_frames-1, n_freqs)
        magnitudes = magnitudes.T  # (n_freqs, n_frames) = (201, 1000)

        # Apply mel filterbank
        mel_spec = self._filterbank @ magnitudes  # (80, 1000)

        # Log scale with Whisper normalization
        log_spec = np.log10(np.maximum(mel_spec, 1e-10))
        log_spec = np.maximum(log_spec, log_spec.max() - 8.0)
        log_spec = (log_spec + 4.0) / 4.0

        return log_spec.astype(np.float32)


# ---------------------------------------------------------------------------
# Hailo Whisper inference engine
# ---------------------------------------------------------------------------
class HailoWhisperEngine:
    """Whisper inference using Hailo-10H NPU.

    Loads encoder and decoder HEF files, plus CPU-side embedding arrays.
    The encoder runs entirely on the NPU. The decoder runs on the NPU
    with CPU-side token embedding lookup.

    Required files in model_dir:
        - {variant}-whisper-encoder-10s.hef
        - {variant}-whisper-decoder-fixed-sequence.hef
        - token_embedding_weight_{variant}.npy
        - onnx_add_input_{variant}.npy
    """

    def __init__(self, model_dir: Path, variant: str = "tiny"):
        self.model_dir = Path(model_dir)
        self.variant = variant
        self._mel = MelSpectrogram()

        # Paths
        self._encoder_hef_path = self.model_dir / f"{variant}-whisper-encoder-10s.hef"
        self._decoder_hef_path = self.model_dir / f"{variant}-whisper-decoder-fixed-sequence.hef"
        self._token_embed_path = self.model_dir / f"token_embedding_weight_{variant}.npy"
        self._pos_embed_path = self.model_dir / f"onnx_add_input_{variant}.npy"

        # Runtime state (populated by initialize())
        self._vdevice = None
        self._encoder_configured = None
        self._decoder_configured = None
        self._encoder_model = None
        self._decoder_model = None
        self._token_embeddings: np.ndarray | None = None
        self._pos_embeddings: np.ndarray | None = None
        self._tokenizer = None
        self._decoder_seq_len: int = 0
        self._decoder_input_names: list[str] = []
        self._decoder_output_names: list[str] = []
        self._encoder_input_shape: tuple = ()
        self._encoder_output_shape: tuple = ()
        self._inference_lock = asyncio.Lock()

    def initialize(self) -> None:
        """Load models and prepare for inference. Call once at startup."""
        # Validate all required files exist
        for path in [
            self._encoder_hef_path,
            self._decoder_hef_path,
            self._token_embed_path,
            self._pos_embed_path,
        ]:
            if not path.exists():
                raise FileNotFoundError(
                    f"Required model file not found: {path}\n"
                    f"Run scripts/download_hailo_models.py to download models."
                )

        # Load CPU-side embedding arrays
        self._token_embeddings = np.load(str(self._token_embed_path))
        self._pos_embeddings = np.load(str(self._pos_embed_path))
        logger.info(
            f"Loaded embeddings: tokens={self._token_embeddings.shape}, "
            f"positions={self._pos_embeddings.shape}"
        )

        # Load tokenizer (transformers already installed for Moonshine)
        from transformers import WhisperTokenizer

        self._tokenizer = WhisperTokenizer.from_pretrained(
            f"openai/whisper-{self.variant}"
        )
        logger.info(f"Loaded WhisperTokenizer for {self.variant}")

        # Import HailoRT
        try:
            from hailo_platform import (
                FormatType,
                HEF,
                HailoSchedulingAlgorithm,
                VDevice,
            )
        except ImportError:
            raise ImportError(
                "hailo_platform not found. Install python3-h10-hailort "
                "system package on Pi #1 with AI HAT+ 2."
            )

        # Create VDevice (Hailo NPU handle)
        params = VDevice.create_params()
        params.scheduling_algorithm = HailoSchedulingAlgorithm.ROUND_ROBIN
        self._vdevice = VDevice(params)
        logger.info("Hailo VDevice created")

        # --- Encoder setup ---
        self._encoder_model = self._vdevice.create_infer_model(
            str(self._encoder_hef_path)
        )
        self._encoder_model.input().set_format_type(FormatType.FLOAT32)
        self._encoder_model.output().set_format_type(FormatType.FLOAT32)
        self._encoder_configured = self._encoder_model.configure()

        self._encoder_input_shape = tuple(self._encoder_model.input().shape)
        self._encoder_output_shape = tuple(self._encoder_model.output().shape)
        logger.info(
            f"Encoder loaded: input={self._encoder_input_shape}, "
            f"output={self._encoder_output_shape}"
        )

        # --- Decoder setup ---
        decoder_hef = HEF(str(self._decoder_hef_path))
        self._decoder_model = self._vdevice.create_infer_model(
            str(self._decoder_hef_path)
        )

        # Discover input/output names from HEF
        input_infos = decoder_hef.get_input_vstream_infos()
        output_infos = decoder_hef.get_output_vstream_infos()

        self._decoder_input_names = [info.name for info in input_infos]
        self._decoder_output_names = sorted(
            [info.name for info in output_infos]
        )

        for info in input_infos:
            logger.info(f"Decoder input: name={info.name}, shape={info.shape}")
        for info in output_infos:
            logger.info(f"Decoder output: name={info.name}, shape={info.shape}")

        # Set format types for all decoder inputs/outputs
        for name in self._decoder_input_names:
            self._decoder_model.input(name).set_format_type(FormatType.FLOAT32)
        for name in self._decoder_output_names:
            self._decoder_model.output(name).set_format_type(FormatType.FLOAT32)

        self._decoder_configured = self._decoder_model.configure()

        # Determine max decoder sequence length from output shape
        # Output shape is typically (batch, seq_len, vocab_chunk) or similar
        if len(output_infos) > 0 and len(output_infos[0].shape) > 1:
            self._decoder_seq_len = output_infos[0].shape[1]
        else:
            self._decoder_seq_len = 32  # Safe default for tiny
        logger.info(f"Decoder max sequence length: {self._decoder_seq_len}")

        logger.info(
            f"Hailo Whisper engine initialized (variant={self.variant}, "
            f"encoder_input={self._encoder_input_shape}, "
            f"decoder_seq_len={self._decoder_seq_len})"
        )

    def transcribe_sync(self, audio: np.ndarray) -> str:
        """Transcribe audio using Hailo Whisper (blocking).

        Args:
            audio: Float32 audio at 16kHz, any length (padded/trimmed to 10s).

        Returns:
            Transcription text.
        """
        start_time = time.monotonic()

        # Audio -> mel spectrogram
        mel = self._mel(audio)  # (80, 1000)

        # Reshape mel to match encoder HEF input shape
        # Typical shapes: (1, 80, 1000) or (1, 80, 1, 1000)
        mel_input = mel.reshape(self._encoder_input_shape)
        mel_input = np.ascontiguousarray(mel_input)

        # --- Encoder inference (NPU) ---
        enc_bindings = self._encoder_configured.create_bindings()
        enc_bindings.input().set_buffer(mel_input)

        enc_output = np.zeros(self._encoder_output_shape, dtype=np.float32)
        enc_bindings.output().set_buffer(enc_output)

        self._encoder_configured.run([enc_bindings], 30_000)  # 30s timeout ms
        encoded_features = np.ascontiguousarray(
            enc_bindings.output().get_buffer()
        )

        encoder_ms = (time.monotonic() - start_time) * 1000
        logger.debug(f"Encoder inference: {encoder_ms:.0f}ms")

        # --- Decoder: autoregressive token generation ---
        decoder_start = time.monotonic()

        # Initial prompt tokens: SOT, language, task, no_timestamps
        initial_tokens = [SOT_TOKEN, EN_TOKEN, TRANSCRIBE_TOKEN, NO_TIMESTAMPS_TOKEN]
        seq_len = self._decoder_seq_len

        decoder_input_ids = np.zeros((1, seq_len), dtype=np.int64)
        for i, tok in enumerate(initial_tokens):
            decoder_input_ids[0, i] = tok

        generated_tokens: list[int] = []
        num_initial = len(initial_tokens)

        for step in range(num_initial, seq_len):
            # CPU: token embedding lookup
            token_embeds = self._embed_tokens(decoder_input_ids)

            # Decoder inference (NPU)
            dec_bindings = self._decoder_configured.create_bindings()

            # Set inputs: first is encoder output, second is token embeddings
            # (order determined by HEF input names — typically sorted alphabetically
            # with encoder/cross-attention first)
            input_buffers = self._prepare_decoder_inputs(
                encoded_features, token_embeds
            )
            for name, buf in input_buffers.items():
                dec_bindings.input(name).set_buffer(buf)

            # Allocate output buffers
            output_shapes = {}
            for name in self._decoder_output_names:
                shape = tuple(self._decoder_model.output(name).shape)
                output_shapes[name] = shape
                dec_bindings.output(name).set_buffer(
                    np.zeros(shape, dtype=np.float32)
                )

            self._decoder_configured.run([dec_bindings], 30_000)

            # Concatenate split outputs along last axis to reconstruct logits
            output_arrays = [
                dec_bindings.output(name).get_buffer()
                for name in self._decoder_output_names
            ]
            if len(output_arrays) > 1:
                decoder_output = np.concatenate(output_arrays, axis=-1)
            else:
                decoder_output = output_arrays[0]

            # Get logits for current token position
            # decoder_output shape: (batch, seq_len, vocab_size) or similar
            if decoder_output.ndim == 3:
                logits = decoder_output[0, step - 1].copy()
            elif decoder_output.ndim == 2:
                logits = decoder_output[step - 1].copy()
            else:
                logits = decoder_output.flatten()

            # Repetition penalty — discourage repeated tokens
            for tok in generated_tokens:
                if tok < len(logits):
                    if logits[tok] > 0:
                        logits[tok] /= REPETITION_PENALTY
                    else:
                        logits[tok] *= REPETITION_PENALTY

            # Greedy decode
            next_token = int(np.argmax(logits))

            if next_token == EOT_TOKEN:
                break

            generated_tokens.append(next_token)
            decoder_input_ids[0, step] = next_token

        decoder_ms = (time.monotonic() - decoder_start) * 1000
        total_ms = (time.monotonic() - start_time) * 1000

        # Decode tokens to text
        text = self._tokenizer.decode(generated_tokens, skip_special_tokens=True)
        text = text.strip()

        logger.info(
            f"Transcribed ({total_ms:.0f}ms, enc={encoder_ms:.0f}ms, "
            f"dec={decoder_ms:.0f}ms, {len(generated_tokens)} tokens): "
            f"{text[:100]}"
        )

        return text

    async def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe audio (async wrapper — runs inference in thread pool).

        Uses a lock to serialize NPU access across concurrent connections.
        """
        async with self._inference_lock:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self.transcribe_sync, audio)

    def _embed_tokens(self, decoder_input_ids: np.ndarray) -> np.ndarray:
        """CPU-side token embedding lookup.

        Args:
            decoder_input_ids: Token IDs, shape (1, seq_len).

        Returns:
            Embedded tokens shaped for the decoder HEF input.
        """
        # Embedding lookup: (1, seq_len) -> (1, seq_len, d_model)
        embeds = self._token_embeddings[decoder_input_ids]
        return embeds.astype(np.float32)

    def _prepare_decoder_inputs(
        self,
        encoded_features: np.ndarray,
        token_embeds: np.ndarray,
    ) -> dict[str, np.ndarray]:
        """Prepare named input buffers for decoder HEF.

        Maps discovered HEF input names to the encoder output and token
        embedding tensors. The decoder HEF typically has two inputs:
        one for cross-attention (encoder features) and one for self-attention
        (token embeddings).

        The mapping is inferred by shape matching: the input whose shape
        matches the encoder output goes to encoded_features, and the other
        gets token embeddings.
        """
        if len(self._decoder_input_names) < 2:
            raise RuntimeError(
                f"Expected 2 decoder inputs, found: {self._decoder_input_names}"
            )

        result = {}
        encoder_matched = False

        for name in self._decoder_input_names:
            expected_shape = tuple(self._decoder_model.input(name).shape)

            # Try to match by shape to encoder output
            if not encoder_matched and self._shapes_compatible(
                encoded_features.shape, expected_shape
            ):
                result[name] = np.ascontiguousarray(
                    encoded_features.reshape(expected_shape)
                )
                encoder_matched = True
            else:
                # Token embeddings — reshape to match expected input shape
                result[name] = np.ascontiguousarray(
                    token_embeds.reshape(expected_shape)
                )

        if not encoder_matched:
            # Fallback: assume first input is encoder, second is tokens
            logger.warning(
                "Could not match decoder inputs by shape, using positional order"
            )
            names = sorted(self._decoder_input_names)
            result = {}
            enc_shape = tuple(self._decoder_model.input(names[0]).shape)
            tok_shape = tuple(self._decoder_model.input(names[1]).shape)
            result[names[0]] = np.ascontiguousarray(
                encoded_features.reshape(enc_shape)
            )
            result[names[1]] = np.ascontiguousarray(
                token_embeds.reshape(tok_shape)
            )

        return result

    @staticmethod
    def _shapes_compatible(actual: tuple, expected: tuple) -> bool:
        """Check if actual data can be reshaped to expected shape."""
        actual_size = 1
        for d in actual:
            actual_size *= d
        expected_size = 1
        for d in expected:
            expected_size *= d
        return actual_size == expected_size

    def cleanup(self) -> None:
        """Release Hailo NPU resources."""
        if self._encoder_configured is not None:
            try:
                self._encoder_configured.release()
            except Exception:
                pass
            self._encoder_configured = None
        if self._decoder_configured is not None:
            try:
                self._decoder_configured.release()
            except Exception:
                pass
            self._decoder_configured = None
        if self._vdevice is not None:
            try:
                self._vdevice.release()
            except Exception:
                pass
            self._vdevice = None
        logger.info("Hailo resources released")


# ---------------------------------------------------------------------------
# Wyoming protocol server
# ---------------------------------------------------------------------------
class WyomingWhisperServer:
    """TCP server accepting Wyoming protocol connections for Whisper STT.

    Each connection receives audio via the Wyoming event protocol,
    transcribes using the Hailo engine, and returns a transcript event.

    Wyoming event format (JSON-lines):
        {"type": "event-type", "data": {...}}\\n
        For audio-chunk: data includes "payload_length", followed by raw bytes.
    """

    def __init__(self, engine: HailoWhisperEngine, port: int = 10300):
        self.engine = engine
        self.port = port
        self._server: asyncio.Server | None = None
        self._shutdown_event = asyncio.Event()

    async def start(self) -> None:
        """Start accepting connections."""
        self._server = await asyncio.start_server(
            self._handle_client, "0.0.0.0", self.port
        )
        logger.info(f"Wyoming Whisper server listening on 0.0.0.0:{self.port}")

        async with self._server:
            await self._shutdown_event.wait()

    async def stop(self) -> None:
        """Stop the server."""
        self._shutdown_event.set()
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle a single Wyoming client connection."""
        peer = writer.get_extra_info("peername", ("unknown", 0))
        logger.debug(f"Client connected: {peer}")

        try:
            await self._process_session(reader, writer)
        except asyncio.CancelledError:
            pass
        except ConnectionResetError:
            logger.debug(f"Client disconnected: {peer}")
        except Exception:
            logger.exception(f"Error handling client {peer}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            logger.debug(f"Client session ended: {peer}")

    async def _process_session(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Process one STT request: receive audio, transcribe, send result."""
        audio_chunks: list[bytes] = []
        sample_rate = SAMPLE_RATE
        started = False

        while True:
            event = await self._receive_event(reader)
            if event is None:
                return  # Client disconnected

            event_type = event.get("type", "")
            data = event.get("data", {})

            if event_type == "audio-start":
                sample_rate = data.get("rate", SAMPLE_RATE)
                audio_chunks = []
                started = True
                logger.debug(
                    f"Audio start: rate={sample_rate}, "
                    f"width={data.get('width', 2)}, "
                    f"channels={data.get('channels', 1)}"
                )

            elif event_type == "audio-chunk" and started:
                payload = event.get("payload")
                if payload:
                    audio_chunks.append(payload)

            elif event_type == "audio-stop" and started:
                logger.debug(
                    f"Audio stop: {len(audio_chunks)} chunks received"
                )

                # Combine PCM chunks and convert to float32
                if audio_chunks:
                    pcm_bytes = b"".join(audio_chunks)
                    samples = np.frombuffer(pcm_bytes, dtype=np.int16)
                    audio = samples.astype(np.float32) / 32768.0

                    # Resample if not 16kHz
                    if sample_rate != SAMPLE_RATE:
                        audio = self._resample(audio, sample_rate)

                    # Transcribe
                    try:
                        text = await self.engine.transcribe(audio)
                    except Exception:
                        logger.exception("Transcription failed")
                        await self._send_event(
                            writer, "error", {"message": "Transcription failed"}
                        )
                        return
                else:
                    text = ""

                # Send transcript
                await self._send_event(
                    writer, "transcript", {"text": text}
                )
                return  # One request per connection (matches client behavior)

    @staticmethod
    async def _receive_event(
        reader: asyncio.StreamReader,
        timeout: float = 60.0,
    ) -> dict | None:
        """Receive a Wyoming protocol event."""
        try:
            line = await asyncio.wait_for(reader.readline(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("Client read timeout")
            return None

        if not line:
            return None

        try:
            event = json.loads(line.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning(f"Invalid event: {e}")
            return None

        # Read binary payload if present
        payload_length = event.get("data", {}).get("payload_length", 0)
        if payload_length > 0:
            try:
                payload = await asyncio.wait_for(
                    reader.readexactly(payload_length), timeout=timeout
                )
                event["payload"] = payload
            except (asyncio.TimeoutError, asyncio.IncompleteReadError) as e:
                logger.warning(f"Failed to read payload: {e}")
                return None

        return event

    @staticmethod
    async def _send_event(
        writer: asyncio.StreamWriter,
        event_type: str,
        data: dict,
    ) -> None:
        """Send a Wyoming protocol event."""
        event = {"type": event_type, "data": data}
        message = json.dumps(event) + "\n"
        writer.write(message.encode("utf-8"))
        await writer.drain()

    @staticmethod
    def _resample(audio: np.ndarray, from_rate: int) -> np.ndarray:
        """Resample audio to 16kHz."""
        if from_rate == SAMPLE_RATE:
            return audio
        from math import gcd

        from scipy.signal import resample_poly

        g = gcd(from_rate, SAMPLE_RATE)
        up = SAMPLE_RATE // g
        down = from_rate // g
        return resample_poly(audio, up, down).astype(np.float32)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Wyoming protocol STT server using Hailo-10H Whisper"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=10300,
        help="TCP port to listen on (default: 10300)",
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "models",
        help="Directory containing HEF and NPY model files",
    )
    parser.add_argument(
        "--variant",
        type=str,
        default="tiny",
        choices=["tiny", "tiny.en", "base"],
        help="Whisper model variant (default: tiny)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: INFO)",
    )
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    logger.info(f"Starting Wyoming Hailo Whisper server (variant={args.variant})")
    logger.info(f"Model directory: {args.model_dir}")

    # Initialize Hailo engine
    engine = HailoWhisperEngine(args.model_dir, args.variant)
    try:
        engine.initialize()
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)
    except ImportError as e:
        logger.error(str(e))
        sys.exit(1)

    # Create server
    server = WyomingWhisperServer(engine, args.port)

    # Signal handling
    loop = asyncio.new_event_loop()

    def signal_handler():
        logger.info("Received shutdown signal")
        loop.create_task(server.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    try:
        loop.run_until_complete(server.start())
    except KeyboardInterrupt:
        logger.info("Interrupted")
    finally:
        engine.cleanup()
        loop.close()

    logger.info("Server stopped")


if __name__ == "__main__":
    main()
