# Phase 4 — Voice Activity Detection (VAD) & Duplex Conversation Loop Implementation

## Overview
Phase 4 implements Voice Activity Detection (VAD), streaming audio frame buffering, telephony audio resampling, barge-in (interruption) handling, and a full voice duplex simulation loop for Nyra.

Key objectives achieved:
- **Voice Activity Detection**: Real-time frame analysis using `webrtcvad-wheels` with energy-threshold fallback to detect speech start and turn boundaries.
- **Barge-In (Interruption) Support**: Instantly detects when a caller speaks while Nyra is playing TTS audio, cancelling playback and resuming listening mode.
- **Audio Resampling**: Seamless PCM conversion between 8kHz (cellular/telephony), 16kHz (STT Whisper), and 24kHz (TTS output).
- **Full Voice Duplex Simulation**: Full integration loop connecting audio input -> VAD -> STT -> Ollama LLM -> TTS -> audio output.

---

## Architecture & Data Flow

```text
Microphone / Telephony Audio Stream (PCM)
                  │
                  ▼
         +------------------+
         |   VADDetector    |
         +------------------+
                  │
        (Is Speech Frame?)
             ├── YES ──► Accumulate Speech Buffer
             └── NO  ──► Check Silence Threshold (Turn Boundary)
                  │
                  ▼ (Speech Segment Completed)
         +------------------+
         |  FasterWhisper   |
         +------------------+
                  │ (Text Transcript)
                  ▼
         +------------------+
         |    Ollama LLM    |
         +------------------+
                  │ (Nyra Response Text)
                  ▼
         +------------------+
         |    Kokoro TTS    |
         +------------------+
                  │ (WAV Speech Chunks)
                  ▼
       Telephone Speaker Playout
```

---

## Core Classes & Modules

### 1. [`app/audio/vad.py`](file:///c:/Users/rafey/Downloads/Nyra/app/audio/vad.py)
Provides `VADDetector`:
- Processes 10ms, 20ms, or 30ms PCM audio frames.
- Uses `webrtcvad` for detection with energy-threshold fallback for robustness.

### 2. [`app/audio/audio_buffer.py`](file:///c:/Users/rafey/Downloads/Nyra/app/audio/audio_buffer.py)
Provides `AudioStreamBuffer`:
- Accumulates raw PCM audio chunks.
- Tracks active speech duration vs silence duration (`silence_threshold_ms=600ms`).
- Emits completed speech segments when a caller finishes speaking.

### 3. [`app/audio/resampler.py`](file:///c:/Users/rafey/Downloads/Nyra/app/audio/resampler.py)
Provides `resample_pcm16_bytes()`:
- High-quality signal resampling using `scipy.signal` for telephony rate conversion.

### 4. [`scripts/local_duplex_chat.py`](file:///c:/Users/rafey/Downloads/Nyra/scripts/local_duplex_chat.py)
Interactive simulation connecting VAD -> STT -> Ollama LLM -> TTS -> Speaker in a duplex loop.

### 5. [`tests/test_audio.py`](file:///c:/Users/rafey/Downloads/Nyra/tests/test_audio.py)
Automated unit tests for VAD, audio stream buffering, and resampling.

---

## Verification
Run audio unit tests:
```powershell
python -m pytest tests/test_audio.py
```
Run the full local duplex simulation:
```powershell
python scripts/local_duplex_chat.py
```
