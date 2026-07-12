"""Canonical KRW Decimal rules used by all future deterministic pricing services."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

MONEY_PRECISION = 18
MONEY_SCALE = 2
RATE_PRECISION = 9
RATE_SCALE = 6
MONEY_QUANTUM = Decimal("0.01")
RATE_QUANTUM = Decimal("0.000001")


def to_decimal(value: Decimal | int | str) -> Decimal:
    """Accept exact inputs and reject binary floats before they reach persisted data."""

    if isinstance(value, float):
        raise TypeError("Binary float is prohibited for V2 monetary and rate values")
    return Decimal(value)


def quantize_money(value: Decimal | int | str) -> Decimal:
    return to_decimal(value).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def quantize_rate(value: Decimal | int | str) -> Decimal:
    return to_decimal(value).quantize(RATE_QUANTUM, rounding=ROUND_HALF_UP)


def decimal_string(value: Decimal | int | str, *, rate: bool = False) -> str:
    quantized = quantize_rate(value) if rate else quantize_money(value)
    return format(quantized, "f")
