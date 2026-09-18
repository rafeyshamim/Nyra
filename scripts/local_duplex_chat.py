import asyncio
import time
import sys
import uuid
import io
import numpy as np
import soundfile as sf
from pathlib import Path

# Add root directory to path
base_dir = Path(__file__).resolve().parent.parent
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

from app.config.logging import setup_logging, logger
from app.audio.audio_buffer import AudioStreamBuffer
from app.stt.faster_whisper import FasterWhisperSTTProvider
from app.llm.client import OllamaLLMProvider
from app.conversation.manager import ConversationManager
from app.tts.kokoro import KokoroTTSProvider


async def simulate_duplex_conversation():
    setup_logging()
    print("=" * 60)
    print("   [DUPLEX] NYRA - Local Full Voice Duplex & VAD Pipeline")
    print("=" * 60)

    # Initialize components
    stt = FasterWhisperSTTProvider(model_size="tiny", device="cpu", compute_type="int8")
    llm = OllamaLLMProvider()
    tts = KokoroTTSProvider(default_voice="female_warm")
    manager = ConversationManager(llm_provider=llm)

    call_id = str(uuid.uuid4())[:8]
    session = manager.create_session(call_id=call_id, phone_number="+919876543210")

    # 1. Initial Greeting
    greeting = manager.get_initial_greeting(session)
    print(f"\nNyra Greeting: '{greeting}'")
    greeting_audio = await tts.synthesize_speech(greeting, voice="female_warm")
    print(f"[OK] Greeting Audio Synthesized ({len(greeting_audio)} bytes)")

    # Simulated User Turns
    user_turns = [
        "Hi Nyra, I'm Rahul from XYZ Technologies. Is Rafey available?",
        "Could you ask him to call me back about the Friday meeting?",
    ]

    for turn_idx, user_speech in enumerate(user_turns, start=1):
        print("\n" + "-" * 60)
        print(f"Simulating Caller Turn {turn_idx}: '{user_speech}'")

        # 2. Process turn through Conversation Manager
        start_turn = time.time()
        response_text = await manager.process_user_turn(session, user_speech)
        llm_latency = (time.time() - start_turn) * 1000

        print(f"Nyra Response: '{response_text}' (LLM: {llm_latency:.1f}ms)")

        # 3. Synthesize Nyra Response Speech
        start_tts = time.time()
        response_audio = await tts.synthesize_speech(response_text, voice="female_warm")
        tts_latency = (time.time() - start_tts) * 1000

        print(f"[OK] Response Audio Generated: {len(response_audio)} bytes (TTS: {tts_latency:.1f}ms)")

    print("\n" + "=" * 60)
    print("[OK] Duplex Voice Conversation pipeline completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(simulate_duplex_conversation())
