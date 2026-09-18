import logging
import numpy as np
from typing import Optional, List

logger = logging.getLogger("nyra.audio.vad")


class VADDetector:
    """Voice Activity Detection wrapper using webrtcvad with fallback."""

    def __init__(self, mode: int = 3, sample_rate: int = 16000, frame_duration_ms: int = 30):
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_size = int(sample_rate * (frame_duration_ms / 1000.0))
        self.mode = mode
        self.vad = None
        self._initialize_vad()

    def _initialize_vad(self):
        try:
            import webrtcvad
            self.vad = webrtcvad.Vad(self.mode)
            logger.info(f"webrtcvad initialized with aggressiveness level {self.mode}.")
        except Exception as e:
            logger.warning(f"webrtcvad initialization error ({e}). Using energy-threshold VAD fallback.")
            self.vad = None

    def is_speech_frame(self, frame_bytes: bytes) -> bool:
        """Check if a single raw PCM frame (16-bit mono) contains speech."""
        if self.vad:
            try:
                return self.vad.is_speech(frame_bytes, self.sample_rate)
            except Exception:
                pass

        # Energy-based fallback VAD
        audio_data = np.frombuffer(frame_bytes, dtype=np.int16)
        if len(audio_data) == 0:
            return False
        
        rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
        return rms > 300.0  # Threshold for active speech energy

    def process_frames(self, pcm_bytes: bytes) -> List[bool]:
        """Process arbitrary length PCM bytes into list of frame speech decisions."""
        bytes_per_frame = self.frame_size * 2  # 16-bit = 2 bytes per sample
        num_frames = len(pcm_bytes) // bytes_per_frame
        decisions = []

        for i in range(num_frames):
            frame = pcm_bytes[i * bytes_per_frame : (i + 1) * bytes_per_frame]
            decisions.append(self.is_speech_frame(frame))

        return decisions
