from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from .database import SessionLocal, engine, Base
from .models import Product, Sale, SaleItem

DEMO_PRODUCTS = [
    {"name": "Arroz Costeño 1kg", "price": Decimal("4.50"), "stock": 50},
    {"name": "Azúcar Rubia Paramonga 1kg", "price": Decimal("3.80"), "stock": 40},
    {"name": "Leche Gloria Azul 400g", "price": Decimal("4.20"), "stock": 60},
    {"name": "Inka Kola 500ml", "price": Decimal("3.50"), "stock": 35},
    {"name": "Coca Cola 500ml", "price": Decimal("3.50"), "stock": 30},
    {"name": "Galletas Soda San Jorge 6pk", "price": Decimal("2.50"), "stock": 4},   # Bajo stock
    {"name": "Galletas Margarita 4pk", "price": Decimal("2.20"), "stock": 25},
    {"name": "Aceite Primor Clásico 1L", "price": Decimal("9.20"), "stock": 3},    # Bajo stock
    {"name": "Fideos Don Vittorio Spaghetti 500g", "price": Decimal("3.20"), "stock": 45},
    {"name": "Atún Primor en Trozos 170g", "price": Decimal("5.80"), "stock": 0},  # Agotado
    {"name": "Detergente Bolívar 800g", "price": Decimal("7.90"), "stock": 18},
    {"name": "Jabón Bolívar Limón 200g", "price": Decimal("2.80"), "stock": 22},
]


def seed_database(db: Session) -> dict:
    """
    Carga de datos de demostración de bodega peruana de forma estrictamente idempotente.
    """
    created_products = 0
    existing_products = 0

    for prod_data in DEMO_PRODUCTS:
        existing = db.query(Product).filter(Product.name == prod_data["name"]).first()
        if not existing:
            product = Product(
                name=prod_data["name"],
                price=prod_data["price"],
                stock=prod_data["stock"],
            )
            db.add(product)
            created_products += 1
        else:
            existing_products += 1

    db.commit()

    # Si no hay ventas previas, generar 2 ventas demostrativas para validar reportes iniciales
    sales_created = 0
    if db.query(Sale).count() == 0:
        p_arroz = db.query(Product).filter(Product.name == "Arroz Costeño 1kg").first()
        p_leche = db.query(Product).filter(Product.name == "Leche Gloria Azul 400g").first()
        p_inka = db.query(Product).filter(Product.name == "Inka Kola 500ml").first()

        if p_arroz and p_leche:
            # Venta demo 1
            v1_total = round(p_arroz.price * 2 + p_leche.price * 1, 2)
            sale1 = Sale(total=v1_total, created_at=datetime.now(timezone.utc))
            sale1.items = [
                SaleItem(product_id=p_arroz.id, quantity=2, unit_price=p_arroz.price, subtotal=p_arroz.price * 2),
                SaleItem(product_id=p_leche.id, quantity=1, unit_price=p_leche.price, subtotal=p_leche.price * 1),
            ]
            db.add(sale1)
            sales_created += 1

        if p_inka and p_arroz:
            # Venta demo 2
            v2_total = round(p_inka.price * 3 + p_arroz.price * 1, 2)
            sale2 = Sale(total=v2_total, created_at=datetime.now(timezone.utc))
            sale2.items = [
                SaleItem(product_id=p_inka.id, quantity=3, unit_price=p_inka.price, subtotal=p_inka.price * 3),
                SaleItem(product_id=p_arroz.id, quantity=1, unit_price=p_arroz.price, subtotal=p_arroz.price * 1),
            ]
            db.add(sale2)
            sales_created += 1

        db.commit()

    return {
        "created_products": created_products,
        "existing_products": existing_products,
        "demo_sales_created": sales_created,
    }


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        res = seed_database(session)
        print(f"Seed completado exitosamente: {res}")
    finally:
        session.close()
