from decimal import Decimal

import pytest

from app.models import CartItem
from app.services.pricing import InvalidCoupon, price_cart


def items(*lines):
    return [CartItem(i, Decimal(price), qty) for i, (price, qty) in enumerate(lines, start=1)]


def test_subtotal_and_shipping_below_threshold():
    result = price_cart(items(("59.90", 2)))

    assert result.subtotal == Decimal("119.80")
    assert result.discount == Decimal("0.00")
    assert result.shipping == Decimal("25.00")
    assert result.total == Decimal("144.80")


def test_percent_coupon():
    result = price_cart(items(("100.00", 1)), "DESCONTO10")

    assert result.discount == Decimal("10.00")
    assert result.total == Decimal("115.00")


def test_coupon_code_is_case_insensitive():
    result = price_cart(items(("100.00", 1)), "desconto10")

    assert result.discount == Decimal("10.00")


def test_fixed_coupon_requires_minimum_subtotal():
    with pytest.raises(InvalidCoupon):
        price_cart(items(("100.00", 2)), "MENOS50")


def test_unknown_coupon_is_rejected():
    with pytest.raises(InvalidCoupon):
        price_cart(items(("100.00", 1)), "BLACKFRIDAY")


def test_free_shipping_coupon():
    result = price_cart(items(("19.90", 1)), "FRETEGRATIS")

    assert result.shipping == Decimal("0.00")
    assert result.total == Decimal("19.90")


def test_free_shipping_above_threshold():
    result = price_cart(items(("1299.90", 1)))

    assert result.shipping == Decimal("0.00")


def test_free_shipping_at_threshold():
    result = price_cart(items(("100.00", 2)))

    assert result.shipping == Decimal("0.00")
    assert result.total == Decimal("200.00")


def test_shipping_uses_subtotal_after_discount():
    # 220.00 - 10% = 198.00 -> abaixo do limite, paga frete
    result = price_cart(items(("110.00", 2)), "DESCONTO10")

    assert result.discount == Decimal("22.00")
    assert result.shipping == Decimal("25.00")
    assert result.total == Decimal("223.00")
