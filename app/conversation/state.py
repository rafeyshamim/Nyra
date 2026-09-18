from enum import Enum, auto
from typing import List, Dict, Optional
import time


class CallStateEnum(Enum):
    IDLE = auto()
    RINGING = auto()
    ANSWERING = auto()
    GREETING = auto()
    LISTENING = auto()
    PROCESSING = auto()
    RESPONDING = auto()
    POST_CALL = auto()
    COMPLETED = auto()
    FAILED = auto()


class CallSession:
    """Session holding active call state and messages history."""

    def __init__(self, call_id: str, phone_number: str, caller_name: Optional[str] = None):
        self.call_id = call_id
        self.phone_number = phone_number
        self.caller_name = caller_name
        self.organization: Optional[str] = None
        self.state: CallStateEnum = CallStateEnum.IDLE
        self.messages: List[Dict[str, str]] = []
        self.start_time: float = time.time()
        self.end_time: Optional[float] = None
        self.detected_language: str = "en"

    def transition_to(self, new_state: CallStateEnum):
        self.state = new_state

    def add_user_message(self, text: str):
        self.messages.append({"role": "user", "content": text})

    def add_assistant_message(self, text: str):
        self.messages.append({"role": "assistant", "content": text})

    @property
    def duration_seconds(self) -> int:
        end = self.end_time or time.time()
        return int(end - self.start_time)
