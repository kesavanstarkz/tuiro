"""add organization receipt counters table

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
"""
from alembic import op
import sqlalchemy as sa

revision = "c5d6e7f8a9b0"
down_revision = "b4c5d6e7f8a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "organization_receipt_counters" not in insp.get_table_names():
        op.create_table(
            "organization_receipt_counters",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("organization_id", sa.Uuid(), nullable=False),
            sa.Column("year", sa.Integer(), nullable=False),
            sa.Column("last_number", sa.Integer(), nullable=False, default=0),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("organization_id", "year", name="uq_org_receipt_counter_year"),
        )
        op.create_index(
            op.f("ix_organization_receipt_counters_organization_id"),
            "organization_receipt_counters",
            ["organization_id"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "organization_receipt_counters" in insp.get_table_names():
        op.drop_index(op.f("ix_organization_receipt_counters_organization_id"), table_name="organization_receipt_counters")
        op.drop_table("organization_receipt_counters")
