"""
Offline sync and idempotency module
"""

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.operations import SyncEvent


class SyncService:
    """Sync and idempotency service"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_idempotency(self, user_id: UUID, idempotency_key: str) -> dict | None:
        """
        Check if request with idempotency key was already processed

        Returns:
            Previous response if exists, None otherwise
        """
        result = await self.db.execute(
            select(SyncEvent)
            .where(SyncEvent.user_id == user_id)
            .where(SyncEvent.idempotency_key == idempotency_key)
            .where(SyncEvent.expires_at > datetime.now())
        )

        event = result.scalar_one_or_none()
        return event.response if event else None

    async def record_sync_event(
        self,
        user_id: UUID,
        idempotency_key: str,
        event_type: str,
        payload: dict,
        response: dict,
        ttl_hours: int = 24,
    ) -> SyncEvent:
        """
        Record sync event for idempotency

        Args:
            user_id: User ID
            idempotency_key: Unique idempotency key
            event_type: Type of event
            payload: Request payload
            response: Response data
            ttl_hours: Time to live in hours

        Returns:
            Created sync event
        """
        event = SyncEvent(
            user_id=user_id,
            idempotency_key=idempotency_key,
            event_type=event_type,
            payload=payload,
            response=response,
            expires_at=datetime.now() + timedelta(hours=ttl_hours),
        )

        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)

        return event

    async def cleanup_expired_events(self) -> int:
        """
        Cleanup expired sync events

        Returns:
            Number of deleted events
        """
        from sqlalchemy import delete

        result = await self.db.execute(
            delete(SyncEvent).where(SyncEvent.expires_at <= datetime.now())
        )

        await self.db.commit()
        return result.rowcount
