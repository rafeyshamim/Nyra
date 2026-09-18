from abc import ABC, abstractmethod
from typing import Dict, Any, Callable, Awaitable


class TelephonyProvider(ABC):
    """Abstract Base Class for Telephony Gateway."""

    @abstractmethod
    async def answer_call(self, call_id: str) -> bool:
        """Answer an incoming phone call."""
        pass

    @abstractmethod
    async def end_call(self, call_id: str) -> bool:
        """Terminate an active call."""
        pass

    @abstractmethod
    async def transfer_call(self, call_id: str, destination: str) -> bool:
        """Transfer call to another number."""
        pass

    @abstractmethod
    def register_audio_handler(
        self,
        handler: Callable[[str, bytes], Awaitable[None]],
    ) -> None:
        """Register handler for incoming audio stream chunks from caller."""
        pass
