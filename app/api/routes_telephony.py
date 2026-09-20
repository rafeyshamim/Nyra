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
from fastapi import HTTPException, status
from fastapi.responses import Response, JSONResponse
from sqlalchemy import select
from app.config.settings import settings
from app.contacts.resolver import CallerResolver
from app.conversation.state import CallSession
import datetime
from app.database.models import Call, Message

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


async def get_or_create_call_record(db: AsyncSession, call_id: str, phone_number: str, status_str: str = "ringing") -> Call:
    """Persist or retrieve call record in database for multi-worker durability."""
    res = await db.execute(select(Call).where(Call.call_id == call_id))
    call_rec = res.scalars().first() if hasattr(res, "scalars") else None
    if not call_rec:
        call_rec = Call(
            call_id=call_id,
            phone_number=phone_number,
            status=status_str,
        )
        db.add(call_rec)
        await db.commit()
        await db.refresh(call_rec)
    elif call_rec.status != status_str and status_str != "ringing":
        call_rec.status = status_str
        await db.commit()
    return call_rec


async def finalize_call_session(call_id: str, db: AsyncSession, session: Optional[CallSession] = None):
    """Ensure post-call processing is executed exactly once per call."""
    # Check DB record status first
    res = await db.execute(select(Call).where(Call.call_id == call_id))
    call_rec = res.scalars().first() if hasattr(res, "scalars") else None
    if call_rec and call_rec.status in ["completed", "analyzed"]:
        logger.info(f"Call {call_id} already marked as completed in database. Skipping duplicate finalization.")
        return

    call_entry = active_calls.get(call_id)
    if not call_entry:
        call_entry = {"call_id": call_id, "processed": False, "processing": False}
        active_calls[call_id] = call_entry

    if call_entry.get("processed"):
        logger.info(f"Call {call_id} post-call analysis already processed. Skipping duplicate.")
        return

    if call_entry.get("processing"):
        logger.info(f"Call {call_id} post-call analysis currently in progress. Skipping concurrent attempt.")
        return

    call_entry["processing"] = True
    session_to_process = call_entry.get("session") or session

    if not session_to_process and call_rec:
        # Multi-worker recovery: reconstruct session from DB
        caller_number = call_rec.phone_number
        caller_ctx = await CallerResolver.resolve_caller_context(db, caller_number) if caller_number else {}
        session_to_process = conv_manager.create_session(
            call_id=call_id,
            phone_number=caller_number,
            caller_name=caller_ctx.get("caller_name"),
        )
        res_msgs = await db.execute(select(Message).where(Message.call_id == call_id).order_by(Message.id.asc()))
        db_msgs = res_msgs.scalars().all() if hasattr(res_msgs, "scalars") else []
        for m in db_msgs:
            session_to_process.messages.append({"role": m.role, "content": m.content})
        call_entry["session"] = session_to_process

    if session_to_process:
        try:
            await postcall_processor.process_completed_call(db, session_to_process)
            call_entry["processed"] = True
            if call_rec:
                call_rec.status = "completed"
                await db.commit()
        except Exception as e:
            logger.error(f"Post-call processing error for call {call_id}: {e}")
        finally:
            call_entry["processing"] = False


def verify_webhook_auth(request: Request, data: Dict[str, Any]):
    """Verify telephony webhook token if TELEPHONY_WEBHOOK_TOKEN setting is configured."""
    expected_token = settings.telephony_webhook_token
    if not expected_token:
        return

    auth_header = request.headers.get("x-webhook-token") or request.headers.get("authorization", "")
    token_param = data.get("token") or data.get("webhook_token")

    provided_token = ""
    if auth_header:
        provided_token = auth_header.replace("Bearer ", "").strip()
    elif token_param:
        provided_token = str(token_param).strip()

    if provided_token != expected_token:
        logger.warning(f"Unauthorized telephony webhook request from {request.client.host if request.client else 'unknown'}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing webhook verification token",
        )


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
    verify_webhook_auth(request, data)
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

    # Store call session in registry and SQLite DB
    active_calls[call_id] = {
        "call_id": call_id,
        "phone_number": phone_number,
        "session": session,
        "status": "ringing",
        "caller_ctx": caller_ctx,
    }
    await get_or_create_call_record(db, call_id, phone_number, status_str="ringing")

    # Construct WebSocket URL for Exotel AgentStream connection
    base_url = settings.public_base_url.rstrip("/")
    if base_url.startswith("https://"):
        ws_base = base_url.replace("https://", "wss://", 1)
    elif base_url.startswith("http://"):
        ws_base = base_url.replace("http://", "ws://", 1)
    else:
        ws_base = f"wss://{base_url}"

    ws_url = f"{ws_base}/ws/call/{call_id}"

    # Return Exotel XML connect instructions by default (or JSON if application/json requested)
    accept_header = request.headers.get("accept", "").lower()
    if "application/json" in accept_header:
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

    xml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{ws_url}" />
    </Connect>
</Response>"""
    return Response(content=xml_response, media_type="application/xml")


@router.api_route("/call/status", methods=["GET", "POST"])
@router.post("/webhooks/telephony")
async def handle_telephony_event(request: Request, db: AsyncSession = Depends(get_db_session)):
    """Webhook for telephony status events (call-start, call-answer, call-end, failed-call)."""
    data = await parse_incoming_request(request)
    verify_webhook_auth(request, data)
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

        res = await db.execute(select(Call).where(Call.call_id == call_id))
        call_rec = res.scalars().first() if hasattr(res, "scalars") else None

        is_ws_active = call_entry.get("ws_active", False) if call_entry else False
        is_in_progress = (call_rec.status == "in-progress") if call_rec else False

        # Stale call check: if in-progress but no local active WS and started > 300s ago (worker crashed)
        is_stale = False
        if is_in_progress and not is_ws_active and call_rec and call_rec.started_at:
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            started_at = call_rec.started_at
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=datetime.timezone.utc)
            if (now_utc - started_at).total_seconds() > 300:
                is_stale = True
                logger.warning(f"Call {call_id} detected as stale in-progress call (>300s old). Forcing finalization recovery.")

        if is_ws_active or (is_in_progress and not is_stale):
            logger.info(f"WebSocket stream is active/in-progress for call {call_id}. Deferring finalization to WebSocket cleanup.")
        else:
            await finalize_call_session(call_id, db)
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

    # Retrieve existing session from registry or DB fallback
    call_entry = active_calls.get(call_id)
    if call_entry and call_entry.get("session"):
        session = call_entry["session"]
    else:
        # Check DB for pre-registered call record
        res = await db.execute(select(Call).where(Call.call_id == call_id))
        call_rec = res.scalars().first() if hasattr(res, "scalars") else None
        caller_number = call_rec.phone_number if call_rec else "Unknown"

        caller_ctx = await CallerResolver.resolve_caller_context(db, caller_number) if caller_number != "Unknown" else {}
        session = conv_manager.create_session(
            call_id=call_id,
            phone_number=caller_number,
            caller_name=caller_ctx.get("caller_name"),
        )

        # Load existing DB messages if present for multi-worker continuity
        res_msgs = await db.execute(select(Message).where(Message.call_id == call_id).order_by(Message.id.asc()))
        db_msgs = res_msgs.scalars().all() if hasattr(res_msgs, "scalars") else []
        for m in db_msgs:
            session.messages.append({"role": m.role, "content": m.content})

        active_calls[call_id] = {
            "call_id": call_id,
            "phone_number": caller_number,
            "session": session,
            "status": "in-progress",
            "caller_ctx": caller_ctx,
        }
        call_entry = active_calls[call_id]

    call_entry["ws_active"] = True
    call_entry["status"] = "in-progress"

    await get_or_create_call_record(db, call_id, session.phone_number, status_str="in-progress")

    greeting_sent = False
    if any(m.get("role") == "assistant" for m in session.messages):
        greeting_sent = True

    audio_buffer = AudioStreamBuffer(sample_rate=16000, silence_threshold_ms=600)

    try:
        while True:
            raw_msg = await websocket.receive_text()
            event_type, stream_sid, pcm_bytes = exotel_provider.parse_websocket_event(raw_msg)
            active_stream_id = stream_sid or call_id

            # Send greeting upon receiving 'start' event or first media frame
            if not greeting_sent and (event_type in ["start", "connected"] or (event_type == "media" and active_stream_id)):
                greeting_text = conv_manager.get_initial_greeting(session)
                db.add(Message(call_id=call_id, role="assistant", content=greeting_text))
                await db.commit()

                greeting_audio = await tts_provider.synthesize_speech(greeting_text)
                response_frame = exotel_provider.format_media_response(active_stream_id, greeting_audio)
                await websocket.send_text(response_frame)
                greeting_sent = True
                logger.info(f"[{call_id}] Initial greeting sent to stream {active_stream_id}.")

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

                        # Persist turn messages to DB for multi-worker state durability
                        db.add(Message(call_id=call_id, role="user", content=user_text))
                        db.add(Message(call_id=call_id, role="assistant", content=nyra_response))
                        await db.commit()

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
        call_entry["ws_active"] = False

        # Flush any remaining speech buffer if call terminates mid-sentence
        remaining_speech = audio_buffer.flush()
        if remaining_speech:
            try:
                transcription = await stt_provider.transcribe_audio_bytes(remaining_speech)
                user_text = transcription.text.strip()
                if user_text:
                    nyra_resp = await conv_manager.process_user_turn(session, user_text)
                    db.add(Message(call_id=call_id, role="user", content=user_text))
                    db.add(Message(call_id=call_id, role="assistant", content=nyra_resp))
                    await db.commit()
            except Exception as e:
                logger.error(f"Error processing remaining speech buffer for call {call_id}: {e}")

        # Finalize post-call analysis (idempotent)
        await finalize_call_session(call_id, db, session)
