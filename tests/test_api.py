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
    assert body["productosBajoInventario"][0]["unidad"] == "pieza"
    assert body["ventasHoy"] == [
        {"product_id": product["_id"], "product_name": "Coca Cola 600ml", "unit": "pieza", "cantidad": 3, "monto": 45.0}
    ]


async def test_granel_product_requires_unit(client):
    token = await register(client)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post(
        "/products",
        headers=headers,
        json={"name": "Masa", "sale_type": "granel", "cost_price": 8, "sale_price": 12, "stock": 0},
    )
    assert r.status_code == 422


async def test_granel_product_sale_with_decimal_quantity(client):
    token = await register(client)
    headers = {"Authorization": f"Bearer {token}"}

    product = await create_product(
        client, token, name="Masa", sale_type="granel", unit="kg", cost_price=8, sale_price=12, stock=50
    )
    assert product["unit"] == "kg"
    assert product["sale_type"] == "granel"

    r = await client.post(
        "/movements/sale", headers=headers, json={"product_id": product["_id"], "quantity": 2.5}
    )
    assert r.status_code == 201
    body = r.json()
    assert body["new_stock"] == 47.5
    assert body["profit_estimated"] == 10.0


async def test_raw_materials_purchase_and_usage(client):
    token = await register(client)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post("/raw-materials", headers=headers, json={"name": "Maiz", "unit": "kg", "stock": 0})
    assert r.status_code == 201
    material = r.json()
    assert material["stock"] == 0

    r = await client.post(
        f"/raw-materials/{material['_id']}/purchases",
        headers=headers,
        json={"quantity": 100, "unit_cost": 12},
    )
    assert r.status_code == 201
    assert r.json()["new_stock"] == 100
    assert r.json()["total_cost"] == 1200

    r = await client.post(
        f"/raw-materials/{material['_id']}/usage",
        headers=headers,
        json={"quantity": 30},
    )
    assert r.status_code == 201
    assert r.json()["new_stock"] == 70

    r = await client.post(
        f"/raw-materials/{material['_id']}/usage",
        headers=headers,
        json={"quantity": 999},
    )
    assert r.status_code == 400

    r = await client.get("/raw-materials", headers=headers)
    assert r.status_code == 200
    assert r.json()[0]["stock"] == 70


async def test_quincena_report_breaks_down_by_day(client):
    token = await register(client)
    headers = {"Authorization": f"Bearer {token}"}
    product = await create_product(client, token)

    await client.post("/movements/sale", headers=headers, json={"product_id": product["_id"], "quantity": 2})

    r = await client.post("/raw-materials", headers=headers, json={"name": "Bolsas", "unit": "pieza"})
    material = r.json()
    await client.post(
        f"/raw-materials/{material['_id']}/purchases", headers=headers, json={"quantity": 100, "unit_cost": 0.5}
    )

    r = await client.get("/summary/quincena", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["ingresosTotal"] == 30.0
    assert body["egresosTotal"] == 50.0
    assert body["gananciaTotal"] == -20.0
    assert len(body["dias"]) > 0
    today_entries = [d for d in body["dias"] if d["ingresos"] > 0 or d["egresos"] > 0]
    assert len(today_entries) == 1
    assert today_entries[0]["ingresos"] == 30.0
    assert today_entries[0]["egresos"] == 50.0


async def test_reservation_creation_computes_total_and_status(client):
    token = await register(client)
    headers = {"Authorization": f"Bearer {token}"}
    masa = await create_product(client, token, name="Masa de sal", sale_type="granel", unit="kg", sale_price=15)

    r = await client.post(
        "/reservations",
        headers=headers,
        json={
            "customer_name": "Martha",
            "pickup_date": "2026-11-01",
            "pickup_time": "11:00",
            "items": [{"product_id": masa["_id"], "quantity": 9, "container": "bote"}],
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["total_amount"] == 135.0
    assert body["payment_status"] == "no_pagado"
    assert body["delivery_status"] == "pendiente"
    assert body["items"][0]["delivered"] is False


async def test_reservation_deliver_hands_over_everything_at_once(client):
    token = await register(client)
    headers = {"Authorization": f"Bearer {token}"}
    masa = await create_product(client, token, name="Masa de sal", sale_type="granel", unit="kg", sale_price=15, stock=50)
    hoja = await create_product(client, token, name="Hoja para tamal", sale_type="granel", unit="kg", sale_price=5, stock=10)

    r = await client.post(
        "/reservations",
        headers=headers,
        json={
            "customer_name": "Martha",
            "pickup_date": "2026-11-01",
            "pickup_time": "11:00",
            "items": [
                {"product_id": masa["_id"], "quantity": 9, "container": "bote"},
                {"product_id": hoja["_id"], "quantity": 2, "container": "bolsa"},
            ],
        },
    )
    reservation = r.json()

    r = await client.post(f"/reservations/{reservation['_id']}/deliver", headers=headers)
    assert r.status_code == 200, r.text
    updated = r.json()
    assert updated["delivery_status"] == "entregado"
    assert all(item["delivered"] for item in updated["items"])

    r = await client.get("/products", headers=headers)
    products_by_name = {p["name"]: p for p in r.json()}
    assert products_by_name["Hoja para tamal"]["stock"] == 8
    assert products_by_name["Masa de sal"]["stock"] == 41

    r = await client.post(f"/reservations/{reservation['_id']}/deliver", headers=headers)
    assert r.status_code == 400  # ya se entrego todo

    r = await client.get("/reservations/summary", headers=headers)
    rows = {row["product_name"]: row for row in r.json()["productos"]}
    assert rows["Masa de sal"]["total_entregado"] == 9
    assert rows["Hoja para tamal"]["total_pendiente"] == 0


async def test_reservation_payment_status_transitions(client):
    token = await register(client)
    headers = {"Authorization": f"Bearer {token}"}
    masa = await create_product(client, token, name="Masa de sal", sale_type="granel", unit="kg", sale_price=10)

    r = await client.post(
        "/reservations",
        headers=headers,
        json={
            "customer_name": "Juan",
            "pickup_date": "2026-11-02",
            "pickup_time": "10:00",
            "items": [{"product_id": masa["_id"], "quantity": 10, "container": "bote"}],
        },
    )
    reservation_id = r.json()["_id"]

    r = await client.post(f"/reservations/{reservation_id}/payments", headers=headers, json={"amount": 40})
    assert r.json()["payment_status"] == "parcial"

    r = await client.post(f"/reservations/{reservation_id}/payments", headers=headers, json={"amount": 60})
    assert r.json()["payment_status"] == "pagado"


async def test_reservation_search_and_estado_filter(client):
    token = await register(client)
    headers = {"Authorization": f"Bearer {token}"}
    masa = await create_product(client, token, name="Masa de sal", sale_type="granel", unit="kg", sale_price=10)

    await client.post(
        "/reservations",
        headers=headers,
        json={
            "customer_name": "Martha Gomez",
            "pickup_date": "2026-11-01",
            "pickup_time": "11:00",
            "items": [{"product_id": masa["_id"], "quantity": 1, "container": "bote"}],
        },
    )
    await client.post(
        "/reservations",
        headers=headers,
        json={
            "customer_name": "Juan Perez",
            "pickup_date": "2026-11-02",
            "pickup_time": "12:00",
            "items": [{"product_id": masa["_id"], "quantity": 1, "container": "bote"}],
        },
    )

    r = await client.get("/reservations", headers=headers, params={"q": "martha"})
    names = [res["customer_name"] for res in r.json()]
    assert names == ["Martha Gomez"]

    r = await client.get("/reservations", headers=headers, params={"estado": "pendiente"})
    assert len(r.json()) == 2

    r = await client.get("/reservations", headers=headers, params={"estado": "entregado"})
    assert len(r.json()) == 0


async def test_reservation_bolsa_adds_fixed_fee(client):
    token = await register(client)
    headers = {"Authorization": f"Bearer {token}"}
    masa = await create_product(client, token, name="Masa de sal", sale_type="granel", unit="kg", sale_price=15)

    r = await client.post(
        "/reservations",
        headers=headers,
        json={
            "customer_name": "Ana",
            "pickup_date": "2026-11-01",
            "pickup_time": "11:00",
            "items": [{"product_id": masa["_id"], "quantity": 2, "container": "bolsa"}],
        },
    )
    body = r.json()
    assert body["items"][0]["subtotal"] == 32.0  # 2*15 + 2 de bolsa
    assert body["total_amount"] == 32.0


async def test_reservation_crud_add_update_remove_item(client):
    token = await register(client)
    headers = {"Authorization": f"Bearer {token}"}
    masa = await create_product(client, token, name="Masa de sal", sale_type="granel", unit="kg", sale_price=15)
    hoja = await create_product(client, token, name="Hoja para tamal", sale_type="granel", unit="kg", sale_price=5)

    r = await client.post(
        "/reservations",
        headers=headers,
        json={
            "customer_name": "Martha",
            "pickup_date": "2026-11-01",
            "pickup_time": "11:00 am",
            "items": [{"product_id": masa["_id"], "quantity": 9, "container": "bote"}],
        },
    )
    reservation_id = r.json()["_id"]
    assert r.json()["total_amount"] == 135.0

    # se le olvido apartar hoja tambien
    r = await client.post(
        f"/reservations/{reservation_id}/items",
        headers=headers,
        json={"product_id": hoja["_id"], "quantity": 2, "container": "bolsa"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert len(body["items"]) == 2
    assert body["total_amount"] == 147.0  # 135 + (2*5 + 2 bolsa)
    hoja_item = next(i for i in body["items"] if i["product_name"] == "Hoja para tamal")

    # corrige la cantidad de hoja
    r = await client.put(
        f"/reservations/{reservation_id}/items/{hoja_item['item_id']}",
        headers=headers,
        json={"quantity": 3},
    )
    assert r.status_code == 200, r.text
    assert r.json()["total_amount"] == 152.0  # 135 + (3*5 + 2 bolsa)

    # cambia nombre y hora
    r = await client.put(
        f"/reservations/{reservation_id}",
        headers=headers,
        json={"customer_name": "Martha Gomez", "pickup_time": "12:00 pm"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["customer_name"] == "Martha Gomez"
    assert r.json()["pickup_time"] == "12:00 pm"

    # quita la hoja
    r = await client.delete(f"/reservations/{reservation_id}/items/{hoja_item['item_id']}", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["items"]) == 1
    assert body["total_amount"] == 135.0

    # no se puede quitar el ultimo producto
    masa_item = body["items"][0]
    r = await client.delete(f"/reservations/{reservation_id}/items/{masa_item['item_id']}", headers=headers)
    assert r.status_code == 400

    # no se puede modificar un producto ya entregado (se entrega el apartado completo)
    r = await client.post(f"/reservations/{reservation_id}/deliver", headers=headers)
    assert r.status_code == 200
    r = await client.put(
        f"/reservations/{reservation_id}/items/{masa_item['item_id']}",
        headers=headers,
        json={"quantity": 1},
    )
    assert r.status_code == 400
