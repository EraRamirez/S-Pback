from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


async def _get_owned_material(db: AsyncIOMotorDatabase, business_id: str, raw_material_id: str) -> dict:
    material = await db.raw_materials.find_one(
        {"_id": ObjectId(raw_material_id), "business_id": ObjectId(business_id), "is_active": True}
    )
    if not material:
        raise ValueError("Materia prima no encontrada")
    return material


async def register_purchase(
    db: AsyncIOMotorDatabase, business_id: str, raw_material_id: str, quantity: float, unit_cost: float
) -> dict:
    material = await _get_owned_material(db, business_id, raw_material_id)

    new_stock = material["stock"] + quantity
    now = datetime.now(timezone.utc)
    total_cost = unit_cost * quantity

    await db.raw_materials.update_one({"_id": material["_id"]}, {"$set": {"stock": new_stock, "updated_at": now}})

    movement = {
        "business_id": ObjectId(business_id),
        "raw_material_id": material["_id"],
        "type": "compra",
        "quantity": quantity,
        "unit_cost": unit_cost,
        "total_cost": total_cost,
        "created_at": now,
    }
    result = await db.raw_material_movements.insert_one(movement)

    return {
        "movement_id": str(result.inserted_id),
        "raw_material_name": material["name"],
        "quantity": quantity,
        "new_stock": new_stock,
        "total_cost": total_cost,
    }


async def register_usage(
    db: AsyncIOMotorDatabase, business_id: str, raw_material_id: str, quantity: float
) -> dict:
    material = await _get_owned_material(db, business_id, raw_material_id)

    if material["stock"] < quantity:
        raise ValueError("No hay suficiente existencia de esta materia prima")

    new_stock = material["stock"] - quantity
    now = datetime.now(timezone.utc)

    await db.raw_materials.update_one({"_id": material["_id"]}, {"$set": {"stock": new_stock, "updated_at": now}})

    movement = {
        "business_id": ObjectId(business_id),
        "raw_material_id": material["_id"],
        "type": "consumo",
        "quantity": quantity,
        "unit_cost": None,
        "total_cost": None,
        "created_at": now,
    }
    result = await db.raw_material_movements.insert_one(movement)

    return {
        "movement_id": str(result.inserted_id),
        "raw_material_name": material["name"],
        "quantity": quantity,
        "new_stock": new_stock,
        "total_cost": None,
    }
