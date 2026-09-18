import asyncio
import time
import sys
from pathlib import Path

# Add root directory to path
base_dir = Path(__file__).resolve().parent.parent
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

from app.config.logging import setup_logging, logger
from app.config.settings import settings
from app.tts.kokoro import KokoroTTSProvider


async def main():
    setup_logging()
    print("=" * 60)
    print("   [TTS] NYRA - TTS Voice Synthesis Benchmark (Kokoro Neural Voice)")
    print("=" * 60)

    tts = KokoroTTSProvider(default_voice="female_warm")

    test_phrases = [
        ("English", "female_warm", "Hi, I'm Nyra, Rafey's AI assistant. How can I help you today?"),
        ("Hindi", "female_hindi", "Namaste, main Nyra hoon, Rafey ki AI assistant. Aapka call karne ka kya reason hai?"),
        ("Hinglish", "female_warm", "Hi, main Nyra hoon, Rafey ki AI assistant. Rafey is unavailable right now. Aap message chhod sakte hain."),
    ]

    recordings_dir = settings.recordings_dir
    recordings_dir.mkdir(parents=True, exist_ok=True)

    for lang, voice_key, phrase in test_phrases:
        print(f"\nSynthesizing {lang} phrase using voice '{voice_key}'...")
        start_time = time.time()
        wav_bytes = await tts.synthesize_speech(phrase, voice=voice_key)
        latency = (time.time() - start_time) * 1000

        output_path = recordings_dir / f"nyra_greeting_{lang.lower()}.wav"
        with open(output_path, "wb") as f:
            f.write(wav_bytes)

        print(f"[OK] Latency:     {latency:.1f} ms")
        print(f"[OK] Audio Size:  {len(wav_bytes)} bytes ({len(wav_bytes) / 1024:.1f} KB)")
        print(f"[OK] Saved WAV:   {output_path}")

    print("\n" + "=" * 60)
    print("[OK] All TTS benchmarks completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
