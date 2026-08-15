"""Pure binary LMSR math with stable log-sum-exp calculations.

Quantities and returned values are ``Decimal`` so callers can persist them directly to
``NUMERIC`` columns. Transcendental operations use bounded floats only after the
largest quantity has been factored out; raw ``q / b`` values are never exponentiated.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from math import exp, log

from .engine import Side

type DecimalLike = Decimal | int | str

LN_2 = Decimal(str(log(2)))


class LmsrValueError(ValueError):
    """Raised when an LMSR input cannot produce a valid market state."""


@dataclass(frozen=True, slots=True)
class LmsrPrices:
    yes: Decimal
    no: Decimal


@dataclass(frozen=True, slots=True)
class LmsrQuote:
    side: Side
    delta_shares: Decimal
    cost: Decimal
    q_yes_after: Decimal
    q_no_after: Decimal
    prices_after: LmsrPrices


def _decimal(value: DecimalLike, *, name: str) -> Decimal:
    try:
        converted = value if isinstance(value, Decimal) else Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise LmsrValueError(f"{name} must be a valid decimal") from exc
    if not converted.is_finite():
        raise LmsrValueError(f"{name} must be finite")
    return converted


def _state(
    q_yes: DecimalLike,
    q_no: DecimalLike,
    b: DecimalLike,
) -> tuple[Decimal, Decimal, Decimal]:
    yes = _decimal(q_yes, name="q_yes")
    no = _decimal(q_no, name="q_no")
    liquidity = _decimal(b, name="b")
    if yes < 0 or no < 0:
        raise LmsrValueError("issued share quantities cannot be negative")
    if liquidity <= 0:
        raise LmsrValueError("b must be greater than zero")
    return yes, no, liquidity


def _bounded_float(value: Decimal) -> float:
    """Convert a non-positive exponent to float without overflow."""

    if value < Decimal("-1000"):
        return float("-inf")
    return float(value)


def cost(q_yes: DecimalLike, q_no: DecimalLike, b: DecimalLike) -> Decimal:
    """Return ``b * log(exp(q_yes/b) + exp(q_no/b))`` stably."""

    yes, no, liquidity = _state(q_yes, q_no, b)
    maximum = max(yes, no)
    yes_offset = _bounded_float((yes - maximum) / liquidity)
    no_offset = _bounded_float((no - maximum) / liquidity)
    log_tail = Decimal(str(log(exp(yes_offset) + exp(no_offset))))
    return maximum + liquidity * log_tail


def prices(q_yes: DecimalLike, q_no: DecimalLike, b: DecimalLike) -> LmsrPrices:
    """Return current YES/NO marginal prices as a stable softmax."""

    yes, no, liquidity = _state(q_yes, q_no, b)
    difference = (no - yes) / liquidity
    if difference >= 100:
        yes_price = Decimal(0)
    elif difference <= -100:
        yes_price = Decimal(1)
    else:
        yes_price = Decimal(str(1 / (1 + exp(float(difference)))))
    return LmsrPrices(yes=yes_price, no=Decimal(1) - yes_price)


def quote_trade(
    q_yes: DecimalLike,
    q_no: DecimalLike,
    b: DecimalLike,
    side: Side | str,
    delta_shares: DecimalLike,
) -> LmsrQuote:
    """Quote a signed share change; negative deltas sell existing shares."""

    yes, no, liquidity = _state(q_yes, q_no, b)
    delta = _decimal(delta_shares, name="delta_shares")
    if delta == 0:
        raise LmsrValueError("delta_shares cannot be zero")
    try:
        selected_side = side if isinstance(side, Side) else Side(side.lower())
    except (AttributeError, ValueError) as exc:
        raise LmsrValueError("side must be 'yes' or 'no'") from exc

    new_yes = yes + delta if selected_side is Side.YES else yes
    new_no = no + delta if selected_side is Side.NO else no
    if new_yes < 0 or new_no < 0:
        raise LmsrValueError("a trade cannot reduce issued shares below zero")

    signed_cost = cost(new_yes, new_no, liquidity) - cost(yes, no, liquidity)
    return LmsrQuote(
        side=selected_side,
        delta_shares=delta,
        cost=signed_cost,
        q_yes_after=new_yes,
        q_no_after=new_no,
        prices_after=prices(new_yes, new_no, liquidity),
    )


def max_house_loss(b: DecimalLike) -> Decimal:
    """Return the worst-case LMSR subsidy for a binary market."""

    liquidity = _decimal(b, name="b")
    if liquidity <= 0:
        raise LmsrValueError("b must be greater than zero")
    return liquidity * LN_2
