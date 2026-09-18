import logging
from typing import Optional, Dict, Any
import httpx

from app.whatsapp.base import NotificationProvider
from app.config.settings import settings

logger = logging.getLogger("nyra.whatsapp.sender")


class MockWhatsAppSender(NotificationProvider):
    """Development / Mock WhatsApp sender logging notifications cleanly to console & file."""

    async def send_summary(
        self,
        recipient: str,
        caller_name: str,
        organization: Optional[str],
        duration_str: str,
        intent: str,
        summary: str,
        action: str,
        priority: str,
        callback_requested: bool,
        preferred_time: Optional[str] = None,
        transcript_link: str = "Available in Dashboard",
    ) -> bool:
        logger.info("=" * 50)
        logger.info(f"📱 [MOCK WHATSAPP] Notification sent to: {recipient}")
        logger.info(f"Caller: {caller_name} | Org: {organization or 'N/A'}")
        logger.info(f"Intent: {intent}")
        logger.info(f"Priority: {priority} | Callback: {callback_requested}")
        logger.info("=" * 50)
        return True

    async def send_text(self, recipient: str, text: str) -> bool:
        logger.info(f"📱 [MOCK WHATSAPP] Message to {recipient}:\n{text}")
        return True


class CloudApiWhatsAppSender(NotificationProvider):
    """Official Meta WhatsApp Cloud API Provider."""

    def __init__(
        self,
        token: str = settings.whatsapp_token,
        phone_id: str = settings.whatsapp_phone_id,
    ):
        self.token = token
        self.phone_id = phone_id
        self.api_url = f"https://graph.facebook.com/v19.0/{self.phone_id}/messages"

    async def send_summary(
        self,
        recipient: str,
        caller_name: str,
        organization: Optional[str],
        duration_str: str,
        intent: str,
        summary: str,
        action: str,
        priority: str,
        callback_requested: bool,
        preferred_time: Optional[str] = None,
        transcript_link: str = "Available in Dashboard",
    ) -> bool:
        message_text = f"🤖 NYRA — NEW CALL\n\nCaller: {caller_name}\nIntent: {intent}\nSummary: {summary}\nAction: {action}"
        return await self.send_text(recipient, message_text)

    async def send_text(self, recipient: str, text: str) -> bool:
        if not self.token or not self.phone_id:
            logger.error("WhatsApp Cloud API credentials not configured.")
            return False

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {"body": text},
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.post(self.api_url, headers=headers, json=payload)
                response.raise_for_status()
                logger.info(f"WhatsApp message sent successfully to {recipient}.")
                return True
            except Exception as e:
                logger.error(f"WhatsApp Cloud API send failed: {e}")
                return False


class WhatsAppService:
    """Factory creating configured WhatsApp sender."""

    @staticmethod
    def get_sender() -> NotificationProvider:
        provider_type = settings.whatsapp_provider.lower()
        if provider_type == "cloud_api":
            return CloudApiWhatsAppSender()
        return MockWhatsAppSender()
