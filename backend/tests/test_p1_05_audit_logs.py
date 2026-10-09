"""Tests for P1-05: Audit Log service and API."""
from __future__ import annotations

from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db import SessionLocal
from app.models import Organization, OrganizationMember, User
from app.core.security import create_access_token, hash_password
from app.services.audit import record_audit_event

client = TestClient(app)


def test_audit_log_service_and_api():
    # 1. Setup Tenant
    db = SessionLocal()
    org = Organization(name=f"Audit Org {uuid4().hex[:6]}", currency_code="USD")
    db.add(org)
    db.flush()

    user_owner = User(
        email=f"owner-audit-{uuid4().hex}@example.com",
        display_name="Audit Owner",
        password_hash=hash_password("AuditPass123!"),
    )
    user_teacher = User(
        email=f"teach-audit-{uuid4().hex}@example.com",
        display_name="Audit Teacher",
        password_hash=hash_password("AuditPass123!"),
    )
    db.add_all([user_owner, user_teacher])
    db.flush()

    db.add(OrganizationMember(organization_id=org.id, user_id=user_owner.id, role="OWNER"))
    db.add(OrganizationMember(organization_id=org.id, user_id=user_teacher.id, role="TEACHER"))
    db.commit()

    token_owner = create_access_token(user_id=str(user_owner.id), organization_id=str(org.id), role="OWNER")
    token_teacher = create_access_token(user_id=str(user_teacher.id), organization_id=str(org.id), role="TEACHER")

    headers_owner = {"Authorization": f"Bearer {token_owner}"}
    headers_teacher = {"Authorization": f"Bearer {token_teacher}"}

    # 2. Record some security & financial events
    req_id = f"req-{uuid4().hex[:8]}"
    record_audit_event(
        db,
        organization_id=org.id,
        user_id=user_owner.id,
        action="ROLE_PERMISSION_UPDATED",
        entity_type="role",
        before={"permissions": ["people:read"]},
        after={"permissions": ["people:read", "tasks:read"]},
        request_id=req_id,
    )
    record_audit_event(
        db,
        organization_id=org.id,
        user_id=user_owner.id,
        action="FEE_CONCESSION_GRANTED",
        entity_type="student_fee",
        before={"discount": 0},
        after={"discount": 500},
        request_id=req_id,
    )
    db.close()

    # 3. Owner queries audit logs
    res = client.get("/api/v1/audit-logs", headers=headers_owner)
    assert res.status_code == 200
    logs = res.json()
    assert len(logs) >= 2
    actions = [l["action"] for l in logs]
    assert "ROLE_PERMISSION_UPDATED" in actions
    assert "FEE_CONCESSION_GRANTED" in actions

    # Verify metadata contains before, after, request_id
    role_log = next(l for l in logs if l["action"] == "ROLE_PERMISSION_UPDATED")
    assert role_log["metadata"]["before"] == {"permissions": ["people:read"]}
    assert role_log["metadata"]["after"] == {"permissions": ["people:read", "tasks:read"]}
    assert role_log["metadata"]["request_id"] == req_id
    assert role_log["user_name"] == "Audit Owner"

    # 4. Filter by entity_type
    filter_res = client.get("/api/v1/audit-logs?entity_type=student_fee", headers=headers_owner)
    assert filter_res.status_code == 200
    filtered = filter_res.json()
    assert len(filtered) == 1
    assert filtered[0]["action"] == "FEE_CONCESSION_GRANTED"

    # 5. Teacher gets 403 Forbidden
    res_t = client.get("/api/v1/audit-logs", headers=headers_teacher)
    assert res_t.status_code == 403

    # 6. Cross-tenant isolation: Second org gets 0 logs
    email2 = f"other-{uuid4().hex[:6]}@example.com"
    reg2 = client.post(
        "/api/v1/auth/register",
        json={
            "email": email2,
            "password": "Password123!",
            "display_name": "Other Admin",
            "organization_name": "Other Org",
        },
    )
    h_other = {"Authorization": f"Bearer {reg2.json()['access_token']}"}
    res_other = client.get("/api/v1/audit-logs", headers=h_other)
    assert res_other.status_code == 200
    assert len(res_other.json()) == 0
