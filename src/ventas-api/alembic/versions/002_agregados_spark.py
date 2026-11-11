"""Tablas de resultados agregados generados por Spark

Revision ID: 002_agregados_spark
Revises: 001_initial_schema
Create Date: 2026-11-10 18:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002_agregados_spark"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _procesado_en() -> sa.Column:
    return sa.Column(
        "procesado_en",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "agg_ventas_diarias",
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("numero_ventas", sa.BigInteger(), nullable=False),
        sa.Column("total_ingresos", sa.Numeric(16, 2), nullable=False),
        _procesado_en(),
        sa.PrimaryKeyConstraint("fecha"),
    )
    op.create_table(
        "agg_productos_top",
        sa.Column("ranking", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(length=150), nullable=False),
        sa.Column("unidades_vendidas", sa.BigInteger(), nullable=False),
        sa.Column("total_recaudado", sa.Numeric(16, 2), nullable=False),
        _procesado_en(),
        sa.PrimaryKeyConstraint("ranking"),
    )
    op.create_table(
        "agg_resumen_general",
        sa.Column("id", sa.SmallInteger(), nullable=False),
        sa.Column("total_ventas", sa.BigInteger(), nullable=False),
        sa.Column("ingresos_totales", sa.Numeric(16, 2), nullable=False),
        sa.Column("total_productos", sa.Integer(), nullable=False),
        _procesado_en(),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("id = 1", name="chk_agg_resumen_fila_unica"),
    )


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS agg_resumen_general CASCADE;"))
    op.execute(sa.text("DROP TABLE IF EXISTS agg_productos_top CASCADE;"))
    op.execute(sa.text("DROP TABLE IF EXISTS agg_ventas_diarias CASCADE;"))