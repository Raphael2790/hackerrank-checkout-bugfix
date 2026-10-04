from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


@dataclass
class Product:
    id: int
    name: str
    price: Decimal
    stock: int


@dataclass
class CartItem:
    product_id: int
    unit_price: Decimal
    quantity: int

    @property
    def line_total(self) -> Decimal:
        return self.unit_price * self.quantity


@dataclass
class Cart:
    id: int
    items: list[CartItem] = field(default_factory=list)

    def add_item(self, product: Product, quantity: int) -> None:
        for item in self.items:
            if item.product_id == product.id:
                item.quantity += quantity
                return
        self.items.append(CartItem(product.id, product.price, quantity))


class PaymentStatus(str, Enum):
    CAPTURED = "CAPTURED"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"
    REFUNDED = "REFUNDED"


@dataclass
class Payment:
    id: int
    order_id: int
    amount: Decimal
    installments: list[Decimal]
    card_last4: str
    status: PaymentStatus = PaymentStatus.CAPTURED
    refunded_amount: Decimal = Decimal("0.00")

    @property
    def refundable_amount(self) -> Decimal:
        return self.amount - self.refunded_amount


@dataclass
class Order:
    id: int
    cart_id: int
    items: list[CartItem]
    subtotal: Decimal
    discount: Decimal
    shipping: Decimal
    total: Decimal
    coupon: str | None = None
    payment_id: int | None = None
