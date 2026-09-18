from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, List, Any


class LLMProvider(ABC):
    """Abstract Base Class for LLM interaction."""

    @abstractmethod
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        temperature: float = 0.7,
    ) -> str:
        """Generate complete response from conversation messages."""
        pass

    @abstractmethod
    async def stream_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """Stream response tokens as they are generated."""
        pass

    @abstractmethod
    async def extract_structured_json(
        self,
        prompt: str,
        schema: Any,
    ) -> Dict[str, Any]:
        """Extract validated structured JSON response using LLM."""
        pass
