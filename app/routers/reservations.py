from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongo import get_db
from app.deps import get_current_business_id
from app.models.schemas import (
    AddPaymentRequest,
    ReservationCreate,
    ReservationDetailsUpdate,
    ReservationItemCreate,
    ReservationItemUpdate,
    ReservationOut,
    ReservationSummaryOut,
)
from app.services import reservations as reservations_service

router = APIRouter(prefix="/reservations", tags=["reservations"])


@router.get("", response_model=list[ReservationOut])
async def list_reservations(
    q: str | None = None,
    estado: Literal["pendiente", "entregado"] | None = None,
    business_id: str = Depends(get_current_business_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    return await reservations_service.list_reservations(db, business_id, q, estado)


@router.post("", response_model=ReservationOut, status_code=201)
async def create_reservation(
    body: ReservationCreate,
    business_id: str = Depends(get_current_business_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    try:
        return await reservations_service.create_reservation(db, business_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/summary", response_model=ReservationSummaryOut)
async def get_summary(
    business_id: str = Depends(get_current_business_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    return await reservations_service.get_summary(db, business_id)


@router.put("/{reservation_id}", response_model=ReservationOut)
async def update_details(
    reservation_id: str,
    body: ReservationDetailsUpdate,
    business_id: str = Depends(get_current_business_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    try:
        return await reservations_service.update_details(
            db, business_id, reservation_id, body.customer_name, body.pickup_date, body.pickup_time
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{reservation_id}/items", response_model=ReservationOut, status_code=201)
async def add_item(
    reservation_id: str,
    body: ReservationItemCreate,
    business_id: str = Depends(get_current_business_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    try:
        return await reservations_service.add_item(
            db, business_id, reservation_id, body.product_id, body.quantity, body.container
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/{reservation_id}/items/{item_id}", response_model=ReservationOut)
async def update_item(
    reservation_id: str,
    item_id: str,
    body: ReservationItemUpdate,
    business_id: str = Depends(get_current_business_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    try:
        return await reservations_service.update_item(
            db, business_id, reservation_id, item_id, body.quantity, body.container
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{reservation_id}/items/{item_id}", response_model=ReservationOut)
async def remove_item(
    reservation_id: str,
    item_id: str,
    business_id: str = Depends(get_current_business_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    try:
        return await reservations_service.remove_item(db, business_id, reservation_id, item_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{reservation_id}/deliver", response_model=ReservationOut)
async def deliver_reservation(
    reservation_id: str,
    business_id: str = Depends(get_current_business_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    try:
        return await reservations_service.deliver_reservation(db, business_id, reservation_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{reservation_id}/payments", response_model=ReservationOut)
async def add_payment(
    reservation_id: str,
    body: AddPaymentRequest,
    business_id: str = Depends(get_current_business_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    try:
        return await reservations_service.add_payment(db, business_id, reservation_id, body.amount)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
