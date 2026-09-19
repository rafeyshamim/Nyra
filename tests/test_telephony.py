import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.telephony.exotel import ExotelAgentStreamProvider
from app.telephony.android_gateway import AndroidGatewayTelephonyProvider

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "components" in data
    assert "database" in data["components"]


def test_whatsapp_webhook_verification():
    response = client.get("/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=&hub.challenge=challenge123")
    assert response.status_code in [200, 403]


def test_exotel_provider_media_formatting():
    provider = ExotelAgentStreamProvider()
    pcm_sample = b"\x00\x00\x01\x00"
    formatted = provider.format_media_response("stream_123", pcm_sample)
    assert "media" in formatted
    assert "stream_123" in formatted

    event, stream_sid, decoded_pcm = provider.parse_websocket_event(formatted)
    assert event == "media"
    assert stream_sid == "stream_123"
    assert decoded_pcm == pcm_sample


def test_exotel_mulaw_codec_decoding_and_resampling():
    import json
    import base64
    provider = ExotelAgentStreamProvider()

    # Generate 8kHz mu-law audio frame sample
    mulaw_bytes = bytes([0x80, 0xFF, 0x00, 0x7F] * 20)
    raw_msg = json.dumps({
        "event": "media",
        "stream_sid": "stream_mulaw_8k",
        "media": {
            "payload": base64.b64encode(mulaw_bytes).decode("utf-8"),
            "encoding": "audio/mulaw",
            "sample_rate": 8000
        }
    })

    event, stream_sid, decoded_pcm = provider.parse_websocket_event(raw_msg)
    assert event == "media"
    assert stream_sid == "stream_mulaw_8k"
    # 8kHz audio resampled to 16kHz produces twice as many 16-bit PCM samples
    assert len(decoded_pcm) == len(mulaw_bytes) * 2 * 2


def test_exotel_outbound_mulaw_formatting():
    import json
    import base64
    provider = ExotelAgentStreamProvider()

    pcm_sample = b"\x00\x00\x01\x00" * 100
    formatted = provider.format_media_response(
        stream_sid="stream_out_mulaw",
        audio_bytes=pcm_sample,
        target_encoding="audio/mulaw",
        target_sample_rate=8000,
    )

    data = json.loads(formatted)
    assert data["event"] == "media"
    assert data["stream_sid"] == "stream_out_mulaw"
    assert data["media"]["encoding"] == "audio/mulaw"
    assert data["media"]["sample_rate"] == 8000
    assert "payload" in data["media"]
    decoded_payload = base64.b64decode(data["media"]["payload"])
    assert len(decoded_payload) > 0


@pytest.mark.asyncio
async def test_finalize_call_session_idempotency():
    from app.api.routes_telephony import finalize_call_session, active_calls
    from app.conversation.state import CallSession
    from unittest.mock import AsyncMock, MagicMock

    call_id = "test_dup_call_99"
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_result

    mock_session = CallSession(call_id=call_id, phone_number="+919999999999")

    active_calls[call_id] = {
        "call_id": call_id,
        "phone_number": "+919999999999",
        "session": mock_session,
        "processed": False
    }

    # First execution should process the call
    with pytest.MonkeyPatch.context() as mp:
        mock_process = AsyncMock()
        from app.api import routes_telephony
        mp.setattr(routes_telephony.postcall_processor, "process_completed_call", mock_process)

        await finalize_call_session(call_id, mock_db)
        assert mock_process.call_count == 1
        assert active_calls[call_id]["processed"] is True

        # Second execution should be a no-op
        await finalize_call_session(call_id, mock_db)
        assert mock_process.call_count == 1


@pytest.mark.asyncio
async def test_android_gateway_provider():
    provider = AndroidGatewayTelephonyProvider()
    res = await provider.answer_call("call_99")
    assert res is True
    res_end = await provider.end_call("call_99")
    assert res_end is True


def test_incoming_call_endpoint_json():
    payload = {
        "CallSid": "exotel_call_1001",
        "From": "+919812345678",
        "To": "+918000000000"
    }
    response = client.post("/call/incoming", json=payload, headers={"Accept": "application/json"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert data["call_id"] == "exotel_call_1001"
    assert data["phone_number"] == "+919812345678"
    assert "websocket_url" in data
    assert "ws/call/exotel_call_1001" in data["websocket_url"]


def test_incoming_call_endpoint_xml_default():
    payload = {
        "CallSid": "exotel_call_1002",
        "From": "+919812345679"
    }
    response = client.post("/call/incoming", json=payload)
    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    assert "<Stream url=" in response.text
    assert "ws/call/exotel_call_1002" in response.text


def test_call_status_webhook():
    status_payload = {
        "CallSid": "exotel_call_1001",
        "Status": "completed"
    }
    response = client.post("/call/status", json=status_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert data["call_id"] == "exotel_call_1001"
    assert data["event"] == "completed"


def test_webhook_token_authentication(monkeypatch):
    from app.config.settings import settings
    monkeypatch.setattr(settings, "telephony_webhook_token", "secret_token_123")

    payload = {"CallSid": "auth_call_1", "From": "+919800000000"}

    # Unauthorized request (no token)
    res_unauth = client.post("/call/incoming", json=payload)
    assert res_unauth.status_code == 401

    # Authorized request with header token
    res_auth = client.post("/call/incoming", json=payload, headers={"X-Webhook-Token": "secret_token_123"})
    assert res_auth.status_code == 200
