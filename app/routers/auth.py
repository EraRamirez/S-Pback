from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.security import create_access_token, hash_pin, verify_pin
from app.db.mongo import get_db
from app.models.schemas import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    existing = await db.businesses.find_one({"phone": body.phone})
    if existing:
        raise HTTPException(status_code=409, detail="Ese telefono ya esta registrado")

    now = datetime.now(timezone.utc)
    business = {
        "name": body.nombre_negocio,
        "owner_name": body.owner_name,
        "phone": body.phone,
        "pin_hash": hash_pin(body.pin),
        "subscription_status": "trial",
        "trial_ends_at": None,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.businesses.insert_one(business)

    token = create_access_token(str(result.inserted_id))
    return TokenResponse(token=token)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    business = await db.businesses.find_one({"phone": body.phone})
    if not business or not verify_pin(body.pin, business["pin_hash"]):
        raise HTTPException(status_code=401, detail="Telefono o PIN incorrecto")

    token = create_access_token(str(business["_id"]))
    return TokenResponse(token=token)
