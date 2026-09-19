import logging
import datetime
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import OutboxNotification
from app.whatsapp.sender import WhatsAppService

logger = logging.getLogger("nyra.whatsapp.outbox")


class OutboxWorker:
    """Processes enqueued outbox notifications and delivers them via WhatsApp."""

    def __init__(self):
        self.sender = WhatsAppService.get_sender()

    async def process_pending_outbox(self, session: AsyncSession) -> int:
        stmt = (
            select(OutboxNotification)
            .where(OutboxNotification.status == "pending")
            .order_by(OutboxNotification.created_at.asc())
            .limit(10)
        )
        result = await session.execute(stmt)
        pending_items: List[OutboxNotification] = list(result.scalars().all())

        if not pending_items:
            return 0

        processed_count = 0
        for item in pending_items:
            logger.info(f"Processing outbox notification #{item.id} for call {item.call_id}...")
            success = await self.sender.send_text(item.recipient, item.payload)

            if success:
                item.status = "sent"
                item.sent_at = datetime.datetime.now(datetime.timezone.utc)
                processed_count += 1
            else:
                item.retry_count += 1
                if item.retry_count >= 5:
                    item.status = "failed"
                logger.warning(f"Failed to send outbox notification #{item.id} (attempt {item.retry_count}).")

        await session.commit()
        return processed_count
