from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.db.mongo import get_db
from app.deps import get_current_business_id
from app.models.schemas import ProductCreate, ProductOut, ProductUpdate
from app.services.normalize import normalize_name

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductOut])
async def list_products(
    business_id: str = Depends(get_current_business_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    cursor = db.products.find({"business_id": ObjectId(business_id), "is_active": True})
    return [doc async for doc in cursor]


@router.post("", response_model=ProductOut, status_code=201)
async def create_product(
    body: ProductCreate,
    business_id: str = Depends(get_current_business_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    product = {
        "business_id": ObjectId(business_id),
        "name": body.name,
        "name_normalized": normalize_name(body.name),
        "sale_type": body.sale_type,
        "unit": body.unit if body.sale_type == "granel" else "pieza",
        "cost_price": body.cost_price,
        "sale_price": body.sale_price,
        "stock": body.stock,
        "min_stock_alert": body.min_stock_alert,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.products.insert_one(product)
    product["_id"] = result.inserted_id
    return product


@router.put("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: str,
    body: ProductUpdate,
    business_id: str = Depends(get_current_business_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if "name" in updates:
        updates["name_normalized"] = normalize_name(updates["name"])
    if updates.get("sale_type") == "pieza":
        updates["unit"] = "pieza"
    updates["updated_at"] = datetime.now(timezone.utc)

    result = await db.products.find_one_and_update(
        {"_id": ObjectId(product_id), "business_id": ObjectId(business_id)},
        {"$set": updates},
        return_document=ReturnDocument.AFTER,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return result


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: str,
    business_id: str = Depends(get_current_business_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    await db.products.update_one(
        {"_id": ObjectId(product_id), "business_id": ObjectId(business_id)},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}},
    )
    return Response(status_code=204)
