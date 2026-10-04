from decimal import Decimal

from app.models import Cart, Order, Payment, PaymentStatus
from app.repository import Repository
from app.services import inventory, payments, pricing


class EmptyCart(Exception):
    pass


def checkout(
    repo: Repository,
    cart: Cart,
    card_number: str,
    installments: int = 1,
    coupon_code: str | None = None,
) -> Order:
    if not cart.items:
        raise EmptyCart("Carrinho vazio")

    breakdown = pricing.price_cart(cart.items, coupon_code)
    inventory.reserve(repo, cart.items)

    order_id = repo.next_order_id()
    try:
        payment = payments.charge(repo, order_id, breakdown.total, card_number, installments)
    except payments.PaymentError:
        inventory.release(repo, cart.items)
        raise

    order = Order(
        id=order_id,
        cart_id=cart.id,
        items=list(cart.items),
        subtotal=breakdown.subtotal,
        discount=breakdown.discount,
        shipping=breakdown.shipping,
        total=breakdown.total,
        coupon=coupon_code.strip().upper() if coupon_code else None,
        payment_id=payment.id,
    )
    repo.orders[order.id] = order
    cart.items.clear()
    return order


def refund_payment(repo: Repository, payment: Payment, amount: Decimal | None = None) -> Decimal:
    refunded = payments.refund(payment, amount)
    if payment.status is PaymentStatus.REFUNDED:
        order = repo.get_order(payment.order_id)
        inventory.release(repo, order.items)
    return refunded
