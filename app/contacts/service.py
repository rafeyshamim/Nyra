import logging
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Contact

logger = logging.getLogger("nyra.contacts")


class ContactService:
    """Manages caller contacts and phone number resolution."""

    @staticmethod
    async def get_contact_by_phone(session: AsyncSession, phone_number: str) -> Optional[Contact]:
        stmt = select(Contact).where(Contact.phone_number == phone_number)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_contact(
        session: AsyncSession,
        name: str,
        phone_number: str,
        organization: Optional[str] = None,
        relationship: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Contact:
        existing = await ContactService.get_contact_by_phone(session, phone_number)
        if existing:
            existing.name = name
            if organization:
                existing.organization = organization
            if relationship:
                existing.relationship_type = relationship
            if notes:
                existing.notes = notes
            await session.commit()
            await session.refresh(existing)
            return existing

        contact = Contact(
            name=name,
            phone_number=phone_number,
            organization=organization,
            relationship_type=relationship,
            notes=notes,
        )
        session.add(contact)
        await session.commit()
        await session.refresh(contact)
        return contact

    @staticmethod
    async def get_all_contacts(session: AsyncSession) -> List[Contact]:
        stmt = select(Contact).order_by(Contact.name.asc())
        result = await session.execute(stmt)
        return list(result.scalars().all())
