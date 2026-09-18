import numpy as np
from scipy import signal


def resample_pcm16_bytes(
    pcm_bytes: bytes,
    orig_sample_rate: int,
    target_sample_rate: int,
) -> bytes:
    """Resample 16-bit mono PCM raw bytes from orig_sample_rate to target_sample_rate."""
    if orig_sample_rate == target_sample_rate or len(pcm_bytes) == 0:
        return pcm_bytes

    audio_data = np.frombuffer(pcm_bytes, dtype=np.int16)
    num_output_samples = int(round(len(audio_data) * target_sample_rate / float(orig_sample_rate)))

    resampled_data = signal.resample(audio_data.astype(np.float32), num_output_samples)
    resampled_data = np.clip(resampled_data, -32768, 32767).astype(np.int16)

    return resampled_data.tobytes()
