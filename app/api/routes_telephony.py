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

from typing import Dict, Any, Optional
from fastapi.responses import Response, JSONResponse
from app.config.settings import settings
from app.contacts.resolver import CallerResolver

logger = logging.getLogger("nyra.api.telephony")
router = APIRouter(tags=["Telephony Webhooks & WebSockets"])

llm_provider = OllamaLLMProvider()
stt_provider = FasterWhisperSTTProvider(model_size="tiny", device="cpu", compute_type="int8")
conv_manager = ConversationManager(llm_provider=llm_provider)
tts_provider = KokoroTTSProvider(default_voice="female_warm")
postcall_processor = PostCallProcessor(llm_provider=llm_provider)
exotel_provider = ExotelAgentStreamProvider()

# Registry of active call metadata indexed by call_id / CallSid
active_calls: Dict[str, Dict[str, Any]] = {}


async def parse_incoming_request(request: Request) -> Dict[str, Any]:
    """Parse request parameters from JSON body, form data, or query params."""
    data: Dict[str, Any] = {}

    # Query params
    if request.query_params:
        data.update(dict(request.query_params))

    # Content-type handling
    content_type = request.headers.get("content-type", "").lower()
    if "application/json" in content_type:
        try:
            body = await request.json()
            if isinstance(body, dict):
                data.update(body)
        except Exception:
            pass
    elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        try:
            form = await request.form()
            data.update({k: str(v) for k, v in form.items()})
        except Exception:
            pass

    return data


def extract_call_id_and_number(data: Dict[str, Any]) -> tuple[str, str]:
    """Extract call_id and caller phone number from parsed payload."""
    call_id = (
        data.get("CallSid")
        or data.get("call_id")
        or data.get("sid")
        or data.get("uuid")
        or f"call_{uuid.uuid4().hex[:10]}"
    )

    phone_number = (
        data.get("From")
        or data.get("Caller")
        or data.get("phone_number")
        or data.get("from_number")
        or data.get("CallerNumber")
        or ""
    )

    # Normalize phone number if missing leading +
    if phone_number and not phone_number.startswith("+") and phone_number.isdigit():
        if len(phone_number) == 10:
            phone_number = f"+91{phone_number}"
        elif len(phone_number) == 12 and phone_number.startswith("91"):
            phone_number = f"+{phone_number}"

    return call_id, phone_number


@router.api_route("/call/incoming", methods=["GET", "POST"])
async def handle_incoming_call(request: Request, db: AsyncSession = Depends(get_db_session)):
    """Callback route for incoming call events from Exotel / telephony providers."""
    data = await parse_incoming_request(request)
    call_id, phone_number = extract_call_id_and_number(data)

    logger.info(f"Incoming call callback received: call_id={call_id}, phone_number={phone_number}")

    # Resolve caller context from contacts database
    caller_ctx = await CallerResolver.resolve_caller_context(db, phone_number)
    caller_name = caller_ctx.get("caller_name")

    # Create Nyra conversation session
    session = conv_manager.create_session(
        call_id=call_id,
        phone_number=phone_number,
        caller_name=caller_name,
    )

    # Store call session in registry
    active_calls[call_id] = {
        "call_id": call_id,
        "phone_number": phone_number,
        "session": session,
        "status": "ringing",
        "caller_ctx": caller_ctx,
    }

    # Construct WebSocket URL for Exotel AgentStream connection
    base_url = settings.public_base_url.rstrip("/")
    if base_url.startswith("https://"):
        ws_base = base_url.replace("https://", "wss://", 1)
    elif base_url.startswith("http://"):
        ws_base = base_url.replace("http://", "ws://", 1)
    else:
        ws_base = f"wss://{base_url}"

    ws_url = f"{ws_base}/ws/call/{call_id}"

    # Return Exotel XML or JSON connect instructions depending on Accept header or default
    accept_header = request.headers.get("accept", "").lower()
    if "xml" in accept_header:
        xml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{ws_url}" />
    </Connect>
</Response>"""
        return Response(content=xml_response, media_type="application/xml")

    return JSONResponse(
        content={
            "status": "accepted",
            "call_id": call_id,
            "phone_number": phone_number,
            "websocket_url": ws_url,
            "select": {
                "stream": {
                    "url": ws_url
                }
            },
            "response": {
                "connect": {
                    "stream": {
                        "url": ws_url
                    }
                }
            }
        }
    )


@router.api_route("/call/status", methods=["GET", "POST"])
@router.post("/webhooks/telephony")
async def handle_telephony_event(request: Request, db: AsyncSession = Depends(get_db_session)):
    """Webhook for telephony status events (call-start, call-answer, call-end, failed-call)."""
    data = await parse_incoming_request(request)
    call_id, phone_number = extract_call_id_and_number(data)
    event_type = (
        data.get("EventType")
        or data.get("event")
        or data.get("Status")
        or data.get("CallStatus")
        or "unknown"
    ).lower()

    logger.info(f"Telephony event received: call_id={call_id}, event={event_type}, data={data}")

    call_entry = active_calls.get(call_id)

    if event_type in ["call-start", "ringing"]:
        if call_entry:
            call_entry["status"] = "ringing"
        logger.info(f"Call {call_id} is ringing.")

    elif event_type in ["call-answer", "in-progress", "answered"]:
        if call_entry:
            call_entry["status"] = "in-progress"
        logger.info(f"Call {call_id} answered.")

    elif event_type in ["call-end", "completed", "terminated", "finished"]:
        if call_entry:
            call_entry["status"] = "completed"
            session = call_entry.get("session")
            if session:
                try:
                    await postcall_processor.process_completed_call(db, session)
                except Exception as e:
                    logger.error(f"Error processing completed call {call_id}: {e}")
        logger.info(f"Call {call_id} ended.")

    elif event_type in ["failed-call", "failed", "busy", "no-answer", "canceled"]:
        if call_entry:
            call_entry["status"] = "failed"
        logger.info(f"Call {call_id} failed with event: {event_type}")

    return {"status": "accepted", "call_id": call_id, "event": event_type}


@router.websocket("/ws/call/{call_id}")
async def websocket_call_stream(
    websocket: WebSocket,
    call_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Bidirectional WebSocket voice stream for phone calls."""
    await websocket.accept()
    logger.info(f"WebSocket connected for call_id={call_id}")

    # Retrieve existing session from registry or create a new session
    call_entry = active_calls.get(call_id)
    if call_entry and call_entry.get("session"):
        session = call_entry["session"]
    else:
        # Fallback to resolver if session was not pre-registered via /call/incoming
        caller_number = (call_entry.get("phone_number") if call_entry else "") or "Unknown"
        caller_ctx = await CallerResolver.resolve_caller_context(db, caller_number) if caller_number != "Unknown" else {}
        session = conv_manager.create_session(
            call_id=call_id,
            phone_number=caller_number,
            caller_name=caller_ctx.get("caller_name"),
        )
        active_calls[call_id] = {
            "call_id": call_id,
            "phone_number": caller_number,
            "session": session,
            "status": "in-progress",
            "caller_ctx": caller_ctx,
        }

    if call_entry:
        call_entry["status"] = "in-progress"
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
