"""add group-centric CMS entities

Revision ID: c2a8f6d9b71e
Revises: fbdf061b8f8e
"""
from alembic import op
import sqlalchemy as sa

revision = "c2a8f6d9b71e"
down_revision = "fbdf061b8f8e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite cannot add FK/unique constraints with ALTER TABLE.  A unique index
    # provides the same one-account-per-profile guarantee across both SQLite and
    # PostgreSQL, while the application already verifies tenant ownership.
    inspector = sa.inspect(op.get_bind())
    if "user_id" not in {column["name"] for column in inspector.get_columns("students")}:
        op.add_column("students", sa.Column("user_id", sa.Uuid(), nullable=True))
    if "ix_students_user_id" not in {index["name"] for index in inspector.get_indexes("students")}:
        op.create_index("ix_students_user_id", "students", ["user_id"], unique=True)
    if "user_id" not in {column["name"] for column in inspector.get_columns("parents")}:
        op.add_column("parents", sa.Column("user_id", sa.Uuid(), nullable=True))
    if "ix_parents_user_id" not in {index["name"] for index in inspector.get_indexes("parents")}:
        op.create_index("ix_parents_user_id", "parents", ["user_id"], unique=True)
    op.create_table("groups", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(160), nullable=False), sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_groups_organization_id", "groups", ["organization_id"])
    op.create_table("group_members", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False), sa.Column("group_id", sa.Uuid(), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False), sa.Column("student_id", sa.Uuid(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False), sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("removed_at", sa.DateTime(timezone=True)), sa.UniqueConstraint("group_id", "student_id"))
    op.create_index("ix_group_members_organization_id", "group_members", ["organization_id"]); op.create_index("ix_group_members_group_id", "group_members", ["group_id"]); op.create_index("ix_group_members_student_id", "group_members", ["student_id"])
    op.create_table("group_schedules", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False), sa.Column("group_id", sa.Uuid(), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False), sa.Column("day_of_week", sa.Integer(), nullable=False), sa.Column("start_time", sa.String(10), nullable=False), sa.Column("end_time", sa.String(10), nullable=False), sa.Column("subject", sa.String(120)))
    op.create_index("ix_group_schedules_organization_id", "group_schedules", ["organization_id"]); op.create_index("ix_group_schedules_group_id", "group_schedules", ["group_id"])
    for table in ("assignments", "fees"):
        columns = [sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False), sa.Column("group_id", sa.Uuid(), sa.ForeignKey("groups.id", ondelete="CASCADE")), sa.Column("student_id", sa.Uuid(), sa.ForeignKey("students.id", ondelete="CASCADE"))]
        if table == "assignments": columns += [sa.Column("title", sa.String(200), nullable=False), sa.Column("description", sa.Text()), sa.Column("due_date", sa.Date()), sa.Column("type", sa.String(20), nullable=False), sa.Column("attachments", sa.Text(), nullable=False, server_default="[]"), sa.Column("overrides_id", sa.Uuid(), sa.ForeignKey("assignments.id")), sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)]
        else: columns += [sa.Column("amount", sa.Numeric(12, 2), nullable=False), sa.Column("due_date", sa.Date(), nullable=False), sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"), sa.Column("overrides_id", sa.Uuid(), sa.ForeignKey("fees.id")), sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)]
        columns.append(sa.CheckConstraint("(group_id IS NOT NULL AND student_id IS NULL) OR (group_id IS NULL AND student_id IS NOT NULL)", name=f"{table[:-1]}_exactly_one_target"))
        op.create_table(table, *columns); op.create_index(f"ix_{table}_organization_id", table, ["organization_id"]); op.create_index(f"ix_{table}_org_target", table, ["organization_id", "group_id", "student_id"])
    op.create_table("chat_threads", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False), sa.Column("type", sa.String(12), nullable=False), sa.Column("group_id", sa.Uuid(), sa.ForeignKey("groups.id", ondelete="CASCADE"), unique=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.CheckConstraint("(type = 'GROUP' AND group_id IS NOT NULL) OR (type = 'DIRECT' AND group_id IS NULL)", name="valid_thread_target"))
    op.create_index("ix_chat_threads_organization_id", "chat_threads", ["organization_id"])
    op.create_table("chat_participants", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("thread_id", sa.Uuid(), sa.ForeignKey("chat_threads.id", ondelete="CASCADE"), nullable=False), sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.UniqueConstraint("thread_id", "user_id")); op.create_index("ix_chat_participants_thread_id", "chat_participants", ["thread_id"]); op.create_index("ix_chat_participants_user_id", "chat_participants", ["user_id"])
    op.create_table("chat_messages", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("thread_id", sa.Uuid(), sa.ForeignKey("chat_threads.id", ondelete="CASCADE"), nullable=False), sa.Column("sender_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False), sa.Column("text", sa.Text(), nullable=False), sa.Column("attachment", sa.Text()), sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)); op.create_index("ix_chat_messages_thread_id", "chat_messages", ["thread_id"])


def downgrade() -> None:
    for table in ("chat_messages", "chat_participants", "chat_threads", "fees", "assignments", "group_schedules", "group_members", "groups"):
        op.drop_table(table)
    op.drop_index("ix_parents_user_id", table_name="parents"); op.drop_column("parents", "user_id")
    op.drop_index("ix_students_user_id", table_name="students"); op.drop_column("students", "user_id")
