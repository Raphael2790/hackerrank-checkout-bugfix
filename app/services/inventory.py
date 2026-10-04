from typing import Iterable

from app.models import CartItem
from app.repository import Repository


class OutOfStock(Exception):
    pass


def reserve(repo: Repository, items: Iterable[CartItem]) -> None:
    """Baixa o estoque de todos os itens, ou de nenhum se algum não tiver saldo."""
    items = list(items)
    for item in items:
        product = repo.get_product(item.product_id)
        if product.stock < item.quantity:
            raise OutOfStock(
                f"Estoque insuficiente para {product.name}: "
                f"disponível {product.stock}, solicitado {item.quantity}"
            )
    for item in items:
        repo.get_product(item.product_id).stock -= item.quantity


def release(repo: Repository, items: Iterable[CartItem]) -> None:
    for item in items:
        repo.get_product(item.product_id).stock += item.quantity
