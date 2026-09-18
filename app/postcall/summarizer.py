from typing import Optional
from app.llm.schemas import CallAnalysisResult


def format_whatsapp_summary(
    analysis: CallAnalysisResult,
    phone_number: str,
    duration_seconds: int,
) -> str:
    """Format CallAnalysisResult into WhatsApp message layout."""
    minutes = duration_seconds // 60
    seconds = duration_seconds % 60
    duration_str = f"{minutes:02d}:{seconds:02d}"

    caller = analysis.caller_name or "Unknown Caller"
    org = analysis.organization or "N/A"
    priority_emoji = {
        "high": "🔴 HIGH",
        "medium": "🟡 MEDIUM",
        "low": "🟢 LOW",
        "spam": "⛔ SPAM",
    }.get(analysis.urgency.lower(), "🟡 MEDIUM")

    callback_str = "YES" if analysis.callback_requested else "NO"
    time_str = analysis.preferred_callback_time or "Not specified"

    msg = f"""🤖 NYRA — NEW CALL

📞 Caller: {caller} ({phone_number})
🏢 Organization: {org}
⏱️ Duration: {duration_str}

🎯 Intent:
{analysis.intent}

📝 Summary:
{analysis.summary}

🎯 Action required:
{analysis.requested_action}

{priority_emoji} Priority
📲 Callback requested: {callback_str}
🕐 Preferred time: {time_str}

🎙️ Transcript:
Available in Nyra dashboard.

Commands:
CALL BACK
IGNORE
REMIND <time>
TRANSFER"""

    return msg
