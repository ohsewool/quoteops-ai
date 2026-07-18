from decimal import Decimal

import pytest

from backend.domain.money import decimal_string, quantize_money, quantize_rate, to_decimal


def test_krw_rounding_uses_decimal_half_up() -> None:
    assert quantize_money("100.005") == Decimal("100.01")
    assert quantize_money("100.004") == Decimal("100.00")
    assert decimal_string("3384.625") == "3384.63"


def test_rates_use_six_decimal_places() -> None:
    assert quantize_rate("0.1234567") == Decimal("0.123457")
    assert decimal_string("0.25", rate=True) == "0.250000"


def test_binary_float_is_rejected_before_persistence() -> None:
    with pytest.raises(TypeError, match="Binary float"):
        to_decimal(0.25)
