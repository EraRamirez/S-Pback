from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongo import get_db
from app.deps import get_current_business_id
from app.models.schemas import SummaryOut
from app.services.movements import ganancia_desde

router = APIRouter(prefix="/summary", tags=["summary"])


@router.get("", response_model=SummaryOut)
async def get_summary(
    business_id: str = Depends(get_current_business_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_week = now - timedelta(days=7)

    products = await db.products.find(
        {"business_id": ObjectId(business_id), "is_active": True}
    ).to_list(length=None)

    stock_total = sum(p["stock"] for p in products)
    ganancia_hoy = await ganancia_desde(db, business_id, start_of_day)
    ganancia_semana = await ganancia_desde(db, business_id, start_of_week)
    bajo_inventario = [p for p in products if p["stock"] <= p["min_stock_alert"]]

    return SummaryOut(
        stockTotal=stock_total,
        gananciaHoy=ganancia_hoy,
        gananciaSemana=ganancia_semana,
        productosBajoInventario=[
            {"id": str(p["_id"]), "nombre": p["name"], "cantidad": p["stock"]} for p in bajo_inventario
        ],
    )
