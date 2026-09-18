import pytest
from app.conversation.state import CallSession, CallStateEnum
from app.llm.schemas import CallAnalysisResult


def test_call_session_transitions():
    session = CallSession(call_id="test1234", phone_number="+919876543210")
    assert session.state == CallStateEnum.IDLE

    session.transition_to(CallStateEnum.RINGING)
    assert session.state == CallStateEnum.RINGING

    session.add_user_message("Hello, is Rafey available?")
    session.add_assistant_message("Hi, I'm Nyra, Rafey's AI assistant.")

    assert len(session.messages) == 2
    assert session.messages[0]["role"] == "user"
    assert session.messages[1]["role"] == "assistant"


def test_call_analysis_result_schema():
    result = CallAnalysisResult(
        caller_name="Rahul Sharma",
        organization="XYZ Tech",
        intent="Interview rescheduling",
        summary="Rahul wants to move Rafey's interview to Friday.",
        requested_action="Confirm new time",
        urgency="high",
        callback_requested=True,
    )
    assert result.caller_name == "Rahul Sharma"
    assert result.urgency == "high"
    assert result.callback_requested is True
