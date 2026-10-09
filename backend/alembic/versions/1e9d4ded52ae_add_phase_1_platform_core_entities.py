"""add_phase_1_platform_core_entities

Revision ID: 1e9d4ded52ae
Revises: ad8addcbf1e7
Create Date: 2026-10-09 11:20:39.920345
"""
from alembic import op
import sqlalchemy as sa


revision = '1e9d4ded52ae'
down_revision = 'ad8addcbf1e7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Organization extensions (org_type, enabled_modules)
    with op.batch_alter_table("organizations", schema=None) as batch_op:
        batch_op.add_column(sa.Column("org_type", sa.String(50), nullable=False, server_default="EDUCATION"))
        batch_op.add_column(
            sa.Column(
                "enabled_modules",
                sa.Text(),
                nullable=False,
                server_default='["home", "people", "groups", "attendance", "requests", "work", "communication", "calendar", "files", "finance", "reports", "settings"]',
            )
        )

    # 2. Notification extensions
    with op.batch_alter_table("notifications", schema=None) as batch_op:
        batch_op.add_column(sa.Column("recipient_user_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("title", sa.String(200), nullable=True))
        batch_op.add_column(sa.Column("deep_link", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("is_read", sa.Boolean(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("read_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("idempotency_key", sa.String(120), nullable=True))
        batch_op.create_index("ix_notifications_recipient_user_id", ["recipient_user_id"])
        batch_op.create_index("ix_notifications_idempotency_key", ["idempotency_key"])
        batch_op.create_foreign_key("fk_notifications_user_id", "users", ["recipient_user_id"], ["id"], ondelete="CASCADE")

    # 3. Create organization_terminologies table
    op.create_table(
        "organization_terminologies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("template", sa.String(50), nullable=False, server_default="EDUCATION"),
        sa.Column("terms", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    with op.batch_alter_table("organization_terminologies", schema=None) as batch_op:
        batch_op.create_index("ix_organization_terminologies_organization_id", ["organization_id"], unique=True)

    # 4. Create organization_roles table
    op.create_table(
        "organization_roles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("permissions", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "name", name="uq_org_role_name"),
    )
    with op.batch_alter_table("organization_roles", schema=None) as batch_op:
        batch_op.create_index("ix_organization_roles_organization_id", ["organization_id"])

    # 5. Create notification_preferences table
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("in_app_enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("sms_enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("whatsapp_enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_org_user_notification_pref"),
    )
    with op.batch_alter_table("notification_preferences", schema=None) as batch_op:
        batch_op.create_index("ix_notification_preferences_organization_id", ["organization_id"])
        batch_op.create_index("ix_notification_preferences_user_id", ["user_id"])


def downgrade() -> None:
    op.drop_table("notification_preferences")
    op.drop_table("organization_roles")
    op.drop_table("organization_terminologies")

    with op.batch_alter_table("notifications", schema=None) as batch_op:
        batch_op.drop_index("ix_notifications_idempotency_key")
        batch_op.drop_index("ix_notifications_recipient_user_id")
        batch_op.drop_column("idempotency_key")
        batch_op.drop_column("read_at")
        batch_op.drop_column("is_read")
        batch_op.drop_column("deep_link")
        batch_op.drop_column("title")
        batch_op.drop_column("recipient_user_id")

    with op.batch_alter_table("organizations", schema=None) as batch_op:
        batch_op.drop_column("enabled_modules")
        batch_op.drop_column("org_type")
