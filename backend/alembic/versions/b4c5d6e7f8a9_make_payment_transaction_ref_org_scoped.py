"""make payment transaction reference unique per organization

Revision ID: b4c5d6e7f8a9
Revises: f2a3b4c5d6e7
"""
from alembic import op
import sqlalchemy as sa

revision = "b4c5d6e7f8a9"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None

convention = {
    "uq": "uq_%(table_name)s_%(column_0_name)s",
}


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    uqs = insp.get_unique_constraints("payments")
    has_org_scoped = any(
        set(u.get("column_names", [])) == {"organization_id", "transaction_reference"}
        for u in uqs
    )
    if has_org_scoped:
        return

    old_uq_name = None
    for u in uqs:
        if u.get("column_names") == ["transaction_reference"]:
            old_uq_name = u.get("name") or "uq_payments_transaction_reference"
            break

    with op.batch_alter_table("payments", naming_convention=convention) as batch_op:
        if old_uq_name:
            batch_op.drop_constraint(old_uq_name, type_="unique")
        batch_op.create_unique_constraint(
            "uq_payments_org_transaction_ref",
            ["organization_id", "transaction_reference"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    uqs = insp.get_unique_constraints("payments")
    has_single_scoped = any(
        u.get("column_names") == ["transaction_reference"]
        for u in uqs
    )
    if has_single_scoped:
        return

    with op.batch_alter_table("payments", naming_convention=convention) as batch_op:
        batch_op.drop_constraint("uq_payments_org_transaction_ref", type_="unique")
        batch_op.create_unique_constraint(
            "uq_payments_transaction_reference",
            ["transaction_reference"],
        )
