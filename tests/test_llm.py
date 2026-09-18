import asyncio
import pytest
from app.llm.client import OllamaLLMProvider
from app.llm.intent import PostCallAnalyzer


def test_ollama_generate():
    async def run():
        llm = OllamaLLMProvider()
        response = await llm.generate_response(
            messages=[{"role": "user", "content": "Hi, is Rafey available?"}],
            system_prompt="You are Nyra, Rafey's AI assistant. Keep responses under 15 words.",
        )
        assert len(response) > 0
        assert isinstance(response, str)

    asyncio.run(run())


def test_post_call_analyzer():
    async def run():
        llm = OllamaLLMProvider()
        analyzer = PostCallAnalyzer(llm_provider=llm)

        sample_messages = [
            {"role": "assistant", "content": "Hi, I'm Nyra, Rafey's AI assistant. How can I help you?"},
            {"role": "user", "content": "Hi, I'm Rahul from XYZ Tech. I am calling to move Rafey's interview to Friday 10 AM."},
            {"role": "assistant", "content": "Got it Rahul. Should I ask Rafey to call you back to confirm?"},
            {"role": "user", "content": "Yes please, ask him to call me back."},
        ]

        analysis = await analyzer.analyze_transcript(
            caller_info="Phone: +919876543210",
            messages=sample_messages,
        )

        assert analysis.caller_name.lower().find("rahul") != -1 or "rahul" in analysis.summary.lower() or "xyz" in analysis.summary.lower()
        assert analysis.callback_requested is True
        assert analysis.urgency in ["high", "medium", "low", "spam"]

    asyncio.run(run())
