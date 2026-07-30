from decimal import Decimal, getcontext

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.modules.amm.engine import AmmValueError, Side, buy_shares, get_prices

getcontext().prec = 38

positive_decimals = st.decimals(
    min_value=Decimal("0.0001"),
    max_value=Decimal("1000000"),
    allow_nan=False,
    allow_infinity=False,
    places=4,
)


def assert_decimal_close(
    actual: Decimal,
    expected: Decimal,
    *,
    relative_tolerance: Decimal = Decimal("1e-24"),
) -> None:
    tolerance = max(abs(expected) * relative_tolerance, Decimal("1e-32"))
    assert abs(actual - expected) <= tolerance


@given(pool_yes=positive_decimals, pool_no=positive_decimals, amount=positive_decimals)
@pytest.mark.parametrize("side", [Side.YES, Side.NO])
def test_buy_preserves_constant_product(
    pool_yes: Decimal, pool_no: Decimal, amount: Decimal, side: Side
) -> None:
    result = buy_shares(pool_yes, pool_no, amount, side)

    assert_decimal_close(result.pool_yes * result.pool_no, pool_yes * pool_no)
    assert result.shares_out.is_finite()
    assert result.shares_out > 0


@given(pool_yes=positive_decimals, pool_no=positive_decimals, amount=positive_decimals)
def test_buying_yes_moves_yes_price_up(
    pool_yes: Decimal, pool_no: Decimal, amount: Decimal
) -> None:
    before = get_prices(pool_yes, pool_no)
    result = buy_shares(pool_yes, pool_no, amount, Side.YES)
    after = get_prices(result.pool_yes, result.pool_no)

    assert after.yes > before.yes
    assert after.no < before.no
    assert_decimal_close(after.yes + after.no, Decimal(1))


@given(pool_yes=positive_decimals, pool_no=positive_decimals, amount=positive_decimals)
def test_buying_no_moves_no_price_up(
    pool_yes: Decimal, pool_no: Decimal, amount: Decimal
) -> None:
    before = get_prices(pool_yes, pool_no)
    result = buy_shares(pool_yes, pool_no, amount, Side.NO)
    after = get_prices(result.pool_yes, result.pool_no)

    assert after.no > before.no
    assert after.yes < before.yes
    assert_decimal_close(after.yes + after.no, Decimal(1))


@given(pool=positive_decimals, amount=positive_decimals)
@pytest.mark.parametrize("side", [Side.YES, Side.NO])
def test_balanced_pool_returns_fewer_shares_than_stake(
    pool: Decimal, amount: Decimal, side: Side
) -> None:
    result = buy_shares(pool, pool, amount, side)

    assert result.shares_out < amount


@given(pool_yes=positive_decimals, pool_no=positive_decimals, amount=positive_decimals)
@pytest.mark.parametrize("side", [Side.YES, Side.NO])
def test_trade_never_withdraws_more_than_available_inventory(
    pool_yes: Decimal, pool_no: Decimal, amount: Decimal, side: Side
) -> None:
    result = buy_shares(pool_yes, pool_no, amount, side)
    starting_inventory = pool_yes if side is Side.YES else pool_no

    assert result.shares_out < starting_inventory


@given(
    pool_yes=positive_decimals,
    pool_no=positive_decimals,
    first_amount=positive_decimals,
    second_amount=positive_decimals,
)
@pytest.mark.parametrize("side", [Side.YES, Side.NO])
def test_path_independence(
    pool_yes: Decimal,
    pool_no: Decimal,
    first_amount: Decimal,
    second_amount: Decimal,
    side: Side,
) -> None:
    single = buy_shares(pool_yes, pool_no, first_amount + second_amount, side)
    first = buy_shares(pool_yes, pool_no, first_amount, side)
    second = buy_shares(first.pool_yes, first.pool_no, second_amount, side)

    assert_decimal_close(first.shares_out + second.shares_out, single.shares_out)
    assert_decimal_close(second.pool_yes, single.pool_yes)
    assert_decimal_close(second.pool_no, single.pool_no)


@given(
    pool_yes=positive_decimals,
    pool_no=positive_decimals,
    small_amount=positive_decimals,
    increment=positive_decimals,
)
@pytest.mark.parametrize("side", [Side.YES, Side.NO])
def test_larger_trade_has_worse_average_price(
    pool_yes: Decimal,
    pool_no: Decimal,
    small_amount: Decimal,
    increment: Decimal,
    side: Side,
) -> None:
    large_amount = small_amount + increment
    small = buy_shares(pool_yes, pool_no, small_amount, side)
    large = buy_shares(pool_yes, pool_no, large_amount, side)

    assert large_amount / large.shares_out > small_amount / small.shares_out


def test_opposite_equal_trades_move_pool_back_toward_balance() -> None:
    first = buy_shares(Decimal(100), Decimal(100), Decimal(20), Side.YES)
    imbalance_after_first = abs(first.pool_yes - first.pool_no)
    second = buy_shares(first.pool_yes, first.pool_no, Decimal(20), Side.NO)

    assert abs(second.pool_yes - second.pool_no) < imbalance_after_first


@pytest.mark.parametrize(
    ("pool_yes", "pool_no", "amount", "side"),
    [
        (0, 100, 1, Side.YES),
        (100, 0, 1, Side.YES),
        (100, 100, 0, Side.YES),
        (100, 100, -1, Side.NO),
        (100, 100, 1, "maybe"),
        ("NaN", 100, 1, Side.YES),
    ],
)
def test_invalid_inputs_are_rejected(
    pool_yes: object, pool_no: object, amount: object, side: object
) -> None:
    with pytest.raises(AmmValueError):
        buy_shares(pool_yes, pool_no, amount, side)  # type: ignore[arg-type]
