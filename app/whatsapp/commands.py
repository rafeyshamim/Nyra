import logging
import re
import datetime
from typing import Optional, Dict, Any
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Call, Task
from app.config.settings import settings

logger = logging.getLogger("nyra.whatsapp.commands")


class CommandResponse:
    def __init__(self, success: bool, message: str, action: str):
        self.success = success
        self.message = message
        self.action = action


class WhatsAppCommandProcessor:
    """Parses and executes WhatsApp control commands sent by owner."""

    def __init__(self, owner_phone: Optional[str] = None):
        self.owner_phone = owner_phone or settings.whatsapp_recipient_number

    def is_authorized(self, sender_phone: str) -> bool:
        """Security verification check for incoming WhatsApp command."""
        if not self.owner_phone:
            return True  # Development mode: allow commands if recipient number not explicitly locked
        return sender_phone.replace("+", "").strip() == self.owner_phone.replace("+", "").strip()

    async def execute_command(
        self,
        session: AsyncSession,
        sender_phone: str,
        command_text: str,
    ) -> CommandResponse:
        if not self.is_authorized(sender_phone):
            logger.warning(f"Unauthorized command attempt from phone: {sender_phone}")
            return CommandResponse(
                success=False,
                message="Unauthorized sender. Command ignored.",
                action="unauthorized",
            )

        cmd = command_text.strip().upper()
        logger.info(f"Processing WhatsApp command '{cmd}' from {sender_phone}...")

        # 1. CALL BACK command
        if cmd == "CALL BACK":
            # Fetch most recent call requiring attention
            stmt = (
                select(Call)
                .where(Call.requires_attention == True)
                .order_by(Call.created_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            latest_call = result.scalar_one_or_none()

            if not latest_call:
                return CommandResponse(
                    success=True,
                    message="No pending callback requests found.",
                    action="callback_none",
                )

            # Create callback task
            task = Task(
                call_id=latest_call.call_id,
                type="callback",
                title=f"Call back {latest_call.phone_number}",
                description=f"Callback requested for call: {latest_call.intent}",
                priority="high",
                status="pending",
            )
            session.add(task)
            latest_call.requires_attention = False
            await session.commit()

            return CommandResponse(
                success=True,
                message=f"Calling back {latest_call.phone_number} ({latest_call.intent})... Task created.",
                action="callback_created",
            )

        # 2. IGNORE command
        elif cmd == "IGNORE":
            stmt = (
                select(Call)
                .where(Call.requires_attention == True)
                .order_by(Call.created_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            latest_call = result.scalar_one_or_none()

            if latest_call:
                latest_call.requires_attention = False
                await session.commit()

            return CommandResponse(
                success=True,
                message="Latest call marked as ignored/handled.",
                action="ignored",
            )

        # 3. REMIND <time> command (e.g., REMIND 10AM, REMIND 5PM)
        elif cmd.startswith("REMIND"):
            time_match = re.search(r"REMIND\s+(.+)", cmd, re.IGNORECASE)
            time_str = time_match.group(1).strip() if time_match else "later"

            task = Task(
                type="reminder",
                title=f"Reminder set for {time_str}",
                description=f"WhatsApp scheduled reminder for {time_str}",
                priority="medium",
                status="pending",
            )
            session.add(task)
            await session.commit()

            return CommandResponse(
                success=True,
                message=f"Reminder created for {time_str}.",
                action="reminder_created",
            )

        # 4. TRANSFER command
        elif cmd == "TRANSFER":
            return CommandResponse(
                success=True,
                message="Call transfer request recorded. Transferring call to owner line...",
                action="transfer",
            )

        else:
            return CommandResponse(
                success=False,
                message="Unknown command. Supported: CALL BACK, IGNORE, REMIND <time>, TRANSFER",
                action="unknown",
            )
