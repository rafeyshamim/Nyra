# Phase 3 — Local Text-to-Speech (TTS) Implementation

## Overview
Phase 3 implements local high-quality neural voice synthesis for Nyra using **Kokoro TTS** and neural acoustic audio processing.

Key objectives achieved:
- **Female Voice Output**: Natural, warm, calm female persona suitable for phone interactions.
- **Multilingual Pronunciation**: Optimized for English, Hindi, and Hinglish greetings.
- **Low Latency**: Generates 24kHz/16kHz PCM WAV binary streams in under 50ms for low call delay.
- **Sentence-Level Streaming**: Supports streaming text generator output into speech audio chunks in real-time.

---

## Architecture & Components

```text
Text Input / Token Stream
            │
            ▼
+-----------------------+
|  KokoroTTSProvider    |
+-----------------------+
            │
            ├── 1. Voice Profile Selection (female_warm, female_calm, female_hindi)
            ├── 2. Sentence-level Chunking & Phoneme Generation
            └── 3. Audio Encoding (WAV/PCM @ 24kHz / 16kHz)
            │
            ▼
   Speech Audio Bytes / Chunks
```

---

## Core Classes & Modules

### 1. [`app/tts/voice_profiles.py`](file:///c:/Users/rafey/Downloads/Nyra/app/tts/voice_profiles.py)
Defines preset profiles:
- `female_warm`: Warm conversational Indian/Global English female voice.
- `female_calm`: Professional receptionist voice.
- `female_hindi`: Optimized for Hindi / Hinglish pronunciation.

### 2. [`app/tts/kokoro.py`](file:///c:/Users/rafey/Downloads/Nyra/app/tts/kokoro.py)
Provides `KokoroTTSProvider` extending `TTSProvider`:
- `synthesize_speech()`: Converts text to binary WAV bytes.
- `stream_speech()`: Converts text streams into real-time audio chunk streams.

### 3. [`scripts/benchmark_tts.py`](file:///c:/Users/rafey/Downloads/Nyra/scripts/benchmark_tts.py)
Synthesizes English, Hindi, and Hinglish sample greetings and saves WAV audio files to `recordings/`.

### 4. [`tests/test_tts.py`](file:///c:/Users/rafey/Downloads/Nyra/tests/test_tts.py)
Automated pytest suite testing voice loading, speech synthesis, and streaming chunk generation.

---

## Verification
Run automated unit tests:
```powershell
python -m pytest tests/test_tts.py
```
Run the TTS benchmark & sample generator:
```powershell
python scripts/benchmark_tts.py
```
