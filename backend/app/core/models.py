"""Import every model so Alembic can discover the complete metadata graph."""

from app.modules.bets.models import Bet, BetEditEvent, BetVisibilityOverride, Outcome
from app.modules.groups.models import Group, GroupMember
from app.modules.ledger.models import LedgerEntry
from app.modules.resolution.models import ResolutionEvent
from app.modules.trading.models import Position
from app.modules.users.models import User

__all__ = [
    "Bet",
    "BetEditEvent",
    "BetVisibilityOverride",
    "Group",
    "GroupMember",
    "LedgerEntry",
    "Outcome",
    "Position",
    "ResolutionEvent",
    "User",
]

