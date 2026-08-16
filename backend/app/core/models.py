"""Import every model so Alembic can discover the complete metadata graph."""

from app.modules.auth.models import VerificationChallenge
from app.modules.bets.models import Bet, BetEditEvent, BetVisibilityOverride, Outcome
from app.modules.groups.models import Group, GroupMember
from app.modules.house.models import HouseLedgerEntry
from app.modules.ledger.models import LedgerEntry
from app.modules.notifications.models import EmailOutbox, Notification, NotificationPreference
from app.modules.resolution.models import ResolutionEvent
from app.modules.trading.models import Position, Trade
from app.modules.users.models import User

__all__ = [
    "Bet",
    "BetEditEvent",
    "BetVisibilityOverride",
    "EmailOutbox",
    "Group",
    "GroupMember",
    "HouseLedgerEntry",
    "LedgerEntry",
    "Notification",
    "NotificationPreference",
    "Outcome",
    "Position",
    "ResolutionEvent",
    "Trade",
    "User",
    "VerificationChallenge",
]
