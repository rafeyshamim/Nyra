import logging
import datetime
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation.state import CallSession
from app.llm.client import OllamaLLMProvider
from app.llm.intent import PostCallAnalyzer
from app.llm.schemas import CallAnalysisResult
from app.database.models import Call, Message, Task, OutboxNotification
from app.contacts.service import ContactService
from app.postcall.summarizer import format_whatsapp_summary
from app.config.settings import settings

logger = logging.getLogger("nyra.postcall")


class PostCallProcessor:
    """Orchestrates post-call transcript analysis, database storage, and notification outbox."""

    def __init__(self, llm_provider: Optional[OllamaLLMProvider] = None):
        self.analyzer = PostCallAnalyzer(llm_provider=llm_provider)

    async def process_completed_call(
        self,
        session: AsyncSession,
        call_session: CallSession,
    ) -> Tuple[Call, CallAnalysisResult]:
        logger.info(f"[{call_session.call_id}] Processing post-call analysis...")

        # 1. Check/Lookup Contact
        contact = await ContactService.get_contact_by_phone(session, call_session.phone_number)
        caller_name_info = contact.name if contact else call_session.caller_name or "Unknown"

        # 2. Extract Intent & Structured JSON via LLM
        analysis: CallAnalysisResult = await self.analyzer.analyze_transcript(
            caller_info=f"Name: {caller_name_info}, Phone: {call_session.phone_number}",
            messages=call_session.messages,
        )

        # 3. Create Contact if caller provided name during conversation
        if not contact and analysis.caller_name and analysis.caller_name.lower() != "unknown":
            contact = await ContactService.create_contact(
                session,
                name=analysis.caller_name,
                phone_number=call_session.phone_number,
                organization=analysis.organization,
            )

        # 4. Save or Update Call Record
        from sqlalchemy import select
        res = await session.execute(select(Call).where(Call.call_id == call_session.call_id))
        call_record = res.scalars().first()

        if call_record:
            call_record.phone_number = call_session.phone_number
            call_record.contact_id = contact.id if contact else None
            call_record.started_at = datetime.datetime.fromtimestamp(call_session.start_time, datetime.timezone.utc)
            call_record.ended_at = datetime.datetime.now(datetime.timezone.utc)
            call_record.duration_seconds = call_session.duration_seconds
            call_record.status = "completed"
            call_record.language = call_session.detected_language
            call_record.intent = analysis.intent
            call_record.summary = analysis.summary
            call_record.requested_action = analysis.requested_action
            call_record.priority = analysis.urgency
            call_record.callback_requested = analysis.callback_requested
            call_record.callback_time = analysis.preferred_callback_time
            call_record.spam_score = analysis.spam_probability
            call_record.requires_attention = analysis.requires_human_attention
        else:
            call_record = Call(
                call_id=call_session.call_id,
                phone_number=call_session.phone_number,
                contact_id=contact.id if contact else None,
                started_at=datetime.datetime.fromtimestamp(call_session.start_time, datetime.timezone.utc),
                ended_at=datetime.datetime.now(datetime.timezone.utc),
                duration_seconds=call_session.duration_seconds,
                status="completed",
                language=call_session.detected_language,
                intent=analysis.intent,
                summary=analysis.summary,
                requested_action=analysis.requested_action,
                priority=analysis.urgency,
                callback_requested=analysis.callback_requested,
                callback_time=analysis.preferred_callback_time,
                spam_score=analysis.spam_probability,
                requires_attention=analysis.requires_human_attention,
            )
            session.add(call_record)
        await session.flush()

        # 5. Save/Sync Transcript Messages
        from sqlalchemy import select
        existing_msgs_res = await session.execute(
            select(Message).where(Message.call_id == call_session.call_id)
        )
        existing_msgs = existing_msgs_res.scalars().all() if hasattr(existing_msgs_res, "scalars") else []

        # If call_session has no messages in memory (e.g. multi-worker recovery without session), sync from DB
        if not call_session.messages and existing_msgs:
            for m in existing_msgs:
                call_session.messages.append({"role": m.role, "content": m.content})
        elif call_session.messages and len(existing_msgs) < len(call_session.messages):
            # If session has more messages than saved in DB, persist missing messages starting from len(existing_msgs)
            for msg in call_session.messages[len(existing_msgs):]:
                msg_record = Message(
                    call_id=call_session.call_id,
                    role=msg["role"],
                    content=msg["content"],
                )
                session.add(msg_record)

        # 6. Create Task if Callback or Attention is Required
        if analysis.callback_requested or analysis.requires_human_attention:
            task_record = Task(
                call_id=call_session.call_id,
                type="callback" if analysis.callback_requested else "followup",
                title=f"Call from {analysis.caller_name}: {analysis.intent}",
                description=f"Action: {analysis.requested_action}\nSummary: {analysis.summary}",
                priority=analysis.urgency,
                status="pending",
            )
            session.add(task_record)

        # 7. Outbox Pattern: Format WhatsApp Summary & Save to Outbox Table
        formatted_summary = format_whatsapp_summary(
            analysis=analysis,
            phone_number=call_session.phone_number,
            duration_seconds=call_session.duration_seconds,
        )

        outbox_entry = OutboxNotification(
            call_id=call_session.call_id,
            recipient=settings.whatsapp_recipient_number or call_session.phone_number,
            payload=formatted_summary,
            status="pending",
        )
        session.add(outbox_entry)

        await session.commit()
        await session.refresh(call_record)
        logger.info(f"[{call_session.call_id}] Post-call record saved. Outbox notification enqueued.")

        return call_record, analysis
