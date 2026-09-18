# Getting Started — How to Run & Test Nyra Locally

This guide will walk you through setting up, launching, and testing **Nyra (Personal AI Call Assistant)** on your local Windows machine.

---

## 📋 Prerequisites Checklist

Before running Nyra, ensure you have:

1. **Python 3.11 or 3.12** installed.
2. **Ollama** installed and running locally.
   - Start Ollama in a terminal:
     ```powershell
     ollama serve
     ```
   - Ensure the AI model is pulled:
     ```powershell
     ollama pull qwen2.5:1.5b
     ```

---

## ⚙️ Step 1: Environment Setup

1. Open your terminal in the `Nyra` project folder:
   ```powershell
   cd c:\Users\rafey\Downloads\Nyra
   ```

2. Verify project dependencies are installed:
   ```powershell
   pip install -r requirements.txt
   ```

3. Create your `.env` configuration file from the template:
   ```powershell
   copy .env.example .env
   ```

---

## 🚀 Step 2: Choose How to Test Nyra

You can test Nyra in **3 different ways**:

### Method A: Interactive Terminal Simulator (Quickest Test)
Simulate a real phone call with Nyra directly inside your terminal using text:

```powershell
python scripts/terminal_chat.py
```

- **How it works**:
  - Nyra greets you as Rafey's AI assistant.
  - You can chat in **English**, **Hindi**, or **Hinglish**.
  - Type `hangup` or `exit` to end the call.
  - Nyra will automatically run **Post-Call Analysis** and display the extracted **Intent, Summary, Action Item, and Priority Rating**!

---

### Method B: Full Voice Duplex Simulation
Test the Voice Activity Detection (VAD) -> Speech-to-Text -> Ollama LLM -> Text-to-Speech synthesis pipeline:

```powershell
python scripts/local_duplex_chat.py
```

- **What it does**:
  - Runs full turn-taking voice synthesis.
  - Synthesizes Nyra's responses into WAV audio files.
  - Check generated WAV files in the [`recordings/`](file:///c:/Users/rafey/Downloads/Nyra/recordings) directory!

---

### Method C: Launch FastAPI Server & Web Dashboard UI (Full App)
Launch the complete web application with the local receptionist dashboard:

```powershell
uvicorn app.main:app --reload
```

1. Open your browser and go to:
   👉 **`http://localhost:8000`**

2. **Dashboard Features**:
   - **Metrics Cards**: View total calls, high priority items, pending callbacks, and blocked spam.
   - **Recent Calls Table**: View caller names, phone numbers, call intents, and priority badges (`HIGH`, `MEDIUM`, `LOW`, `SPAM`).
   - **View Transcript Modal**: Click the **View** button on any call to read the full conversation transcript and extracted action items!

---

## 🧪 Step 3: Run Automated Verification Tests

To verify all components (LLM, STT, TTS, VAD, Database, WhatsApp Outbox, Telephony, Dashboard):

```powershell
python -m pytest tests/
```

All 25 test cases should pass cleanly!

---

## 📌 Useful Commands Reference

| Task | Command |
|---|---|
| Start Web Server & UI | `uvicorn app.main:app --reload` |
| Run Terminal Chat | `python scripts/terminal_chat.py` |
| Run Duplex Voice Test | `python scripts/local_duplex_chat.py` |
| Run STT Benchmark | `python scripts/benchmark_stt.py` |
| Run TTS Benchmark | `python scripts/benchmark_tts.py` |
| Run Pytest Test Suite | `python -m pytest tests/` |
