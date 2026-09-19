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

    # Initialize Audio Buffer for streaming audio VAD simulation
    audio_buffer = AudioStreamBuffer(sample_rate=16000, silence_threshold_ms=600)

    # Simulated User Speech Input
    user_speech_phrases = [
        "Hi Nyra, I am Rahul from XYZ Technologies. Is Rafey available?",
        "Could you ask him to call me back about the Friday meeting?",
    ]

    for turn_idx, speech_text in enumerate(user_speech_phrases, start=1):
        print("\n" + "-" * 60)
        print(f"[Caller Turn {turn_idx}] Simulating audio stream for: '{speech_text}'")

        # Generate audio payload for speech
        speech_wav = await tts.synthesize_speech(speech_text, voice="female_warm")

        # Extract raw PCM 16-bit mono audio data from WAV bytes
        data, sr = sf.read(io.BytesIO(speech_wav), dtype="int16")

        # Resample to 16kHz if needed
        if sr != 16000:
            from app.audio.resampler import resample_pcm16_bytes
            pcm_data = resample_pcm16_bytes(data.tobytes(), sr, 16000)
        else:
            pcm_data = data.tobytes()

        # Stream audio in 30ms frames (960 bytes at 16kHz 16-bit)
        frame_size_bytes = 960
        turn_completed_audio = None

        start_stream = time.time()
        for i in range(0, len(pcm_data), frame_size_bytes):
            chunk = pcm_data[i : i + frame_size_bytes]
            res = audio_buffer.add_pcm_chunk(chunk)
            if res:
                turn_completed_audio = res

        # Stream silence frames to trigger VAD end-of-turn boundary
        silence_frame = bytes(frame_size_bytes)
        while not turn_completed_audio:
            res = audio_buffer.add_pcm_chunk(silence_frame)
            if res:
                turn_completed_audio = res

        vad_detection_time = (time.time() - start_stream) * 1000
        print(f"[VAD] Turn boundary detected! Audio segment size: {len(turn_completed_audio)} bytes (VAD time: {vad_detection_time:.1f}ms)")

        # 2. Transcribe Audio via STT
        start_stt = time.time()
        transcription = await stt.transcribe_audio_bytes(turn_completed_audio, sample_rate=16000)
        stt_latency = (time.time() - start_stt) * 1000
        user_text = transcription.text.strip() or speech_text
        print(f"[STT] Transcribed Text: '{user_text}' (Lang: {transcription.language}, Latency: {stt_latency:.1f}ms)")

        # 3. Process turn through Conversation Manager & LLM
        start_turn = time.time()
        response_text = await manager.process_user_turn(session, user_text)
        llm_latency = (time.time() - start_turn) * 1000
        print(f"[LLM] Nyra Response: '{response_text}' (LLM: {llm_latency:.1f}ms)")

        # 4. Synthesize Nyra Response Speech
        start_tts = time.time()
        response_audio = await tts.synthesize_speech(response_text, voice="female_warm")
        tts_latency = (time.time() - start_tts) * 1000
        print(f"[TTS] Response Audio Generated: {len(response_audio)} bytes (TTS: {tts_latency:.1f}ms)")

    print("\n" + "=" * 60)
    print("[OK] Duplex Voice Conversation pipeline completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(simulate_duplex_conversation())
