from decimal import Decimal, InvalidOperation

from flask import Blueprint, Flask, current_app, jsonify, request

from app.models import Cart, CartItem, Order, Payment, Product
from app.repository import NotFound, Repository
from app.services import checkout as checkout_service
from app.services import pricing
from app.services.checkout import EmptyCart
from app.services.inventory import OutOfStock
from app.services.payments import InvalidPayment, PaymentDeclined, RefundNotAllowed
from app.services.pricing import InvalidCoupon

api = Blueprint("api", __name__)


class BadRequest(Exception):
    pass


def repo() -> Repository:
    return current_app.extensions["repo"]


def money(value: Decimal) -> str:
    return f"{value:.2f}"


def parse_money(value) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise BadRequest(f"Valor monetário inválido: {value!r}") from None


def body() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise BadRequest("Corpo da requisição deve ser um JSON")
    return data


# ---------- serialização ----------

def product_json(product: Product) -> dict:
    return {
        "id": product.id,
        "name": product.name,
        "price": money(product.price),
        "stock": product.stock,
    }


def item_json(item: CartItem) -> dict:
    return {
        "product_id": item.product_id,
        "unit_price": money(item.unit_price),
        "quantity": item.quantity,
        "line_total": money(item.line_total),
    }


def cart_json(cart: Cart) -> dict:
    return {
        "id": cart.id,
        "items": [item_json(i) for i in cart.items],
        "subtotal": money(pricing.calculate_subtotal(cart.items)),
    }


def order_json(order: Order) -> dict:
    return {
        "id": order.id,
        "cart_id": order.cart_id,
        "items": [item_json(i) for i in order.items],
        "subtotal": money(order.subtotal),
        "discount": money(order.discount),
        "shipping": money(order.shipping),
        "total": money(order.total),
        "coupon": order.coupon,
        "payment_id": order.payment_id,
    }


def payment_json(payment: Payment) -> dict:
    return {
        "id": payment.id,
        "order_id": payment.order_id,
        "amount": money(payment.amount),
        "installments": [money(v) for v in payment.installments],
        "card_last4": payment.card_last4,
        "status": payment.status.value,
        "refunded_amount": money(payment.refunded_amount),
    }


# ---------- produtos ----------

@api.get("/products")
def list_products():
    return jsonify([product_json(p) for p in repo().products.values()])


@api.get("/products/<int:product_id>")
def get_product(product_id: int):
    return jsonify(product_json(repo().get_product(product_id)))


# ---------- carrinho ----------

@api.post("/carts")
def create_cart():
    return jsonify(cart_json(repo().create_cart())), 201


@api.get("/carts/<int:cart_id>")
def get_cart(cart_id: int):
    return jsonify(cart_json(repo().get_cart(cart_id)))


@api.post("/carts/<int:cart_id>/items")
def add_item(cart_id: int):
    data = body()
    cart = repo().get_cart(cart_id)
    quantity = data.get("quantity", 1)
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1:
        raise BadRequest("quantity deve ser um inteiro >= 1")
    product = repo().get_product(data.get("product_id"))
    cart.add_item(product, quantity)
    return jsonify(cart_json(cart))


@api.post("/carts/<int:cart_id>/checkout")
def checkout(cart_id: int):
    data = body()
    cart = repo().get_cart(cart_id)
    order = checkout_service.checkout(
        repo(),
        cart,
        card_number=data.get("card_number"),
        installments=data.get("installments", 1),
        coupon_code=data.get("coupon"),
    )
    return jsonify(order_json(order)), 201


# ---------- pedidos e pagamentos ----------

@api.get("/orders/<int:order_id>")
def get_order(order_id: int):
    return jsonify(order_json(repo().get_order(order_id)))


@api.get("/payments/<int:payment_id>")
def get_payment(payment_id: int):
    return jsonify(payment_json(repo().get_payment(payment_id)))


@api.post("/payments/<int:payment_id>/refund")
def refund(payment_id: int):
    data = request.get_json(silent=True) or {}
    payment = repo().get_payment(payment_id)
    amount = parse_money(data["amount"]) if data.get("amount") is not None else None
    refunded = checkout_service.refund_payment(repo(), payment, amount)
    return jsonify({"refunded": money(refunded), "payment": payment_json(payment)})


# ---------- erros ----------

ERROR_STATUS = {
    BadRequest: 400,
    EmptyCart: 400,
    InvalidCoupon: 400,
    InvalidPayment: 400,
    PaymentDeclined: 402,
    NotFound: 404,
    OutOfStock: 409,
    RefundNotAllowed: 409,
}


def register_error_handlers(app: Flask) -> None:
    for exc_type, status in ERROR_STATUS.items():
        app.register_error_handler(
            exc_type, lambda e, status=status: (jsonify({"error": str(e)}), status)
        )
