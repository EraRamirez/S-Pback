from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongo import get_db
from app.deps import get_current_business_id
from app.models.schemas import QuincenaOut, SummaryOut
from app.services.movements import ganancia_desde
from app.services.reports import quincena_breakdown

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

    ganancia_hoy = await ganancia_desde(db, business_id, start_of_day)
    ganancia_semana = await ganancia_desde(db, business_id, start_of_week)
    bajo_inventario = [p for p in products if p["stock"] <= p["min_stock_alert"]]

    return SummaryOut(
        stockTotal=sum(p["stock"] for p in products if p.get("sale_type", "pieza") == "pieza"),
        gananciaHoy=ganancia_hoy,
        gananciaSemana=ganancia_semana,
        productosBajoInventario=[
            {"id": str(p["_id"]), "nombre": p["name"], "cantidad": p["stock"], "unidad": p["unit"]}
            for p in bajo_inventario
        ],
    )


@router.get("/quincena", response_model=QuincenaOut)
async def get_quincena(
    fecha: str | None = Query(default=None, description="YYYY-MM-DD, por defecto hoy"),
    business_id: str = Depends(get_current_business_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    reference = datetime.strptime(fecha, "%Y-%m-%d").replace(tzinfo=timezone.utc) if fecha else datetime.now(timezone.utc)
    return await quincena_breakdown(db, business_id, reference)
