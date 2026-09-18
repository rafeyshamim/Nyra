import asyncio
import uuid
import sys
from pathlib import Path

# Ensure root directory is on sys.path
base_dir = Path(__file__).resolve().parent.parent
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

from app.config.logging import setup_logging, logger
from app.conversation.manager import ConversationManager
from app.llm.client import OllamaLLMProvider
from app.llm.intent import PostCallAnalyzer


async def main():
    setup_logging()
    print("=" * 60)
    print("   🤖 NYRA — Terminal Conversation Simulator")
    print("=" * 60)
    print("Type 'exit' or 'hangup' to end the call.\n")

    llm = OllamaLLMProvider()

    # Check Ollama status
    try:
        greeting_check = await llm.generate_response(
            messages=[{"role": "user", "content": "ping"}],
            system_prompt="Reply with 'pong' only.",
        )
        print(f"[System] Ollama connected successfully! Response: {greeting_check}\n")
    except Exception as e:
        print(f"[Error] Failed to connect to Ollama: {e}")
        print("Please make sure Ollama is running (`ollama serve`).")
        return

    manager = ConversationManager(llm_provider=llm)
    call_id = str(uuid.uuid4())[:8]
    session = manager.create_session(call_id=call_id, phone_number="+919876543210")

    initial_greeting = manager.get_initial_greeting(session)
    print(f"Nyra: {initial_greeting}\n")

    while True:
        try:
            user_input = input("Caller: ").strip()
            if not user_input:
                continue

            if user_input.lower() in ["exit", "hangup", "quit", "bye"]:
                print("\n[System] Call ended by caller.")
                break

            response = await manager.process_user_turn(session, user_input)
            print(f"Nyra: {response}\n")

        except (KeyboardInterrupt, EOFError):
            print("\n[System] Call terminated.")
            break

    # Run post-call analysis
    print("\n" + "=" * 60)
    print("   📊 POST-CALL ANALYSIS")
    print("=" * 60)
    analyzer = PostCallAnalyzer(llm_provider=llm)
    analysis = await analyzer.analyze_transcript(
        caller_info=f"Phone: {session.phone_number}",
        messages=session.messages,
    )

    print(f"📞 Caller Name:     {analysis.caller_name}")
    print(f"🏢 Organization:    {analysis.organization or 'N/A'}")
    print(f"🎯 Intent:          {analysis.intent}")
    print(f"📝 Summary:         {analysis.summary}")
    print(f"🎯 Action Required: {analysis.requested_action}")
    print(f"🔴 Priority:        {analysis.urgency.upper()}")
    print(f"📲 Callback:        {'YES' if analysis.callback_requested else 'NO'}")
    print(f"🤖 Spam Prob:       {analysis.spam_probability * 100:.1f}%")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
