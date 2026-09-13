from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services import movements as movements_service
from app.services.normalize import normalize_name

# Cargo fijo por empaque cuando el cliente no trae su propio bote.
BOLSA_FEE = 2.0


def _compute_subtotal(unit_price: float, quantity: float, container: str) -> float:
    return unit_price * quantity + (BOLSA_FEE if container == "bolsa" else 0)


def _payment_status(total_amount: float, amount_paid: float) -> str:
    if amount_paid <= 0:
        return "no_pagado"
    if amount_paid >= total_amount:
        return "pagado"
    return "parcial"


def _delivery_status(items: list[dict]) -> str:
    return "entregado" if all(item["delivered"] for item in items) else "pendiente"


def _with_status(doc: dict) -> dict:
    doc["payment_status"] = _payment_status(doc["total_amount"], doc["amount_paid"])
    doc["delivery_status"] = _delivery_status(doc["items"])
    return doc


async def _get_owned_product(db: AsyncIOMotorDatabase, business_id: str, product_id: str) -> dict:
    product = await db.products.find_one(
        {"_id": ObjectId(product_id), "business_id": ObjectId(business_id), "is_active": True}
    )
    if not product:
        raise ValueError("Uno de los productos del apartado no existe")
    return product


def _build_item(product: dict, quantity: float, container: str) -> dict:
    unit_price = product["sale_price"]
    return {
        "item_id": ObjectId(),
        "product_id": product["_id"],
        "product_name": product["name"],
        "unit": product["unit"],
        "quantity": quantity,
        "unit_price": unit_price,
        "subtotal": _compute_subtotal(unit_price, quantity, container),
        "container": container,
        "delivered": False,
        "delivered_at": None,
    }


async def create_reservation(db: AsyncIOMotorDatabase, business_id: str, body) -> dict:
    items_out = []
    for item in body.items:
        product = await _get_owned_product(db, business_id, item.product_id)
        items_out.append(_build_item(product, item.quantity, item.container))

    now = datetime.now(timezone.utc)
    doc = {
        "business_id": ObjectId(business_id),
        "customer_name": body.customer_name,
        "customer_name_normalized": normalize_name(body.customer_name),
        "pickup_date": body.pickup_date,
        "pickup_time": body.pickup_time,
        "items": items_out,
        "total_amount": sum(i["subtotal"] for i in items_out),
        "amount_paid": body.amount_paid,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.reservations.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _with_status(doc)


async def list_reservations(
    db: AsyncIOMotorDatabase, business_id: str, q: str | None, estado: str | None
) -> list[dict]:
    query: dict = {"business_id": ObjectId(business_id)}
    if q:
        query["customer_name_normalized"] = {"$regex": normalize_name(q)}

    docs = await db.reservations.find(query).sort("pickup_date", 1).to_list(length=None)
    docs = [_with_status(d) for d in docs]

    if estado:
        docs = [d for d in docs if d["delivery_status"] == estado]

    return docs


async def _get_owned_reservation(db: AsyncIOMotorDatabase, business_id: str, reservation_id: str) -> dict:
    reservation = await db.reservations.find_one(
        {"_id": ObjectId(reservation_id), "business_id": ObjectId(business_id)}
    )
    if not reservation:
        raise ValueError("Apartado no encontrado")
    return reservation


async def _save_items(db: AsyncIOMotorDatabase, reservation_id: ObjectId, items: list[dict]) -> dict:
    now = datetime.now(timezone.utc)
    await db.reservations.update_one(
        {"_id": reservation_id},
        {"$set": {"items": items, "total_amount": sum(i["subtotal"] for i in items), "updated_at": now}},
    )
    updated = await db.reservations.find_one({"_id": reservation_id})
    return _with_status(updated)


async def update_details(
    db: AsyncIOMotorDatabase,
    business_id: str,
    reservation_id: str,
    customer_name: str | None,
    pickup_date: str | None,
    pickup_time: str | None,
) -> dict:
    reservation = await _get_owned_reservation(db, business_id, reservation_id)

    updates: dict = {"updated_at": datetime.now(timezone.utc)}
    if customer_name is not None:
        updates["customer_name"] = customer_name
        updates["customer_name_normalized"] = normalize_name(customer_name)
    if pickup_date is not None:
        updates["pickup_date"] = pickup_date
    if pickup_time is not None:
        updates["pickup_time"] = pickup_time

    await db.reservations.update_one({"_id": reservation["_id"]}, {"$set": updates})
    updated = await db.reservations.find_one({"_id": reservation["_id"]})
    return _with_status(updated)


async def add_item(
    db: AsyncIOMotorDatabase, business_id: str, reservation_id: str, product_id: str, quantity: float, container: str
) -> dict:
    reservation = await _get_owned_reservation(db, business_id, reservation_id)
    product = await _get_owned_product(db, business_id, product_id)

    items = reservation["items"] + [_build_item(product, quantity, container)]
    return await _save_items(db, reservation["_id"], items)


async def update_item(
    db: AsyncIOMotorDatabase,
    business_id: str,
    reservation_id: str,
    item_id: str,
    quantity: float | None,
    container: str | None,
) -> dict:
    reservation = await _get_owned_reservation(db, business_id, reservation_id)
    item = next((i for i in reservation["items"] if i["item_id"] == ObjectId(item_id)), None)
    if not item:
        raise ValueError("Producto del apartado no encontrado")
    if item["delivered"]:
        raise ValueError("Ese producto ya fue entregado, no se puede modificar")

    if quantity is not None:
        item["quantity"] = quantity
    if container is not None:
        item["container"] = container
    item["subtotal"] = _compute_subtotal(item["unit_price"], item["quantity"], item["container"])

    items = [item if i["item_id"] == ObjectId(item_id) else i for i in reservation["items"]]
    return await _save_items(db, reservation["_id"], items)


async def remove_item(db: AsyncIOMotorDatabase, business_id: str, reservation_id: str, item_id: str) -> dict:
    reservation = await _get_owned_reservation(db, business_id, reservation_id)
    item = next((i for i in reservation["items"] if i["item_id"] == ObjectId(item_id)), None)
    if not item:
        raise ValueError("Producto del apartado no encontrado")
    if item["delivered"]:
        raise ValueError("Ese producto ya fue entregado, no se puede quitar")
    if len(reservation["items"]) <= 1:
        raise ValueError("Un apartado debe tener al menos un producto")

    items = [i for i in reservation["items"] if i["item_id"] != ObjectId(item_id)]
    return await _save_items(db, reservation["_id"], items)


async def deliver_reservation(db: AsyncIOMotorDatabase, business_id: str, reservation_id: str) -> dict:
    reservation = await _get_owned_reservation(db, business_id, reservation_id)
    if _delivery_status(reservation["items"]) == "entregado":
        raise ValueError("Este apartado ya fue entregado")

    now = datetime.now(timezone.utc)
    items = []
    for item in reservation["items"]:
        if not item["delivered"]:
            # Entregar registra una venta real: descuenta stock y cuenta en ganancia/quincena,
            # igual que una venta normal desde Productos. Se entrega todo el apartado junto,
            # no producto por producto (si se recoge en partes, se hacen apartados separados).
            await movements_service.register_sale(db, business_id, str(item["product_id"]), item["quantity"], False)
            item = {**item, "delivered": True, "delivered_at": now}
        items.append(item)

    return await _save_items(db, reservation["_id"], items)


async def add_payment(db: AsyncIOMotorDatabase, business_id: str, reservation_id: str, amount: float) -> dict:
    reservation = await _get_owned_reservation(db, business_id, reservation_id)
    now = datetime.now(timezone.utc)
    new_paid = reservation["amount_paid"] + amount

    await db.reservations.update_one(
        {"_id": reservation["_id"]}, {"$set": {"amount_paid": new_paid, "updated_at": now}}
    )
    updated = await db.reservations.find_one({"_id": reservation["_id"]})
    return _with_status(updated)


async def get_summary(db: AsyncIOMotorDatabase, business_id: str) -> dict:
    reservations = await db.reservations.find({"business_id": ObjectId(business_id)}).to_list(length=None)

    by_product: dict[str, dict] = {}
    for reservation in reservations:
        for item in reservation["items"]:
            pid = str(item["product_id"])
            row = by_product.setdefault(
                pid,
                {
                    "product_id": pid,
                    "product_name": item["product_name"],
                    "unit": item["unit"],
                    "total_reservado": 0.0,
                    "total_entregado": 0.0,
                },
            )
            row["total_reservado"] += item["quantity"]
            if item["delivered"]:
                row["total_entregado"] += item["quantity"]

    rows = list(by_product.values())
    for row in rows:
        row["total_pendiente"] = row["total_reservado"] - row["total_entregado"]

    return {"productos": rows}
