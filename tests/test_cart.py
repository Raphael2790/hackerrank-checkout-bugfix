def test_create_empty_cart(client):
    resp = client.post("/carts")

    assert resp.status_code == 201
    assert resp.get_json() == {"id": 1, "items": [], "subtotal": "0.00"}


def test_add_item_to_cart(client):
    cart_id = client.post("/carts").get_json()["id"]

    resp = client.post(f"/carts/{cart_id}/items", json={"product_id": 2, "quantity": 3})

    assert resp.status_code == 200
    cart = resp.get_json()
    assert cart["items"] == [
        {"product_id": 2, "unit_price": "59.90", "quantity": 3, "line_total": "179.70"}
    ]
    assert cart["subtotal"] == "179.70"


def test_adding_same_product_merges_quantity(client, make_cart):
    cart_id = make_cart((1, 1), (1, 2))

    cart = client.get(f"/carts/{cart_id}").get_json()

    assert len(cart["items"]) == 1
    assert cart["items"][0]["quantity"] == 3
    assert cart["subtotal"] == "300.00"


def test_add_item_with_invalid_quantity_returns_400(client):
    cart_id = client.post("/carts").get_json()["id"]

    resp = client.post(f"/carts/{cart_id}/items", json={"product_id": 1, "quantity": 0})

    assert resp.status_code == 400


def test_add_unknown_product_returns_404(client):
    cart_id = client.post("/carts").get_json()["id"]

    resp = client.post(f"/carts/{cart_id}/items", json={"product_id": 999, "quantity": 1})

    assert resp.status_code == 404


def test_carts_are_independent(client, make_cart):
    first = make_cart((1, 1))
    second = make_cart()

    assert client.get(f"/carts/{first}").get_json()["subtotal"] == "100.00"
    assert client.get(f"/carts/{second}").get_json()["items"] == []
