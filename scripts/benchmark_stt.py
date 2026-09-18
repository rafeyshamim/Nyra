import asyncio
import time
import sys
import numpy as np
import soundfile as sf
import io
from pathlib import Path

# Add root directory to path
base_dir = Path(__file__).resolve().parent.parent
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

from app.config.logging import setup_logging, logger
from app.stt.faster_whisper import FasterWhisperSTTProvider


def create_synthetic_sine_audio(duration_sec: float = 2.0, sample_rate: int = 16000) -> bytes:
    """Generate a clean synthetic sine wave WAV audio for testing pipeline speed."""
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), False)
    # Generate 440 Hz tone
    audio = 0.5 * np.sin(2 * np.pi * 440 * t)
    
    buffer = io.BytesIO()
    sf.write(buffer, audio, sample_rate, format="WAV", subtype="PCM_16")
    return buffer.getvalue()


async def main():
    setup_logging()
    print("=" * 60)
    print("   [STT] NYRA - STT Performance Benchmark (faster-whisper)")
    print("=" * 60)

    start_load = time.time()
    stt = FasterWhisperSTTProvider(model_size="tiny", device="cpu", compute_type="int8")
    load_time = time.time() - start_load
    print(f"[OK] Model initialization time: {load_time:.2f}s (Device: {stt.device}, Compute: {stt.compute_type})\n")

    audio_bytes = create_synthetic_sine_audio(duration_sec=2.0)

    print("Transcribing synthetic audio sample...")
    start_trans = time.time()
    result = await stt.transcribe_audio_bytes(audio_bytes)
    trans_time = time.time() - start_trans

    print("=" * 60)
    print(f"[OK] Transcription Latency: {trans_time * 1000:.1f} ms")
    print(f"[OK] Detected Language:    {result.language}")
    print(f"[OK] Confidence Score:    {result.confidence:.2f}")
    print(f"[OK] Transcribed Text:    '{result.text}'")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
