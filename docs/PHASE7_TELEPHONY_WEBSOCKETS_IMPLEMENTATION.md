# Phase 7 — Telephony Strategy, FastAPI & WebSockets Implementation

## Overview
Phase 7 implements the telephony gateway architecture, FastAPI web server endpoints, and real-time bidirectional WebSocket audio streaming for phone calls.

Key objectives achieved:
- **Dual Telephony Gateway Strategy**:
  1. **Android SIM Gateway (`AndroidGatewayTelephonyProvider`)**: Primary ₹0 experimental route for cellular calls over local audio/Bluetooth HFP/USB bridge.
  2. **Exotel AgentStream (`ExotelAgentStreamProvider`)**: Fallback enterprise telephony route supporting WebSocket media streaming (base64 JSON frames).
- **FastAPI Web Server**:
  - `/health`: Component health check endpoint (Ollama LLM status, SQLite DB connection).
  - `/webhooks/whatsapp`: Webhook verification and incoming message handler.
  - `/webhooks/telephony`: Call event webhook receiver.
  - `/ws/call/{call_id}`: Real-time bidirectional WebSocket voice streaming endpoint.

---

## Architecture & Data Flow

```text
       Incoming Call / PSTN
                 │
                 ├── Android SIM Gateway (Primary ₹0 Route)
                 └── Exotel AgentStream (Fallback WebSocket Route)
                 │
                 ▼
+------------------------------------+
|  FastAPI WS (/ws/call/{call_id})  |
+------------------------------------+
                 │
                 ├── Decode Base64 / PCM Stream
                 ├── Run Conversation Turn & VAD
                 └── Encode Response Media Frame
                 │
                 ▼
     Real-Time Telephone Playout
```

---

## Core Classes & Modules

### 1. [`app/telephony/android_gateway.py`](file:///c:/Users/rafey/Downloads/Nyra/app/telephony/android_gateway.py)
Provides `AndroidGatewayTelephonyProvider` for managing local Android SIM gateway calls and audio streams.

### 2. [`app/telephony/exotel.py`](file:///c:/Users/rafey/Downloads/Nyra/app/telephony/exotel.py)
Provides `ExotelAgentStreamProvider`:
- `parse_websocket_event()`: Decodes incoming Exotel WebSocket media frames into raw PCM audio bytes.
- `format_media_response()`: Encodes synthesized speech PCM bytes into base64 JSON frames for Exotel.

### 3. [`app/api/routes_telephony.py`](file:///c:/Users/rafey/Downloads/Nyra/app/api/routes_telephony.py)
FastAPI router managing `/webhooks/telephony` and `/ws/call/{call_id}` WebSocket voice connection sessions.

### 4. [`app/main.py`](file:///c:/Users/rafey/Downloads/Nyra/app/main.py)
Main FastAPI application entrypoint with startup lifecycle hooks (`init_db()`) and CORS middleware.

### 5. [`tests/test_telephony.py`](file:///c:/Users/rafey/Downloads/Nyra/tests/test_telephony.py)
Automated pytest suite testing FastAPI `/health` endpoint, WhatsApp webhook verification, and Exotel frame serialization.

---

## Verification
Run telephony & API test suite:
```powershell
python -m pytest tests/test_telephony.py
```
Start the local FastAPI development server:
```powershell
uvicorn app.main:app --reload
```
