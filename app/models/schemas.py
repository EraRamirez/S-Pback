from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.models.common import PyObjectId

MovementType = Literal["sale", "purchase", "adjustment"]
MovementSource = Literal["voice", "manual"]


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
    cost_price: float = Field(ge=0)
    sale_price: float = Field(ge=0)
    stock: int = Field(ge=0, default=0)
    min_stock_alert: int = Field(ge=0, default=0)


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    cost_price: Optional[float] = Field(default=None, ge=0)
    sale_price: Optional[float] = Field(default=None, ge=0)
    stock: Optional[int] = Field(default=None, ge=0)
    min_stock_alert: Optional[int] = Field(default=None, ge=0)


class ProductOut(BaseModel):
    id: PyObjectId = Field(alias="_id")
    business_id: PyObjectId
    name: str
    unit: str
    cost_price: float
    sale_price: float
    stock: int
    min_stock_alert: int
    is_active: bool

    model_config = {"populate_by_name": True}


class RegisterSaleRequest(BaseModel):
    product_id: str
    quantity: int = Field(gt=0)
    created_by_voice: bool = False


class RegisterPurchaseRequest(BaseModel):
    product_id: str
    quantity: int = Field(gt=0)
    unit_cost: Optional[float] = Field(default=None, ge=0)
    created_by_voice: bool = False


class AdjustStockRequest(BaseModel):
    product_id: str
    delta_quantity: int
    reason: str
    created_by_voice: bool = False


class MovementOut(BaseModel):
    id: PyObjectId = Field(alias="_id")
    product_id: PyObjectId
    type: MovementType
    quantity: int
    new_stock: int
    total_amount: Optional[float] = None
    profit_estimated: Optional[float] = None

    model_config = {"populate_by_name": True}


class LowStockProduct(BaseModel):
    id: str
    nombre: str
    cantidad: int


class SummaryOut(BaseModel):
    stockTotal: int
    gananciaHoy: float
    gananciaSemana: float
    productosBajoInventario: list[LowStockProduct]
