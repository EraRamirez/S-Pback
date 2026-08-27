import pytest

pytestmark = pytest.mark.asyncio


async def register(client, phone="5512345678", pin="1234"):
    r = await client.post(
        "/auth/register",
        json={"nombre_negocio": "Abarrotes Lupita", "owner_name": "Don Jose", "phone": phone, "pin": pin},
    )
    assert r.status_code == 200, r.text
    return r.json()["token"]


async def create_product(client, token, **overrides):
    body = {"name": "Coca Cola 600ml", "cost_price": 10, "sale_price": 15, "stock": 24, "min_stock_alert": 5}
    body.update(overrides)
    r = await client.post("/products", headers={"Authorization": f"Bearer {token}"}, json=body)
    assert r.status_code == 201, r.text
    return r.json()


async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


async def test_register_and_login(client):
    await register(client)

    r = await client.post(
        "/auth/register",
        json={"nombre_negocio": "Otra", "owner_name": "X", "phone": "5512345678", "pin": "1234"},
    )
    assert r.status_code == 409

    r = await client.post("/auth/login", json={"phone": "5512345678", "pin": "9999"})
    assert r.status_code == 401

    r = await client.post("/auth/login", json={"phone": "5512345678", "pin": "1234"})
    assert r.status_code == 200


async def test_products_require_auth(client):
    r = await client.get("/products")
    assert r.status_code == 401


async def test_product_crud(client):
    token = await register(client)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.get("/products", headers=headers)
    assert r.json() == []

    product = await create_product(client, token)
    product_id = product["_id"]

    r = await client.put(f"/products/{product_id}", headers=headers, json={"stock": 100})
    assert r.status_code == 200
    assert r.json()["stock"] == 100

    r = await client.delete(f"/products/{product_id}", headers=headers)
    assert r.status_code == 204

    r = await client.get("/products", headers=headers)
    assert r.json() == []


async def test_sale_updates_stock_and_rejects_insufficient(client):
    token = await register(client)
    headers = {"Authorization": f"Bearer {token}"}
    product = await create_product(client, token)

    r = await client.post(
        "/movements/sale", headers=headers, json={"product_id": product["_id"], "quantity": 3}
    )
    assert r.status_code == 201
    assert r.json()["new_stock"] == 21
    assert r.json()["profit_estimated"] == 15.0

    r = await client.post(
        "/movements/sale", headers=headers, json={"product_id": product["_id"], "quantity": 999}
    )
    assert r.status_code == 400


async def test_purchase_and_adjustment(client):
    token = await register(client)
    headers = {"Authorization": f"Bearer {token}"}
    product = await create_product(client, token)

    r = await client.post(
        "/movements/purchase",
        headers=headers,
        json={"product_id": product["_id"], "quantity": 10, "unit_cost": 11},
    )
    assert r.status_code == 201
    assert r.json()["new_stock"] == 34

    r = await client.post(
        "/movements/adjustment",
        headers=headers,
        json={"product_id": product["_id"], "delta_quantity": -2, "reason": "merma"},
    )
    assert r.status_code == 201
    assert r.json()["new_stock"] == 32


async def test_summary(client):
    token = await register(client)
    headers = {"Authorization": f"Bearer {token}"}
    product = await create_product(client, token, min_stock_alert=25)

    await client.post("/movements/sale", headers=headers, json={"product_id": product["_id"], "quantity": 3})

    r = await client.get("/summary", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["stockTotal"] == 21
    assert body["gananciaHoy"] == 15.0
    assert body["productosBajoInventario"][0]["nombre"] == "Coca Cola 600ml"
