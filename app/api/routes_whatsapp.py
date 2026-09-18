import logging
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.whatsapp.commands import WhatsAppCommandProcessor
from app.config.settings import settings

logger = logging.getLogger("nyra.api.whatsapp")
router = APIRouter(prefix="/webhooks/whatsapp", tags=["WhatsApp Webhook"])
command_processor = WhatsAppCommandProcessor()


@router.get("")
async def verify_whatsapp_webhook(request: Request):
    """Verification endpoint for WhatsApp Cloud API setup."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == settings.whatsapp_token:
        logger.info("WhatsApp webhook verified successfully!")
        return Response(content=challenge, media_type="text/plain")
    return Response(content="Verification failed", status_code=403)


@router.post("")
async def receive_whatsapp_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Handle incoming WhatsApp messages and owner control commands."""
    data = await request.json()
    logger.info(f"Incoming WhatsApp Webhook Payload: {data}")

    try:
        entries = data.get("entry", [])
        for entry in entries:
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])
                for msg in messages:
                    sender = msg.get("from", "")
                    text_body = msg.get("text", {}).get("body", "")

                    if sender and text_body:
                        cmd_res = await command_processor.execute_command(
                            session=db,
                            sender_phone=sender,
                            command_text=text_body,
                        )
                        logger.info(f"Command execution result for {sender}: {cmd_res.message}")
    except Exception as e:
        logger.error(f"Error handling WhatsApp webhook: {e}")

    return {"status": "success"}
