import logging
from typing import List, Dict
from app.llm.client import OllamaLLMProvider
from app.llm.prompts import INTENT_EXTRACTION_SYSTEM_PROMPT
from app.llm.schemas import CallAnalysisResult

logger = logging.getLogger("nyra.intent")


class PostCallAnalyzer:
    """Extracts structured intent, summary, priority, and actions from transcripts."""

    def __init__(self, llm_provider: OllamaLLMProvider = None):
        self.llm = llm_provider or OllamaLLMProvider()

    async def analyze_transcript(
        self,
        caller_info: str,
        messages: List[Dict[str, str]],
    ) -> CallAnalysisResult:
        transcript_text = "\n".join(
            f"{msg['role'].upper()}: {msg['content']}" for msg in messages
        )

        prompt = f"""{INTENT_EXTRACTION_SYSTEM_PROMPT}

Caller Details: {caller_info}

Transcript:
{transcript_text}

Respond ONLY with valid JSON matching the specified structure.
"""

        try:
            json_dict = await self.llm.extract_structured_json(prompt)
            result = CallAnalysisResult(**json_dict)
            return result
        except Exception as e:
            logger.error(f"Failed to parse post-call analysis result: {e}")
            # Safe fallback result
            return CallAnalysisResult(
                caller_name="Unknown",
                intent="General Inquiry",
                summary="Call ended before detailed intent could be extracted.",
                requested_action="Review transcript in dashboard",
                urgency="medium",
                callback_requested=True,
                spam_probability=0.0,
                requires_human_attention=True,
            )
