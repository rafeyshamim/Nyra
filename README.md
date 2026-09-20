<div align="center">

# Nyra - Personal AI Call Assistant

**A local-first, zero-API-cost personal receptionist that answers your phone calls using on-device AI.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-FF6B35?style=for-the-badge)](https://ollama.ai/)
[![SQLite](https://img.shields.io/badge/SQLite-Async-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

> Nyra answers your calls in your absence, holds real conversations in English, Hindi, or Hinglish,
> extracts intent and action items, and notifies you on WhatsApp — all running locally on your machine
> with **zero recurring API cost**.

</div>

---

## Table of Contents

- [What is Nyra?](#what-is-nyra)
- [Key Features](#key-features)
- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running Nyra](#running-nyra)
- [Testing Nyra](#testing-nyra)
- [API Reference](#api-reference)
- [Telephony Setup](#telephony-setup)
- [WhatsApp Notifications](#whatsapp-notifications)
- [Web Dashboard](#web-dashboard)
- [Benchmarking](#benchmarking)
- [Development Guide](#development-guide)
- [Roadmap](#roadmap)
- [Troubleshooting](#troubleshooting)

---

## What is Nyra?

Nyra is a **local-first personal AI receptionist** built for busy individuals who cannot always answer their phone. When a call comes in:

1. **Nyra answers the call** and greets the caller warmly as your AI assistant.
2. **Nyra holds a real conversation** — asking who is calling, what they need, and taking messages.
3. **Nyra auto-detects the language** — English, Hindi, or Hinglish — and responds accordingly.
4. **Post-call analysis** extracts the caller name, intent, priority level, action items, and a structured summary.
5. **WhatsApp notification** is sent to you with the full summary so you can decide whether to call back immediately.

Everything runs on your local machine. **No cloud APIs. No subscriptions. No data leaves your device.**

---

## Key Features

| Feature | Details |
|---|---|
| **Local LLM Brain** | Powered by Ollama (Qwen2.5 or any compatible model) |
| **Speech-to-Text** | faster-whisper (CTranslate2, GPU-accelerated) |
| **Text-to-Speech** | Kokoro TTS — high-quality, natural-sounding voice |
| **Voice Activity Detection** | WebRTC VAD for barge-in detection and turn-taking |
| **Telephony** | Android SIP gateway or Exotel cloud telephony |
| **WhatsApp Notifier** | Meta Cloud API or mock outbox for local testing |
| **SQLite Database** | Async SQLAlchemy — call logs, contacts, WhatsApp outbox |
| **Caller Recognition** | Match callers by phone number against your contacts |
| **Calendar Context** | Awareness of your schedule for informed responses |
| **Web Dashboard** | Local FastAPI + HTML dashboard to review all calls |
| **Multi-language** | English, Hindi, Hinglish — auto-detected per caller |
| **Privacy First** | 100% local — nothing leaves your device |
| **Zero Cost** | No API keys needed for core functionality |

---

## Architecture Overview

```
Incoming Call
     |
     v
+---------------------------------------------+
|              Telephony Layer                |
|  Android SIP Gateway  OR  Exotel Cloud     |
+-------------------+-------------------------+
                    | WebSocket / Audio Stream
                    v
+---------------------------------------------+
|           Audio Processing Pipeline         |
|  WebRTC VAD --> Audio Buffer --> Resampler  |
+-------------------+-------------------------+
                    | PCM Audio Chunks
                    v
+---------------------------------------------+
|         Speech-to-Text (faster-whisper)     |
|         GPU-accelerated transcription       |
+-------------------+-------------------------+
                    | Transcript Text
                    v
+---------------------------------------------+
|          Local LLM Brain (Ollama)           |
|  Qwen2.5  .  Conversation Manager . Prompts|
|  Caller Context  .  Calendar Awareness     |
+-------------------+-------------------------+
                    | Response Text
                    v
+---------------------------------------------+
|         Text-to-Speech (Kokoro TTS)         |
|         Natural voice synthesis             |
+-------------------+-------------------------+
                    | Audio Output
                    v
             Caller hears Nyra

After Call Ends:
     |
     v
Post-Call Analyzer --> SQLite DB --> WhatsApp Notifier --> YOU
```

---

## Tech Stack

| Component | Technology | Purpose |
|---|---|---|
| **Web Framework** | FastAPI 0.110+ | REST API, WebSocket server, Dashboard |
| **LLM Engine** | Ollama (Qwen2.5) | Local language model inference |
| **Speech-to-Text** | faster-whisper | Local ASR with GPU support |
| **Text-to-Speech** | Kokoro TTS | Natural voice synthesis |
| **Voice Activity Detection** | webrtcvad-wheels | Turn-taking, barge-in detection |
| **Database ORM** | SQLAlchemy (async) + aiosqlite | Async SQLite operations |
| **Database Migrations** | Alembic | Schema versioning |
| **Task Scheduling** | APScheduler | WhatsApp outbox worker |
| **Data Validation** | Pydantic v2 | Structured schemas, settings |
| **Configuration** | pydantic-settings + python-dotenv | Environment-based config |
| **HTTP Client** | httpx | Async HTTP calls to Ollama/WhatsApp |
| **Testing** | pytest + pytest-asyncio | Async test suite |
| **Linting** | Ruff + Black + mypy | Code quality |

---

## Project Structure

```
Nyra/
├── app/                          # Core application package
│   ├── main.py                   # FastAPI app entry point, lifespan, routers
│   ├── config/
│   │   ├── settings.py           # Pydantic Settings (env-based config)
│   │   └── logging.py            # Structured logging setup
│   ├── llm/
│   │   ├── base.py               # Abstract LLMProvider interface
│   │   ├── client.py             # OllamaLLMProvider (httpx-based)
│   │   ├── prompts.py            # System prompts, personality, language rules
│   │   ├── schemas.py            # Pydantic models (CallAnalysisResult, etc.)
│   │   └── intent.py             # Post-call analyzer (intent extraction)
│   ├── stt/
│   │   ├── base.py               # Abstract STTProvider interface
│   │   └── faster_whisper.py     # FasterWhisperSTT implementation
│   ├── tts/
│   │   ├── base.py               # Abstract TTSProvider interface
│   │   ├── kokoro.py             # KokoroTTS implementation
│   │   └── voice_profiles.py     # Voice profile configurations
│   ├── audio/
│   │   ├── vad.py                # WebRTC VAD integration
│   │   ├── audio_buffer.py       # PCM audio buffering
│   │   └── resampler.py          # Audio sample rate conversion
│   ├── conversation/
│   │   └── state.py              # Call state machine (IDLE to RINGING to ACTIVE to ENDED)
│   ├── database/
│   │   ├── models.py             # SQLAlchemy ORM models
│   │   └── session.py            # Async engine, session factory, init_db
│   ├── contacts/
│   │   ├── resolver.py           # Phone number to contact name lookup
│   │   └── service.py            # Contact management service
│   ├── calendar/                 # Calendar context provider
│   ├── memory/                   # Conversation memory management
│   ├── postcall/                 # Post-call summary generation
│   ├── telephony/
│   │   ├── base.py               # Abstract TelephonyProvider interface
│   │   ├── android_gateway.py    # Android SIP gateway implementation
│   │   ├── exotel.py             # Exotel cloud telephony implementation
│   │   └── service.py            # Telephony service factory
│   ├── whatsapp/
│   │   ├── base.py               # Abstract NotificationProvider interface
│   │   ├── sender.py             # WhatsApp Cloud API sender
│   │   ├── commands.py           # WhatsApp command parser
│   │   └── outbox_worker.py      # Async outbox pattern worker
│   └── api/
│       ├── routes_health.py      # GET /health endpoint
│       ├── routes_telephony.py   # POST /call/* and WS /ws/call
│       ├── routes_whatsapp.py    # POST /whatsapp/webhook
│       └── routes_dashboard.py   # GET /dashboard/calls and /metrics
├── dashboard/
│   └── templates/
│       └── index.html            # Local web dashboard UI
├── scripts/
│   ├── terminal_chat.py          # Text-based call simulator (quickest test)
│   ├── local_duplex_chat.py      # Full audio VAD to STT to LLM to TTS test
│   ├── benchmark_stt.py          # STT latency/accuracy benchmarks
│   └── benchmark_tts.py          # TTS latency/quality benchmarks
├── tests/
│   ├── test_llm.py               # LLM provider unit tests
│   ├── test_stt.py               # STT provider unit tests
│   ├── test_tts.py               # TTS provider unit tests
│   ├── test_audio.py             # VAD and audio pipeline tests
│   ├── test_database.py          # Database CRUD tests
│   ├── test_conversation.py      # Call state machine tests
│   ├── test_whatsapp.py          # WhatsApp outbox tests
│   ├── test_telephony.py         # Telephony route tests
│   └── test_dashboard.py         # Dashboard API tests
├── docs/
│   ├── GETTING_STARTED.md        # Quick-start local testing guide
│   ├── NYRA_IMPLEMENTATION_PLAN.md  # Full original design document
│   ├── PHASE2_STT_IMPLEMENTATION.md
│   ├── PHASE3_TTS_IMPLEMENTATION.md
│   ├── PHASE4_VAD_DUPLEX_IMPLEMENTATION.md
│   ├── PHASE5_DATABASE_POSTCALL_IMPLEMENTATION.md
│   ├── PHASE6_WHATSAPP_IMPLEMENTATION.md
│   ├── PHASE7_TELEPHONY_WEBSOCKETS_IMPLEMENTATION.md
│   ├── PHASE8_CALLER_RECOGNITION_CALENDAR_IMPLEMENTATION.md
│   └── PHASE10_DASHBOARD_IMPLEMENTATION.md
├── data/                         # SQLite database files (auto-created, gitignored)
├── recordings/                   # TTS output WAV files (auto-created, gitignored)
├── logs/                         # Application logs (auto-created, gitignored)
├── .env.example                  # Environment variable template
├── .env                          # Your local config (gitignored - create from .env.example)
├── .gitignore
├── requirements.txt
├── pytest.ini
└── README.md
```

---

## Prerequisites

### 1. Python 3.11 or 3.12

Download from https://www.python.org/downloads/ — during installation, check **"Add Python to PATH"**.

```powershell
python --version
# Should print: Python 3.11.x or Python 3.12.x
```

### 2. Ollama (Local LLM Runtime)

Download from https://ollama.ai/download. After installation, pull the recommended model:

```powershell
# Lightweight - recommended (~1 GB)
ollama pull qwen2.5:1.5b

# More capable - optional (~4 GB, needs more VRAM)
ollama pull qwen2.5:7b
```

Start Ollama before running Nyra:

```powershell
ollama serve
```

Verify Ollama is running:

```powershell
curl http://localhost:11434/api/tags
```

### 3. Microsoft C++ Build Tools

Required to compile webrtcvad and faster-whisper native extensions.

Download from https://visualstudio.microsoft.com/visual-cpp-build-tools/ and install the
**"Desktop development with C++"** workload.

### 4. NVIDIA GPU (Optional but Recommended)

Optimized for NVIDIA RTX 3050 4 GB VRAM or better. Without a GPU, Ollama and faster-whisper
fall back to CPU — slower, but still fully functional.

Install CUDA Toolkit 12.x from https://developer.nvidia.com/cuda-toolkit for GPU acceleration.

---

## Installation

### Step 1 — Enter the project folder

```powershell
cd C:\Users\rafey\Downloads\Nyra
```

### Step 2 — Create and activate a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

> If you get an execution policy error, run:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

### Step 3 — Install dependencies

```powershell
pip install -r requirements.txt
```

> This may take 5-10 minutes the first time (PyTorch, CTranslate2, and other large packages).

### Step 4 — Create your environment file

```powershell
copy .env.example .env
```

Open `.env` in your editor and fill in your values (see Configuration section below).

### Step 5 — Database is auto-initialized

When you start the app for the first time, `data/nyra.db` is created automatically via `init_db()`.
No manual migration step is needed.

---

## Configuration

All settings live in the `.env` file. Here is the complete reference:

```dotenv
# Application
APP_ENV=development           # development | production

# Ollama LLM
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5          # e.g., qwen2.5, qwen2.5:7b, llama3.2

# Database
DATABASE_URL=sqlite+aiosqlite:///./data/nyra.db

# Personality and Identity
NYRA_NAME=Nyra
OWNER_NAME=Rafey

# Telephony  (sip | exotel | android)
TELEPHONY_PROVIDER=sip
SIP_SERVER_HOST=192.168.1.100
SIP_SERVER_PORT=5060
SIP_EXTENSION=1001
SIP_PASSWORD=change_this_password
SIP_MEDIA_ENCODING=audio/mulaw
SIP_MEDIA_SAMPLE_RATE=8000

# Optional PSTN Provider (Exotel)
EXOTEL_ACCOUNT_SID=
EXOTEL_API_KEY=
EXOTEL_API_TOKEN=

# WhatsApp  (mock | cloud_api)
WHATSAPP_PROVIDER=mock
WHATSAPP_TOKEN=
WHATSAPP_PHONE_ID=
WHATSAPP_RECIPIENT_NUMBER=

# Network
PUBLIC_BASE_URL=http://localhost:8000

# Logging  (DEBUG | INFO | WARNING | ERROR)
LOG_LEVEL=INFO
```

---

## Running Nyra

### Option A — Terminal Chat Simulator (No hardware needed — fastest)

```powershell
python scripts/terminal_chat.py
```

Type as the "caller". Nyra greets you, holds a conversation, and responds in the same language you
use (English / Hindi / Hinglish). Type `hangup` or `exit` to end the call — post-call analysis runs
automatically and prints the extracted intent, summary, action items, and priority.

**Example session:**

```
[NYRA] Hello! You have reached Rafey's personal assistant, Nyra.
       Rafey is unavailable right now. May I know who is calling and how I can help?

You: Hi, this is Amit from InfoEdge, calling about a job opportunity for Rafey.

[NYRA] Thank you, Amit! I will let Rafey know you called regarding a job opportunity from InfoEdge.
       Could you leave a callback number?

You: hangup

POST-CALL ANALYSIS
  Caller:       Amit
  Organization: InfoEdge
  Intent:       job_opportunity
  Priority:     HIGH
  Action:       Call back Amit from InfoEdge regarding job opportunity
  Summary:      Amit from InfoEdge called to discuss a job opportunity for Rafey.
```

---

### Option B — Full Voice Duplex Test (Audio pipeline)

```powershell
python scripts/local_duplex_chat.py
```

Uses your microphone and speaker. On first run, faster-whisper downloads its model (~150 MB for tiny).
Synthesized responses are saved as WAV files in the `recordings/` directory.

---

### Option C — Full FastAPI Server and Web Dashboard

```powershell
uvicorn app.main:app --reload
```

| URL | Description |
|---|---|
| http://localhost:8000 | Web Dashboard UI |
| http://localhost:8000/docs | Swagger interactive API docs |
| http://localhost:8000/redoc | ReDoc API docs |
| http://localhost:8000/health | Health check endpoint |

---

## Testing Nyra

### Run all tests

```powershell
python -m pytest tests/ -v
```

### Run with coverage report

```powershell
python -m pytest tests/ --cov=app --cov-report=term-missing
```

### Run a single test module

```powershell
python -m pytest tests/test_llm.py -v
python -m pytest tests/test_database.py -v
python -m pytest tests/test_whatsapp.py -v
```

### Test coverage by module

| Test File | What It Tests |
|---|---|
| test_llm.py | OllamaLLMProvider — generate, stream, model health check |
| test_stt.py | FasterWhisperSTT — transcription, language detection |
| test_tts.py | KokoroTTS — synthesis, WAV output |
| test_audio.py | VAD, AudioBuffer, Resampler |
| test_database.py | SQLAlchemy models and CRUD operations |
| test_conversation.py | Call state machine transitions |
| test_whatsapp.py | Outbox worker, Cloud API sender, message queuing |
| test_telephony.py | FastAPI telephony routes, WebSocket handshake |
| test_dashboard.py | Dashboard metrics API and call list endpoint |

---

## API Reference

### Health

| Method | Endpoint | Description |
|---|---|---|
| GET | /health | Server status, DB connectivity, Ollama reachability |

### Telephony

| Method | Endpoint | Description |
|---|---|---|
| POST | /call/incoming | Incoming call webhook — triggers Nyra to answer |
| POST | /call/end | Call end webhook — triggers post-call analysis |
| WebSocket | /ws/call/{call_id} | Real-time bidirectional audio stream |

### WhatsApp

| Method | Endpoint | Description |
|---|---|---|
| GET | /whatsapp/webhook | Meta verification challenge handshake |
| POST | /whatsapp/webhook | Receive inbound WhatsApp commands from owner |

### Dashboard

| Method | Endpoint | Description |
|---|---|---|
| GET | /dashboard/calls | Paginated list of all call records |
| GET | /dashboard/calls/{id} | Full detail including transcript for one call |
| GET | /dashboard/metrics | Summary stats (total calls, priorities, spam count) |
| GET | / | Serve the local HTML dashboard |
| GET | /docs | Swagger UI (auto-generated) |

---

## Telephony Setup

### Option 1 — Local SIP PBX / Wi-Fi (Primary Free Development Setup)

Nyra uses local SIP telephony as its base provider at zero recurring cost.

1. Install Asterisk or FreeSWITCH on your PC (or run a local SIP client like Linphone on your iPhone/Android).
2. Connect both your phone and PC to the same Wi-Fi / LAN network.
3. Register your phone's SIP client (e.g., Linphone) as extension `1001` on your local PBX.
4. Set `TELEPHONY_PROVIDER=sip` in `.env`:
   ```dotenv
   TELEPHONY_PROVIDER=sip
   SIP_SERVER_HOST=192.168.1.100
   SIP_SERVER_PORT=5060
   SIP_EXTENSION=1001
   SIP_PASSWORD=change_this_password
   SIP_MEDIA_ENCODING=audio/mulaw
   SIP_MEDIA_SAMPLE_RATE=8000
   ```
5. Call Nyra's SIP extension directly over Wi-Fi.

### Option 2 — Exotel Cloud Telephony / PSTN (Optional Paid Provider)

1. Create an account at https://exotel.com and purchase a virtual number.
2. In your Exotel App settings, set the **Answer URL** to your ngrok URL:
   ```
   https://your-ngrok-url/call/incoming
   ```
3. Fill in your `.env`:
   ```dotenv
   TELEPHONY_PROVIDER=exotel
   EXOTEL_ACCOUNT_SID=your_sid
   EXOTEL_API_KEY=your_key
   EXOTEL_API_TOKEN=your_token
   ```
4. Expose your local server with ngrok:
   ```powershell
   ngrok http 8000
   ```
5. Update `PUBLIC_BASE_URL` in `.env` with your ngrok HTTPS URL.

---

## WhatsApp Notifications

### Mock Mode (default — local testing)

`WHATSAPP_PROVIDER=mock` — all post-call summaries are printed to the console and logged.
No real WhatsApp messages are sent.

### Meta Cloud API (real WhatsApp)

1. Create a Meta Developer App at https://developers.facebook.com with WhatsApp Business API enabled.
2. Get your **Phone Number ID**, **Bearer Token**, and your **recipient WhatsApp number**.
3. Configure `.env`:
   ```dotenv
   WHATSAPP_PROVIDER=cloud_api
   WHATSAPP_TOKEN=your_bearer_token
   WHATSAPP_PHONE_ID=your_phone_number_id
   WHATSAPP_RECIPIENT_NUMBER=919876543210
   ```

### WhatsApp Command Interface

Send these commands from your WhatsApp to Nyra's number to control it remotely:

| Command | Action |
|---|---|
| status | Get current Nyra operational status |
| calls | List recent calls with caller and intent |
| summary <id> | Get full summary for a specific call ID |
| callback <number> | Mark a phone number for callback |
| block <number> | Add a number to the spam blocklist |

---

## Web Dashboard

The local web dashboard at http://localhost:8000 provides a real-time call overview:

- **Metrics Cards** — Total calls handled, high-priority items, pending callbacks, spam blocked
- **Recent Calls Table** — Caller name, phone number, timestamp, intent, priority badge (HIGH / MEDIUM / LOW / SPAM)
- **Transcript Viewer** — Click the View button on any call row to read the full conversation transcript and extracted action items

---

## Benchmarking

```powershell
# STT latency benchmark
python scripts/benchmark_stt.py

# TTS latency benchmark
python scripts/benchmark_tts.py
```

**Target latencies for RTX 3050 4 GB VRAM:**

| Component | Target Latency |
|---|---|
| STT (Whisper tiny) | < 500 ms |
| LLM (Qwen2.5 1.5B) | < 1.5 s |
| TTS (Kokoro) | < 800 ms |
| Full round-trip | < 3 s |

---

## Development Guide

### Code Style

```powershell
ruff check app/      # Lint
black app/           # Format
mypy app/            # Type check
```

### Adding a New LLM Provider

1. Create `app/llm/yourprovider.py`
2. Inherit from `app.llm.base.LLMProvider`
3. Implement `generate_response()` and `stream_response()`
4. Add a selector in `app/config/settings.py`

### Adding a New STT Provider

1. Create `app/stt/yourprovider.py`
2. Inherit from `app.stt.base.STTProvider`
3. Implement `transcribe(audio_bytes, language) -> TranscriptionResult`

### Adding a New TTS Provider

1. Create `app/tts/yourprovider.py`
2. Inherit from `app.tts.base.TTSProvider`
3. Implement `synthesize_speech(text, voice) -> bytes`

### Database Migrations with Alembic

After modifying `app/database/models.py`:

```powershell
# Generate a new migration
alembic revision --autogenerate -m "describe your change"

# Apply migrations to the database
alembic upgrade head

# View migration history
alembic history
```

---

## Roadmap

| Phase | Status | Description |
|---|---|---|
| Phase 0 - Foundation | Done | Project structure, settings, logging, provider interfaces |
| Phase 1 - LLM Brain | Done | Ollama client, prompts, conversation state, intent extractor |
| Phase 2 - STT | Done | faster-whisper, multilingual support (EN/HI) |
| Phase 3 - TTS | Done | Kokoro TTS, voice profiles, streaming synthesis |
| Phase 4 - Audio Pipeline | Done | WebRTC VAD, audio buffer, resampler, duplex loop |
| Phase 5 - Database | Done | SQLite models, async sessions, CRUD |
| Phase 6 - WhatsApp | Done | Cloud API sender, outbox worker, command parser |
| Phase 7 - Telephony | Done | FastAPI WebSocket routes, Android gateway, Exotel |
| Phase 8 - Caller Recognition | Done | Contact resolver, caller matching, calendar context |
| Phase 10 - Dashboard | Done | Web dashboard UI, metrics API, transcript viewer |
| Phase 11 - Tests | Done | 25+ pytest unit tests across all modules |
| Phase 12 - Voice Cloning | Planned | Owner voice profile for personalized call rejections |
| Phase 13 - SMS Fallback | Planned | SMS notification as WhatsApp fallback |
| Phase 14 - iOS Shortcut | Planned | Trigger Nyra modes via iPhone Shortcuts |

---

## Troubleshooting

| Problem | Solution |
|---|---|
| httpx.ConnectError — Connection refused | Run `ollama serve` in a separate terminal |
| Error: model 'qwen2.5' not found | Run `ollama pull qwen2.5:1.5b` |
| webrtcvad install fails with C++ error | Install Microsoft C++ Build Tools from https://visualstudio.microsoft.com/visual-cpp-build-tools/ |
| running scripts is disabled on this system | Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| CUDA error: no kernel image available | Verify CUDA version matches your GPU driver; use compute_type="int8" as fallback |
| sqlite3.OperationalError: database is locked | Only one Nyra process should access the database at a time |
| ModuleNotFoundError: No module named 'app' | Ensure your virtual environment is activated and you are in the project root |

---

## License

This project is licensed under the **MIT License**.

---

## Author

Built by **Rafey Shamim** with heart and a lot of coffee.

---

<div align="center">

**Nyra — Because your time is too valuable to answer every call.**

</div>