import logging
import tempfile
import io
import os
import asyncio
from typing import Optional, Union, Tuple
import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel

from app.stt.base import STTProvider, TranscriptionResult

logger = logging.getLogger("nyra.stt")


class FasterWhisperSTTProvider(STTProvider):
    """Local Speech-to-Text provider using faster-whisper (CTranslate2)."""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cuda",
        compute_type: str = "float16",
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model: Optional[WhisperModel] = None
        self._initialize_model()

    def _initialize_model(self):
        try:
            logger.info(f"Loading faster-whisper model '{self.model_size}' on {self.device} ({self.compute_type})...")
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            logger.info("faster-whisper model loaded successfully on CUDA.")
        except Exception as e:
            logger.warning(f"CUDA initialization failed for faster-whisper ({e}). Falling back to CPU (int8)...")
            self.device = "cpu"
            self.compute_type = "int8"
            try:
                self.model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type,
                )
                logger.info("faster-whisper model loaded successfully on CPU.")
            except Exception as cpu_err:
                logger.error(f"Failed to load faster-whisper on CPU: {cpu_err}")
                raise cpu_err

    async def transcribe_audio_bytes(
        self,
        audio_bytes: bytes,
        sample_rate: int = 16000,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe audio bytes (WAV/PCM/MP3) to text."""
        if not self.model:
            raise RuntimeError("faster-whisper model is not initialized.")

        # Convert raw PCM bytes (missing RIFF header) into valid WAV format
        if not audio_bytes.startswith(b"RIFF"):
            audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
            buffer = io.BytesIO()
            sf.write(buffer, audio_data, sample_rate, format="WAV", subtype="PCM_16")
            wav_payload = buffer.getvalue()
        else:
            wav_payload = audio_bytes

        # Save bytes to a temporary WAV file for CTranslate2 processing
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(wav_payload)
            tmp_path = tmp.name

        def _sync_transcribe() -> TranscriptionResult:
            segments, info = self.model.transcribe(
                tmp_path,
                language=language,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
            )

            text_segments = [seg.text.strip() for seg in segments]
            full_text = " ".join(text_segments).strip()
            detected_lang = info.language
            confidence = float(info.language_probability)

            logger.info(f"STT Result [{detected_lang}]: '{full_text}' (prob: {confidence:.2f})")
            return TranscriptionResult(
                text=full_text,
                language=detected_lang,
                confidence=confidence,
            )

        try:
            return await asyncio.to_thread(_sync_transcribe)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    def transcribe_numpy_array(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 16000,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe floating-point audio numpy array directly."""
        if not self.model:
            raise RuntimeError("faster-whisper model is not initialized.")

        segments, info = self.model.transcribe(
            audio_data,
            language=language,
            beam_size=5,
            vad_filter=True,
        )

        text_segments = [seg.text.strip() for seg in segments]
        full_text = " ".join(text_segments).strip()

        return TranscriptionResult(
            text=full_text,
            language=info.language,
            confidence=float(info.language_probability),
        )
