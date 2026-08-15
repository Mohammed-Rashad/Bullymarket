from decimal import ROUND_HALF_UP, Decimal

MONEY_SCALE = Decimal("0.00000001")


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_SCALE, rounding=ROUND_HALF_UP)
