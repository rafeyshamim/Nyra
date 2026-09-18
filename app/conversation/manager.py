import logging
from typing import AsyncGenerator, Optional
from app.config.settings import settings
from app.conversation.state import CallSession, CallStateEnum
from app.llm.client import OllamaLLMProvider
from app.llm.prompts import NYRA_SYSTEM_PROMPT

logger = logging.getLogger("nyra.conversation")


class ConversationManager:
    """Orchestrates turn-taking, LLM prompts, and state for active phone calls."""

    def __init__(self, llm_provider: Optional[OllamaLLMProvider] = None):
        self.llm = llm_provider or OllamaLLMProvider()

    def create_session(
        self,
        call_id: str,
        phone_number: str,
        caller_name: Optional[str] = None,
    ) -> CallSession:
        session = CallSession(call_id, phone_number, caller_name)
        session.transition_to(CallStateEnum.RINGING)
        return session

    def get_initial_greeting(self, session: CallSession) -> str:
        session.transition_to(CallStateEnum.GREETING)

        if session.caller_name:
            greeting = f"Hi {session.caller_name}, I'm {settings.nyra_name}, {settings.owner_name}'s AI assistant. He's unavailable right now. How can I help you today?"
        else:
            greeting = f"Hi, I'm {settings.nyra_name}, {settings.owner_name}'s AI assistant. He's unavailable at the moment. May I know who's calling and what this is regarding?"

        session.add_assistant_message(greeting)
        session.transition_to(CallStateEnum.LISTENING)
        return greeting

    async def process_user_turn(self, session: CallSession, user_text: str) -> str:
        """Process caller speech and return Nyra's response."""
        session.transition_to(CallStateEnum.PROCESSING)
        session.add_user_message(user_text)

        logger.info(f"[{session.call_id}] Caller: {user_text}")

        response_text = await self.llm.generate_response(
            messages=session.messages,
            system_prompt=NYRA_SYSTEM_PROMPT,
            temperature=0.6,
        )

        session.transition_to(CallStateEnum.RESPONDING)
        session.add_assistant_message(response_text)
        logger.info(f"[{session.call_id}] Nyra: {response_text}")

        session.transition_to(CallStateEnum.LISTENING)
        return response_text

    async def process_user_turn_stream(
        self, session: CallSession, user_text: str
    ) -> AsyncGenerator[str, None]:
        """Stream response tokens as they arrive from LLM."""
        session.transition_to(CallStateEnum.PROCESSING)
        session.add_user_message(user_text)

        full_response = []
        session.transition_to(CallStateEnum.RESPONDING)

        async for chunk in self.llm.stream_response(
            messages=session.messages,
            system_prompt=NYRA_SYSTEM_PROMPT,
            temperature=0.6,
        ):
            full_response.append(chunk)
            yield chunk

        complete_text = "".join(full_response)
        session.add_assistant_message(complete_text)
        session.transition_to(CallStateEnum.LISTENING)
