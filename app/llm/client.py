import json
import logging
from typing import AsyncGenerator, Dict, List, Any
import httpx

from app.config.settings import settings
from app.llm.base import LLMProvider

logger = logging.getLogger("nyra.llm")


class OllamaLLMProvider(LLMProvider):
    """Ollama API Client implementing LLMProvider."""

    def __init__(
        self,
        base_url: str = settings.ollama_base_url,
        model: str = settings.ollama_model,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        temperature: float = 0.7,
    ) -> str:
        url = f"{self.base_url}/api/chat"

        formatted_messages = [{"role": "system", "content": system_prompt}] + messages

        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("message", {}).get("content", "").strip()
            except Exception as e:
                logger.error(f"Ollama generation error: {e}")
                raise

    async def stream_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        url = f"{self.base_url}/api/chat"

        formatted_messages = [{"role": "system", "content": system_prompt}] + messages

        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "stream": True,
            "options": {
                "temperature": temperature,
            },
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                async with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                            content = chunk.get("message", {}).get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                logger.error(f"Ollama streaming error: {e}")
                raise

    async def extract_structured_json(
        self,
        prompt: str,
        schema: Any = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.1,
            },
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                raw_response = data.get("response", "").strip()
                return json.loads(raw_response)
            except Exception as e:
                logger.error(f"Structured JSON extraction error: {e}")
                raise
