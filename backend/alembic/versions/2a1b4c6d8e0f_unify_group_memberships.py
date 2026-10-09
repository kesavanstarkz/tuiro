"""add canonical group metadata and memberships without removing legacy tables

Revision ID: 2a1b4c6d8e0f
Revises: 1e9d4ded52ae
"""
from alembic import op
import sqlalchemy as sa

revision = "2a1b4c6d8e0f"
down_revision = "1e9d4ded52ae"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Additive changes let the v1 class/group endpoints keep serving existing
    # mobile clients while v2 moves to the canonical rows.
    with op.batch_alter_table("groups") as batch:
        batch.add_column(sa.Column("kind", sa.String(40), nullable=False, server_default="class"))
        batch.add_column(sa.Column("description", sa.Text(), nullable=True))
        batch.add_column(sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"))
        batch.add_column(sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"))
        batch.add_column(sa.Column("parent_group_id", sa.Uuid(), nullable=True))
        batch.create_index("ix_groups_kind", ["kind"])
        batch.create_index("ix_groups_status", ["status"])
        batch.create_index("ix_groups_parent_group_id", ["parent_group_id"])
        batch.create_foreign_key("fk_groups_parent_group", "groups", ["parent_group_id"], ["id"], ondelete="SET NULL")

    op.create_table(
        "group_memberships",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("group_id", sa.Uuid(), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("member_type", sa.String(30), nullable=False, server_default="student"),
        sa.Column("member_id", sa.Uuid(), nullable=False),
        sa.Column("member_role", sa.String(30), nullable=False, server_default="member"),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("added_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.UniqueConstraint("group_id", "member_type", "member_id", name="uq_group_member_identity"),
    )
    op.create_index("ix_group_memberships_organization_id", "group_memberships", ["organization_id"])
    op.create_index("ix_group_memberships_group_id", "group_memberships", ["group_id"])
    op.create_index("ix_group_memberships_member_id", "group_memberships", ["member_id"])
    op.create_index("ix_group_memberships_org_group_active", "group_memberships", ["organization_id", "group_id", "removed_at"])

    # A group without a matching class is valid.  Insert class enrollments
    # first and then legacy group memberships, relying on the unique identity
    # constraint to avoid duplicates where IDs were previously synchronized.
    op.execute("""
        INSERT INTO group_memberships (id, organization_id, group_id, member_type, member_id, member_role, joined_at, removed_at)
        SELECT id, organization_id, class_id, 'student', student_id, 'member', enrolled_on, NULL
        FROM class_students
        WHERE class_id IN (SELECT id FROM groups)
    """)
    # UUID values are portable, but legacy identifiers can collide. Use a
    # deterministic exclusion rather than database-specific upsert syntax.
    op.execute("""
        INSERT INTO group_memberships (id, organization_id, group_id, member_type, member_id, member_role, joined_at, removed_at)
        SELECT gm.id, gm.organization_id, gm.group_id, 'student', gm.student_id, 'member', gm.joined_at, gm.removed_at
        FROM group_members gm
        WHERE NOT EXISTS (
            SELECT 1 FROM group_memberships m
            WHERE m.group_id = gm.group_id AND m.member_type = 'student' AND m.member_id = gm.student_id
        )
    """)


def downgrade() -> None:
    op.drop_index("ix_group_memberships_org_group_active", table_name="group_memberships")
    op.drop_index("ix_group_memberships_member_id", table_name="group_memberships")
    op.drop_index("ix_group_memberships_group_id", table_name="group_memberships")
    op.drop_index("ix_group_memberships_organization_id", table_name="group_memberships")
    op.drop_table("group_memberships")
    with op.batch_alter_table("groups") as batch:
        batch.drop_constraint("fk_groups_parent_group", type_="foreignkey")
        batch.drop_index("ix_groups_parent_group_id")
        batch.drop_index("ix_groups_status")
        batch.drop_index("ix_groups_kind")
        batch.drop_column("parent_group_id")
        batch.drop_column("status")
        batch.drop_column("metadata_json")
        batch.drop_column("description")
        batch.drop_column("kind")
