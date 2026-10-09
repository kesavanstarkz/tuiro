"""Tests for P1-02: Organization model extensions (type, timezone, currency, enabled modules, settings)."""
from __future__ import annotations

from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_organization_extensions_lifecycle():
    # 1. Register organization
    email = f"orgext-{uuid4().hex[:6]}@example.com"
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "display_name": "Org Admin",
            "organization_name": "Apex Enterprise",
        },
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get initial settings
    get_res = client.get("/api/v1/settings", headers=headers)
    assert get_res.status_code == 200
    settings = get_res.json()
    assert settings["org_type"] == "EDUCATION"  # Default
    assert isinstance(settings["enabled_modules"], list)
    assert "people" in settings["enabled_modules"]
    assert "settings" in settings["enabled_modules"]

    # 3. Update org_type to CORPORATE and customize enabled modules
    patch_res = client.patch(
        "/api/v1/settings",
        headers=headers,
        json={
            "org_type": "CORPORATE",
            "timezone": "America/New_York",
            "currency_code": "usd",
            "enabled_modules": ["home", "people", "groups", "work", "communication", "calendar", "settings"],
            "settings": {
                "work_week": ["MON", "TUE", "WED", "THU", "FRI"],
                "leave_approver": "supervisor",
            },
        },
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["org_type"] == "CORPORATE"
    assert updated["timezone"] == "America/New_York"
    assert updated["currency_code"] == "USD"  # Normalized to uppercase
    assert updated["enabled_modules"] == ["home", "people", "groups", "work", "communication", "calendar", "settings"]
    assert updated["settings"]["leave_approver"] == "supervisor"
    assert "MON" in updated["settings"]["work_week"]

    # 4. Invalid timezone yields 422
    bad_tz = client.patch(
        "/api/v1/settings",
        headers=headers,
        json={"timezone": "Invalid/Fake_Zone"},
    )
    assert bad_tz.status_code == 422

    # 5. Invalid org_type yields 422
    bad_type = client.patch(
        "/api/v1/settings",
        headers=headers,
        json={"org_type": "HOSPITAL"},
    )
    assert bad_type.status_code == 422
