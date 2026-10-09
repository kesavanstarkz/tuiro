"""add corporate people entities and shared person metadata

Revision ID: 3b2c5d7e9f01
Revises: 2a1b4c6d8e0f
"""
from alembic import op
import sqlalchemy as sa

revision = "3b2c5d7e9f01"
down_revision = "2a1b4c6d8e0f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("departments", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(160), nullable=False), sa.Column("description", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("organization_id", "name", name="uq_department_org_name"))
    op.create_index("ix_departments_organization_id", "departments", ["organization_id"])
    op.create_table("job_titles", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(160), nullable=False), sa.Column("description", sa.Text()), sa.UniqueConstraint("organization_id", "name", name="uq_job_title_org_name"))
    op.create_index("ix_job_titles_organization_id", "job_titles", ["organization_id"])
    op.create_table("employees", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False), sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")), sa.Column("employee_number", sa.String(80), nullable=False), sa.Column("first_name", sa.String(100), nullable=False), sa.Column("last_name", sa.String(100), nullable=False, server_default=""), sa.Column("email", sa.String(320)), sa.Column("phone", sa.String(40)), sa.Column("department_id", sa.Uuid(), sa.ForeignKey("departments.id", ondelete="SET NULL")), sa.Column("job_title_id", sa.Uuid(), sa.ForeignKey("job_titles.id", ondelete="SET NULL")), sa.Column("manager_id", sa.Uuid(), sa.ForeignKey("employees.id", ondelete="SET NULL")), sa.Column("employment_type", sa.String(30), nullable=False, server_default="FULL_TIME"), sa.Column("start_date", sa.Date()), sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("organization_id", "employee_number", name="uq_employee_org_number"))
    for column in ("organization_id", "user_id", "department_id", "job_title_id", "manager_id", "status"):
        op.create_index(f"ix_employees_{column}", "employees", [column])
    op.create_table("person_custom_fields", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False), sa.Column("entity_type", sa.String(30), nullable=False), sa.Column("entity_id", sa.Uuid(), nullable=False), sa.Column("field_key", sa.String(80), nullable=False), sa.Column("value_json", sa.Text(), nullable=False), sa.UniqueConstraint("organization_id", "entity_type", "entity_id", "field_key", name="uq_person_custom_field"))
    op.create_index("ix_person_custom_fields_organization_id", "person_custom_fields", ["organization_id"]); op.create_index("ix_person_custom_fields_entity_id", "person_custom_fields", ["entity_id"])
    op.create_table("person_documents", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False), sa.Column("entity_type", sa.String(30), nullable=False), sa.Column("entity_id", sa.Uuid(), nullable=False), sa.Column("name", sa.String(200), nullable=False), sa.Column("storage_key", sa.String(500), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_person_documents_organization_id", "person_documents", ["organization_id"]); op.create_index("ix_person_documents_entity_id", "person_documents", ["entity_id"])


def downgrade() -> None:
    op.drop_table("person_documents"); op.drop_table("person_custom_fields"); op.drop_table("employees"); op.drop_table("job_titles"); op.drop_table("departments")
