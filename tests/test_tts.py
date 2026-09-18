import asyncio
import pytest
from app.tts.kokoro import KokoroTTSProvider
from app.tts.voice_profiles import DEFAULT_VOICE_PROFILES


def test_voice_profiles_loaded():
    assert "female_warm" in DEFAULT_VOICE_PROFILES
    assert "female_calm" in DEFAULT_VOICE_PROFILES
    assert "female_hindi" in DEFAULT_VOICE_PROFILES


def test_tts_synthesize_speech():
    async def run():
        tts = KokoroTTSProvider()
        wav_bytes = await tts.synthesize_speech(
            text="Hi, I am Nyra, Rafey's AI assistant.",
            voice="female_warm",
        )
        assert isinstance(wav_bytes, bytes)
        assert len(wav_bytes) > 44  # Valid WAV header + audio payload

    asyncio.run(run())


def test_tts_stream_speech():
    async def run():
        tts = KokoroTTSProvider()

        async def mock_text_generator():
            yield "Hi there! "
            yield "I am Nyra. "
            yield "How can I help?"

        chunks = []
        async for chunk in tts.stream_speech(mock_text_generator()):
            chunks.append(chunk)

        assert len(chunks) > 0
        for chunk in chunks:
            assert isinstance(chunk, bytes)
            assert len(chunk) > 44

    asyncio.run(run())
