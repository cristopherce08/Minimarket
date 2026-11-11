import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text, func

from .config import settings
from .database import engine, get_db, Base
from .models import Product, Sale, SaleItem
from .schemas import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    SaleCreate,
    SaleResponse,
    SaleItemResponse,
    InventorySummaryResponse,
    InventoryItemSimple,
    HealthResponse,
    ReadyResponse,
)
from .sales_service import process_sale_transaction
from .metrics import PrometheusMiddleware, metrics_endpoint

# Configuración de Logging Estructurado
logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "service": "ventas-api", "message": "%(message)s"}',
)
logger = logging.getLogger("ventas-api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Esquema de base de datos verificado exitosamente.")
    except Exception as e:
        logger.error(f"Advertencia al conectar con la base de datos en inicio: {e}")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Microservicio transaccional de ventas, catálogo e inventario para MiniMarket Cloud.",
    lifespan=lifespan,
)
app.add_middleware(PrometheusMiddleware)


# -------------------------------------------------------------
# Endpoints de Diagnóstico y Telemetría
# -------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["Diagnóstico"])
def health_check():
    """Liveness probe para Kubernetes."""
    return HealthResponse(
        status="healthy",
        service="ventas-api",
        timestamp=datetime.now(timezone.utc),
    )


@app.get("/ready", response_model=ReadyResponse, tags=["Diagnóstico"])
def readiness_check(db: Session = Depends(get_db)):
    """Readiness probe para Kubernetes: valida conexión activa con PostgreSQL."""
    start = time.time()
    try:
        db.execute(text("SELECT 1"))
        latency = (time.time() - start) * 1000
        return ReadyResponse(
            status="ready",
            database="connected",
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        logger.error(f"Fallo en readiness probe de base de datos: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Fallo de conexión a base de datos: {str(e)}",
        )


@app.get("/metrics", tags=["Diagnóstico"])
def metrics():
    """Exposición de métricas Prometheus en formato OpenMetrics."""
    return metrics_endpoint()


# -------------------------------------------------------------
# Módulo de Productos
# -------------------------------------------------------------

@app.get("/api/v1/productos", response_model=List[ProductResponse], tags=["Productos"])
def list_products(
    buscar: Optional[str] = Query(None, description="Término para filtrar por nombre"),
    solo_bajo_stock: bool = Query(False, description="Filtrar únicamente productos con bajo stock"),
    db: Session = Depends(get_db),
):
    """Lista todos los productos del catálogo con indicadores de stock bajo."""
    query = db.query(Product)
    if buscar and buscar.strip():
        query = query.filter(Product.name.ilike(f"%{buscar.strip()}%"))

    if solo_bajo_stock:
        query = query.filter(Product.stock <= settings.LOW_STOCK_THRESHOLD)

    products = query.order_by(Product.name.asc()).all()

    result = []
    for p in products:
        p_dict = {
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "stock": p.stock,
            "is_low_stock": p.stock <= settings.LOW_STOCK_THRESHOLD,
            "created_at": p.created_at,
        }
        result.append(ProductResponse(**p_dict))
    return result


@app.post("/api/v1/productos", response_model=ProductResponse, status_code=status.HTTP_201_CREATED, tags=["Productos"])
def create_product(product_in: ProductCreate, db: Session = Depends(get_db)):
    """Registra un nuevo producto en el catálogo con validaciones estrictas."""
    existing = db.query(Product).filter(Product.name.ilike(product_in.name)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un producto registrado con el nombre '{product_in.name}'.",
        )

    product = Product(
        name=product_in.name,
        price=product_in.price,
        stock=product_in.stock,
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    return ProductResponse(
        id=product.id,
        name=product.name,
        price=product.price,
        stock=product.stock,
        is_low_stock=product.stock <= settings.LOW_STOCK_THRESHOLD,
        created_at=product.created_at,
    )


@app.get("/api/v1/productos/{id}", response_model=ProductResponse, tags=["Productos"])
def get_product(id: int, db: Session = Depends(get_db)):
    """Consulta el detalle, precio y stock de un producto por su ID."""
    if id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de producto inválido.")

    product = db.query(Product).filter(Product.id == id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Producto con ID {id} no encontrado.",
        )

    return ProductResponse(
        id=product.id,
        name=product.name,
        price=product.price,
        stock=product.stock,
        is_low_stock=product.stock <= settings.LOW_STOCK_THRESHOLD,
        created_at=product.created_at,
    )


@app.put("/api/v1/productos/{id}", response_model=ProductResponse, tags=["Productos"])
def update_product(id: int, product_in: ProductUpdate, db: Session = Depends(get_db)):
    """Edita nombre, precio o stock de un producto existente."""
    if id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de producto inválido.")

    product = db.query(Product).filter(Product.id == id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Producto con ID {id} no encontrado.",
        )

    if product_in.name is not None:
        name_clean = product_in.name.strip()
        dup = db.query(Product).filter(Product.name.ilike(name_clean), Product.id != id).first()
        if dup:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Otro producto ya utiliza el nombre '{name_clean}'.",
            )
        product.name = name_clean

    if product_in.price is not None:
        product.price = product_in.price

    if product_in.stock is not None:
        product.stock = product_in.stock

    db.commit()
    db.refresh(product)

    return ProductResponse(
        id=product.id,
        name=product.name,
        price=product.price,
        stock=product.stock,
        is_low_stock=product.stock <= settings.LOW_STOCK_THRESHOLD,
        created_at=product.created_at,
    )


@app.get("/api/v1/productos/alertas/bajo-stock", response_model=List[ProductResponse], tags=["Productos"])
def get_low_stock_products(
    threshold: Optional[int] = Query(None, description="Umbral de stock bajo (por defecto 5)"),
    db: Session = Depends(get_db),
):
    """Retorna los productos con inventario igual o inferior al umbral configurado."""
    limit_val = threshold if threshold is not None and threshold >= 0 else settings.LOW_STOCK_THRESHOLD
    products = db.query(Product).filter(Product.stock <= limit_val).order_by(Product.stock.asc()).all()

    return [
        ProductResponse(
            id=p.id,
            name=p.name,
            price=p.price,
            stock=p.stock,
            is_low_stock=True,
            created_at=p.created_at,
        )
        for p in products
    ]


# -------------------------------------------------------------
# Módulo de Ventas
# -------------------------------------------------------------

@app.post("/api/v1/ventas", response_model=SaleResponse, status_code=status.HTTP_201_CREATED, tags=["Ventas"])
def create_sale(sale_in: SaleCreate, db: Session = Depends(get_db)):
    """
    Registra una venta con múltiples productos de forma atómica en PostgreSQL.
    Aplica bloqueo de fila, valida stock, descuenta inventario y congela el precio histórico.
    Si cualquier ítem no tiene stock suficiente, revierte toda la operación (ROLLBACK).
    """
    sale = process_sale_transaction(db, sale_in)

    # Construir respuesta
    items_response = []
    for item in sale.items:
        items_response.append(
            SaleItemResponse(
                id=item.id,
                product_id=item.product_id,
                product_name=item.product.name if item.product else f"Producto #{item.product_id}",
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
            )
        )

    return SaleResponse(
        id=sale.id,
        total=sale.total,
        created_at=sale.created_at,
        items=items_response,
    )


@app.get("/api/v1/ventas", response_model=List[SaleResponse], tags=["Ventas"])
def list_sales(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Lista las ventas registradas con orden cronológico descendente."""
    sales = db.query(Sale).order_by(Sale.created_at.desc()).offset(offset).limit(limit).all()

    result = []
    for s in sales:
        items_resp = [
            SaleItemResponse(
                id=item.id,
                product_id=item.product_id,
                product_name=item.product.name if item.product else f"Producto #{item.product_id}",
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
            )
            for item in s.items
        ]
        result.append(SaleResponse(id=s.id, total=s.total, created_at=s.created_at, items=items_resp))
    return result


@app.get("/api/v1/ventas/{id}", response_model=SaleResponse, tags=["Ventas"])
def get_sale(id: int, db: Session = Depends(get_db)):
    """Obtiene el detalle completo de una venta por ID."""
    if id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de venta inválido.")

    sale = db.query(Sale).filter(Sale.id == id).first()
    if not sale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Venta con ID {id} no encontrada.")

    items_resp = [
        SaleItemResponse(
            id=item.id,
            product_id=item.product_id,
            product_name=item.product.name if item.product else f"Producto #{item.product_id}",
            quantity=item.quantity,
            unit_price=item.unit_price,
            subtotal=item.subtotal,
        )
        for item in sale.items
    ]
    return SaleResponse(id=sale.id, total=sale.total, created_at=sale.created_at, items=items_resp)


# -------------------------------------------------------------
# Módulo de Inventario
# -------------------------------------------------------------

@app.get("/api/v1/inventario/resumen", response_model=InventorySummaryResponse, tags=["Inventario"])
def get_inventory_summary(db: Session = Depends(get_db)):
    """
    Consulta directamente el estado persistido en PostgreSQL sin depender del frontend.
    Identifica existencias totales, productos agotados y con stock bajo.
    """
    total_products = db.query(Product).count()
    total_stock = db.query(func.coalesce(func.sum(Product.stock), 0)).scalar()

    # Productos agotados (stock == 0)
    out_of_stock = db.query(Product).filter(Product.stock == 0).order_by(Product.name.asc()).all()

    # Productos con bajo stock (0 < stock <= threshold)
    low_stock = (
        db.query(Product)
        .filter(Product.stock > 0, Product.stock <= settings.LOW_STOCK_THRESHOLD)
        .order_by(Product.stock.asc())
        .all()
    )

    return InventorySummaryResponse(
        total_productos=total_products,
        total_unidades_en_stock=int(total_stock),
        productos_agotados=len(out_of_stock),
        productos_stock_bajo=len(low_stock),
        items_agotados=[InventoryItemSimple(id=p.id, name=p.name, stock=p.stock, price=p.price) for p in out_of_stock],
        items_stock_bajo=[InventoryItemSimple(id=p.id, name=p.name, stock=p.stock, price=p.price) for p in low_stock],
    )
