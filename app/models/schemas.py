from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from app.models.common import PyObjectId

MovementType = Literal["sale", "purchase", "adjustment"]
MovementSource = Literal["voice", "manual"]
SaleType = Literal["pieza", "granel"]
GranelUnit = Literal["kg", "g"]
RawMaterialMovementType = Literal["compra", "consumo"]


class RegisterRequest(BaseModel):
    nombre_negocio: str
    owner_name: str
    phone: str = Field(min_length=10)
    pin: str = Field(min_length=4, max_length=6)


class LoginRequest(BaseModel):
    phone: str = Field(min_length=10)
    pin: str = Field(min_length=4, max_length=6)


class TokenResponse(BaseModel):
    token: str


class ProductCreate(BaseModel):
    name: str
    sale_type: SaleType = "pieza"
    unit: Optional[GranelUnit] = None
    cost_price: float = Field(ge=0, default=0)
    sale_price: float = Field(ge=0)
    stock: float = Field(ge=0, default=0)
    min_stock_alert: float = Field(ge=0, default=0)

    @model_validator(mode="after")
    def check_unit(self):
        if self.sale_type == "granel" and self.unit is None:
            raise ValueError("unit es requerido para productos a granel (kg o g)")
        return self


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    sale_type: Optional[SaleType] = None
    unit: Optional[GranelUnit] = None
    cost_price: Optional[float] = Field(default=None, ge=0)
    sale_price: Optional[float] = Field(default=None, ge=0)
    stock: Optional[float] = Field(default=None, ge=0)
    min_stock_alert: Optional[float] = Field(default=None, ge=0)


class ProductOut(BaseModel):
    id: PyObjectId = Field(alias="_id")
    business_id: PyObjectId
    name: str
    sale_type: SaleType
    unit: str
    cost_price: float
    sale_price: float
    stock: float
    min_stock_alert: float
    is_active: bool

    model_config = {"populate_by_name": True}


class RegisterSaleRequest(BaseModel):
    product_id: str
    quantity: float = Field(gt=0)
    created_by_voice: bool = False


class RegisterPurchaseRequest(BaseModel):
    product_id: str
    quantity: float = Field(gt=0)
    unit_cost: Optional[float] = Field(default=None, ge=0)
    created_by_voice: bool = False


class AdjustStockRequest(BaseModel):
    product_id: str
    delta_quantity: float
    reason: str
    created_by_voice: bool = False


class MovementOut(BaseModel):
    id: PyObjectId = Field(alias="_id")
    product_id: PyObjectId
    type: MovementType
    quantity: float
    new_stock: float
    total_amount: Optional[float] = None
    profit_estimated: Optional[float] = None

    model_config = {"populate_by_name": True}


class LowStockProduct(BaseModel):
    id: str
    nombre: str
    cantidad: float
    unidad: str


class VentaHoyRow(BaseModel):
    product_id: str
    product_name: str
    unit: str
    cantidad: float
    monto: float


class SummaryOut(BaseModel):
    stockTotal: float
    gananciaHoy: float
    gananciaSemana: float
    productosBajoInventario: list[LowStockProduct]
    ventasHoy: list[VentaHoyRow]


class QuincenaDia(BaseModel):
    fecha: str
    ingresos: float
    egresos: float
    ganancia: float


class QuincenaOut(BaseModel):
    quincenaInicio: str
    quincenaFin: str
    ingresosTotal: float
    egresosTotal: float
    gananciaTotal: float
    dias: list[QuincenaDia]


class RawMaterialCreate(BaseModel):
    name: str
    unit: str = Field(min_length=1)
    stock: float = Field(ge=0, default=0)


class RawMaterialUpdate(BaseModel):
    name: Optional[str] = None
    unit: Optional[str] = Field(default=None, min_length=1)


class RawMaterialOut(BaseModel):
    id: PyObjectId = Field(alias="_id")
    business_id: PyObjectId
    name: str
    unit: str
    stock: float
    is_active: bool

    model_config = {"populate_by_name": True}


class RawMaterialPurchaseRequest(BaseModel):
    quantity: float = Field(gt=0)
    unit_cost: float = Field(ge=0)


class RawMaterialUsageRequest(BaseModel):
    quantity: float = Field(gt=0)


class RawMaterialMovementOut(BaseModel):
    movement_id: str
    raw_material_name: str
    quantity: float
    new_stock: float
    total_cost: Optional[float] = None


Container = Literal["bote", "bolsa"]
PaymentStatus = Literal["pagado", "parcial", "no_pagado"]
DeliveryStatus = Literal["pendiente", "entregado"]


class ReservationItemCreate(BaseModel):
    product_id: str
    quantity: float = Field(gt=0)
    container: Container


class ReservationCreate(BaseModel):
    customer_name: str = Field(min_length=1)
    pickup_date: str
    pickup_time: str
    items: list[ReservationItemCreate] = Field(min_length=1)
    amount_paid: float = Field(ge=0, default=0)


class ReservationItemOut(BaseModel):
    item_id: PyObjectId
    product_id: PyObjectId
    product_name: str
    unit: str
    quantity: float
    unit_price: float
    subtotal: float
    container: Container
    delivered: bool
    delivered_at: Optional[datetime] = None


class ReservationOut(BaseModel):
    id: PyObjectId = Field(alias="_id")
    customer_name: str
    pickup_date: str
    pickup_time: str
    items: list[ReservationItemOut]
    total_amount: float
    amount_paid: float
    payment_status: PaymentStatus
    delivery_status: DeliveryStatus
    created_at: datetime

    model_config = {"populate_by_name": True}


class AddPaymentRequest(BaseModel):
    amount: float = Field(gt=0)


class ReservationDetailsUpdate(BaseModel):
    customer_name: Optional[str] = Field(default=None, min_length=1)
    pickup_date: Optional[str] = None
    pickup_time: Optional[str] = None


class ReservationItemUpdate(BaseModel):
    quantity: Optional[float] = Field(default=None, gt=0)
    container: Optional[Container] = None


class ReservationSummaryRow(BaseModel):
    product_id: str
    product_name: str
    unit: str
    total_reservado: float
    total_entregado: float
    total_pendiente: float


class ReservationSummaryOut(BaseModel):
    productos: list[ReservationSummaryRow]
