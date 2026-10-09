"""Tests for P1-03: Terminology Engine (Backend service, API, templates, isolation)."""
from __future__ import annotations

from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_terminology_engine_lifecycle_and_templates():
    # 1. Register organization 1
    email1 = f"term1-{uuid4().hex[:6]}@example.com"
    reg1 = client.post(
        "/api/v1/auth/register",
        json={
            "email": email1,
            "password": "Password123!",
            "display_name": "Term Admin",
            "organization_name": "Pioneer Learning Center",
        },
    )
    assert reg1.status_code == 201
    h1 = {"Authorization": f"Bearer {reg1.json()['access_token']}"}

    # 2. Get starter templates
    tpl_res = client.get("/api/v1/terminology/templates", headers=h1)
    assert tpl_res.status_code == 200
    templates = tpl_res.json()
    assert "EDUCATION" in templates
    assert "CORPORATE" in templates
    assert templates["EDUCATION"]["group"]["singular"] == "Class"
    assert templates["CORPORATE"]["group"]["singular"] == "Team"

    # 3. Get initial terminology (defaults to EDUCATION)
    get_res1 = client.get("/api/v1/terminology", headers=h1)
    assert get_res1.status_code == 200
    data1 = get_res1.json()
    assert data1["template"] == "EDUCATION"
    assert data1["terms"]["group"]["singular"] == "Class"
    assert data1["terms"]["group"]["plural"] == "Classes"
    assert data1["terms"]["person"]["singular"] == "Student"

    # 4. Update terminology: rename "group" to "Cohort" / "Cohorts"
    # and "work_item" to "Assignment" / "Assignments"
    put_res = client.put(
        "/api/v1/terminology",
        headers=h1,
        json={
            "terms": {
                "group": {"singular": "Cohort", "plural": "Cohorts"},
                "work_item": {"singular": "Milestone", "plural": "Milestones"},
            }
        },
    )
    assert put_res.status_code == 200
    updated1 = put_res.json()
    assert updated1["terms"]["group"]["singular"] == "Cohort"
    assert updated1["terms"]["group"]["plural"] == "Cohorts"
    assert updated1["terms"]["work_item"]["singular"] == "Milestone"
    assert updated1["terms"]["work_item"]["plural"] == "Milestones"
    # Unmodified terms still fall back cleanly to template defaults
    assert updated1["terms"]["person"]["singular"] == "Student"

    # 5. Fetch again - must be served with cached/persisted updated terms
    fetch_again = client.get("/api/v1/terminology", headers=h1)
    assert fetch_again.status_code == 200
    assert fetch_again.json()["terms"]["group"]["singular"] == "Cohort"

    # 6. Apply CORPORATE template
    apply_res = client.post("/api/v1/terminology/apply-template/CORPORATE", headers=h1)
    assert apply_res.status_code == 200
    corp_data = apply_res.json()
    assert corp_data["template"] == "CORPORATE"
    assert corp_data["terms"]["group"]["singular"] == "Team"
    assert corp_data["terms"]["group"]["plural"] == "Teams"
    assert corp_data["terms"]["person"]["singular"] == "Employee"
    assert corp_data["terms"]["work_item"]["singular"] == "Task"

    # 7. Invalid template returns 400
    bad_tpl = client.post("/api/v1/terminology/apply-template/NONEXISTENT", headers=h1)
    assert bad_tpl.status_code == 400

    # 8. Multi-tenant isolation: Second organization sees default EDUCATION terminology
    email2 = f"term2-{uuid4().hex[:6]}@example.com"
    reg2 = client.post(
        "/api/v1/auth/register",
        json={
            "email": email2,
            "password": "Password123!",
            "display_name": "Org 2 Admin",
            "organization_name": "Second Academy",
        },
    )
    h2 = {"Authorization": f"Bearer {reg2.json()['access_token']}"}
    get_res2 = client.get("/api/v1/terminology", headers=h2)
    assert get_res2.status_code == 200
    data2 = get_res2.json()
    assert data2["terms"]["group"]["singular"] == "Class"
    assert data2["terms"]["person"]["singular"] == "Student"
