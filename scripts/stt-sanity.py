"""STT sanity loopback: Kokoro TTS -> Wyoming/Hailo STT. Usage: stt-sanity.py [phrase]"""
import asyncio, sys
sys.path.insert(0, "/home/tom/tele-ai/payphone-app")
import numpy as np
from scipy.signal import resample_poly
from kokoro_onnx import Kokoro
from services.stt import WyomingSTTClient

PHRASE = sys.argv[1] if len(sys.argv) > 1 else "The quick brown fox jumps over the lazy dog."

async def main():
    k = Kokoro("/home/tom/tele-ai/payphone-app/models/kokoro-v1.0.onnx",
               "/home/tom/tele-ai/payphone-app/models/voices-v1.0.bin")
    samples, sr = k.create(PHRASE, voice="af_bella", speed=1.0)
    audio16 = resample_poly(np.asarray(samples, dtype=np.float32), 16000, sr).astype(np.float32)
    client = WyomingSTTClient("localhost", 10300)
    res = await client.transcribe(audio16, 16000)
    print(f"TRANSCRIPT: {res.text!r}")
    await client.disconnect()

asyncio.run(main())
