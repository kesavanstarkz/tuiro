"""repair orphan classes and groups

Revision ID: e1f2a3b4c5d6
Revises: d4e1b3c7a920
"""
from alembic import op
import sqlalchemy as sa

revision = "e1f2a3b4c5d6"
down_revision = "d4e1b3c7a920"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # Find all groups without a matching class id
    orphan_groups = conn.execute(sa.text("""
        SELECT g.id, g.organization_id, g.name
        FROM groups g
        LEFT JOIN classes c ON g.id = c.id
        WHERE c.id IS NULL
    """)).fetchall()

    for g_id, org_id, name in orphan_groups:
        # Check if there is an orphan class with same org and name
        orphan_class = conn.execute(sa.text("""
            SELECT c.id FROM classes c
            LEFT JOIN groups g ON c.id = g.id
            WHERE g.id IS NULL AND c.organization_id = :org_id AND c.name = :name
        """), {"org_id": org_id, "name": name}).first()

        if orphan_class:
            old_c_id = orphan_class[0]
            for tbl in ["class_students", "class_teachers", "attendance_sessions", "homework", "academic_tests", "schedule_entries"]:
                conn.execute(sa.text(f"UPDATE {tbl} SET class_id = :new_id WHERE class_id = :old_id"), {"new_id": g_id, "old_id": old_c_id})
            conn.execute(sa.text("DELETE FROM classes WHERE id = :old_id"), {"old_id": old_c_id})

        conn.execute(sa.text("""
            INSERT INTO classes (id, organization_id, name, fee_amount, status)
            VALUES (:id, :org_id, :name, 0, 'ACTIVE')
        """), {"id": g_id, "org_id": org_id, "name": name})

    # Also repair any classes without a matching group
    orphan_classes = conn.execute(sa.text("""
        SELECT c.id, c.organization_id, c.name
        FROM classes c
        LEFT JOIN groups g ON c.id = g.id
        WHERE g.id IS NULL
    """)).fetchall()
    for c_id, org_id, name in orphan_classes:
        om = conn.execute(sa.text("SELECT user_id FROM organization_members WHERE organization_id = :org_id LIMIT 1"), {"org_id": org_id}).first()
        if om:
            user_id = om[0]
            conn.execute(sa.text("""
                INSERT INTO groups (id, organization_id, name, created_by)
                VALUES (:id, :org_id, :name, :created_by)
            """), {"id": c_id, "org_id": org_id, "name": name, "created_by": user_id})


def downgrade() -> None:
    pass
