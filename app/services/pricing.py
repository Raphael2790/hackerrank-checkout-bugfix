from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable

from app.models import CartItem

CENT = Decimal("0.01")
ZERO = Decimal("0.00")
SHIPPING_FEE = Decimal("25.00")
FREE_SHIPPING_THRESHOLD = Decimal("200.00")


class InvalidCoupon(Exception):
    pass


@dataclass(frozen=True)
class Coupon:
    code: str
    percent_off: Decimal = ZERO
    amount_off: Decimal = ZERO
    min_subtotal: Decimal = ZERO
    free_shipping: bool = False


COUPONS = {
    "DESCONTO10": Coupon("DESCONTO10", percent_off=Decimal("10")),
    "MENOS50": Coupon("MENOS50", amount_off=Decimal("50.00"), min_subtotal=Decimal("250.00")),
    "FRETEGRATIS": Coupon("FRETEGRATIS", free_shipping=True),
}


@dataclass(frozen=True)
class PriceBreakdown:
    subtotal: Decimal
    discount: Decimal
    shipping: Decimal
    total: Decimal


def get_coupon(code: str | None) -> Coupon | None:
    if not code:
        return None
    coupon = COUPONS.get(code.strip().upper())
    if coupon is None:
        raise InvalidCoupon(f"Cupom {code} inválido")
    return coupon


def calculate_subtotal(items: Iterable[CartItem]) -> Decimal:
    return sum((item.line_total for item in items), ZERO).quantize(CENT)


def calculate_discount(subtotal: Decimal, coupon: Coupon | None) -> Decimal:
    if coupon is None:
        return ZERO
    if subtotal < coupon.min_subtotal:
        raise InvalidCoupon(
            f"Cupom {coupon.code} exige subtotal mínimo de R$ {coupon.min_subtotal}"
        )
    discount = subtotal * coupon.percent_off / 100 + coupon.amount_off
    return min(discount, subtotal).quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_shipping(discounted_subtotal: Decimal, coupon: Coupon | None) -> Decimal:
    if coupon is not None and coupon.free_shipping:
        return ZERO
    if discounted_subtotal >= FREE_SHIPPING_THRESHOLD:
        return ZERO
    return SHIPPING_FEE


def price_cart(items: Iterable[CartItem], coupon_code: str | None = None) -> PriceBreakdown:
    coupon = get_coupon(coupon_code)
    subtotal = calculate_subtotal(items)
    discount = calculate_discount(subtotal, coupon)
    shipping = calculate_shipping(subtotal - discount, coupon)
    total = subtotal - discount + shipping
    return PriceBreakdown(subtotal, discount, shipping, total)
