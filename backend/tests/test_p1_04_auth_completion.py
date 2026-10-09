"""Tests for P1-04: Auth completion (multi-org switching, invites, email verification, password reset, rate limits)."""
from __future__ import annotations

from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.rate_limit import reset_rate_limits

client = TestClient(app)


def test_auth_completion_invites_and_revoke():
    # 1. Register owner
    email_owner = f"owner-{uuid4().hex[:6]}@example.com"
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email_owner,
            "password": "Password123!",
            "display_name": "Org Director",
            "organization_name": "Invite Testing Org",
        },
    )
    assert reg.status_code == 201
    headers_owner = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    # 2. Create Invite for a Teacher
    inv_res = client.post(
        "/api/v1/auth/invites",
        headers=headers_owner,
        json={"role": "TEACHER", "email": f"teacher-{uuid4().hex[:4]}@example.com"},
    )
    assert inv_res.status_code == 201
    invite_id = inv_res.json()["id"]
    invite_code = inv_res.json()["code"]

    # 3. Revoke Invite
    revoke_res = client.delete(f"/api/v1/auth/invites/{invite_id}", headers=headers_owner)
    assert revoke_res.status_code == 204

    # 4. Attempting to accept revoked invite returns 404
    accept_res = client.post(
        "/api/v1/auth/invites/accept",
        json={
            "code": invite_code,
            "display_name": "Teacher Name",
            "password": "TeacherPassword123!",
        },
    )
    assert accept_res.status_code == 404

    # 5. Create valid invite and accept
    inv_valid = client.post(
        "/api/v1/auth/invites",
        headers=headers_owner,
        json={"role": "TEACHER", "email": f"teach-valid-{uuid4().hex[:4]}@example.com"},
    )
    assert inv_valid.status_code == 201
    valid_code = inv_valid.json()["code"]

    accept_valid = client.post(
        "/api/v1/auth/invites/accept",
        json={
            "code": valid_code,
            "display_name": "Valid Teacher",
            "password": "TeacherPassword123!",
        },
    )
    assert accept_valid.status_code == 200
    assert "access_token" in accept_valid.json()


def test_email_verification_lifecycle():
    email = f"verify-{uuid4().hex[:6]}@example.com"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "display_name": "Verify User",
            "organization_name": "Verify Academy",
        },
    )

    # Request verification token
    req_res = client.post("/api/v1/auth/verify-email/request", json={"email": email})
    assert req_res.status_code == 204

    from app.services.invite_reset import _last_verify_token
    assert _last_verify_token is not None

    # Confirm with valid token
    conf_res = client.post("/api/v1/auth/verify-email/confirm", json={"token": _last_verify_token})
    assert conf_res.status_code == 200
    assert conf_res.json()["verified"] is True

    # Re-using the same token fails with 400
    reuse_res = client.post("/api/v1/auth/verify-email/confirm", json={"token": _last_verify_token})
    assert reuse_res.status_code == 400


def test_auth_rate_limiting():
    reset_rate_limits()
    test_email = f"ratelimit-{uuid4().hex[:6]}@example.com"

    # Rapid requests to password-reset/request (limit is 5)
    for _ in range(5):
        res = client.post("/api/v1/auth/password-reset/request", json={"email": test_email})
        assert res.status_code == 204

    # 6th attempt should be rate limited to 429
    res_blocked = client.post("/api/v1/auth/password-reset/request", json={"email": test_email})
    assert res_blocked.status_code == 429
    assert "Too many requests" in res_blocked.json()["detail"]
    reset_rate_limits()
