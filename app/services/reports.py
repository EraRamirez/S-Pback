import calendar
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


def quincena_range(reference: datetime) -> tuple[datetime, datetime]:
    year, month, day = reference.year, reference.month, reference.day
    if day <= 15:
        start = datetime(year, month, 1, tzinfo=timezone.utc)
        end = datetime(year, month, 15, 23, 59, 59, tzinfo=timezone.utc)
    else:
        last_day = calendar.monthrange(year, month)[1]
        start = datetime(year, month, 16, tzinfo=timezone.utc)
        end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)
    return start, end


async def _totals_by_day(
    db: AsyncIOMotorDatabase, collection: str, match_extra: dict, amount_field: str, start: datetime, end: datetime
) -> dict[str, float]:
    pipeline = [
        {"$match": {"created_at": {"$gte": start, "$lte": end}, **match_extra}},
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                "total": {"$sum": amount_field},
            }
        },
    ]
    rows = await db[collection].aggregate(pipeline).to_list(length=None)
    return {row["_id"]: row["total"] for row in rows}


async def quincena_breakdown(db: AsyncIOMotorDatabase, business_id: str, reference: datetime) -> dict:
    start, end = quincena_range(reference)
    business_oid = ObjectId(business_id)

    ingresos_by_day = await _totals_by_day(
        db, "inventory_movements", {"business_id": business_oid, "type": "sale"}, "$total_amount", start, end
    )
    egresos_producto_by_day = await _totals_by_day(
        db, "inventory_movements", {"business_id": business_oid, "type": "purchase"}, "$total_amount", start, end
    )
    egresos_materia_by_day = await _totals_by_day(
        db, "raw_material_movements", {"business_id": business_oid, "type": "compra"}, "$total_cost", start, end
    )

    dias = []
    current = start
    while current <= end:
        key = current.strftime("%Y-%m-%d")
        ingresos = ingresos_by_day.get(key, 0.0)
        egresos = egresos_producto_by_day.get(key, 0.0) + egresos_materia_by_day.get(key, 0.0)
        dias.append({"fecha": key, "ingresos": ingresos, "egresos": egresos, "ganancia": ingresos - egresos})
        current += timedelta(days=1)

    return {
        "quincenaInicio": start.strftime("%Y-%m-%d"),
        "quincenaFin": end.strftime("%Y-%m-%d"),
        "ingresosTotal": sum(d["ingresos"] for d in dias),
        "egresosTotal": sum(d["egresos"] for d in dias),
        "gananciaTotal": sum(d["ganancia"] for d in dias),
        "dias": dias,
    }
