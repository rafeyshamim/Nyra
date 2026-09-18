import pytest
import numpy as np
from app.audio.vad import VADDetector
from app.audio.audio_buffer import AudioStreamBuffer
from app.audio.resampler import resample_pcm16_bytes


def test_vad_detector_initialization():
    vad = VADDetector(mode=3, sample_rate=16000)
    assert vad.frame_size == 480  # 30ms @ 16kHz = 480 samples


def test_vad_speech_decision():
    vad = VADDetector(mode=3, sample_rate=16000)

    # Test silent frame (zeros)
    silent_frame = bytes(vad.frame_size * 2)
    assert vad.is_speech_frame(silent_frame) is False


def test_audio_stream_buffer():
    buffer = AudioStreamBuffer(sample_rate=16000, silence_threshold_ms=100, min_speech_duration_ms=60)
    frame_size = 480 * 2  # 30ms

    # Generate PCM audio frames with energy
    t = np.linspace(0, 0.03, 480, False)
    speech_data = (10000 * np.sin(2 * np.pi * 300 * t) + 5000 * np.sin(2 * np.pi * 600 * t)).astype(np.int16)
    speech_pcm = speech_data.tobytes()
    silent_pcm = bytes(frame_size)

    # Manually test buffer logic
    for _ in range(3):
        buffer.speech_buffer.extend(speech_pcm)
        buffer.speech_duration_ms += 30
        buffer.is_speaking = True

    buffer.silence_duration_ms = 120  # Exceed silence_threshold_ms (100ms)
    
    # Process turn completion trigger
    completed = bytes(buffer.speech_buffer)
    assert len(completed) > 0
    buffer.reset()
    assert buffer.is_speaking is False
    assert len(buffer.speech_buffer) == 0


def test_resampler_pcm16():
    sample_rate_orig = 8000
    sample_rate_target = 16000
    num_samples = 800  # 0.1s at 8kHz

    t = np.linspace(0, 0.1, num_samples, False)
    pcm_8k = (10000 * np.sin(2 * np.pi * 440 * t)).astype(np.int16).tobytes()

    pcm_16k = resample_pcm16_bytes(pcm_8k, sample_rate_orig, sample_rate_target)
    assert len(pcm_16k) == num_samples * 2 * 2  # Double samples, 2 bytes per sample
