"""Testes ocultos — simulam a correção automática da plataforma.

NÃO abra este arquivo (nem deixe sua IA abrir) antes de terminar o desafio.
"""
from decimal import Decimal

import pytest

from app.models import CartItem
from app.services.payments import split_installments
from app.services.pricing import price_cart
from conftest import APPROVED_CARD, DECLINED_CARD


def do_checkout(client, cart_id, **payload):
    payload.setdefault("card_number", APPROVED_CARD)
    return client.post(f"/carts/{cart_id}/checkout", json=payload)


# ---------- frete ----------

def test_api_free_shipping_at_threshold(client, make_cart):
    cart_id = make_cart((1, 2))

    order = do_checkout(client, cart_id).get_json()

    assert order["shipping"] == "0.00"
    assert order["total"] == "200.00"


def test_free_shipping_when_discounted_subtotal_hits_threshold(client, make_cart):
    cart_id = make_cart((1, 2), (5, 1))  # 250.00 - 50.00 = 200.00

    order = do_checkout(client, cart_id, coupon="MENOS50").get_json()

    assert order["shipping"] == "0.00"
    assert order["total"] == "200.00"


def test_shipping_charged_one_cent_below_threshold():
    result = price_cart([CartItem(1, Decimal("199.99"), 1)])

    assert result.shipping == Decimal("25.00")
    assert result.total == Decimal("224.99")


# ---------- parcelas ----------

@pytest.mark.parametrize(
    "total, n, expected",
    [
        ("200.00", 3, ["66.68", "66.66", "66.66"]),
        ("0.10", 3, ["0.04", "0.03", "0.03"]),
        ("125.00", 3, ["41.68", "41.66", "41.66"]),
        ("1299.90", 12, ["108.38"] + ["108.32"] * 11),
    ],
)
def test_installments_remainder_goes_to_first(total, n, expected):
    assert split_installments(Decimal(total), n) == [Decimal(v) for v in expected]


def test_installments_always_sum_to_total():
    for cents in range(1, 5000, 7):
        total = Decimal(cents) / 100
        for n in range(1, 13):
            plan = split_installments(total, n)
            assert sum(plan) == total, (total, n, plan)
            assert all(plan[0] >= value for value in plan)


def test_api_installments_match_order_total(client, make_cart):
    cart_id = make_cart((1, 1))  # 125.00 com frete

    order = do_checkout(client, cart_id, installments=3).get_json()
    payment = client.get(f"/payments/{order['payment_id']}").get_json()

    assert payment["installments"] == ["41.68", "41.66", "41.66"]
    assert sum(Decimal(v) for v in payment["installments"]) == Decimal(order["total"])


# ---------- pedidos, estorno e estoque ----------

def test_order_keeps_its_items_after_checkout(client, make_cart):
    cart_id = make_cart((1, 1), (2, 2))

    resp = do_checkout(client, cart_id)
    order = client.get(f"/orders/{resp.get_json()['id']}").get_json()

    assert resp.get_json()["items"] == order["items"]
    assert [(i["product_id"], i["quantity"]) for i in order["items"]] == [(1, 1), (2, 2)]


def test_reusing_cart_does_not_change_previous_order(client, make_cart):
    cart_id = make_cart((1, 1))
    first = do_checkout(client, cart_id).get_json()

    client.post(f"/carts/{cart_id}/items", json={"product_id": 3, "quantity": 1})
    do_checkout(client, cart_id)

    order = client.get(f"/orders/{first['id']}").get_json()
    assert [(i["product_id"], i["quantity"]) for i in order["items"]] == [(1, 1)]


def test_full_refund_restores_stock(client, make_cart, stock):
    cart_id = make_cart((1, 2), (2, 3))
    order = do_checkout(client, cart_id).get_json()
    assert (stock(1), stock(2)) == (8, 17)

    resp = client.post(f"/payments/{order['payment_id']}/refund")

    assert resp.get_json()["payment"]["status"] == "REFUNDED"
    assert (stock(1), stock(2)) == (10, 20)


def test_partial_refunds_adding_up_to_total_restore_stock(client, make_cart, stock):
    cart_id = make_cart((1, 1))  # 125.00
    order = do_checkout(client, cart_id).get_json()
    url = f"/payments/{order['payment_id']}/refund"

    client.post(url, json={"amount": "100.00"})
    assert stock(1) == 9
    resp = client.post(url, json={"amount": "25.00"})

    assert resp.get_json()["payment"]["status"] == "REFUNDED"
    assert stock(1) == 10


def test_partial_refunds_cannot_exceed_total(client, make_cart):
    cart_id = make_cart((1, 1))
    order = do_checkout(client, cart_id).get_json()
    url = f"/payments/{order['payment_id']}/refund"

    assert client.post(url, json={"amount": "100.00"}).status_code == 200
    assert client.post(url, json={"amount": "30.00"}).status_code == 409


def test_refund_after_full_refund_returns_409(client, make_cart, stock):
    cart_id = make_cart((1, 1))
    order = do_checkout(client, cart_id).get_json()
    url = f"/payments/{order['payment_id']}/refund"

    client.post(url)
    resp = client.post(url)

    assert resp.status_code == 409
    assert stock(1) == 10


def test_declined_payment_does_not_create_order(client, make_cart, stock):
    cart_id = make_cart((1, 1))

    assert do_checkout(client, cart_id, card_number=DECLINED_CARD).status_code == 402

    assert client.get(f"/carts/{cart_id}").get_json()["subtotal"] == "100.00"
    assert do_checkout(client, cart_id).status_code == 201
    assert stock(1) == 9
