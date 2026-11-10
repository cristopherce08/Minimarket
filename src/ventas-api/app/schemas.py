from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


# -------------------------------------------------------------
# Esquemas para Productos
# -------------------------------------------------------------

class ProductBase(BaseModel):
    name: str = Field(..., description="Nombre del producto comercial", min_length=2, max_length=150)
    price: Decimal = Field(..., description="Precio unitario en soles (PEN)", gt=0)
    stock: int = Field(..., description="Cantidad disponible en inventario", ge=0)

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("El nombre del producto no puede estar vacío ni contener solo espacios.")
        return cleaned

    @field_validator("price")
    @classmethod
    def validate_price_precision(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("El precio debe ser un número positivo mayor a 0.")
        return round(v, 2)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    price: Optional[Decimal] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)

    @field_validator("name")
    @classmethod
    def validate_name_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            cleaned = v.strip()
            if not cleaned:
                raise ValueError("El nombre no puede estar vacío.")
            return cleaned
        return v

    @field_validator("price")
    @classmethod
    def validate_price_optional(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None:
            if v <= Decimal("0"):
                raise ValueError("El precio debe ser un número positivo mayor a 0.")
            return round(v, 2)
        return v


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price: Decimal
    stock: int
    is_low_stock: bool = False
    created_at: datetime


# -------------------------------------------------------------
# Esquemas para Ventas
# -------------------------------------------------------------

class SaleItemCreate(BaseModel):
    product_id: int = Field(..., gt=0, description="ID del producto existente")
    quantity: int = Field(..., gt=0, description="Cantidad a comprar (entero mayor a 0)")


class SaleCreate(BaseModel):
    items: List[SaleItemCreate] = Field(..., min_length=1, description="Lista de artículos a vender")


class SaleItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class SaleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    total: Decimal
    created_at: datetime
    items: List[SaleItemResponse]


# -------------------------------------------------------------
# Esquemas para Inventario
# -------------------------------------------------------------

class InventoryItemSimple(BaseModel):
    id: int
    name: str
    stock: int
    price: Decimal


class InventorySummaryResponse(BaseModel):
    total_productos: int
    total_unidades_en_stock: int
    productos_agotados: int
    productos_stock_bajo: int
    items_agotados: List[InventoryItemSimple]
    items_stock_bajo: List[InventoryItemSimple]


# -------------------------------------------------------------
# Esquemas de Diagnóstico y Salud
# -------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: datetime


class ReadyResponse(BaseModel):
    status: str
    database: str
    latency_ms: float
