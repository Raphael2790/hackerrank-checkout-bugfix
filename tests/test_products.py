def test_list_products(client):
    resp = client.get("/products")

    assert resp.status_code == 200
    products = resp.get_json()
    assert len(products) == 5
    assert products[0] == {
        "id": 1,
        "name": "Teclado Mecânico",
        "price": "100.00",
        "stock": 10,
    }


def test_get_product(client):
    resp = client.get("/products/2")

    assert resp.status_code == 200
    assert resp.get_json()["price"] == "59.90"


def test_get_unknown_product_returns_404(client):
    resp = client.get("/products/999")

    assert resp.status_code == 404
    assert "error" in resp.get_json()
