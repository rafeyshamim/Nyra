import logging
import json
import asyncio
from typing import Dict, Any, Optional, Callable, Awaitable
from app.telephony.base import TelephonyProvider

logger = logging.getLogger("nyra.telephony.android")


class AndroidGatewayTelephonyProvider(TelephonyProvider):
    """Telephony provider for Android SIM Gateway / Bluetooth HFP bridge."""

    def __init__(self):
        self.active_calls: Dict[str, Dict[str, Any]] = {}
        self.audio_handler: Optional[Callable[[str, bytes], Awaitable[None]]] = None

    async def answer_call(self, call_id: str) -> bool:
        logger.info(f"[Android SIM Gateway] Answering incoming call {call_id}...")
        self.active_calls[call_id] = {"status": "answered", "call_id": call_id}
        return True

    async def end_call(self, call_id: str) -> bool:
        logger.info(f"[Android SIM Gateway] Terminating call {call_id}...")
        if call_id in self.active_calls:
            self.active_calls[call_id]["status"] = "ended"
            del self.active_calls[call_id]
        return True

    async def transfer_call(self, call_id: str, destination: str) -> bool:
        logger.info(f"[Android SIM Gateway] Transferring call {call_id} to {destination}...")
        return True

    def register_audio_handler(
        self,
        handler: Callable[[str, bytes], Awaitable[None]],
    ) -> None:
        self.audio_handler = handler

    async def handle_incoming_pcm_audio(self, call_id: str, pcm_chunk: bytes):
        """Process incoming raw audio from Android gateway connection."""
        if self.audio_handler:
            await self.audio_handler(call_id, pcm_chunk)
