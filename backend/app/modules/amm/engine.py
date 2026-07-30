"""Pure CPMM math.

This module intentionally has no framework or database imports. Financial values use
``Decimal`` so the same calculations can be persisted to PostgreSQL ``NUMERIC`` columns
without a float conversion.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum

type DecimalLike = Decimal | int | str


class Side(StrEnum):
    YES = "yes"
    NO = "no"


@dataclass(frozen=True, slots=True)
class Prices:
    yes: Decimal
    no: Decimal


@dataclass(frozen=True, slots=True)
class TradeResult:
    pool_yes: Decimal
    pool_no: Decimal
    shares_out: Decimal


class AmmValueError(ValueError):
    """Raised when a pool or trade input cannot produce a valid market state."""


def _decimal(value: DecimalLike, *, name: str) -> Decimal:
    try:
        converted = value if isinstance(value, Decimal) else Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise AmmValueError(f"{name} must be a valid decimal") from exc
    if not converted.is_finite():
        raise AmmValueError(f"{name} must be finite")
    return converted


def _validated_pools(pool_yes: DecimalLike, pool_no: DecimalLike) -> tuple[Decimal, Decimal]:
    yes = _decimal(pool_yes, name="pool_yes")
    no = _decimal(pool_no, name="pool_no")
    if yes <= 0 or no <= 0:
        raise AmmValueError("pool values must be greater than zero")
    return yes, no


def get_prices(pool_yes: DecimalLike, pool_no: DecimalLike) -> Prices:
    """Return implied YES and NO probabilities for a valid pool state."""

    yes, no = _validated_pools(pool_yes, pool_no)
    total = yes + no
    return Prices(yes=no / total, no=yes / total)


def buy_shares(
    pool_yes: DecimalLike,
    pool_no: DecimalLike,
    amount: DecimalLike,
    side: Side | str,
) -> TradeResult:
    """Buy outcome shares while preserving ``pool_yes * pool_no``.

    Buying one outcome depletes that outcome's inventory and adds the stake to the
    opposite pool, exactly as specified in ``01_overview_and_mechanism.md``.
    """

    yes, no = _validated_pools(pool_yes, pool_no)
    stake = _decimal(amount, name="amount")
    if stake <= 0:
        raise AmmValueError("amount must be greater than zero")

    try:
        selected_side = side if isinstance(side, Side) else Side(side.lower())
    except (AttributeError, ValueError) as exc:
        raise AmmValueError("side must be 'yes' or 'no'") from exc

    invariant = yes * no
    if selected_side is Side.YES:
        new_no = no + stake
        new_yes = invariant / new_no
        shares_out = yes - new_yes
    else:
        new_yes = yes + stake
        new_no = invariant / new_yes
        shares_out = no - new_no

    if shares_out <= 0 or not shares_out.is_finite():
        raise AmmValueError("trade did not produce positive finite shares")

    return TradeResult(pool_yes=new_yes, pool_no=new_no, shares_out=shares_out)
