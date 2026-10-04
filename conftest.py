import pytest

from app import create_app

APPROVED_CARD = "4111111111111111"
DECLINED_CARD = "4000000000000002"


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def make_cart(client):
    """Cria um carrinho com os itens informados: make_cart((product_id, qty), ...)."""

    def _make(*items):
        cart_id = client.post("/carts").get_json()["id"]
        for product_id, quantity in items:
            resp = client.post(
                f"/carts/{cart_id}/items",
                json={"product_id": product_id, "quantity": quantity},
            )
            assert resp.status_code == 200, resp.get_json()
        return cart_id

    return _make


@pytest.fixture
def stock(client):
    def _stock(product_id):
        return client.get(f"/products/{product_id}").get_json()["stock"]

    return _stock
