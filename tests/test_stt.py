import asyncio
import io
import pytest
import numpy as np
import soundfile as sf
from app.stt.faster_whisper import FasterWhisperSTTProvider


def create_sample_wav() -> bytes:
    sample_rate = 16000
    duration = 1.0
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio = 0.5 * np.sin(2 * np.pi * 440 * t)

    buffer = io.BytesIO()
    sf.write(buffer, audio, sample_rate, format="WAV", subtype="PCM_16")
    return buffer.getvalue()


def test_stt_provider_initialization():
    stt = FasterWhisperSTTProvider(model_size="tiny", device="cpu", compute_type="int8")
    assert stt.model is not None
    assert stt.device == "cpu"


def test_stt_transcribe_audio_bytes():
    async def run():
        stt = FasterWhisperSTTProvider(model_size="tiny", device="cpu", compute_type="int8")
        wav_bytes = create_sample_wav()
        result = await stt.transcribe_audio_bytes(wav_bytes)

        assert isinstance(result.text, str)
        assert isinstance(result.language, str)
        assert isinstance(result.confidence, float)

    asyncio.run(run())
