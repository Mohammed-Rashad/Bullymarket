from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bets.service import list_resolved_bet_ids
from app.modules.groups.service import require_membership
from app.modules.leaderboard.schemas import (
    LeaderboardEntry,
    LeaderboardResponse,
    LeaderboardWindow,
)
from app.modules.ledger.service import get_net_results
from app.modules.users.service import list_users_by_ids


def _resolved_since(window: LeaderboardWindow, now: datetime) -> datetime | None:
    days = {
        LeaderboardWindow.WEEKLY: 7,
        LeaderboardWindow.BIWEEKLY: 14,
        LeaderboardWindow.MONTHLY: 30,
    }.get(window)
    return None if days is None else now - timedelta(days=days)


async def _build(
    session: AsyncSession,
    *,
    scope: str,
    window: LeaderboardWindow,
    bet_ids: list[UUID],
) -> LeaderboardResponse:
    results = await get_net_results(session, bet_ids)
    users = {
        user.id: user
        for user in await list_users_by_ids(
            session,
            [user_id for user_id, _amount in results],
        )
    }
    sorted_results = sorted(results, key=lambda row: (-row[1], str(row[0])))
    entries = [
        LeaderboardEntry(
            rank=index,
            user_id=user_id,
            display_name=users[user_id].display_name,
            net_profit_loss=Decimal(amount),
        )
        for index, (user_id, amount) in enumerate(sorted_results, start=1)
        if user_id in users
    ]
    return LeaderboardResponse(scope=scope, window=window, entries=entries)


async def get_group_leaderboard(
    session: AsyncSession,
    *,
    group_id: UUID,
    requesting_user_id: UUID,
    window: LeaderboardWindow,
    now: datetime | None = None,
) -> LeaderboardResponse:
    await require_membership(session, group_id, requesting_user_id)
    resolved_since = _resolved_since(window, now or datetime.now(UTC))
    bet_ids = await list_resolved_bet_ids(
        session,
        group_id=group_id,
        public=False,
        resolved_since=resolved_since,
    )
    return await _build(
        session,
        scope=f"group:{group_id}",
        window=window,
        bet_ids=bet_ids,
    )


async def get_public_leaderboard(
    session: AsyncSession,
    *,
    window: LeaderboardWindow,
    now: datetime | None = None,
) -> LeaderboardResponse:
    resolved_since = _resolved_since(window, now or datetime.now(UTC))
    bet_ids = await list_resolved_bet_ids(
        session,
        group_id=None,
        public=True,
        resolved_since=resolved_since,
    )
    return await _build(
        session,
        scope="public",
        window=window,
        bet_ids=bet_ids,
    )

