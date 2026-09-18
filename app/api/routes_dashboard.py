import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.session import get_db_session
from app.database.models import Call, Contact, Message, Task
from app.contacts.service import ContactService

logger = logging.getLogger("nyra.api.dashboard")
router = APIRouter(prefix="/api/dashboard", tags=["Dashboard API"])


@router.get("/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db_session)):
    """Fetch summary metrics for dashboard home page."""
    total_calls_stmt = select(func.count(Call.id))
    total_calls = (await db.execute(total_calls_stmt)).scalar() or 0

    high_priority_stmt = select(func.count(Call.id)).where(Call.priority == "high")
    high_priority_calls = (await db.execute(high_priority_stmt)).scalar() or 0

    callbacks_stmt = select(func.count(Call.id)).where(Call.callback_requested == True)
    callbacks_requested = (await db.execute(callbacks_stmt)).scalar() or 0

    spam_stmt = select(func.count(Call.id)).where(Call.priority == "spam")
    spam_calls = (await db.execute(spam_stmt)).scalar() or 0

    return {
        "total_calls": total_calls,
        "high_priority_calls": high_priority_calls,
        "callbacks_requested": callbacks_requested,
        "spam_calls": spam_calls,
    }


@router.get("/calls")
async def list_calls(
    priority: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session),
):
    """List calls with optional priority filtering and pagination."""
    stmt = select(Call).options(selectinload(Call.contact)).order_by(Call.started_at.desc())
    if priority:
        stmt = stmt.where(Call.priority == priority.lower())

    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    calls = list(result.scalars().all())

    call_list = []
    for c in calls:
        call_list.append({
            "id": c.id,
            "call_id": c.call_id,
            "phone_number": c.phone_number,
            "caller_name": c.contact.name if c.contact else "Unknown",
            "organization": c.contact.organization if c.contact else None,
            "intent": c.intent or "N/A",
            "summary": c.summary or "N/A",
            "priority": c.priority,
            "duration_seconds": c.duration_seconds,
            "callback_requested": c.callback_requested,
            "started_at": c.started_at.isoformat() if c.started_at else None,
        })

    return {"calls": call_list, "limit": limit, "offset": offset}


@router.get("/calls/{call_id}")
async def get_call_detail(call_id: str, db: AsyncSession = Depends(get_db_session)):
    """Fetch complete call details including transcript messages."""
    stmt = select(Call).options(selectinload(Call.contact), selectinload(Call.messages)).where(Call.call_id == call_id)
    result = await db.execute(stmt)
    call = result.scalar_one_or_none()

    if not call:
        raise HTTPException(status_code=404, detail="Call record not found")

    messages = [
        {
            "role": m.role,
            "content": m.content,
            "timestamp": m.timestamp.isoformat() if m.timestamp else None,
        }
        for m in call.messages
    ]

    return {
        "call_id": call.call_id,
        "phone_number": call.phone_number,
        "caller_name": call.contact.name if call.contact else "Unknown",
        "organization": call.contact.organization if call.contact else None,
        "intent": call.intent,
        "summary": call.summary,
        "requested_action": call.requested_action,
        "priority": call.priority,
        "duration_seconds": call.duration_seconds,
        "callback_requested": call.callback_requested,
        "callback_time": call.callback_time,
        "started_at": call.started_at.isoformat() if call.started_at else None,
        "messages": messages,
    }
