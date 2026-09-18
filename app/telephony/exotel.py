import logging
import json
import base64
from typing import Dict, Any, Optional, Callable, Awaitable, Tuple
from app.telephony.base import TelephonyProvider
from app.config.settings import settings

logger = logging.getLogger("nyra.telephony.exotel")


class ExotelAgentStreamProvider(TelephonyProvider):
    """Exotel AgentStream WebSocket Telephony Provider."""

    def __init__(
        self,
        account_sid: str = settings.exotel_account_sid,
        api_key: str = settings.exotel_api_key,
        api_token: str = settings.exotel_api_token,
    ):
        self.account_sid = account_sid
        self.api_key = api_key
        self.api_token = api_token
        self.active_streams: Dict[str, Dict[str, Any]] = {}
        self.audio_handler: Optional[Callable[[str, bytes], Awaitable[None]]] = None

    async def answer_call(self, call_id: str) -> bool:
        logger.info(f"[Exotel AgentStream] Answering call {call_id}...")
        self.active_streams[call_id] = {"status": "connected"}
        return True

    async def end_call(self, call_id: str) -> bool:
        logger.info(f"[Exotel AgentStream] Ending call {call_id}...")
        if call_id in self.active_streams:
            del self.active_streams[call_id]
        return True

    async def transfer_call(self, call_id: str, destination: str) -> bool:
        logger.info(f"[Exotel AgentStream] Transferring call {call_id} to {destination}...")
        return True

    def register_audio_handler(
        self,
        handler: Callable[[str, bytes], Awaitable[None]],
    ) -> None:
        self.audio_handler = handler

    def parse_websocket_event(self, raw_message: str) -> Tuple[str, str, bytes]:
        """Parse incoming Exotel WebSocket JSON message to (event_type, stream_sid, pcm_bytes)."""
        data = json.loads(raw_message)
        event_type = data.get("event", "")
        stream_sid = data.get("stream_sid", "")

        pcm_bytes = b""
        if event_type == "media":
            payload_b64 = data.get("media", {}).get("payload", "")
            if payload_b64:
                pcm_bytes = base64.b64decode(payload_b64)

        return event_type, stream_sid, pcm_bytes

    def format_media_response(self, stream_sid: str, pcm_bytes: bytes) -> str:
        """Format audio response payload into Exotel AgentStream WebSocket JSON frame."""
        payload_b64 = base64.b64encode(pcm_bytes).decode("utf-8")
        msg = {
            "event": "media",
            "stream_sid": stream_sid,
            "media": {
                "payload": payload_b64,
            },
        }
        return json.dumps(msg)
