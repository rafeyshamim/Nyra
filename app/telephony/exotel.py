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
                raw_audio = base64.b64decode(payload_b64)
                encoding = data.get("media", {}).get("encoding", "").lower()
                sample_rate = int(data.get("media", {}).get("sample_rate") or 16000)

                # Decode audio format if non-PCM16 or non-16kHz
                pcm_bytes = self._convert_to_pcm16_16k(raw_audio, encoding, sample_rate)

        return event_type, stream_sid, pcm_bytes

    def _convert_to_pcm16_16k(self, raw_audio: bytes, encoding: str, sample_rate: int) -> bytes:
        """Convert raw audio payload (e.g., 8kHz / mulaw / pcm) to 16kHz 16-bit mono PCM bytes."""
        import numpy as np
        from app.audio.resampler import resample_pcm16_bytes

        if not raw_audio:
            return b""

        # Decode mulaw / alaw to int16 PCM if needed
        if "mulaw" in encoding or "ulaw" in encoding:
            # μ-law decoding table or transformation
            mulaw_samples = np.frombuffer(raw_audio, dtype=np.uint8)
            # Expand mulaw to int16
            pcm16_data = self._mulaw_to_pcm16(mulaw_samples)
            pcm_bytes = pcm16_data.tobytes()
        elif "alaw" in encoding:
            alaw_samples = np.frombuffer(raw_audio, dtype=np.uint8)
            pcm16_data = self._alaw_to_pcm16(alaw_samples)
            pcm_bytes = pcm16_data.tobytes()
        else:
            pcm_bytes = raw_audio

        # Resample to 16kHz if necessary
        if sample_rate != 16000 and len(pcm_bytes) > 0:
            pcm_bytes = resample_pcm16_bytes(pcm_bytes, orig_sample_rate=sample_rate, target_sample_rate=16000)

        return pcm_bytes

    @staticmethod
    def _mulaw_to_pcm16(mulaw_samples) -> Any:
        import numpy as np
        mu = 255
        y = mulaw_samples.astype(np.float32)
        y = 0x80 - y
        sign = np.sign(y)
        y = np.abs(y)
        exponent = (y.astype(np.int32) >> 4) & 0x07
        mantissa = y.astype(np.int32) & 0x0F
        sample = ((mantissa << 3) + 0x84) << exponent
        sample = sample - 0x84
        sample = sign * sample
        return np.clip(sample, -32768, 32767).astype(np.int16)

    @staticmethod
    def _alaw_to_pcm16(alaw_samples) -> Any:
        import numpy as np
        y = alaw_samples ^ 0x55
        sign = np.where((y & 0x80) != 0, -1, 1)
        exponent = (y & 0x70) >> 4
        mantissa = y & 0x0F
        if (exponent == 0):
            sample = (mantissa << 4) + 8
        else:
            sample = ((mantissa << 4) + 0x108) << (exponent - 1)
        return np.clip(sign * sample, -32768, 32767).astype(np.int16)

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
