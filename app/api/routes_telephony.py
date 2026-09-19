import logging
import uuid
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.conversation.manager import ConversationManager
from app.llm.client import OllamaLLMProvider
from app.stt.faster_whisper import FasterWhisperSTTProvider
from app.tts.kokoro import KokoroTTSProvider
from app.audio.audio_buffer import AudioStreamBuffer
from app.postcall.analyzer import PostCallProcessor
from app.telephony.exotel import ExotelAgentStreamProvider

logger = logging.getLogger("nyra.api.telephony")
router = APIRouter(tags=["Telephony Webhooks & WebSockets"])

llm_provider = OllamaLLMProvider()
stt_provider = FasterWhisperSTTProvider(model_size="tiny", device="cpu", compute_type="int8")
conv_manager = ConversationManager(llm_provider=llm_provider)
tts_provider = KokoroTTSProvider(default_voice="female_warm")
postcall_processor = PostCallProcessor(llm_provider=llm_provider)
exotel_provider = ExotelAgentStreamProvider()


@router.post("/webhooks/telephony")
async def handle_telephony_event(request: Request):
    """Webhook for incoming call events from telephony providers."""
    data = await request.json()
    logger.info(f"Incoming telephony event: {data}")
    return {"status": "accepted"}


@router.websocket("/ws/call/{call_id}")
async def websocket_call_stream(
    websocket: WebSocket,
    call_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Bidirectional WebSocket voice stream for phone calls."""
    await websocket.accept()
    logger.info(f"WebSocket connected for call_id={call_id}")

    session = conv_manager.create_session(call_id=call_id, phone_number="+919876543210")
    greeting_text = conv_manager.get_initial_greeting(session)

    # Synthesize and send initial greeting speech
    greeting_audio = await tts_provider.synthesize_speech(greeting_text)
    response_frame = exotel_provider.format_media_response(call_id, greeting_audio)
    await websocket.send_text(response_frame)

    audio_buffer = AudioStreamBuffer(sample_rate=16000, silence_threshold_ms=600)

    try:
        while True:
            raw_msg = await websocket.receive_text()
            event_type, stream_sid, pcm_bytes = exotel_provider.parse_websocket_event(raw_msg)

            if event_type == "media" and pcm_bytes:
                # Buffer audio frames and wait for turn completion (silence detection)
                completed_speech = audio_buffer.add_pcm_chunk(pcm_bytes)

                if completed_speech:
                    # Transcribe actual caller speech
                    transcription = await stt_provider.transcribe_audio_bytes(completed_speech)
                    user_text = transcription.text.strip()

                    if user_text:
                        logger.info(f"[{call_id}] Caller said: '{user_text}'")
                        nyra_response = await conv_manager.process_user_turn(session, user_text)

                        audio_response = await tts_provider.synthesize_speech(nyra_response)
                        out_frame = exotel_provider.format_media_response(stream_sid or call_id, audio_response)
                        await websocket.send_text(out_frame)
                    else:
                        logger.debug(f"[{call_id}] Silence or non-verbal audio recorded.")

            elif event_type == "stop":
                logger.info(f"Call {call_id} stopped by caller.")
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for call_id={call_id}")
    finally:
        # Flush any remaining speech buffer if call terminates mid-sentence
        remaining_speech = audio_buffer.flush()
        if remaining_speech:
            try:
                transcription = await stt_provider.transcribe_audio_bytes(remaining_speech)
                user_text = transcription.text.strip()
                if user_text:
                    await conv_manager.process_user_turn(session, user_text)
            except Exception as e:
                logger.error(f"Error processing remaining speech buffer for call {call_id}: {e}")

        # Finalize post-call analysis
        try:
            await postcall_processor.process_completed_call(db, session)
        except Exception as e:
            logger.error(f"Post-call processing error for call {call_id}: {e}")
