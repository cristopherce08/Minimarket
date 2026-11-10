from collections import defaultdict
from decimal import Decimal
from typing import Dict, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import update
from .models import Product, Sale, SaleItem
from .schemas import SaleCreate
from .metrics import SALES_TOTAL, SALES_REVENUE, SALES_FAILED


def process_sale_transaction(db: Session, sale_in: SaleCreate) -> Sale:
    """
    Ejecuta el registro de venta atómica con transacciones ACID y control de concurrencia.
    Aplica SELECT ... FOR UPDATE sobre PostgreSQL en orden ascendente de IDs para evitar deadlocks,
    y actualización condicional atómica (stock = stock - qty WHERE stock >= qty) que garantiza
    cero sobreventa en cualquier motor SQL.
    Si cualquier producto carece de stock, revierte toda la transacción (ROLLBACK).
    """
    if not sale_in.items:
        SALES_FAILED.labels(service="ventas-api", reason="carrito_vacio").inc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La venta debe contener al menos un producto.",
        )

    # 1. Consolidar cantidades por producto
    qty_by_product_id: Dict[int, int] = defaultdict(int)
    for item in sale_in.items:
        if item.quantity <= 0:
            SALES_FAILED.labels(service="ventas-api", reason="cantidad_invalida").inc()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"La cantidad para el producto ID {item.product_id} debe ser mayor a 0.",
            )
        qty_by_product_id[item.product_id] += item.quantity

    sorted_product_ids: List[int] = sorted(qty_by_product_id.keys())

    try:
        # 2. Bloqueo pesimista de filas en orden ascendente (en PostgreSQL)
        query = db.query(Product).filter(Product.id.in_(sorted_product_ids))
        if db.bind and db.bind.dialect.name != "sqlite":
            query = query.with_for_update()

        locked_products = {p.id: p for p in query.all()}

        # 3. Validar existencia de todos los productos solicitados
        for pid in sorted_product_ids:
            if pid not in locked_products:
                db.rollback()
                SALES_FAILED.labels(service="ventas-api", reason="producto_no_encontrado").inc()
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"El producto con ID {pid} no existe en el catálogo.",
                )

        # 4. Validar disponibilidad previa en memoria de sesión
        for pid, requested_qty in qty_by_product_id.items():
            product = locked_products[pid]
            if product.stock < requested_qty:
                db.rollback()
                SALES_FAILED.labels(service="ventas-api", reason="stock_insuficiente").inc()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Stock insuficiente para '{product.name}'. "
                        f"Stock disponible: {product.stock}, solicitado: {requested_qty}."
                    ),
                )

        # 5. Descuento atómico condicional en base de datos para impedir sobreventa concurrente
        for pid, requested_qty in qty_by_product_id.items():
            stmt = (
                update(Product)
                .where(Product.id == pid, Product.stock >= requested_qty)
                .values(stock=Product.stock - requested_qty)
            )
            res = db.execute(stmt)
            if res.rowcount == 0:
                db.rollback()
                SALES_FAILED.labels(service="ventas-api", reason="stock_insuficiente_concurrencia").inc()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Stock insuficiente para '{locked_products[pid].name}'. "
                        f"El stock fue agotado por otra transacción simultánea."
                    ),
                )

        # 6. Crear cabecera y detalle de venta con precio histórico congelado
        total_sale = Decimal("0.00")
        sale = Sale(total=Decimal("0.00"))
        db.add(sale)
        db.flush()  # Obtiene sale.id

        sale_items_to_create = []
        for item in sale_in.items:
            product = locked_products[item.product_id]
            unit_price = Decimal(str(product.price))
            item_subtotal = round(unit_price * Decimal(item.quantity), 2)
            total_sale += item_subtotal

            sale_item = SaleItem(
                sale_id=sale.id,
                product_id=product.id,
                quantity=item.quantity,
                unit_price=unit_price,
                subtotal=item_subtotal,
            )
            sale_items_to_create.append(sale_item)

        sale.total = round(total_sale, 2)
        db.add_all(sale_items_to_create)
        db.commit()
        db.refresh(sale)

        # 7. Registrar métricas de negocio
        SALES_TOTAL.labels(service="ventas-api").inc()
        SALES_REVENUE.labels(service="ventas-api").inc(float(sale.total))

        return sale

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        SALES_FAILED.labels(service="ventas-api", reason="error_interno").inc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error transaccional al procesar la venta: {str(e)}",
        )
