import asyncio
import time
import sys
import uuid
import io
import logging
import soundfile as sf
import numpy as np
from pathlib import Path
from sqlalchemy import select

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
from app.postcall.analyzer import PostCallProcessor
from app.database.session import init_db, AsyncSessionLocal
from app.database.models import Call, Message


def record_microphone_turn(audio_buffer: AudioStreamBuffer, max_seconds: int = 30):
    """Record one microphone turn until VAD detects the end of speech."""
    try:
        import sounddevice as sd
    except ImportError as exc:
        raise RuntimeError("Microphone support requires sounddevice. Run: pip install sounddevice") from exc

    frame_samples = 480  # 30 ms at 16 kHz
    print("[Microphone] Listening... speak now, then pause when finished.")
    with sd.InputStream(
        samplerate=16000,
        channels=1,
        dtype="int16",
        blocksize=frame_samples,
    ) as stream:
        for _ in range(int(max_seconds * 1000 / 30)):
            frame, _ = stream.read(frame_samples)
            completed_speech = audio_buffer.add_pcm_chunk(np.asarray(frame).tobytes())
            if completed_speech:
                return completed_speech

    return audio_buffer.flush()


def play_wav_audio(wav_bytes: bytes) -> None:
    """Play WAV bytes through the default Windows audio output."""
    try:
        import sounddevice as sd
    except ImportError as exc:
        raise RuntimeError("Speaker support requires sounddevice. Run: pip install sounddevice") from exc

    audio_data, sample_rate = sf.read(io.BytesIO(wav_bytes), dtype="float32")
    sd.play(audio_data, sample_rate)
    sd.wait()


async def run_interactive_duplex_conversation():
    setup_logging()
    await init_db()

    # Configure dedicated log file for local duplex chat session stats
    logs_dir = base_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(logs_dir / "local_duplex_chat.log", encoding="utf-8")
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    print("=" * 60)
    print("   [DUPLEX] NYRA - Interactive Real-Time Voice Chat & VAD Pipeline")
    print("   (Press Enter to speak, type text for text mode, or type 'exit' to end)")
    print("=" * 60)

    logger.info("Starting local interactive duplex conversation session...")

    # Initialize core Nyra providers
    stt = FasterWhisperSTTProvider(model_size="tiny", device="cpu", compute_type="int8")
    llm = OllamaLLMProvider()
    tts = KokoroTTSProvider(default_voice="female_warm")
    manager = ConversationManager(llm_provider=llm)
    postcall_processor = PostCallProcessor(llm_provider=llm)

    call_id = f"local_call_{uuid.uuid4().hex[:8]}"
    phone_number = "+919876543210"
    session = manager.create_session(call_id=call_id, phone_number=phone_number)

    # Persist call in database
    async with AsyncSessionLocal() as db:
        call_rec = Call(call_id=call_id, phone_number=phone_number, status="in-progress")
        db.add(call_rec)
        await db.commit()

    # 1. Initial Greeting
    greeting = manager.get_initial_greeting(session)
    print(f"\nNyra: '{greeting}'")
    logger.info(f"[{call_id}] Nyra Greeting: '{greeting}'")

    start_tts = time.time()
    greeting_audio = await tts.synthesize_speech(greeting, voice="female_warm")
    tts_latency = (time.time() - start_tts) * 1000
    print(f"[Stats] Initial Greeting TTS Latency: {tts_latency:.1f}ms ({len(greeting_audio)} bytes WAV)")
    logger.info(f"[{call_id}] Greeting TTS Latency: {tts_latency:.1f}ms, Audio Size: {len(greeting_audio)} bytes")
    try:
        await asyncio.to_thread(play_wav_audio, greeting_audio)
    except Exception as exc:
        print(f"[Audio Warning] Could not play greeting: {exc}")
        print("The WAV file is still available in memory; continuing with text output.")

    async with AsyncSessionLocal() as db:
        db.add(Message(call_id=call_id, role="assistant", content=greeting))
        await db.commit()

    audio_buffer = AudioStreamBuffer(sample_rate=16000, silence_threshold_ms=600)
    turn_idx = 1

    try:
        while True:
            print("\n" + "-" * 60)
            user_input = input(f"[Caller Turn {turn_idx}] Press Enter to speak or type a message: ").strip()

            if user_input.lower() in ["hangup", "exit", "quit", "bye"]:
                print("\n[Call Ended] Caller hung up.")
                logger.info(f"[{call_id}] Call hung up by user on turn {turn_idx}.")
                break

            if not user_input:
                try:
                    turn_completed_audio = await asyncio.to_thread(record_microphone_turn, audio_buffer)
                except Exception as exc:
                    print(f"[Audio Error] {exc}")
                    print("Type a message instead, or install/check your microphone and speakers.")
                    continue
                if not turn_completed_audio:
                    print("[Microphone] No speech detected. Try again.")
                    continue
            else:
                logger.info(f"[{call_id}] Caller Turn {turn_idx} Input: '{user_input}'")

                # Preserve text mode by synthesizing the typed turn through the same audio pipeline.
                speech_wav = await tts.synthesize_speech(user_input, voice="female_warm")
                data, sr = sf.read(io.BytesIO(speech_wav), dtype="int16")
                if sr != 16000:
                    from app.audio.resampler import resample_pcm16_bytes
                    pcm_data = resample_pcm16_bytes(data.tobytes(), sr, 16000)
                else:
                    pcm_data = data.tobytes()

                frame_size_bytes = 960
                turn_completed_audio = None
                start_vad = time.time()
                for i in range(0, len(pcm_data), frame_size_bytes):
                    res = audio_buffer.add_pcm_chunk(pcm_data[i : i + frame_size_bytes])
                    if res:
                        turn_completed_audio = res
                while not turn_completed_audio:
                    res = audio_buffer.add_pcm_chunk(bytes(frame_size_bytes))
                    if res:
                        turn_completed_audio = res
                vad_latency = (time.time() - start_vad) * 1000

            if not user_input:
                vad_latency = 0.0

            # 2. Transcribe via STT
            start_stt = time.time()
            transcription = await stt.transcribe_audio_bytes(turn_completed_audio, sample_rate=16000)
            stt_latency = (time.time() - start_stt) * 1000
            transcribed_text = transcription.text.strip() or user_input

            print(f"[STT] Transcribed: '{transcribed_text}' (Lang: {transcription.language}, Latency: {stt_latency:.1f}ms, VAD: {vad_latency:.1f}ms)")
            logger.info(f"[{call_id}] STT Result: '{transcribed_text}' [Lang: {transcription.language}, STT Latency: {stt_latency:.1f}ms, VAD: {vad_latency:.1f}ms]")

            # 3. Process Turn via Conversation Manager & Ollama LLM
            start_llm = time.time()
            nyra_response = await manager.process_user_turn(session, transcribed_text)
            llm_latency = (time.time() - start_llm) * 1000

            print(f"\nNyra: '{nyra_response}'")
            logger.info(f"[{call_id}] Nyra LLM Response: '{nyra_response}' [LLM Latency: {llm_latency:.1f}ms]")

            # 4. Synthesize Response Voice via Kokoro TTS
            start_tts = time.time()
            response_audio = await tts.synthesize_speech(nyra_response, voice="female_warm")
            tts_latency = (time.time() - start_tts) * 1000
            total_turn_time = vad_latency + stt_latency + llm_latency + tts_latency

            print(f"[TTS] Generated audio: {len(response_audio)} bytes (TTS Latency: {tts_latency:.1f}ms, Round-Trip: {total_turn_time:.1f}ms)")
            logger.info(f"[{call_id}] TTS Latency: {tts_latency:.1f}ms, Total Turn Round-Trip: {total_turn_time:.1f}ms")
            try:
                await asyncio.to_thread(play_wav_audio, response_audio)
            except Exception as exc:
                print(f"[Audio Warning] Could not play response: {exc}")

            # Persist turn in database
            async with AsyncSessionLocal() as db:
                db.add(Message(call_id=call_id, role="user", content=transcribed_text))
                db.add(Message(call_id=call_id, role="assistant", content=nyra_response))
                await db.commit()

            turn_idx += 1

    finally:
        print("\n" + "=" * 60)
        print("   [POST-CALL] Running Automated Post-Call Analysis...")
        print("=" * 60)

        async with AsyncSessionLocal() as db:
            call_rec = (await db.execute(select(Call).where(Call.call_id == call_id))).scalars().first()
            if call_rec:
                call_rec.status = "completed"
                await db.commit()

            await postcall_processor.process_completed_call(db, session)

            # Retrieve updated call record
            updated_call = (await db.execute(select(Call).where(Call.call_id == call_id))).scalars().first()
            if updated_call:
                summary_msg = (
                    f"\nCall Stats & Summary:\n"
                    f"  Call ID:       {updated_call.call_id}\n"
                    f"  Phone Number:   {updated_call.phone_number}\n"
                    f"  Intent:         {updated_call.intent}\n"
                    f"  Priority:       {updated_call.priority}\n"
                    f"  Requested Action: {updated_call.requested_action}\n"
                    f"  Summary:       {updated_call.summary}\n"
                )
                print(summary_msg)
                logger.info(f"[{call_id}] Post-Call Analysis Completed:\n{summary_msg}")

        print("[OK] Interactive duplex chat session finished successfully!")


if __name__ == "__main__":
    asyncio.run(run_interactive_duplex_conversation())
