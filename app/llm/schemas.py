from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class CallAnalysisResult(BaseModel):
    caller_name: Optional[str] = Field(default="Unknown", description="Name of the caller")
    organization: Optional[str] = Field(default=None, description="Company or organization name")
    intent: str = Field(description="Primary reason for the call")
    summary: str = Field(description="Concise 2-3 sentence summary")
    requested_action: str = Field(description="Action required by owner")
    urgency: Literal["high", "medium", "low", "spam"] = Field(
        default="medium", description="Priority level of call"
    )
    callback_requested: bool = Field(default=False, description="Whether caller asked for a callback")
    preferred_callback_time: Optional[str] = Field(default=None, description="Requested callback time/date")
    spam_probability: float = Field(default=0.0, description="Estimated probability of spam (0.0 to 1.0)")
    requires_human_attention: bool = Field(default=True, description="Whether owner needs to take action")


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str
    timestamp: Optional[str] = None
    language: Optional[str] = None


class CallContext(BaseModel):
    call_id: str
    phone_number: str
    caller_name: Optional[str] = None
    organization: Optional[str] = None
    language: str = "en"
    known_contact: bool = False
    messages: List[ChatMessage] = []
