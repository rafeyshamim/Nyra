import logging
from typing import Optional, List, Tuple
from app.audio.vad import VADDetector

logger = logging.getLogger("nyra.audio.buffer")


class AudioStreamBuffer:
    """Buffers incoming streaming PCM audio frames and detects complete speech segments."""

    def __init__(
        self,
        sample_rate: int = 16000,
        silence_threshold_ms: int = 600,
        min_speech_duration_ms: int = 300,
    ):
        self.sample_rate = sample_rate
        self.silence_threshold_ms = silence_threshold_ms
        self.min_speech_duration_ms = min_speech_duration_ms
        self.vad = VADDetector(mode=3, sample_rate=sample_rate)

        self.buffer = bytearray()
        self.speech_buffer = bytearray()
        self.is_speaking = False
        self.silence_duration_ms = 0
        self.speech_duration_ms = 0

    def add_pcm_chunk(self, chunk: bytes) -> Optional[bytes]:
        """Add PCM chunk to stream. Returns complete speech bytes when turn ends, else None."""
        self.buffer.extend(chunk)
        bytes_per_frame = self.vad.frame_size * 2

        completed_speech: Optional[bytes] = None

        while len(self.buffer) >= bytes_per_frame:
            frame = bytes(self.buffer[:bytes_per_frame])
            del self.buffer[:bytes_per_frame]

            is_speech = self.vad.is_speech_frame(frame)

            if is_speech:
                if not self.is_speaking:
                    logger.debug("Speech start detected.")
                    self.is_speaking = True
                
                self.speech_buffer.extend(frame)
                self.speech_duration_ms += self.vad.frame_duration_ms
                self.silence_duration_ms = 0
            else:
                if self.is_speaking:
                    self.speech_buffer.extend(frame)
                    self.silence_duration_ms += self.vad.frame_duration_ms

                    if self.silence_duration_ms >= self.silence_threshold_ms:
                        logger.debug("Speech end / turn boundary detected.")
                        if self.speech_duration_ms >= self.min_speech_duration_ms:
                            completed_speech = bytes(self.speech_buffer)
                        
                        self.reset()

        return completed_speech

    def reset(self):
        """Reset current buffering state."""
        self.speech_buffer.clear()
        self.is_speaking = False
        self.silence_duration_ms = 0
        self.speech_duration_ms = 0
