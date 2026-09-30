"""align models and migrations

Revision ID: feafcf8ce39c
Revises: c5d6e7f8a9b0
Create Date: 2026-09-30 16:11:06.681559
"""
from alembic import op
import sqlalchemy as sa


revision = 'feafcf8ce39c'
down_revision = 'c5d6e7f8a9b0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    assignment_indexes = {ix["name"] for ix in inspector.get_indexes("assignments")}
    fee_indexes = {ix["name"] for ix in inspector.get_indexes("fees")}

    if "ix_assignments_due_date" not in assignment_indexes:
        op.create_index("ix_assignments_due_date", "assignments", ["due_date"], unique=False)
    if "ix_assignments_overrides_id" not in assignment_indexes:
        op.create_index("ix_assignments_overrides_id", "assignments", ["overrides_id"], unique=False)
    if "ix_fees_org_target" in fee_indexes:
        op.drop_index("ix_fees_org_target", table_name="fees")
    if "ix_fees_due_date" not in fee_indexes:
        op.create_index("ix_fees_due_date", "fees", ["due_date"], unique=False)
    if "ix_fees_overrides_id" not in fee_indexes:
        op.create_index("ix_fees_overrides_id", "fees", ["overrides_id"], unique=False)
    if "ix_group_fees_org_target" not in fee_indexes:
        op.create_index("ix_group_fees_org_target", "fees", ["organization_id", "group_id", "student_id"], unique=False)

    parent_fks = {fk.get("name") for fk in inspector.get_foreign_keys("parents")}
    if "fk_parents_user_id_users" not in parent_fks:
        with op.batch_alter_table("parents") as batch_op:
            batch_op.create_foreign_key("fk_parents_user_id_users", "users", ["user_id"], ["id"])

    student_fks = {fk.get("name") for fk in inspector.get_foreign_keys("students")}
    if "fk_students_user_id_users" not in student_fks:
        with op.batch_alter_table("students") as batch_op:
            batch_op.create_foreign_key("fk_students_user_id_users", "users", ["user_id"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("students") as batch_op:
        batch_op.drop_constraint("fk_students_user_id_users", type_="foreignkey")
    with op.batch_alter_table("parents") as batch_op:
        batch_op.drop_constraint("fk_parents_user_id_users", type_="foreignkey")
    op.drop_index("ix_group_fees_org_target", table_name="fees")
    op.drop_index("ix_fees_overrides_id", table_name="fees")
    op.drop_index("ix_fees_due_date", table_name="fees")
    op.create_index("ix_fees_org_target", "fees", ["organization_id", "group_id", "student_id"], unique=False)
    op.drop_index("ix_assignments_overrides_id", table_name="assignments")
    op.drop_index("ix_assignments_due_date", table_name="assignments")
