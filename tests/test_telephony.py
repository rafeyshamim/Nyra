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
