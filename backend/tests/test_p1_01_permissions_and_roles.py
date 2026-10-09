"""Tests for P1-01: Permission catalog, configurable roles, and role matrix enforcement."""
from __future__ import annotations

import re
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db import SessionLocal
from app.models import Organization, OrganizationMember, User
from app.core.security import create_access_token, hash_password
from app.core.permissions import ALL_PERMISSION_CODES, DEFAULT_ROLE_PERMISSIONS, PERMISSION_CATALOG, PERMISSION_MATRIX

client = TestClient(app)


def test_permission_catalog_completeness():
    assert len(PERMISSION_CATALOG) >= 20
    codes = {p["code"] for p in PERMISSION_CATALOG}
    assert "org:read" in codes
    assert "people:read" in codes
    assert "attendance:read" in codes
    assert "finance:read" in codes
    assert "reports:read" in codes
    assert "audit_log:read" in codes

    for cat in PERMISSION_CATALOG:
        assert cat["code"]
        assert cat["name"]
        assert cat["category"]
        assert cat["description"]


def test_configurable_roles_lifecycle():
    # 1. Register test tenant
    email = f"roles-{uuid4().hex[:6]}@example.com"
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "display_name": "Role Admin",
            "organization_name": "Roles Academy",
        },
    )
    assert reg.status_code == 201
    auth_data = reg.json()
    headers = {"Authorization": f"Bearer {auth_data['access_token']}"}

    # 2. Query Permission Catalog API
    catalog_res = client.get("/api/v1/roles/permissions", headers=headers)
    assert catalog_res.status_code == 200
    catalog = catalog_res.json()
    assert len(catalog) >= 20

    # 3. Query Default Roles for Organization
    roles_res = client.get("/api/v1/roles", headers=headers)
    assert roles_res.status_code == 200
    roles = roles_res.json()
    role_names = {r["name"] for r in roles}
    assert "OWNER" in role_names
    assert "ADMIN" in role_names
    assert "TEACHER" in role_names

    # 4. Create Custom Role (e.g. LAB_ASSISTANT)
    create_res = client.post(
        "/api/v1/roles",
        headers=headers,
        json={
            "name": "LAB_ASSISTANT",
            "display_name": "Lab Assistant",
            "description": "Assists with classroom labs and materials",
            "permissions": ["people:read", "groups:read", "tasks:read"],
        },
    )
    assert create_res.status_code == 201
    custom_role = create_res.json()
    assert custom_role["name"] == "LAB_ASSISTANT"
    assert custom_role["is_system"] is False
    assert "tasks:read" in custom_role["permissions"]

    # 5. Duplicate name rejected with 409 Conflict
    dup_res = client.post(
        "/api/v1/roles",
        headers=headers,
        json={
            "name": "LAB_ASSISTANT",
            "display_name": "Duplicate Lab Assistant",
            "permissions": ["people:read"],
        },
    )
    assert dup_res.status_code == 409

    # 6. Invalid permission rejected with 422
    invalid_res = client.post(
        "/api/v1/roles",
        headers=headers,
        json={
            "name": "INVALID_ROLE",
            "display_name": "Invalid Role",
            "permissions": ["nonexistent:permission"],
        },
    )
    assert invalid_res.status_code == 422

    # 7. Update Custom Role permissions
    update_res = client.put(
        "/api/v1/roles/LAB_ASSISTANT",
        headers=headers,
        json={
            "display_name": "Senior Lab Assistant",
            "permissions": ["people:read", "groups:read", "tasks:read", "files:read"],
        },
    )
    assert update_res.status_code == 200
    updated_role = update_res.json()
    assert updated_role["display_name"] == "Senior Lab Assistant"
    assert "files:read" in updated_role["permissions"]

    # 8. Attempting to delete a system role fails with 400
    del_sys = client.delete("/api/v1/roles/TEACHER", headers=headers)
    assert del_sys.status_code == 400

    # 9. Delete custom role succeeds with 204
    del_custom = client.delete("/api/v1/roles/LAB_ASSISTANT", headers=headers)
    assert del_custom.status_code == 204

    # Verify deleted
    roles_after = client.get("/api/v1/roles", headers=headers).json()
    assert "LAB_ASSISTANT" not in {r["name"] for r in roles_after}


def test_every_operation_x_every_role_matrix():
    db = SessionLocal()
    org = Organization(name=f"Matrix Org {uuid4().hex[:6]}", currency_code="USD")
    db.add(org)
    db.flush()

    tokens = {}
    for role in ["SUPER_ADMIN", "OWNER", "ADMIN", "TEACHER", "PARENT", "STUDENT"]:
        u = User(
            email=f"matrix-{role.lower()}-{uuid4().hex}@example.com",
            display_name=f"Matrix {role}",
            password_hash=hash_password("MatrixPw123!"),
        )
        db.add(u)
        db.flush()
        mem = OrganizationMember(organization_id=org.id, user_id=u.id, role=role)
        db.add(mem)
        db.flush()
        tokens[role] = create_access_token(user_id=str(u.id), organization_id=str(org.id), role=role)
    db.commit()
    db.close()

    dummy_id = str(uuid4())
    failures = []

    for (method, path_template), allowed_roles in PERMISSION_MATRIX.items():
        url = re.sub(r"\{[^}]+\}", dummy_id, path_template)
        params = {}
        if "attendance" in path_template:
            params["session_date"] = "2026-09-30"

        for role, token in tokens.items():
            headers = {"Authorization": f"Bearer {token}"}
            res = client.request(method, url, headers=headers, json={}, params=params)
            is_allowed = role in allowed_roles
            if not is_allowed and res.status_code != 403:
                failures.append(f"{method} {path_template} as {role}: expected 403, got {res.status_code}")
            elif is_allowed and res.status_code == 403:
                failures.append(f"{method} {path_template} as {role}: unexpected 403 ({res.text})")

    assert not failures, "Permission matrix drift detected:\n" + "\n".join(failures[:20])
