# Phase 2 — Local Speech-to-Text (STT) Implementation

## Overview
Phase 2 implements local high-accuracy speech transcription for Nyra using **faster-whisper** (a CTranslate2-optimized implementation of OpenAI's Whisper model).

Key objectives achieved:
- **₹0 recurring cost**: 100% offline local execution without reliance on external cloud speech APIs.
- **Multilingual Support**: Supports English, Hindi, and Hinglish auto-detection and transcription.
- **Hardware Optimized**: Supports CUDA FP16/INT8 GPU acceleration with automatic CPU INT8 fallback.

---

## Architecture & Components

```text
Incoming Audio (WAV/PCM Bytes)
             │
             ▼
+--------------------------+
|  FasterWhisperSTTProvider |
+--------------------------+
             │
             ├── 1. Hardware Check (CUDA / CPU Fallback)
             ├── 2. VAD Filtering (silence removal)
             └── 3. Beam Search Transcription
             │
             ▼
   TranscriptionResult
   (text, language, confidence)
```

---

## Core Classes & Modules

### 1. [`app/stt/faster_whisper.py`](file:///c:/Users/rafey/Downloads/Nyra/app/stt/faster_whisper.py)
Provides `FasterWhisperSTTProvider` extending `STTProvider`.

Features:
- `transcribe_audio_bytes()`: Converts raw WAV/PCM binary streams into structured transcription.
- `transcribe_numpy_array()`: Direct array floating point audio processing.
- Automatic CUDA device detection and CPU fallback handling.

### 2. [`scripts/benchmark_stt.py`](file:///c:/Users/rafey/Downloads/Nyra/scripts/benchmark_stt.py)
Benchmark CLI to test model initialization speed, transcription latency, and audio formatting.

### 3. [`tests/test_stt.py`](file:///c:/Users/rafey/Downloads/Nyra/tests/test_stt.py)
Automated test suite verifying model loading, audio decoding, and error recovery.

---

## Recommended Model Configuration

For the **NVIDIA RTX 3050 (4GB VRAM)**:

```python
# Primary CUDA setup
FasterWhisperSTTProvider(
    model_size="base",
    device="cuda",
    compute_type="float16"
)
```

If VRAM is needed for other services or lower latency is required:

```python
# Low VRAM / CPU setup
FasterWhisperSTTProvider(
    model_size="small",
    device="cpu",
    compute_type="int8"
)
```

---

## Verification
Run tests to verify the STT module:
```powershell
python -m pytest tests/test_stt.py
```
Run the STT benchmark:
```powershell
python scripts/benchmark_stt.py
```
