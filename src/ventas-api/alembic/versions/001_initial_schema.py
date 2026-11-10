"""Esquema inicial de MiniMarket Cloud (products, sales, sale_items)

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-10 05:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Tabla de productos
    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('stock', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('price > 0', name='chk_product_price_positive'),
        sa.CheckConstraint('stock >= 0', name='chk_product_stock_non_negative'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_products_id'), 'products', ['id'], unique=False)
    op.create_index(op.f('ix_products_name'), 'products', ['name'], unique=False)

    # 2. Tabla de ventas
    op.create_table(
        'sales',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('total', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('total >= 0', name='chk_sale_total_non_negative'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_sales_id'), 'sales', ['id'], unique=False)
    op.create_index(op.f('ix_sales_created_at'), 'sales', ['created_at'], unique=False)

    # 3. Tabla de detalle de venta (sale_items)
    op.create_table(
        'sale_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sale_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('subtotal', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.CheckConstraint('quantity > 0', name='chk_sale_item_quantity_positive'),
        sa.CheckConstraint('unit_price > 0', name='chk_sale_item_unit_price_positive'),
        sa.CheckConstraint('subtotal >= 0', name='chk_sale_item_subtotal_non_negative'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.ForeignKeyConstraint(['sale_id'], ['sales.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_sale_items_id'), 'sale_items', ['id'], unique=False)
    op.create_index(op.f('ix_sale_items_product_id'), 'sale_items', ['product_id'], unique=False)
    op.create_index(op.f('ix_sale_items_sale_id'), 'sale_items', ['sale_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_sale_items_sale_id'), table_name='sale_items')
    op.drop_index(op.f('ix_sale_items_product_id'), table_name='sale_items')
    op.drop_index(op.f('ix_sale_items_id'), table_name='sale_items')
    op.drop_table('sale_items')

    op.drop_index(op.f('ix_sales_created_at'), table_name='sales')
    op.drop_index(op.f('ix_sales_id'), table_name='sales')
    op.drop_table('sales')

    op.drop_index(op.f('ix_products_name'), table_name='products')
    op.drop_index(op.f('ix_products_id'), table_name='products')
    op.drop_table('products')
