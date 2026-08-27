from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


async def _get_owned_product(db: AsyncIOMotorDatabase, business_id: str, product_id: str) -> dict:
    product = await db.products.find_one(
        {"_id": ObjectId(product_id), "business_id": ObjectId(business_id), "is_active": True}
    )
    if not product:
        raise ValueError("Producto no encontrado")
    return product


# Mongo standalone (no replica set) doesn't support multi-document transactions,
# so stock update + movement insert run sequentially instead of atomically.
async def register_sale(
    db: AsyncIOMotorDatabase, business_id: str, product_id: str, quantity: int, created_by_voice: bool
) -> dict:
    product = await _get_owned_product(db, business_id, product_id)

    if product["stock"] < quantity:
        raise ValueError("No hay suficiente stock")

    unit_sale = product["sale_price"]
    unit_cost = product["cost_price"]
    new_stock = product["stock"] - quantity
    now = datetime.now(timezone.utc)

    await db.products.update_one({"_id": product["_id"]}, {"$set": {"stock": new_stock, "updated_at": now}})

    movement = {
        "business_id": ObjectId(business_id),
        "product_id": product["_id"],
        "type": "sale",
        "quantity": quantity,
        "unit_cost_snapshot": unit_cost,
        "unit_sale_snapshot": unit_sale,
        "total_amount": unit_sale * quantity,
        "source": "voice" if created_by_voice else "manual",
        "created_at": now,
        "updated_at": now,
    }
    result = await db.inventory_movements.insert_one(movement)

    return {
        "movement_id": str(result.inserted_id),
        "product_name": product["name"],
        "quantity": quantity,
        "new_stock": new_stock,
        "profit_estimated": (unit_sale - unit_cost) * quantity,
        "total_sale_amount": unit_sale * quantity,
    }


async def register_purchase(
    db: AsyncIOMotorDatabase,
    business_id: str,
    product_id: str,
    quantity: int,
    unit_cost: float | None,
    created_by_voice: bool,
) -> dict:
    product = await _get_owned_product(db, business_id, product_id)

    unit_cost_used = unit_cost if unit_cost is not None else product["cost_price"]
    new_stock = product["stock"] + quantity
    now = datetime.now(timezone.utc)

    update = {"stock": new_stock, "updated_at": now}
    if unit_cost is not None:
        update["cost_price"] = unit_cost

    await db.products.update_one({"_id": product["_id"]}, {"$set": update})

    movement = {
        "business_id": ObjectId(business_id),
        "product_id": product["_id"],
        "type": "purchase",
        "quantity": quantity,
        "unit_cost_snapshot": unit_cost_used,
        "unit_sale_snapshot": product["sale_price"],
        "total_amount": unit_cost_used * quantity,
        "source": "voice" if created_by_voice else "manual",
        "created_at": now,
        "updated_at": now,
    }
    result = await db.inventory_movements.insert_one(movement)

    return {
        "movement_id": str(result.inserted_id),
        "product_name": product["name"],
        "quantity": quantity,
        "new_stock": new_stock,
        "unit_cost_used": unit_cost_used,
    }


async def adjust_stock(
    db: AsyncIOMotorDatabase,
    business_id: str,
    product_id: str,
    delta_quantity: int,
    reason: str,
    created_by_voice: bool,
) -> dict:
    product = await _get_owned_product(db, business_id, product_id)

    new_stock = product["stock"] + delta_quantity
    if new_stock < 0:
        raise ValueError("El ajuste dejaria el stock en negativo")

    now = datetime.now(timezone.utc)
    await db.products.update_one({"_id": product["_id"]}, {"$set": {"stock": new_stock, "updated_at": now}})

    movement = {
        "business_id": ObjectId(business_id),
        "product_id": product["_id"],
        "type": "adjustment",
        "quantity": delta_quantity,
        "unit_cost_snapshot": product["cost_price"],
        "unit_sale_snapshot": product["sale_price"],
        "total_amount": None,
        "reason": reason,
        "source": "voice" if created_by_voice else "manual",
        "created_at": now,
        "updated_at": now,
    }
    result = await db.inventory_movements.insert_one(movement)

    return {
        "movement_id": str(result.inserted_id),
        "product_name": product["name"],
        "delta_quantity": delta_quantity,
        "new_stock": new_stock,
    }


async def check_stock(db: AsyncIOMotorDatabase, business_id: str, product_id: str) -> dict:
    product = await _get_owned_product(db, business_id, product_id)
    return {
        "product_name": product["name"],
        "stock": product["stock"],
        "min_stock_alert": product["min_stock_alert"],
        "is_low_stock": product["stock"] <= product["min_stock_alert"],
    }


async def ganancia_desde(db: AsyncIOMotorDatabase, business_id: str, since: datetime) -> float:
    pipeline = [
        {
            "$match": {
                "business_id": ObjectId(business_id),
                "type": "sale",
                "created_at": {"$gte": since},
            }
        },
        {
            "$group": {
                "_id": None,
                "total": {
                    "$sum": {
                        "$multiply": [
                            {"$subtract": ["$unit_sale_snapshot", "$unit_cost_snapshot"]},
                            "$quantity",
                        ]
                    }
                },
            }
        },
    ]
    result = await db.inventory_movements.aggregate(pipeline).to_list(length=1)
    return result[0]["total"] if result else 0.0
