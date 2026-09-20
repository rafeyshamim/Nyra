import pytest
import time
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.telephony.sip import SIPTelephonyProvider, RTPPacket
from app.audio.codecs import pcm16_to_mulaw, mulaw_to_pcm16

client = TestClient(app)


def test_sip_provider_initialization():
    provider = SIPTelephonyProvider(
        server_host="127.0.0.1",
        server_port=5060,
        extension="1001",
    )
    assert provider.server_host == "127.0.0.1"
    assert provider.server_port == 5060
    assert provider.extension == "1001"


@pytest.mark.asyncio
async def test_sip_provider_answer_and_end_call():
    provider = SIPTelephonyProvider()
    call_id = "sip_test_call_001"
    provider.active_calls[call_id] = {
        "call_id": call_id,
        "status": "ringing",
        "created_at": time.time(),
    }

    ans_res = await provider.answer_call(call_id)
    assert ans_res is True
    assert provider.active_calls[call_id]["status"] == "in-progress"

    end_res = await provider.end_call(call_id)
    assert end_res is True
    assert call_id not in provider.active_calls


def test_sip_message_parsing():
    provider = SIPTelephonyProvider()
    raw_invite = (
        "INVITE sip:1001@192.168.1.100 SIP/2.0\r\n"
        "Via: SIP/2.0/UDP 192.168.1.105:5060;branch=z9hG4bK776\r\n"
        "From: <sip:9876543210@192.168.1.100>;tag=12345\r\n"
        "To: <sip:1001@192.168.1.100>\r\n"
        "Call-ID: test_invite_call_101\r\n"
        "CSeq: 1 INVITE\r\n"
        "Content-Type: application/sdp\r\n"
        "Content-Length: 120\r\n\r\n"
        "v=0\r\n"
        "c=IN IP4 192.168.1.105\r\n"
        "m=audio 8000 RTP/AVP 0 101\r\n"
    )

    msg = provider.parse_sip_message(raw_invite.encode("utf-8"))
    assert msg["method"] == "INVITE"
    assert msg["call_id"] == "test_invite_call_101"
    assert msg["phone_number"] == "9876543210"
    assert msg["remote_rtp_host"] == "192.168.1.105"
    assert msg["remote_rtp_port"] == 8000


def test_sip_process_invite_request():
    provider = SIPTelephonyProvider()
    raw_invite = (
        "INVITE sip:1001@192.168.1.100 SIP/2.0\r\n"
        "Via: SIP/2.0/UDP 192.168.1.105:5060;branch=z9hG4bK776\r\n"
        "From: <sip:9876543210@192.168.1.100>;tag=12345\r\n"
        "To: <sip:1001@192.168.1.100>\r\n"
        "Call-ID: test_invite_call_102\r\n"
        "CSeq: 1 INVITE\r\n"
        "Content-Length: 0\r\n\r\n"
    )

    msg = provider.parse_sip_message(raw_invite.encode("utf-8"))
    cid, sip_resp = provider.process_sip_request(msg, ("192.168.1.105", 5060))

    assert cid == "test_invite_call_102"
    assert "SIP/2.0 200 OK" in sip_resp
    assert "Call-ID: test_invite_call_102" in sip_resp
    assert "Content-Type: application/sdp" in sip_resp
    assert cid in provider.active_calls


def test_sip_process_bye_request():
    provider = SIPTelephonyProvider()
    cid_init = "test_bye_call_103"
    provider.active_calls[cid_init] = {"call_id": cid_init, "status": "in-progress"}

    raw_bye = (
        "BYE sip:1001@192.168.1.100 SIP/2.0\r\n"
        "Via: SIP/2.0/UDP 192.168.1.105:5060;branch=z9hG4bK777\r\n"
        "From: <sip:9876543210@192.168.1.100>;tag=12345\r\n"
        "To: <sip:1001@192.168.1.100>\r\n"
        "Call-ID: test_bye_call_103\r\n"
        "CSeq: 2 BYE\r\n"
        "Content-Length: 0\r\n\r\n"
    )

    msg = provider.parse_sip_message(raw_bye.encode("utf-8"))
    cid, sip_resp = provider.process_sip_request(msg, ("192.168.1.105", 5060))

    assert cid == "test_bye_call_103"
    assert "SIP/2.0 200 OK" in sip_resp
    assert provider.active_calls[cid]["status"] == "completed"


def test_rtp_packet_building_and_parsing():
    payload = b"\x00\x7f\x80\xff" * 20
    pkt = RTPPacket(payload_type=0, sequence_number=100, timestamp=1600, ssrc=123456, payload=payload)
    raw_bytes = pkt.build()

    parsed = RTPPacket.parse(raw_bytes)
    assert parsed is not None
    assert parsed.version == 2
    assert parsed.payload_type == 0
    assert parsed.sequence_number == 100
    assert parsed.timestamp == 1600
    assert parsed.ssrc == 123456
    assert parsed.payload == payload


def test_sip_rtp_incoming_and_outgoing_audio_conversion():
    provider = SIPTelephonyProvider()

    # Generate 16 kHz PCM sample
    pcm16_sample = b"\x00\x00\x10\x00" * 80
    rtp_out = provider.format_outgoing_rtp(pcm16_sample, payload_type=0, sample_rate=8000)

    parsed_rtp = RTPPacket.parse(rtp_out)
    assert parsed_rtp is not None
    assert parsed_rtp.payload_type == 0
    assert len(parsed_rtp.payload) > 0

    decoded_pcm16 = provider.process_incoming_rtp(rtp_out, "test_rtp_call")
    assert len(decoded_pcm16) > 0


def test_sip_stale_call_cleanup():
    provider = SIPTelephonyProvider()
    now = time.time()
    provider.active_calls["stale_call_1"] = {
        "call_id": "stale_call_1",
        "last_active": now - 400,
    }
    provider.active_calls["active_call_2"] = {
        "call_id": "active_call_2",
        "last_active": now - 50,
    }

    stale_ids = provider.cleanup_stale_calls(timeout_seconds=300)
    assert "stale_call_1" in stale_ids
    assert "stale_call_1" not in provider.active_calls
    assert "active_call_2" in provider.active_calls


def test_sip_call_event_endpoint():
    payload = {
        "call_id": "sip_route_call_1",
        "phone_number": "+919876543210",
        "event": "ringing"
    }
    res_ring = client.post("/call/sip/event", json=payload)
    assert res_ring.status_code == 200
    assert res_ring.json()["status"] == "accepted"

    payload["event"] = "answered"
    res_ans = client.post("/call/sip/event", json=payload)
    assert res_ans.status_code == 200

    payload["event"] = "completed"
    res_end = client.post("/call/sip/event", json=payload)
    assert res_end.status_code == 200
