"""add group attendance facts and per-student fee settlements

Revision ID: d4e1b3c7a920
Revises: c2a8f6d9b71e
"""
from alembic import op
import sqlalchemy as sa

revision = "d4e1b3c7a920"
down_revision = "c2a8f6d9b71e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("fee_payments", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("fee_id", sa.Uuid(), sa.ForeignKey("fees.id", ondelete="CASCADE"), nullable=False), sa.Column("student_id", sa.Uuid(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False), sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"), sa.Column("paid_on", sa.Date()), sa.Column("amount_paid", sa.Numeric(12, 2), nullable=False, server_default="0"), sa.UniqueConstraint("fee_id", "student_id"))
    op.create_index("ix_fee_payments_fee_id", "fee_payments", ["fee_id"]); op.create_index("ix_fee_payments_student_id", "fee_payments", ["student_id"])
    op.create_table("group_attendance_sessions", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False), sa.Column("group_id", sa.Uuid(), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False), sa.Column("session_date", sa.Date(), nullable=False), sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False), sa.UniqueConstraint("organization_id", "group_id", "session_date"))
    op.create_index("ix_group_attendance_sessions_organization_id", "group_attendance_sessions", ["organization_id"]); op.create_index("ix_group_attendance_sessions_group_id", "group_attendance_sessions", ["group_id"]); op.create_index("ix_group_attendance_sessions_session_date", "group_attendance_sessions", ["session_date"])
    op.create_table("group_attendance_records", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("session_id", sa.Uuid(), sa.ForeignKey("group_attendance_sessions.id", ondelete="CASCADE"), nullable=False), sa.Column("student_id", sa.Uuid(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("notes", sa.Text()), sa.UniqueConstraint("session_id", "student_id"))
    op.create_index("ix_group_attendance_records_session_id", "group_attendance_records", ["session_id"]); op.create_index("ix_group_attendance_records_student_id", "group_attendance_records", ["student_id"])


def downgrade() -> None:
    op.drop_table("group_attendance_records"); op.drop_table("group_attendance_sessions"); op.drop_table("fee_payments")
