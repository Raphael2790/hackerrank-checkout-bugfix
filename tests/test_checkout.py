from conftest import APPROVED_CARD, DECLINED_CARD


def do_checkout(client, cart_id, **payload):
    payload.setdefault("card_number", APPROVED_CARD)
    return client.post(f"/carts/{cart_id}/checkout", json=payload)


def test_checkout_creates_order_and_payment(client, make_cart):
    cart_id = make_cart((1, 1))

    resp = do_checkout(client, cart_id, installments=2)

    assert resp.status_code == 201
    order = resp.get_json()
    assert order["subtotal"] == "100.00"
    assert order["shipping"] == "25.00"
    assert order["total"] == "125.00"

    payment = client.get(f"/payments/{order['payment_id']}").get_json()
    assert payment["status"] == "CAPTURED"
    assert payment["amount"] == "125.00"
    assert payment["installments"] == ["62.50", "62.50"]
    assert payment["card_last4"] == "1111"


def test_checkout_decreases_stock(client, make_cart, stock):
    cart_id = make_cart((2, 3))

    do_checkout(client, cart_id)

    assert stock(2) == 17


def test_checkout_empties_cart(client, make_cart):
    cart_id = make_cart((2, 1))

    do_checkout(client, cart_id)

    assert client.get(f"/carts/{cart_id}").get_json()["items"] == []


def test_checkout_with_coupon(client, make_cart):
    cart_id = make_cart((4, 1), (5, 1))  # 249.90 + 50.00

    order = do_checkout(client, cart_id, coupon="MENOS50").get_json()

    assert order["subtotal"] == "299.90"
    assert order["discount"] == "50.00"
    assert order["shipping"] == "0.00"
    assert order["total"] == "249.90"
    assert order["coupon"] == "MENOS50"


def test_checkout_empty_cart_returns_400(client):
    cart_id = client.post("/carts").get_json()["id"]

    assert do_checkout(client, cart_id).status_code == 400


def test_checkout_out_of_stock_returns_409(client, make_cart, stock):
    cart_id = make_cart((2, 1), (4, 4))  # Headset tem 3 em estoque

    resp = do_checkout(client, cart_id)

    assert resp.status_code == 409
    assert stock(2) == 20
    assert stock(4) == 3


def test_declined_card_returns_402_and_keeps_stock(client, make_cart, stock):
    cart_id = make_cart((1, 2))

    resp = do_checkout(client, cart_id, card_number=DECLINED_CARD)

    assert resp.status_code == 402
    assert stock(1) == 10


def test_invalid_card_returns_400(client, make_cart):
    cart_id = make_cart((1, 1))

    assert do_checkout(client, cart_id, card_number="1234").status_code == 400


def test_partial_refund(client, make_cart, stock):
    cart_id = make_cart((1, 1))
    order = do_checkout(client, cart_id).get_json()

    resp = client.post(f"/payments/{order['payment_id']}/refund", json={"amount": "25.00"})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["refunded"] == "25.00"
    assert data["payment"]["status"] == "PARTIALLY_REFUNDED"
    assert data["payment"]["refunded_amount"] == "25.00"
    assert stock(1) == 9


def test_full_refund_changes_status(client, make_cart):
    cart_id = make_cart((1, 1))
    order = do_checkout(client, cart_id).get_json()

    resp = client.post(f"/payments/{order['payment_id']}/refund")

    assert resp.status_code == 200
    assert resp.get_json()["refunded"] == "125.00"
    assert resp.get_json()["payment"]["status"] == "REFUNDED"


def test_refund_above_available_returns_409(client, make_cart):
    cart_id = make_cart((1, 1))
    order = do_checkout(client, cart_id).get_json()

    resp = client.post(f"/payments/{order['payment_id']}/refund", json={"amount": "200.00"})

    assert resp.status_code == 409
