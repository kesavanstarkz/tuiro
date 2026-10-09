"""add organization_id to refresh_sessions

Revision ID: d6e7f8a9b0c1
Revises: feafcf8ce39c
Create Date: 2026-09-30 16:30:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'd6e7f8a9b0c1'
down_revision = 'feafcf8ce39c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("refresh_sessions")}
    indexes = {ix["name"] for ix in inspector.get_indexes("refresh_sessions")}
    
    with op.batch_alter_table("refresh_sessions") as batch_op:
        if "organization_id" not in cols:
            batch_op.add_column(sa.Column("organization_id", sa.Uuid(), nullable=True))
            batch_op.create_foreign_key("fk_refresh_sessions_org_id", "organizations", ["organization_id"], ["id"], ondelete="CASCADE")
        if "ix_refresh_sessions_organization_id" not in indexes:
            batch_op.create_index("ix_refresh_sessions_organization_id", ["organization_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("refresh_sessions") as batch_op:
        batch_op.drop_index("ix_refresh_sessions_organization_id")
        batch_op.drop_constraint("fk_refresh_sessions_org_id", type_="foreignkey")
        batch_op.drop_column("organization_id")
