from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.modules.amm import LmsrValueError, Side
from app.modules.amm.lmsr import cost, max_house_loss, prices, quote_trade

positive = st.decimals(
    min_value="0.01",
    max_value="100000",
    allow_nan=False,
    allow_infinity=False,
    places=2,
)
quantities = st.decimals(
    min_value="0",
    max_value="100000",
    allow_nan=False,
    allow_infinity=False,
    places=2,
)


@given(q_yes=quantities, q_no=quantities, b=positive)
def test_prices_sum_to_one(q_yes: Decimal, q_no: Decimal, b: Decimal) -> None:
    result = prices(q_yes, q_no, b)
    assert result.yes + result.no == Decimal(1)
    assert Decimal(0) <= result.yes <= Decimal(1)
    assert Decimal(0) <= result.no <= Decimal(1)


@given(b=positive)
def test_initial_cost_is_binary_loss_bound(b: Decimal) -> None:
    assert cost(0, 0, b) == max_house_loss(b)


@given(q_yes=quantities, q_no=quantities, b=positive, shares=positive)
def test_buy_then_sell_is_reversible(
    q_yes: Decimal,
    q_no: Decimal,
    b: Decimal,
    shares: Decimal,
) -> None:
    bought = quote_trade(q_yes, q_no, b, Side.YES, shares)
    sold = quote_trade(
        bought.q_yes_after,
        bought.q_no_after,
        b,
        Side.YES,
        -shares,
    )
    assert abs(bought.cost + sold.cost) < Decimal("0.0000000001")
    assert sold.q_yes_after == q_yes
    assert sold.q_no_after == q_no


@given(b=positive, yes=quantities, no=quantities)
def test_house_loss_is_bounded_for_either_resolution(
    b: Decimal,
    yes: Decimal,
    no: Decimal,
) -> None:
    collected = cost(yes, no, b) - cost(0, 0, b)
    bound = max_house_loss(b)
    assert collected - yes >= -bound - Decimal("0.0000000001")
    assert collected - no >= -bound - Decimal("0.0000000001")


def test_large_ratio_does_not_overflow() -> None:
    result = quote_trade(
        Decimal("1e1000"),
        Decimal(0),
        Decimal("50"),
        Side.YES,
        Decimal(1),
    )
    assert result.cost.is_finite()
    assert result.prices_after.yes == Decimal(1)
    assert result.prices_after.no == Decimal(0)


@pytest.mark.parametrize(
    ("q_yes", "q_no", "b", "delta"),
    [
        (0, 0, 0, 1),
        (-1, 0, 100, 1),
        (0, 0, 100, 0),
        (0, 0, 100, -1),
    ],
)
def test_invalid_states_are_rejected(
    q_yes: int,
    q_no: int,
    b: int,
    delta: int,
) -> None:
    with pytest.raises(LmsrValueError):
        quote_trade(q_yes, q_no, b, Side.YES, delta)
