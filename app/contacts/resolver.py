import logging
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.contacts.service import ContactService
from app.memory.service import MemoryService
from app.database.models import Contact

logger = logging.getLogger("nyra.contacts.resolver")


class CallerResolver:
    """Resolves caller context, relationship, and history for Nyra sessions."""

    @staticmethod
    async def resolve_caller_context(session: AsyncSession, phone_number: str) -> Dict[str, Any]:
        contact: Optional[Contact] = await ContactService.get_contact_by_phone(session, phone_number)

        if contact:
            logger.info(f"Resolved known caller: {contact.name} ({contact.organization or 'Personal'})")
            # Fetch caller memory note if exists
            pref_time = await MemoryService.get_memory(session, f"contact:{contact.id}:preferred_time")
            return {
                "known": True,
                "caller_name": contact.name,
                "organization": contact.organization,
                "relationship": contact.relationship_type or "acquaintance",
                "preferred_language": contact.preferred_language or "en",
                "notes": contact.notes,
                "preferred_time": pref_time,
            }

        logger.info(f"Unknown caller phone number: {phone_number}")
        return {
            "known": False,
            "caller_name": None,
            "organization": None,
            "relationship": "unknown",
            "preferred_language": "en",
            "notes": None,
            "preferred_time": None,
        }
