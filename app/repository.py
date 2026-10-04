import itertools
from decimal import Decimal

from app.models import Cart, Order, Payment, Product

SEED_PRODUCTS = [
    ("Teclado Mecânico", "100.00", 10),
    ("Mouse Gamer", "59.90", 20),
    ("Monitor 27''", "1299.90", 5),
    ("Headset", "249.90", 3),
    ("Cabo USB-C", "50.00", 50),
]


class NotFound(Exception):
    pass


class Repository:
    """Armazenamento em memória. Uma instância por aplicação."""

    def __init__(self) -> None:
        self.products: dict[int, Product] = {}
        self.carts: dict[int, Cart] = {}
        self.orders: dict[int, Order] = {}
        self.payments: dict[int, Payment] = {}
        self._product_ids = itertools.count(1)
        self._cart_ids = itertools.count(1)
        self._order_ids = itertools.count(1)
        self._payment_ids = itertools.count(1)

    def seed(self) -> None:
        for name, price, stock in SEED_PRODUCTS:
            product_id = next(self._product_ids)
            self.products[product_id] = Product(product_id, name, Decimal(price), stock)

    def next_order_id(self) -> int:
        return next(self._order_ids)

    def next_payment_id(self) -> int:
        return next(self._payment_ids)

    def create_cart(self) -> Cart:
        cart = Cart(id=next(self._cart_ids))
        self.carts[cart.id] = cart
        return cart

    def get_product(self, product_id: int) -> Product:
        return self._get(self.products, product_id, "Produto")

    def get_cart(self, cart_id: int) -> Cart:
        return self._get(self.carts, cart_id, "Carrinho")

    def get_order(self, order_id: int) -> Order:
        return self._get(self.orders, order_id, "Pedido")

    def get_payment(self, payment_id: int) -> Payment:
        return self._get(self.payments, payment_id, "Pagamento")

    @staticmethod
    def _get(store: dict, key: int, label: str):
        try:
            return store[key]
        except KeyError:
            raise NotFound(f"{label} {key} não encontrado") from None
