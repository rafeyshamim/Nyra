from abc import ABC, abstractmethod
from typing import NamedTuple, Optional


class TranscriptionResult(NamedTuple):
    text: str
    language: str
    confidence: float


class STTProvider(ABC):
    """Abstract Base Class for Speech-to-Text provider."""

    @abstractmethod
    async def transcribe_audio_bytes(
        self,
        audio_bytes: bytes,
        sample_rate: int = 16000,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe raw audio bytes to text."""
        pass
