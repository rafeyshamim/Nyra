import logging
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Memory

logger = logging.getLogger("nyra.memory")


class MemoryService:
    """Manages long-term caller memory and system preferences."""

    @staticmethod
    async def set_memory(
        session: AsyncSession,
        key: str,
        value: str,
        category: str = "caller_note",
        source: Optional[str] = None,
    ) -> Memory:
        stmt = select(Memory).where(Memory.key == key)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.value = value
            existing.category = category
            if source:
                existing.source = source
            await session.commit()
            await session.refresh(existing)
            return existing

        mem = Memory(
            key=key,
            value=value,
            category=category,
            source=source,
        )
        session.add(mem)
        await session.commit()
        await session.refresh(mem)
        return mem

    @staticmethod
    async def get_memory(session: AsyncSession, key: str) -> Optional[str]:
        stmt = select(Memory).where(Memory.key == key)
        result = await session.execute(stmt)
        mem = result.scalar_one_or_none()
        return mem.value if mem else None
