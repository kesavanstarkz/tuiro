"""sync existing group fees to student fees

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
"""
from uuid import uuid4, UUID
from datetime import date
from alembic import op
import sqlalchemy as sa

revision = "f2a3b4c5d6e7"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    fees = conn.execute(sa.text("""
        SELECT id, organization_id, group_id, student_id, amount, due_date
        FROM fees
    """)).fetchall()

    for fee_id, org_id, group_id, student_id, amount, due_date in fees:
        fee_uuid = UUID(str(fee_id))
        bp = f"GF-{fee_uuid.hex[:24]}"
        student_ids = []
        if student_id:
            student_ids.append(student_id)
        elif group_id:
            members = conn.execute(sa.text("""
                SELECT student_id FROM group_members
                WHERE group_id = :group_id AND removed_at IS NULL
            """), {"group_id": group_id}).fetchall()
            student_ids.extend([m[0] for m in members])

        for sid in student_ids:
            exists = conn.execute(sa.text("""
                SELECT id FROM student_fees
                WHERE organization_id = :org_id AND student_id = :sid AND billing_period = :bp
            """), {"org_id": org_id, "sid": sid, "bp": bp}).first()

            if not exists:
                conn.execute(sa.text("""
                    INSERT INTO student_fees (id, organization_id, student_id, billing_period, amount, discount, fine, amount_due, due_date, status)
                    VALUES (:id, :org_id, :sid, :bp, :amount, 0, 0, :amount, :due_date, 'PENDING')
                """), {
                    "id": str(uuid4()),
                    "org_id": org_id,
                    "sid": sid,
                    "bp": bp,
                    "amount": amount,
                    "due_date": due_date,
                })


def downgrade() -> None:
    pass
