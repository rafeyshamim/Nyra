from abc import ABC, abstractmethod
from typing import AsyncGenerator


class TTSProvider(ABC):
    """Abstract Base Class for Text-to-Speech provider."""

    @abstractmethod
    async def synthesize_speech(
        self,
        text: str,
        voice: str = "female_warm",
    ) -> bytes:
        """Synthesize text to audio bytes (PCM/WAV/telephony audio)."""
        pass

    @abstractmethod
    async def stream_speech(
        self,
        text_stream: AsyncGenerator[str, None],
        voice: str = "female_warm",
    ) -> AsyncGenerator[bytes, None]:
        """Synthesize text stream into streaming audio chunks."""
        pass
