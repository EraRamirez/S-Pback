from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.db.mongo import get_db
from app.deps import get_current_business_id
from app.models.schemas import (
    RawMaterialCreate,
    RawMaterialMovementOut,
    RawMaterialOut,
    RawMaterialPurchaseRequest,
    RawMaterialUpdate,
    RawMaterialUsageRequest,
)
from app.services import raw_materials as raw_materials_service

router = APIRouter(prefix="/raw-materials", tags=["raw-materials"])


@router.get("", response_model=list[RawMaterialOut])
async def list_raw_materials(
    business_id: str = Depends(get_current_business_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    cursor = db.raw_materials.find({"business_id": ObjectId(business_id), "is_active": True})
    return [doc async for doc in cursor]


@router.post("", response_model=RawMaterialOut, status_code=201)
async def create_raw_material(
    body: RawMaterialCreate,
    business_id: str = Depends(get_current_business_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    material = {
        "business_id": ObjectId(business_id),
        "name": body.name,
        "unit": body.unit,
        "stock": body.stock,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.raw_materials.insert_one(material)
    material["_id"] = result.inserted_id
    return material


@router.put("/{raw_material_id}", response_model=RawMaterialOut)
async def update_raw_material(
    raw_material_id: str,
    body: RawMaterialUpdate,
    business_id: str = Depends(get_current_business_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    updates["updated_at"] = datetime.now(timezone.utc)

    result = await db.raw_materials.find_one_and_update(
        {"_id": ObjectId(raw_material_id), "business_id": ObjectId(business_id)},
        {"$set": updates},
        return_document=ReturnDocument.AFTER,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Materia prima no encontrada")
    return result


@router.delete("/{raw_material_id}", status_code=204)
async def delete_raw_material(
    raw_material_id: str,
    business_id: str = Depends(get_current_business_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    await db.raw_materials.update_one(
        {"_id": ObjectId(raw_material_id), "business_id": ObjectId(business_id)},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}},
    )
    return Response(status_code=204)


@router.post("/{raw_material_id}/purchases", response_model=RawMaterialMovementOut, status_code=201)
async def register_purchase(
    raw_material_id: str,
    body: RawMaterialPurchaseRequest,
    business_id: str = Depends(get_current_business_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    try:
        return await raw_materials_service.register_purchase(
            db, business_id, raw_material_id, body.quantity, body.unit_cost
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{raw_material_id}/usage", response_model=RawMaterialMovementOut, status_code=201)
async def register_usage(
    raw_material_id: str,
    body: RawMaterialUsageRequest,
    business_id: str = Depends(get_current_business_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    try:
        return await raw_materials_service.register_usage(db, business_id, raw_material_id, body.quantity)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
