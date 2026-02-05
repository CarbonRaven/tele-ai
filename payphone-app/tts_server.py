#!/usr/bin/env python3
"""Standalone TTS server for offloading synthesis to Pi #2.

This server runs Kokoro-82M TTS and exposes an HTTP API for remote synthesis.
Running TTS on Pi #2 offloads ~30% CPU from Pi #1 during speech output.

Usage:
    # On Pi #2 (10.10.10.11)
    python tts_server.py

    # Or with custom settings
    TTS_SERVER_HOST=0.0.0.0 TTS_SERVER_PORT=10200 python tts_server.py

The server exposes:
    GET  /health     - Health check, returns sample rate
    POST /synthesize - Synthesize text to audio

Requirements:
    pip install fastapi uvicorn kokoro-onnx numpy
"""

import asyncio
import base64
import logging
import os
from contextlib import asynccontextmanager

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Server configuration from environment
HOST = os.getenv("TTS_SERVER_HOST", "0.0.0.0")
PORT = int(os.getenv("TTS_SERVER_PORT", "10200"))
MODEL_PATH = os.getenv("TTS_MODEL_PATH", "kokoro-v1.0.onnx")
VOICES_PATH = os.getenv("TTS_VOICES_PATH", "voices-v1.0.bin")

# Global model instance
_model = None
_lock = asyncio.Lock()
SAMPLE_RATE = 24000
MAX_TEXT_LENGTH = 2000  # Reject requests exceeding this to prevent DoS


class SynthesizeRequest(BaseModel):
    """Request body for synthesis endpoint."""

    text: str
    voice: str = "af_bella"
    speed: float = 1.0


class SynthesizeResponse(BaseModel):
    """Response body for synthesis endpoint."""

    audio: str  # Base64-encoded float32 audio
    sample_rate: int
    duration_seconds: float


class HealthResponse(BaseModel):
    """Response body for health endpoint."""

    status: str
    sample_rate: int
    model_loaded: bool
    available_voices: list[str]


def load_model():
    """Load the Kokoro TTS model."""
    global _model

    try:
        from kokoro_onnx import Kokoro

        logger.info(f"Loading Kokoro model from {MODEL_PATH}")
        _model = Kokoro(MODEL_PATH, VOICES_PATH)
        logger.info(f"Model loaded. Available voices: {_model.get_voices()}")

    except FileNotFoundError as e:
        logger.error(f"Model files not found: {e}")
        logger.error(
            "Download models from: https://github.com/thewh1teagle/kokoro-onnx/releases"
        )
        raise

    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup: load model
    logger.info("Starting TTS server...")
    load_model()
    logger.info(f"TTS server ready on {HOST}:{PORT}")

    yield

    # Shutdown: cleanup
    logger.info("Shutting down TTS server...")


app = FastAPI(
    title="Kokoro TTS Server",
    description="Remote TTS service for payphone-ai",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy" if _model is not None else "degraded",
        sample_rate=SAMPLE_RATE,
        model_loaded=_model is not None,
        available_voices=_model.get_voices() if _model else [],
    )


@app.post("/synthesize", response_model=SynthesizeResponse)
async def synthesize(request: SynthesizeRequest):
    """Synthesize text to audio.

    Args:
        request: Synthesis parameters (text, voice, speed).

    Returns:
        Base64-encoded audio data with metadata.
    """
    if _model is None:
        raise HTTPException(status_code=503, detail="TTS model not loaded")

    if not request.text or not request.text.strip():
        # Return empty audio for empty text
        return SynthesizeResponse(
            audio=base64.b64encode(np.array([], dtype=np.float32).tobytes()).decode(),
            sample_rate=SAMPLE_RATE,
            duration_seconds=0.0,
        )

    if len(request.text) > MAX_TEXT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Text exceeds maximum length of {MAX_TEXT_LENGTH} characters",
        )

    # Acquire lock to prevent concurrent synthesis (model not thread-safe)
    async with _lock:
        loop = asyncio.get_running_loop()

        try:
            # Run synthesis in executor to avoid blocking
            samples, sample_rate = await loop.run_in_executor(
                None,
                lambda: _model.create(
                    request.text,
                    voice=request.voice,
                    speed=request.speed,
                ),
            )

            # Convert to float32 and encode
            audio = samples.astype(np.float32)
            audio_bytes = audio.tobytes()
            audio_b64 = base64.b64encode(audio_bytes).decode()

            duration = len(audio) / sample_rate

            logger.debug(
                f"Synthesized {len(request.text)} chars -> {duration:.2f}s audio"
            )

            return SynthesizeResponse(
                audio=audio_b64,
                sample_rate=sample_rate,
                duration_seconds=duration,
            )

        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "tts_server:app",
        host=HOST,
        port=PORT,
        log_level="info",
        access_log=True,
    )
