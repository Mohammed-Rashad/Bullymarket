from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.resolution.models import ResolutionEvent


async def add_event(
    session: AsyncSession, event: ResolutionEvent
) -> ResolutionEvent:
    session.add(event)
    await session.flush()
    return event


async def list_events(
    session: AsyncSession, bet_id: UUID
) -> list[ResolutionEvent]:
    return list(
        await session.scalars(
            select(ResolutionEvent)
            .where(ResolutionEvent.bet_id == bet_id)
            .order_by(ResolutionEvent.created_at)
        )
    )
