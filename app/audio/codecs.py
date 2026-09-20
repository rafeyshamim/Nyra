import io
import logging
import numpy as np
import soundfile as sf
from typing import Optional, Tuple
from app.audio.resampler import resample_pcm16_bytes

logger = logging.getLogger("nyra.audio.codecs")


def mulaw_to_pcm16(mulaw_bytes: bytes) -> bytes:
    """Convert G.711 mu-law raw bytes to 16-bit linear PCM raw bytes."""
    if not mulaw_bytes:
        return b""

    mulaw_samples = np.frombuffer(mulaw_bytes, dtype=np.uint8)
    y = mulaw_samples.astype(np.float32)
    y = 0x80 - y
    sign = np.sign(y)
    y = np.abs(y)
    exponent = (y.astype(np.int32) >> 4) & 0x07
    mantissa = y.astype(np.int32) & 0x0F
    sample = ((mantissa << 3) + 0x84) << exponent
    sample = sample - 0x84
    sample = sign * sample
    pcm16_samples = np.clip(sample, -32768, 32767).astype(np.int16)
    return pcm16_samples.tobytes()


def alaw_to_pcm16(alaw_bytes: bytes) -> bytes:
    """Convert G.711 a-law raw bytes to 16-bit linear PCM raw bytes."""
    if not alaw_bytes:
        return b""

    alaw_samples = np.frombuffer(alaw_bytes, dtype=np.uint8)
    y = (alaw_samples ^ 0x55).astype(np.int32)
    sign = np.where((y & 0x80) != 0, -1, 1)
    exponent = (y & 0x70) >> 4
    mantissa = y & 0x0F
    sample = np.where(
        exponent == 0,
        (mantissa << 4) + 8,
        ((mantissa << 4) + 0x108) << np.maximum(0, exponent - 1)
    )
    pcm16_samples = np.clip(sign * sample, -32768, 32767).astype(np.int16)
    return pcm16_samples.tobytes()


def pcm16_to_mulaw(pcm_bytes: bytes) -> bytes:
    """Convert 16-bit linear PCM raw bytes to G.711 mu-law raw bytes."""
    if not pcm_bytes:
        return b""

    pcm16_samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
    normalized = pcm16_samples / 32768.0
    sign = np.sign(normalized)
    abs_norm = np.abs(normalized)

    mu = 255.0
    compressed = sign * (np.log(1.0 + mu * abs_norm) / np.log(1.0 + mu))
    quantized = ((compressed + 1.0) / 2.0 * 255.0).astype(np.uint8)
    mulaw_bytes = (quantized ^ 0xFF).tobytes()
    return mulaw_bytes


def pcm16_to_alaw(pcm_bytes: bytes) -> bytes:
    """Convert 16-bit linear PCM raw bytes to G.711 a-law raw bytes."""
    if not pcm_bytes:
        return b""

    pcm16_samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.int32)
    sign = (pcm16_samples >> 8) & 0x80
    pcm_val = np.abs(pcm16_samples)
    pcm_val = np.where(pcm_val > 32635, 32635, pcm_val)

    exponent = np.zeros_like(pcm_val)
    mask = 0x4000
    for exp in range(7, 0, -1):
        cond = (pcm_val & mask) != 0
        exponent = np.where((exponent == 0) & cond, exp, exponent)
        mask >>= 1

    mantissa = (pcm_val >> np.where(exponent == 0, 4, exponent + 3)) & 0x0F
    alaw_byte = sign | (exponent << 4) | mantissa
    alaw_byte = (alaw_byte ^ 0x55).astype(np.uint8)
    return alaw_byte.tobytes()


def decode_audio_to_pcm16_16k(
    raw_audio: bytes,
    encoding: str,
    orig_sample_rate: int = 8000,
) -> bytes:
    """Convert incoming raw audio payload (PCMU, PCMA, linear PCM) to 16-bit 16kHz mono PCM."""
    if not raw_audio:
        return b""

    encoding_lower = encoding.lower()
    if "mulaw" in encoding_lower or "ulaw" in encoding_lower or "pcmu" in encoding_lower:
        pcm_bytes = mulaw_to_pcm16(raw_audio)
    elif "alaw" in encoding_lower or "pcma" in encoding_lower:
        pcm_bytes = alaw_to_pcm16(raw_audio)
    else:
        pcm_bytes = raw_audio

    if orig_sample_rate != 16000 and len(pcm_bytes) > 0:
        pcm_bytes = resample_pcm16_bytes(
            pcm_bytes,
            orig_sample_rate=orig_sample_rate,
            target_sample_rate=16000,
        )

    return pcm_bytes


def encode_pcm16_16k_to_target(
    audio_bytes: bytes,
    target_encoding: str = "audio/mulaw",
    target_sample_rate: int = 8000,
) -> bytes:
    """Encode internal audio payload (WAV or PCM16 16kHz) to target codec and sample rate."""
    if not audio_bytes:
        return b""

    pcm_bytes = audio_bytes
    current_sr = 16000

    # Strip WAV header if present
    if audio_bytes.startswith(b"RIFF") and b"WAVE" in audio_bytes[:16]:
        try:
            buffer = io.BytesIO(audio_bytes)
            data, current_sr = sf.read(buffer, dtype="int16")
            pcm_bytes = data.tobytes()
        except Exception as e:
            logger.warning(f"Failed to parse WAV header ({e}); stripping 44-byte header.")
            if len(audio_bytes) > 44:
                pcm_bytes = audio_bytes[44:]

    # Resample if target sample rate differs
    if current_sr != target_sample_rate and len(pcm_bytes) > 0:
        pcm_bytes = resample_pcm16_bytes(
            pcm_bytes,
            orig_sample_rate=current_sr,
            target_sample_rate=target_sample_rate,
        )

    enc_lower = target_encoding.lower()
    if "mulaw" in enc_lower or "ulaw" in enc_lower or "pcmu" in enc_lower:
        return pcm16_to_mulaw(pcm_bytes)
    elif "alaw" in enc_lower or "pcma" in enc_lower:
        return pcm16_to_alaw(pcm_bytes)

    return pcm_bytes
