"""Registra la clave de idempotencia en la misma transacción que la venta."""

from alembic import op
import sqlalchemy as sa


revision = "003_sale_requests"
down_revision = "002_agregados_spark"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sale_requests",
        sa.Column("key", sa.String(128), primary_key=True),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("sale_id", sa.Integer(), sa.ForeignKey("sales.id", ondelete="CASCADE"), unique=True),
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_table("sale_requests")
