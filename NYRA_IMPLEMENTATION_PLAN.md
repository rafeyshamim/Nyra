# NYRA — Personal AI Call Assistant
## Complete Implementation Plan

**Project name:** Nyra  
**Goal:** Build a local-first personal AI assistant that answers incoming phone calls on behalf of Rafey, conducts a natural conversation using a female voice, understands the caller's intent, and sends Rafey a concise WhatsApp summary and actionable controls.

**Primary constraint:** Target **₹0 recurring software/AI cost** wherever technically possible. Paid telephony is a fallback, not the default.

---

## 1. Product Vision

Nyra should behave like a capable personal receptionist rather than an IVR.

A caller should be able to say:

> "Hi, is Rafey available?"

Nyra should respond naturally:

> "Hi, I'm Nyra, Rafey's AI assistant. He's unavailable at the moment. May I know who's calling and what this is regarding?"

Nyra should then understand the conversation, ask sensible follow-up questions, collect a message/action, end politely, and send Rafey a WhatsApp notification.

### Example WhatsApp result

```text
🤖 NYRA — NEW CALL

📞 Caller: Rahul Sharma
🏢 Organization: XYZ Technologies
⏱️ Duration: 02:18

🎯 Intent:
Interview rescheduling

📝 Summary:
Rahul from XYZ called regarding Rafey's interview
and wants to move it to Friday.

🎯 Action required:
Rafey should contact Rahul and confirm the new time.

🔴 Priority: HIGH
📲 Callback requested: YES

📝 Transcript:
Available in Nyra dashboard.
```

---

# 2. Core Requirements

## 2.1 Functional requirements

Nyra MUST:

1. Answer incoming calls.
2. Identify itself as an AI assistant rather than secretly impersonating Rafey.
3. Use a natural-sounding female voice.
4. Support English.
5. Support Hindi.
6. Support Hinglish/code-switching.
7. Detect when a caller is speaking.
8. Detect when the caller has stopped speaking.
9. Handle interruptions/barge-in.
10. Ask for caller name when unknown.
11. Ask why the caller is calling.
12. Ask follow-up questions when required.
13. Understand free-form conversation.
14. Extract caller intent.
15. Extract requested action.
16. Determine urgency/priority.
17. Determine whether a callback is requested.
18. Produce a concise summary.
19. Preserve a transcript.
20. Recognize known callers/contacts when possible.
21. Handle spam/irrelevant calls politely.
22. Support escalation/transfer where the telephony layer permits it.
23. Send the post-call summary to Rafey through WhatsApp.
24. Allow WhatsApp commands such as:
    - `CALL BACK`
    - `IGNORE`
    - `REMIND 10AM`
    - `TRANSFER`
25. Store call history.
26. Store caller/contact information.
27. Maintain configurable personal-assistant rules.
28. Integrate with a calendar in a later phase.
29. Expose tools to the AI through controlled function calls.
30. Keep sensitive credentials outside source code.

---

# 3. Non-Functional Requirements

Nyra SHOULD:

- Feel conversational rather than robotic.
- Respond with low latency.
- Prefer short responses during phone calls.
- Avoid talking over callers.
- Recover gracefully from recognition errors.
- Work without internet for AI processing whenever possible.
- Keep call audio/transcripts local by default.
- Require explicit approval before taking consequential actions.
- Be modular so STT, LLM, TTS, telephony, and WhatsApp components can be replaced independently.
- Run on Windows 11 during development.
- Use the available NVIDIA RTX 3050 when beneficial.
- Start with SQLite and remain upgradeable to PostgreSQL.
- Be observable and debuggable.

---

# 4. Cost Strategy

## Target architecture

### Free/local

| Component | Planned choice | Cost target |
|---|---|---:|
| LLM | Ollama + local model | ₹0 |
| STT | faster-whisper | ₹0 |
| TTS | Kokoro first; compare other local neural TTS models | ₹0 |
| Backend | Python + FastAPI | ₹0 |
| Database | SQLite | ₹0 |
| Tunnel | Cloudflare Tunnel for development | ₹0 |
| Audio processing | PyAV / soundfile / NumPy | ₹0 |
| Dashboard | FastAPI + simple HTML/JS | ₹0 |
| Development | VS Code | ₹0 |

Ollama exposes a local API for chat/completions, model management, embeddings, and streaming.  
Official API documentation: https://docs.ollama.com/api

### Telephony

The hardest part of a permanently free implementation is connecting a normal Indian cellular call to a computer.

Priority:

1. **Experiment with Android/SIM gateway approach first.**
2. If reliable, keep it as the zero-cost route.
3. If it is unreliable/impossible, use Exotel as the controlled fallback.
4. Exotel AgentStream supports bidirectional real-time voice streaming over WebSocket for conversational voicebots, but access/onboarding and telecom charges can apply.

Exotel AgentStream documentation:
https://docs.exotel.com/exotel-agentstream

Exotel states that AgentStream supports unidirectional streaming for analysis and bidirectional streaming for interactive voicebots. AgentStream access currently requires account setup and KYC. See:
https://docs.exotel.com/exotel-agentstream/overview-and-quickstart

---

# 5. High-Level Architecture

```text
                         INCOMING CALL
                               |
                               v
                  +-------------------------+
                  |     TELEPHONY LAYER     |
                  |                         |
                  | Android/SIM Gateway     |
                  |        OR               |
                  | Exotel AgentStream      |
                  +------------+------------+
                               |
                         live audio
                               |
                               v
                  +-------------------------+
                  |     AUDIO ENGINE        |
                  |                         |
                  | VAD / buffering         |
                  | interruption handling   |
                  +------------+------------+
                               |
                  +------------+------------+
                  |                         |
                  v                         v
          +---------------+          +---------------+
          | faster-whisper|          | TTS           |
          | STT           |          | Kokoro/local  |
          +-------+-------+          +-------+-------+
                  |                          ^
                  v                          |
          +---------------------------------------+
          |              NYRA BRAIN               |
          |                                       |
          | Ollama + local LLM                    |
          | system prompt                         |
          | conversation state                    |
          | tool calling                          |
          | intent extraction                     |
          +----------------+----------------------+
                           |
             +-------------+-------------+
             |             |             |
             v             v             v
         Contacts      Calendar       Memory
             |             |             |
             +-------------+-------------+
                           |
                           v
                  +--------------------+
                  | POST-CALL ANALYZER |
                  | intent/summary     |
                  | action/priority    |
                  | transcript         |
                  +---------+----------+
                            |
                            v
                    +---------------+
                    |   WhatsApp    |
                    | notification  |
                    +-------+-------+
                            |
                            v
                         RAFey
```

---

# 6. Local-First Architecture

The AI processing pipeline should be:

```text
Phone audio
    |
    v
Local STT
    |
    v
Local LLM
    |
    v
Local TTS
    |
    v
Phone
```

No cloud AI API is required for the core conversational intelligence.

This is important because the project goal is:

> **No API bill for every minute of conversation.**

---

# 7. Hardware Target

Development machine:

- Windows 11
- NVIDIA RTX 3050 4 GB VRAM
- Python
- VS Code
- Internet connection for initial model downloads
- Optional Android phone for cellular gateway experiments

The 4 GB VRAM constraint means model selection must be conservative.

Do not assume a large 7B/14B model will run entirely in GPU memory.

Prefer a quantized local model and benchmark:

- response latency
- VRAM usage
- RAM usage
- CPU utilization
- tokens/second

---

# 8. AI Stack

## 8.1 LLM — Ollama

Purpose:

- conversation reasoning
- intent classification
- response generation
- structured output
- tool selection
- summarization

Ollama local API supports chat generation and streaming.

Official documentation:
https://docs.ollama.com/api

Suggested initial model strategy:

```text
Phase 1:
Use a small/medium instruction model compatible with
4 GB VRAM + system RAM.

Phase 2:
Benchmark 3-4 candidate models.

Phase 3:
Select based on:
- latency
- instruction following
- multilingual performance
- Hinglish quality
- memory use
```

Do not hard-code the model name throughout the application.

Configure it through:

```env
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=<selected-model>
```

---

# 9. Speech-to-Text — faster-whisper

Use faster-whisper for local transcription.

It is a Whisper implementation using CTranslate2 and supports GPU/CPU execution and quantization.

Official repository:
https://github.com/SYSTRAN/faster-whisper

For NVIDIA GPU operation, current faster-whisper documentation notes CUDA 12/cuDNN 9 requirements for current CTranslate2 versions.

Initial settings to test:

```python
WhisperModel(
    "small",
    device="cuda",
    compute_type="float16"
)
```

If VRAM or latency is a problem:

```python
WhisperModel(
    "small",
    device="cuda",
    compute_type="int8_float16"
)
```

Fallback:

```python
WhisperModel(
    "small",
    device="cpu",
    compute_type="int8"
)
```

### STT requirements

Nyra should:

- detect English/Hindi automatically where possible
- preserve Hinglish
- retain timestamps
- support streaming/chunked transcription
- avoid waiting for the whole call before responding
- maintain partial transcript state

---

# 10. Voice / TTS

## Primary goal

Nyra must sound:

- female
- warm
- natural
- calm
- confident
- conversational
- not robotic
- not overly enthusiastic
- not like an IVR
- suitable for Indian English
- usable with Hindi/Hinglish

## First local candidate: Kokoro

Kokoro is an open-weight TTS model with multiple voices and local/offline deployment options.

Reference:
https://github.com/hexgrad/kokoro

A convenient local/API implementation can also expose Kokoro voices through HTTP and offline execution:
https://github.com/hangry-labs/kokoroTTS

### Voice evaluation criteria

Benchmark candidate voices on:

1. Naturalness
2. Indian-English suitability
3. Hindi pronunciation
4. Hinglish switching
5. Latency
6. Voice consistency
7. Emotional range
8. 8 kHz phone-call intelligibility
9. CPU/GPU load
10. Licensing suitability

Do not choose a voice simply because it sounds good in a studio-quality WAV.

It must still sound good after:

```text
TTS
 -> resampling
 -> telephony codec
 -> telephone speaker
```

---

# 11. Nyra Voice Personality

System-level voice personality:

```text
Name: Nyra

Role:
Personal AI assistant for Rafey.

Tone:
Warm, calm, concise, confident and polite.

Conversation style:
Natural human-like conversation.
Use short sentences.
Do not over-explain.
Do not repeat information unnecessarily.

Language:
Match the caller's language.
If the caller speaks Hindi, respond in Hindi.
If the caller speaks English, respond in English.
If the caller uses Hinglish, naturally use Hinglish.

Behavior:
Ask one question at a time.
Allow interruptions.
Do not speak over the caller.
Use natural pauses.
Never sound like a call-center IVR.

Identity:
Always identify yourself as Rafey's AI assistant when appropriate.
Never falsely claim to be Rafey.
```

---

# 12. Opening Greeting

Default:

> "Hi, I'm Nyra, Rafey's AI assistant. He's unavailable at the moment. May I know who's calling and what this is regarding?"

Hindi:

> "Namaste, main Nyra hoon, Rafey ki AI assistant. Woh abhi available nahi hain. Aapka naam aur call karne ka reason bata sakte hain?"

Hinglish:

> "Hi, main Nyra hoon, Rafey ki AI assistant. Rafey abhi available nahi hain. Aap bataiye, kaun bol rahe hain aur kis silsile mein call kiya hai?"

The greeting should be configurable.

---

# 13. Call Conversation Logic

```text
CALL START
    |
    v
Play greeting
    |
    v
Listen
    |
    +---- caller gives name ----> save name
    |
    +---- caller gives purpose --> save purpose
    |
    v
Determine missing information
    |
    +---- information missing ----> ask follow-up
    |
    +---- sufficient information -> confirm understanding
    |
    v
Ask whether caller wants callback/message
    |
    v
Thank caller
    |
    v
End call
    |
    v
Post-call analysis
    |
    v
WhatsApp notification
```

---

# 14. Intent Extraction

Every completed call should produce structured data.

Example:

```json
{
  "caller_name": "Rahul Sharma",
  "phone_number": "+91XXXXXXXXXX",
  "organization": "XYZ Technologies",
  "intent": "interview_rescheduling",
  "summary": "Rahul wants to move Rafey's interview to Friday.",
  "requested_action": "Confirm Friday interview time",
  "urgency": "high",
  "callback_requested": true,
  "preferred_callback_time": null,
  "appointment_date": "2026-09-25",
  "appointment_time": null,
  "spam_probability": 0.02,
  "sentiment": "neutral",
  "requires_human_attention": true
}
```

Use Pydantic models to validate the output.

---

# 15. Priority Logic

Priority should NOT be based only on emotion.

Use explicit factors:

```text
HIGH:
- urgent deadline
- interview/job opportunity
- family emergency
- explicit urgent callback
- important scheduled event
- security/account issue

MEDIUM:
- business enquiry
- appointment
- normal callback
- project/work request

LOW:
- general enquiry
- advertisement
- non-urgent information

SPAM:
- obvious marketing
- robocall
- repeated irrelevant calls
```

Make this configurable.

---

# 16. Caller Recognition

Maintain a contacts table.

```text
contacts
--------
id
name
phone_number
organization
relationship
notes
preferred_language
created_at
updated_at
```

When a call arrives:

```text
phone number
     |
     v
contacts lookup
     |
 +---+---+
 |       |
found   unknown
 |       |
known   ask name
```

Future enhancement:

- caller history
- previous intents
- preferred language
- last call
- notes

---

# 17. Memory

Nyra should have two memory layers.

## Short-term memory

Current call:

```text
conversation messages
caller information
current intent
pending questions
```

## Long-term memory

Only store useful, non-sensitive information:

```text
caller identity
organization
previous call summaries
preferences
approved notes
```

Do not automatically store arbitrary private information.

---

# 18. Tool System

Nyra should use tools rather than letting the LLM directly perform unrestricted actions.

Example tools:

```python
lookup_contact()
save_contact()
get_call_history()
create_callback_task()
check_calendar()
create_calendar_event()
send_whatsapp()
schedule_reminder()
transfer_call()
end_call()
```

Every tool should have:

- strict input schema
- authorization check
- logging
- error handling
- timeout
- audit entry

---

# 19. Calendar Integration

Phase 2/3 feature.

Possible providers:

- Google Calendar API
- local calendar integration
- ICS files

Use cases:

```text
Caller:
"Can Rafey attend tomorrow at 11?"

Nyra:
"I'll pass that along to him. I won't confirm the appointment
until he approves it."
```

Important:

Nyra should **not automatically commit Rafey to appointments** unless configured to do so.

---

# 20. WhatsApp Architecture

## Prototype

Use a controlled WhatsApp notification mechanism during development.

Possible approaches:

1. Official WhatsApp Business/Cloud API.
2. WhatsApp Web-based prototype automation.

The second approach can be fragile and should not be considered the production interface.

## Production

Prefer the official WhatsApp API if automated outbound messaging becomes important.

---

# 21. WhatsApp Message Format

```text
🤖 NYRA — NEW CALL

📞 Caller: {caller}
🏢 Organization: {organization}
⏱️ Duration: {duration}

🎯 Intent:
{intent}

📝 Summary:
{summary}

🎯 Action required:
{action}

🔴 Priority:
{priority}

📲 Callback:
{callback}

🕐 Preferred callback:
{time}

🎙️ Transcript:
{transcript_link}

Commands:
CALL BACK
IGNORE
REMIND <time>
TRANSFER
```

---

# 22. WhatsApp Command Processing

Example:

```text
Rafey:
CALL BACK
```

Nyra:

```text
Calling Rahul Sharma...
```

Example:

```text
Rafey:
REMIND 10AM
```

Nyra:

```text
Reminder created for 10:00 AM.
```

Example:

```text
Rafey:
IGNORE
```

Nyra:

```text
Call marked as handled.
```

All commands must be authenticated to Rafey's configured WhatsApp identity.

---

# 23. Telephony Strategy

## Route A — Android/SIM Gateway

This is the first route to investigate for the ₹0 target.

Concept:

```text
Indian SIM
   |
Android phone
   |
local telephony bridge
   |
Windows laptop
   |
Nyra
```

Research and test:

- Android call audio routing
- Bluetooth HFP
- USB audio routing
- SIP client/gateway options
- Android automation
- Asterisk compatibility
- whether bidirectional cellular audio can be legally/reliably exposed to the local computer

This route is technically experimental.

Do not assume Android will provide unrestricted cellular call audio to a normal application.

## Route B — Exotel AgentStream

Use if the Android route is unreliable.

Exotel AgentStream supports:

- real-time streaming
- WebSocket
- unidirectional audio
- bidirectional voicebot mode
- SIP/PSTN integration

Official docs:
https://docs.exotel.com/exotel-agentstream

Exotel's current documentation says AgentStream access requires KYC and appropriate account setup.

This route is therefore a **fallback**, not part of the ₹0 guarantee.

---

# 24. Audio Pipeline

Expected telephony pipeline:

```text
8 kHz/telephony audio
        |
        v
decode
        |
        v
noise/VAD processing
        |
        v
STT
        |
        v
LLM
        |
        v
TTS
        |
        v
resample/encode
        |
        v
telephone
```

Keep audio handling isolated in:

```text
nyra/audio/
```

---

# 25. Voice Activity Detection

Nyra must know when the caller starts/stops speaking.

Candidate:

- Silero VAD
- WebRTC VAD

Use VAD to:

- reduce unnecessary STT calls
- detect end-of-turn
- improve latency
- enable barge-in

---

# 26. Barge-In / Interruption Handling

This is essential for natural voice.

Example:

```text
Nyra:
"Sure, I can take a message—"

Caller:
"No, wait, actually..."

Nyra immediately stops speaking.
```

Implementation:

```text
TTS playing
    |
    v
VAD detects caller speech
    |
    v
cancel TTS playback
    |
    v
start STT
    |
    v
continue conversation
```

---

# 27. Latency Target

Target:

```text
Caller stops speaking
        ↓
~200-800 ms processing/turn detection
        ↓
AI response starts
```

Real-world latency will depend on:

- VAD
- STT
- LLM
- TTS
- CPU/GPU
- telephony network

Benchmark every component independently.

---

# 28. Suggested Python Libraries

## Core

```text
fastapi
uvicorn[standard]
pydantic
pydantic-settings
python-dotenv
httpx
websockets
```

## AI

```text
ollama
faster-whisper
```

## Audio

```text
numpy
scipy
soundfile
av
webrtcvad
```

Depending on selected implementation:

```text
silero-vad
```

## TTS

Evaluate:

```text
kokoro
soundfile
numpy
torch
```

Exact Kokoro installation should follow the current official repository instructions because package names/dependencies can change.

## Database

Start with:

```text
sqlalchemy
aiosqlite
alembic
```

Optional later:

```text
asyncpg
psycopg
```

## HTTP / API

```text
httpx
requests
```

## Security

```text
cryptography
passlib
python-jose
```

Only install authentication libraries actually needed by the selected dashboard/auth approach.

## Scheduling

```text
APScheduler
```

## Testing

```text
pytest
pytest-asyncio
pytest-cov
```

## Code quality

```text
ruff
black
mypy
pre-commit
```

---

# 29. Proposed requirements.txt

Start approximately with:

```text
fastapi
uvicorn[standard]
pydantic
pydantic-settings
python-dotenv

ollama
faster-whisper

numpy
scipy
soundfile
av
webrtcvad

sqlalchemy
aiosqlite
alembic

httpx
websockets

apscheduler

pytest
pytest-asyncio
pytest-cov

ruff
black
mypy
```

Add the exact TTS package after the Kokoro benchmark.

Do not blindly pin every package to arbitrary versions. After the environment works, generate a reproducible lock/requirements file with tested versions.

---

# 30. System Dependencies

Windows development machine may require:

- Python 3.11 or 3.12
- Git
- VS Code
- NVIDIA driver
- CUDA-compatible dependencies required by the selected inference stack
- Ollama for Windows
- optional Docker Desktop
- optional FFmpeg if a chosen audio component requires it

Note: current faster-whisper uses PyAV for bundled FFmpeg libraries, so a system FFmpeg install is not necessarily required.

---

# 31. Environment Variables

Create:

```text
.env
```

Example:

```env
APP_ENV=development

OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=<model>

DATABASE_URL=sqlite+aiosqlite:///./data/nyra.db

NYRA_NAME=Nyra
OWNER_NAME=Rafey

WHATSAPP_PROVIDER=<provider>
WHATSAPP_TOKEN=<secret>
WHATSAPP_PHONE_ID=<secret>

TELEPHONY_PROVIDER=android

EXOTEL_ACCOUNT_SID=<secret>
EXOTEL_API_KEY=<secret>
EXOTEL_API_TOKEN=<secret>

PUBLIC_BASE_URL=<cloudflare-tunnel-url>

LOG_LEVEL=INFO
```

Never commit `.env`.

Add:

```text
.env
*.db
data/
logs/
recordings/
```

to `.gitignore`.

---

# 32. Project Structure

```text
nyra/
│
├── app/
│   ├── main.py
│   │
│   ├── config/
│   │   ├── settings.py
│   │   └── logging.py
│   │
│   ├── api/
│   │   ├── routes_health.py
│   │   ├── routes_calls.py
│   │   ├── routes_whatsapp.py
│   │   └── routes_dashboard.py
│   │
│   ├── audio/
│   │   ├── vad.py
│   │   ├── audio_buffer.py
│   │   ├── resampler.py
│   │   └── codecs.py
│   │
│   ├── stt/
│   │   ├── base.py
│   │   └── faster_whisper.py
│   │
│   ├── tts/
│   │   ├── base.py
│   │   ├── kokoro.py
│   │   └── voice_profiles.py
│   │
│   ├── llm/
│   │   ├── client.py
│   │   ├── prompts.py
│   │   ├── schemas.py
│   │   └── intent.py
│   │
│   ├── conversation/
│   │   ├── manager.py
│   │   ├── state.py
│   │   └── policies.py
│   │
│   ├── telephony/
│   │   ├── base.py
│   │   ├── android_gateway.py
│   │   └── exotel.py
│   │
│   ├── whatsapp/
│   │   ├── base.py
│   │   ├── sender.py
│   │   └── commands.py
│   │
│   ├── contacts/
│   │   └── service.py
│   │
│   ├── calendar/
│   │   └── service.py
│   │
│   ├── memory/
│   │   └── service.py
│   │
│   ├── tools/
│   │   ├── registry.py
│   │   ├── contacts.py
│   │   ├── calendar.py
│   │   ├── callbacks.py
│   │   └── call_control.py
│   │
│   ├── database/
│   │   ├── models.py
│   │   ├── session.py
│   │   └── migrations/
│   │
│   └── postcall/
│       ├── analyzer.py
│       ├── summarizer.py
│       └── notifier.py
│
├── dashboard/
│   ├── templates/
│   └── static/
│
├── tests/
│   ├── test_intent.py
│   ├── test_conversation.py
│   ├── test_stt.py
│   ├── test_tts.py
│   ├── test_whatsapp.py
│   └── test_telephony.py
│
├── data/
├── recordings/
├── logs/
│
├── scripts/
│   ├── benchmark_stt.py
│   ├── benchmark_tts.py
│   └── test_call.py
│
├── .env.example
├── .gitignore
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

# 33. Database Schema

## calls

```text
id
call_id
phone_number
contact_id
started_at
ended_at
duration_seconds
status
language
intent
summary
requested_action
priority
callback_requested
callback_time
spam_score
requires_attention
recording_path
transcript_path
created_at
```

## contacts

```text
id
name
phone_number
organization
relationship
preferred_language
notes
created_at
updated_at
```

## messages

```text
id
call_id
role
content
timestamp
language
```

## tasks

```text
id
call_id
type
title
description
priority
status
due_at
created_at
completed_at
```

## memory

```text
id
category
key
value
source
confidence
created_at
updated_at
```

---

# 34. API Endpoints

Example:

```text
GET  /health
GET  /api/calls
GET  /api/calls/{id}
GET  /api/contacts
POST /api/contacts
GET  /api/tasks
POST /api/tasks
POST /api/callback/{call_id}
POST /api/ignore/{call_id}
POST /api/remind/{call_id}

POST /webhooks/whatsapp
POST /webhooks/telephony
WS   /ws/call/{call_id}
```

---

# 35. WebSocket Audio Architecture

For a streaming telephony provider:

```text
Telephony
    |
    | WebSocket
    v
FastAPI WebSocket
    |
    v
Audio buffer
    |
    +--> VAD
    |
    +--> STT
    |
    v
Conversation Manager
    |
    v
Ollama
    |
    v
TTS
    |
    v
audio encoder
    |
    v
WebSocket
    |
    v
Caller
```

Exotel's AgentStream documentation describes WebSocket-based real-time streaming and bidirectional voicebot operation.

---

# 36. Call State Machine

```text
IDLE
 |
 v
RINGING
 |
 v
ANSWERING
 |
 v
GREETING
 |
 v
LISTENING
 |
 +---- speech detected ----> PROCESSING
 |                              |
 |                              v
 |                          RESPONDING
 |                              |
 |                              v
 |                          LISTENING
 |
 +---- caller ends ----------> POST_CALL
 |
 v
POST_CALL
 |
 +--> transcript
 +--> intent
 +--> summary
 +--> priority
 +--> action
 +--> WhatsApp
 |
 v
COMPLETED
```

---

# 37. AI Prompt Design

Nyra should have a strict system prompt.

Core rules:

```text
You are Nyra, Rafey's personal AI phone assistant.

You are not Rafey.
Never claim to be Rafey.

Your job is to:
1. answer calls,
2. understand the caller,
3. collect useful information,
4. answer only within your authorized knowledge,
5. take messages,
6. identify required actions,
7. escalate when necessary.

Conversation rules:
- Be concise.
- Ask one question at a time.
- Do not interrupt.
- Never invent facts.
- Never make commitments unless explicitly authorized.
- Never reveal private information.
- Match the caller's language.
- Use natural English/Hindi/Hinglish.
- If unsure, say so and take a message.
- If the caller requests Rafey, explain that he is unavailable.
```

---

# 38. Structured AI Output

For post-call extraction:

```json
{
  "caller_name": null,
  "organization": null,
  "intent": "",
  "summary": "",
  "requested_action": "",
  "urgency": "low|medium|high",
  "callback_requested": false,
  "callback_time": null,
  "appointment": null,
  "spam": false,
  "requires_human_attention": true
}
```

Validate with Pydantic.

Never trust raw LLM JSON without validation.

---

# 39. Safety Rules

Nyra must NOT:

- give passwords
- disclose private documents
- disclose personal financial information
- reveal private calendar details
- make financial commitments
- accept contracts
- authorize payments
- pretend to be Rafey
- fabricate information
- automatically agree to important appointments unless explicitly configured
- transfer calls to arbitrary destinations without authorization

---

# 40. Security

## Secrets

Store credentials in:

```text
.env
```

Never:

```text
hard-code API tokens
commit API tokens
print API tokens to logs
```

## Webhooks

Verify:

- provider signature
- request timestamp
- request origin where applicable
- replay protection

## Dashboard

Require authentication if exposed beyond localhost.

## Data protection

Protect:

- call recordings
- transcripts
- caller phone numbers
- contact data
- WhatsApp credentials

---

# 41. Privacy Design

Default:

```text
Audio -> local
Transcript -> local
LLM -> local
TTS -> local
Database -> local
```

Cloud services should be optional.

Provide settings:

```text
SAVE_CALL_RECORDINGS=false
SAVE_TRANSCRIPTS=true
DELETE_RECORDINGS_AFTER_DAYS=7
DELETE_TRANSCRIPTS_AFTER_DAYS=30
```

---

# 42. Logging

Use structured logs.

Example:

```text
2026-09-18T23:15:02 INFO call.started call_id=...
2026-09-18T23:15:03 INFO stt.ready
2026-09-18T23:15:05 INFO intent.detected intent=interview
2026-09-18T23:16:43 INFO call.ended duration=101
2026-09-18T23:16:44 INFO whatsapp.sent
```

Never log:

- passwords
- tokens
- complete sensitive transcripts in normal production logs

---

# 43. Dashboard

Build a lightweight local dashboard.

Pages:

## Home

```text
Nyra

Calls today: 7
Important: 2
Callbacks: 3
Spam: 1
```

## Calls

```text
Caller | Intent | Priority | Duration | Status
```

## Call detail

```text
Caller
Phone
Time
Summary
Intent
Action
Priority
Transcript
Recording
```

## Contacts

```text
Name
Phone
Organization
History
```

## Settings

```text
Voice
Language
Greeting
AI model
TTS model
Recording
Privacy
Call rules
```

---

# 44. Testing Strategy

## Unit tests

Test:

- intent extraction
- priority calculation
- phone normalization
- caller recognition
- JSON validation
- WhatsApp command parsing
- tool authorization

## STT tests

Use a fixed set of recordings:

- English
- Hindi
- Hinglish
- noisy audio
- fast speech
- accents
- interruptions

## TTS tests

Measure:

- latency
- intelligibility
- naturalness
- pronunciation
- phone-quality audio

## Conversation tests

Scenarios:

1. Friend calls.
2. Unknown caller.
3. Job recruiter.
4. College call.
5. Spam caller.
6. Wrong number.
7. Caller asks for Rafey.
8. Caller leaves a message.
9. Caller requests callback.
10. Caller changes language.
11. Caller interrupts Nyra.
12. Caller speaks unclearly.
13. Caller refuses to identify themselves.
14. Caller asks for private information.

---

# 45. Acceptance Criteria — MVP

MVP is complete when:

- [ ] Nyra answers a test call.
- [ ] Nyra identifies herself as an AI assistant.
- [ ] Voice sounds natural enough for normal conversation.
- [ ] Caller can speak English.
- [ ] Caller can speak Hindi.
- [ ] Caller can use Hinglish.
- [ ] Nyra detects caller speech.
- [ ] Nyra handles at least basic interruption.
- [ ] Nyra asks caller name.
- [ ] Nyra asks reason for call.
- [ ] Nyra asks relevant follow-up questions.
- [ ] Nyra generates an accurate intent.
- [ ] Nyra creates a useful summary.
- [ ] Nyra determines requested action.
- [ ] Nyra assigns priority.
- [ ] Nyra stores transcript.
- [ ] WhatsApp notification is generated.
- [ ] Call history is stored.
- [ ] No paid LLM API is required.
- [ ] Core AI runs locally.

---

# 46. Phase-by-Phase Roadmap

## Phase 0 — Environment

Install:

```text
Python
Git
VS Code
Ollama
NVIDIA dependencies as required
```

Create:

```text
nyra/
```

Verify:

```text
python --version
ollama --version
nvidia-smi
```

---

## Phase 1 — Local Brain

Build:

```text
Python
  |
Ollama
  |
conversation manager
```

Implement:

- system prompt
- chat loop
- language matching
- tool schemas
- structured output

Goal:

```text
terminal <-> Nyra
```

---

## Phase 2 — Local STT

Install faster-whisper.

Build:

```text
audio file
    |
Whisper
    |
text
```

Benchmark:

- CPU
- GPU FP16
- GPU INT8

Goal:

Reliable English/Hindi/Hinglish transcription.

---

## Phase 3 — Local TTS

Install/test Kokoro.

Create:

```text
voice_profiles.py
```

Benchmark at least 3 voices.

Evaluate:

- naturalness
- female voice quality
- Hindi
- English
- Hinglish
- latency

Goal:

```text
text -> natural Nyra voice
```

---

## Phase 4 — Full Local Conversation

Build:

```text
Microphone
   |
VAD
   |
STT
   |
Ollama
   |
TTS
   |
Speaker
```

Add:

- turn detection
- interruption
- conversation state
- timeout
- silence handling

Goal:

A local voice conversation with Nyra.

---

## Phase 5 — Post-Call Intelligence

Implement:

```text
transcript
   |
post-call analyzer
   |
structured JSON
   |
summary
   |
priority
   |
action
```

Goal:

Accurate call analysis.

---

## Phase 6 — WhatsApp

Implement:

```text
summary
   |
WhatsApp adapter
   |
Rafey
```

Then implement:

```text
CALL BACK
IGNORE
REMIND
TRANSFER
```

Goal:

WhatsApp becomes Nyra's control panel.

---

## Phase 7 — Telephony

First investigate Android/SIM gateway.

Test:

```text
real phone call
   |
Android
   |
PC
   |
Nyra
```

If unreliable, move to Exotel AgentStream.

Exotel's bidirectional AgentStream is designed for real-time conversational voicebots over WebSocket.

---

## Phase 8 — Caller Recognition

Add:

```text
phone number
   |
contacts
   |
caller profile
```

Nyra can then say:

> "Hi Rahul, this is Nyra..."

instead of asking for the caller's name every time.

---

## Phase 9 — Calendar

Add calendar read access.

Then optionally:

```text
check availability
create event
reschedule
remind
```

Require confirmation for important actions.

---

## Phase 10 — Dashboard

Build the local web dashboard.

Goal:

Manage Nyra without editing configuration files.

---

## Phase 11 — Reliability

Add:

- retries
- timeouts
- crash recovery
- service auto-start
- health checks
- backups
- database migrations
- structured logs

---

# 47. Windows Startup

Once stable, Nyra should start automatically.

Recommended services:

```text
Ollama
Nyra backend
Cloudflare Tunnel
```

Use Windows Task Scheduler or a proper service wrapper.

Do not expose the dashboard publicly without authentication.

---

# 48. Cloudflare Tunnel

During development:

```text
Internet
   |
Cloudflare Tunnel
   |
localhost:8000
```

Use it when a telephony provider needs a public HTTPS/WSS endpoint.

Do not treat a temporary tunnel as a permanent production architecture.

---

# 49. Failure Handling

If STT fails:

> "Sorry, I didn't catch that. Could you repeat that?"

If LLM fails:

> "I'm having a little trouble processing that. I can take a message for Rafey."

If TTS fails:

Fallback to a simpler local voice.

If network fails:

Use local AI where possible.

If WhatsApp fails:

Store notification in an outbox and retry.

If telephony disconnects:

Finalize the call as incomplete and still process the transcript collected so far.

---

# 50. Outbox Pattern

Do not send WhatsApp directly from the call-ending handler.

Use:

```text
Call ends
   |
create notification
   |
outbox
   |
worker
   |
WhatsApp
```

This prevents losing a summary because WhatsApp is temporarily unavailable.

---

# 51. Backup Strategy

Back up:

```text
data/nyra.db
config
voice profiles
approved prompts
```

Do NOT automatically back up recordings forever.

Suggested:

```text
recordings: 7 days
transcripts: 30 days
database: periodic backup
```

Make retention configurable.

---

# 52. Performance Benchmarks

Track:

```text
STT latency
LLM first-token latency
LLM total latency
TTS first-audio latency
end-of-speech -> response latency
GPU VRAM
RAM
CPU
call quality
```

Example target dashboard:

```text
STT:       220 ms
LLM:       480 ms
TTS:       350 ms
Total:    ~1.0 sec
```

These are targets, not guaranteed results.

---

# 53. Model Selection Procedure

Do not pick models solely from benchmarks.

Create a test suite containing:

```text
20 English calls
20 Hindi calls
20 Hinglish calls
10 noisy calls
10 fast speakers
10 interruption cases
```

Score:

```text
STT accuracy
LLM response quality
TTS naturalness
latency
memory usage
```

Then select the best overall local combination for the RTX 3050.

---

# 54. Licensing

Before deploying publicly or commercially, verify the licenses of:

- LLM
- STT model
- TTS model
- voice model
- libraries
- datasets
- telephony provider

"Free to download" does not necessarily mean "free for every commercial use."

Keep a `THIRD_PARTY_LICENSES.md` file.

---

# 55. Future Features

After the core assistant works:

### Smart caller profiles

```text
Rahul
→ recruiter
→ preferred language English
→ previous calls: 3
→ last topic: internship
```

### Voice customization

Create a configurable Nyra voice profile:

```text
warmth
speed
pitch
pause length
formality
```

### Smart routing

```text
friend -> casual
recruiter -> professional
college -> formal
spam -> short
```

### Human transfer

```text
Caller needs Rafey
       |
       v
Nyra asks permission
       |
       v
transfer call
```

### Email integration

Send the same summary by email.

### Telegram backup

Optional secondary notification channel.

### Local semantic memory

Use embeddings for:

- previous caller interactions
- old call summaries
- contact notes

Possible local stack:

```text
Ollama embeddings
+
FAISS/Chroma
```

Only add this if normal SQL search is insufficient.

---

# 56. Recommended Final Stack

```text
                 NYRA
                  |
       +----------+----------+
       |                     |
   TELEPHONY             LOCAL AI
       |                     |
 Android/SIM          +------+------+
       |              |             |
 experimental        STT           LLM
       |          faster-whisper   Ollama
       |              |             |
       |              +------+------+
       |                     |
       |                    TTS
       |                  Kokoro
       |                     |
       +----------+----------+
                  |
              WhatsApp
                  |
                Rafey
```

### Core technologies

```text
Python
FastAPI
WebSockets
Ollama
faster-whisper
Kokoro
PyTorch
NumPy
PyAV
WebRTC/Silero VAD
SQLAlchemy
SQLite
APScheduler
Pydantic
HTTPX
pytest
Ruff
Black
MyPy
Cloudflare Tunnel
```

### Optional/fallback technologies

```text
Exotel AgentStream
Google Calendar API
PostgreSQL
Docker
WhatsApp Cloud API
FAISS/Chroma
```

---

# 57. Definition of Done

Nyra is considered production-ready for personal use when:

```text
[✓] Answers real incoming calls
[✓] Natural female voice
[✓] English
[✓] Hindi
[✓] Hinglish
[✓] Caller identification
[✓] Intent recognition
[✓] Follow-up questions
[✓] Summary
[✓] Action extraction
[✓] Priority detection
[✓] Callback detection
[✓] Transcript
[✓] Caller memory
[✓] WhatsApp summary
[✓] WhatsApp controls
[✓] Calendar integration
[✓] Spam handling
[✓] Barge-in
[✓] Local AI
[✓] Secure credentials
[✓] Call history
[✓] Dashboard
[✓] Error recovery
[✓] Logging
[✓] Backups
```

---

# 58. Recommended Build Order

Do NOT start with the telephone integration.

Build in this exact order:

```text
1. Ollama
      ↓
2. Nyra text personality
      ↓
3. faster-whisper
      ↓
4. Kokoro TTS
      ↓
5. Local voice conversation
      ↓
6. VAD + interruption
      ↓
7. Intent extraction
      ↓
8. SQLite memory
      ↓
9. WhatsApp notification
      ↓
10. WhatsApp commands
      ↓
11. Android/SIM telephony experiment
      ↓
12. Exotel fallback if required
      ↓
13. Caller recognition
      ↓
14. Calendar
      ↓
15. Dashboard
      ↓
16. Security/reliability
      ↓
17. Always-on deployment
```

This order minimizes wasted work.

If the telephone integration changes later, the AI system remains reusable.

---

# 59. Final Design Principle

Nyra should be built as a **replaceable local-first platform**, not as one giant script.

The interfaces should be:

```python
class STTProvider:
    ...

class TTSProvider:
    ...

class LLMProvider:
    ...

class TelephonyProvider:
    ...

class NotificationProvider:
    ...
```

Then:

```text
Nyra
 |
 +-- LocalSTT
 +-- LocalTTS
 +-- OllamaLLM
 +-- AndroidTelephony
 +-- WhatsAppNotifier
```

can later become:

```text
Nyra
 |
 +-- LocalSTT
 +-- LocalTTS
 +-- OllamaLLM
 +-- ExotelTelephony
 +-- WhatsAppCloudNotifier
```

without rewriting the entire project.

**The core objective is therefore:**

> Build Nyra's intelligence completely locally and for ₹0 first. Treat telephony as a pluggable layer, with Android/SIM as the experimental free route and Exotel AgentStream as the reliable fallback.

---

## Official references

- Ollama API: https://docs.ollama.com/api
- faster-whisper: https://github.com/SYSTRAN/faster-whisper
- Kokoro: https://github.com/hexgrad/kokoro
- Kokoro local/API implementation: https://github.com/hangry-labs/kokoroTTS
- Exotel AgentStream: https://docs.exotel.com/exotel-agentstream
- Exotel AgentStream quickstart: https://docs.exotel.com/exotel-agentstream/overview-and-quickstart

---

## Project Status

**Current phase:** Planning  
**Project:** Nyra  
**Architecture:** Local-first  
**Target recurring AI cost:** ₹0  
**Primary development machine:** Windows laptop + RTX 3050  
**Primary language:** Python  
**Voice:** Natural female neural TTS  
**Languages:** English + Hindi + Hinglish  
**Primary notification:** WhatsApp  
**Primary telephony experiment:** Android/SIM gateway  
**Fallback telephony:** Exotel AgentStream
