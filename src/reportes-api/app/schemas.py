from datetime import date, datetime
from decimal import Decimal
from typing import List
from pydantic import BaseModel, ConfigDict


class VentasHoyResponse(BaseModel):
    fecha: date
    total_ventas: int
    total_ingresos: Decimal
    ticket_promedio: Decimal


class ProductoTopItem(BaseModel):
    ranking: int
    product_id: int
    product_name: str
    unidades_vendidas: int
    total_recaudado: Decimal


class VentaDiaItem(BaseModel):
    fecha: str
    numero_ventas: int
    total_ingresos: Decimal


class ResumenGeneralResponse(BaseModel):
    total_ventas_historicas: int
    ingresos_totales_historicos: Decimal
    total_productos_activos: int


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: datetime


class ReadyResponse(BaseModel):
    status: str
    database: str
    latency_ms: float
