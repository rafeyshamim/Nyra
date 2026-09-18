import logging
import uuid
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.conversation.manager import ConversationManager
from app.llm.client import OllamaLLMProvider
from app.tts.kokoro import KokoroTTSProvider
from app.postcall.analyzer import PostCallProcessor
from app.telephony.exotel import ExotelAgentStreamProvider

logger = logging.getLogger("nyra.api.telephony")
router = APIRouter(tags=["Telephony Webhooks & WebSockets"])

llm_provider = OllamaLLMProvider()
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

    try:
        while True:
            raw_msg = await websocket.receive_text()
            event_type, stream_sid, pcm_bytes = exotel_provider.parse_websocket_event(raw_msg)

            if event_type == "media" and pcm_bytes:
                # Process speech turn
                user_text = "Simulated caller turn text"
                nyra_response = await conv_manager.process_user_turn(session, user_text)

                audio_response = await tts_provider.synthesize_speech(nyra_response)
                out_frame = exotel_provider.format_media_response(stream_sid, audio_response)
                await websocket.send_text(out_frame)

            elif event_type == "stop":
                logger.info(f"Call {call_id} stopped by caller.")
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for call_id={call_id}")
    finally:
        # Finalize post-call analysis
        try:
            await postcall_processor.process_completed_call(db, session)
        except Exception as e:
            logger.error(f"Post-call processing error for call {call_id}: {e}")
