from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class NotificationProvider(ABC):
    """Abstract Base Class for WhatsApp Notification Provider."""

    @abstractmethod
    async def send_summary(
        self,
        recipient: str,
        caller_name: str,
        organization: Optional[str],
        duration_str: str,
        intent: str,
        summary: str,
        action: str,
        priority: str,
        callback_requested: bool,
        preferred_time: Optional[str] = None,
        transcript_link: str = "Available in Dashboard",
    ) -> bool:
        """Send formatted call summary notification."""
        pass

    @abstractmethod
    async def send_text(self, recipient: str, text: str) -> bool:
        """Send generic text message."""
        pass
