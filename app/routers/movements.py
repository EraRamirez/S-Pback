from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongo import get_db
from app.deps import get_current_business_id
from app.models.schemas import AdjustStockRequest, RegisterPurchaseRequest, RegisterSaleRequest
from app.services import movements as movements_service

router = APIRouter(prefix="/movements", tags=["movements"])


@router.post("/sale", status_code=201)
async def register_sale(
    body: RegisterSaleRequest,
    business_id: str = Depends(get_current_business_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    try:
        return await movements_service.register_sale(
            db, business_id, body.product_id, body.quantity, body.created_by_voice
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/purchase", status_code=201)
async def register_purchase(
    body: RegisterPurchaseRequest,
    business_id: str = Depends(get_current_business_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    try:
        return await movements_service.register_purchase(
            db, business_id, body.product_id, body.quantity, body.unit_cost, body.created_by_voice
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/adjustment", status_code=201)
async def register_adjustment(
    body: AdjustStockRequest,
    business_id: str = Depends(get_current_business_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    try:
        return await movements_service.adjust_stock(
            db, business_id, body.product_id, body.delta_quantity, body.reason, body.created_by_voice
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
