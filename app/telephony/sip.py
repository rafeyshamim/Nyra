import asyncio
import logging
import re
import time
import struct
import random
from typing import Dict, Any, Optional, Callable, Awaitable, Tuple
from app.telephony.base import TelephonyProvider
from app.config.settings import settings
from app.audio.codecs import (
    decode_audio_to_pcm16_16k,
    encode_pcm16_16k_to_target,
    pcm16_to_mulaw,
    mulaw_to_pcm16,
)

logger = logging.getLogger("nyra.telephony.sip")


class RTPPacket:
    """RFC 3550 RTP Packet parser and builder."""

    def __init__(
        self,
        payload_type: int = 0,  # 0 = PCMU / G.711 mu-law
        sequence_number: int = 0,
        timestamp: int = 0,
        ssrc: int = 0,
        payload: bytes = b"",
    ):
        self.version = 2
        self.padding = 0
        self.extension = 0
        self.csrc_count = 0
        self.marker = 0
        self.payload_type = payload_type
        self.sequence_number = sequence_number
        self.timestamp = timestamp
        self.ssrc = ssrc
        self.payload = payload

    @classmethod
    def parse(cls, raw_data: bytes) -> Optional["RTPPacket"]:
        if len(raw_data) < 12:
            return None

        header = struct.unpack("!BBHII", raw_data[:12])
        b0, b1 = header[0], header[1]

        version = (b0 >> 6) & 0x03
        if version != 2:
            return None

        padding = (b0 >> 5) & 0x01
        extension = (b0 >> 4) & 0x01
        csrc_count = b0 & 0x0F
        marker = (b1 >> 7) & 0x01
        payload_type = b1 & 0x7F

        seq_num = header[2]
        timestamp = header[3]
        ssrc = header[4]

        offset = 12 + (csrc_count * 4)
        if extension and len(raw_data) >= offset + 4:
            ext_len = struct.unpack("!H", raw_data[offset + 2:offset + 4])[0]
            offset += 4 + (ext_len * 4)

        if len(raw_data) < offset:
            return None

        payload = raw_data[offset:]
        if padding and len(payload) > 0:
            pad_len = payload[-1]
            if pad_len <= len(payload):
                payload = payload[:-pad_len]

        pkt = cls(
            payload_type=payload_type,
            sequence_number=seq_num,
            timestamp=timestamp,
            ssrc=ssrc,
            payload=payload,
        )
        pkt.padding = padding
        pkt.extension = extension
        pkt.csrc_count = csrc_count
        pkt.marker = marker
        return pkt

    def build(self) -> bytes:
        b0 = (self.version << 6) | (self.padding << 5) | (self.extension << 4) | (self.csrc_count & 0x0F)
        b1 = (self.marker << 7) | (self.payload_type & 0x7F)
        header = struct.pack("!BBHII", b0, b1, self.sequence_number & 0xFFFF, self.timestamp & 0xFFFFFFFF, self.ssrc & 0xFFFFFFFF)
        return header + self.payload


class SIPTelephonyProvider(TelephonyProvider):
    """Local SIP PBX & Peer Telephony Gateway Provider for Nyra."""

    def __init__(
        self,
        server_host: str = settings.SIP_SERVER_HOST if hasattr(settings, "SIP_SERVER_HOST") else "0.0.0.0",
        server_port: int = settings.SIP_SERVER_PORT if hasattr(settings, "SIP_SERVER_PORT") else 5060,
        extension: str = settings.SIP_EXTENSION if hasattr(settings, "SIP_EXTENSION") else "1001",
        password: str = settings.SIP_PASSWORD if hasattr(settings, "SIP_PASSWORD") else "",
    ):
        self.server_host = server_host
        self.server_port = server_port
        self.extension = extension
        self.password = password

        self.active_calls: Dict[str, Dict[str, Any]] = {}
        self.audio_handler: Optional[Callable[[str, bytes], Awaitable[None]]] = None

        self._sip_transport: Optional[asyncio.DatagramTransport] = None
        self._rtp_transport: Optional[asyncio.DatagramTransport] = None
        self._ssrc = random.randint(100000, 999999)
        self._rtp_seq = random.randint(1000, 9999)
        self._rtp_ts = random.randint(10000, 99999)

    def register_audio_handler(
        self,
        handler: Callable[[str, bytes], Awaitable[None]],
    ) -> None:
        self.audio_handler = handler

    async def answer_call(self, call_id: str) -> bool:
        """Answer incoming call by setting status to in-progress."""
        logger.info(f"[SIP Provider] Answering call {call_id}...")
        call_info = self.active_calls.get(call_id)
        if call_info:
            call_info["status"] = "in-progress"
            call_info["answered_at"] = time.time()
            return True
        return False

    async def end_call(self, call_id: str) -> bool:
        """Terminate call and cleanup resources."""
        logger.info(f"[SIP Provider] Terminating call {call_id}...")
        call_info = self.active_calls.get(call_id)
        if call_info:
            call_info["status"] = "completed"
            call_info["ended_at"] = time.time()
            if call_id in self.active_calls:
                del self.active_calls[call_id]
            return True
        return False

    async def transfer_call(self, call_id: str, destination: str) -> bool:
        logger.info(f"[SIP Provider] Transferring call {call_id} to {destination}...")
        return True

    def parse_sip_message(self, raw_data: bytes) -> Dict[str, Any]:
        """Parse raw SIP request or response text into structured dictionary."""
        text = raw_data.decode("utf-8", errors="ignore")
        parts = text.split("\r\n\r\n", 1)
        header_lines = parts[0].split("\r\n")
        body = parts[1] if len(parts) > 1 else ""

        first_line = header_lines[0]
        method = ""
        uri = ""
        status_code = 0

        if first_line.startswith("SIP/2.0"):
            method_match = re.search(r"SIP/2.0\s+(\d+)\s+(.*)", first_line)
            if method_match:
                status_code = int(method_match.group(1))
        else:
            first_parts = first_line.split()
            if len(first_parts) >= 2:
                method = first_parts[0]
                uri = first_parts[1]

        headers: Dict[str, str] = {}
        for line in header_lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()

        call_id = headers.get("call-id", "")
        from_header = headers.get("from", "")
        to_header = headers.get("to", "")
        cseq = headers.get("cseq", "")

        # Extract caller phone / extension number from From header
        caller_match = re.search(r"sip:([^@>]+)", from_header)
        phone_number = caller_match.group(1) if caller_match else "Unknown"

        # Parse SDP body for remote RTP media host and port
        remote_rtp_host = ""
        remote_rtp_port = 0
        if "c=IN IP4 " in body:
            host_match = re.search(r"c=IN IP4 ([\d\.]+)", body)
            if host_match:
                remote_rtp_host = host_match.group(1)
        if "m=audio " in body:
            port_match = re.search(r"m=audio (\d+)", body)
            if port_match:
                remote_rtp_port = int(port_match.group(1))

        return {
            "method": method,
            "status_code": status_code,
            "uri": uri,
            "headers": headers,
            "call_id": call_id,
            "phone_number": phone_number,
            "from_header": from_header,
            "to_header": to_header,
            "cseq": cseq,
            "remote_rtp_host": remote_rtp_host,
            "remote_rtp_port": remote_rtp_port,
            "body": body,
        }

    def process_incoming_rtp(self, raw_rtp: bytes, call_id: str) -> bytes:
        """Decode incoming RFC 3550 PCMU 8 kHz RTP frame to 16 kHz 16-bit PCM."""
        pkt = RTPPacket.parse(raw_rtp)
        if not pkt or not pkt.payload:
            return b""

        # Support PCMU (payload_type 0) or fallback
        if pkt.payload_type == 0 or pkt.payload_type == 8 or pkt.payload_type == 96:
            pcm_16k = decode_audio_to_pcm16_16k(
                raw_audio=pkt.payload,
                encoding="audio/mulaw" if pkt.payload_type == 0 else "audio/alaw",
                orig_sample_rate=8000,
            )
            return pcm_16k
        else:
            logger.warning(f"Unsupported RTP payload type {pkt.payload_type} for call {call_id}")
            return b""

    def format_outgoing_rtp(
        self,
        pcm_16k_bytes: bytes,
        payload_type: int = 0,
        sample_rate: int = 8000,
    ) -> bytes:
        """Encode internal 16 kHz PCM speech to PCMU 8 kHz RTP packet."""
        mulaw_payload = encode_pcm16_16k_to_target(
            audio_bytes=pcm_16k_bytes,
            target_encoding="audio/mulaw",
            target_sample_rate=sample_rate,
        )

        self._rtp_seq = (self._rtp_seq + 1) & 0xFFFF
        self._rtp_ts = (self._rtp_ts + len(mulaw_payload)) & 0xFFFFFFFF

        pkt = RTPPacket(
            payload_type=payload_type,
            sequence_number=self._rtp_seq,
            timestamp=self._rtp_ts,
            ssrc=self._ssrc,
            payload=mulaw_payload,
        )
        return pkt.build()

    def process_sip_request(
        self,
        msg: Dict[str, Any],
        remote_addr: Tuple[str, int],
    ) -> Tuple[Optional[str], str]:
        """Process SIP signaling request (INVITE, BYE, ACK, CANCEL) and construct SIP response."""
        method = msg["method"]
        call_id = msg["call_id"] or f"sip_call_{int(time.time())}"
        phone_number = msg["phone_number"]

        if method == "INVITE":
            logger.info(f"[SIP] Incoming INVITE for call_id={call_id} from {phone_number}")

            self.active_calls[call_id] = {
                "call_id": call_id,
                "phone_number": phone_number,
                "status": "ringing",
                "remote_addr": remote_addr,
                "remote_rtp_host": msg["remote_rtp_host"] or remote_addr[0],
                "remote_rtp_port": msg["remote_rtp_port"],
                "created_at": time.time(),
                "last_active": time.time(),
            }

            # Build 200 OK with SDP answer
            local_host = self.server_host if self.server_host != "0.0.0.0" else remote_addr[0]
            sdp_body = (
                "v=0\r\n"
                f"o=Nyra {int(time.time())} {int(time.time())} IN IP4 {local_host}\r\n"
                "s=Nyra SIP Call\r\n"
                f"c=IN IP4 {local_host}\r\n"
                "t=0 0\r\n"
                f"m=audio {self.server_port + 2} RTP/AVP 0 101\r\n"
                "a=rtpmap:0 PCMU/8000\r\n"
                "a=rtpmap:101 telephone-event/8000\r\n"
                "a=sendrecv\r\n"
            )

            sip_response = (
                "SIP/2.0 200 OK\r\n"
                f"Via: {msg['headers'].get('via', '')}\r\n"
                f"From: {msg['from_header']}\r\n"
                f"To: {msg['to_header']};tag=nyra_{random.randint(1000,9999)}\r\n"
                f"Call-ID: {call_id}\r\n"
                f"CSeq: {msg['cseq']}\r\n"
                "Content-Type: application/sdp\r\n"
                f"Content-Length: {len(sdp_body)}\r\n\r\n"
                f"{sdp_body}"
            )
            return call_id, sip_response

        elif method == "ACK":
            logger.info(f"[SIP] ACK received for call_id={call_id}")
            if call_id in self.active_calls:
                self.active_calls[call_id]["status"] = "in-progress"
                self.active_calls[call_id]["last_active"] = time.time()
            return call_id, ""

        elif method == "BYE" or method == "CANCEL":
            logger.info(f"[SIP] {method} received for call_id={call_id}")
            if call_id in self.active_calls:
                self.active_calls[call_id]["status"] = "completed"

            sip_response = (
                "SIP/2.0 200 OK\r\n"
                f"Via: {msg['headers'].get('via', '')}\r\n"
                f"From: {msg['from_header']}\r\n"
                f"To: {msg['to_header']}\r\n"
                f"Call-ID: {call_id}\r\n"
                f"CSeq: {msg['cseq']}\r\n"
                "Content-Length: 0\r\n\r\n"
            )
            return call_id, sip_response

        elif method == "OPTIONS":
            sip_response = (
                "SIP/2.0 200 OK\r\n"
                f"Via: {msg['headers'].get('via', '')}\r\n"
                f"From: {msg['from_header']}\r\n"
                f"To: {msg['to_header']}\r\n"
                f"Call-ID: {call_id}\r\n"
                f"CSeq: {msg['cseq']}\r\n"
                "Allow: INVITE, ACK, CANCEL, OPTIONS, BYE\r\n"
                "Content-Length: 0\r\n\r\n"
            )
            return call_id, sip_response

        return call_id, ""

    def cleanup_stale_calls(self, timeout_seconds: int = 300) -> list[str]:
        """Sweep inactive call records that exceed the timeout duration."""
        now = time.time()
        stale_call_ids = []

        for cid, call_info in list(self.active_calls.items()):
            last_active = call_info.get("last_active") or call_info.get("created_at") or now
            if (now - last_active) > timeout_seconds:
                call_info["status"] = "stale"
                stale_call_ids.append(cid)
                logger.warning(f"[SIP] Call {cid} timed out after {timeout_seconds}s of inactivity. Marking stale.")

        for cid in stale_call_ids:
            if cid in self.active_calls:
                del self.active_calls[cid]

        return stale_call_ids
