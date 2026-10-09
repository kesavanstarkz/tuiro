"""P1-06 notification inbox, preferences, isolation, and job idempotency."""
from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.db import SessionLocal
from app.main import app
from app.models import Organization, OrganizationMember, User
from app.services.jobs import ThreadJobRunner

client = TestClient(app)


def _member(db, org, suffix: str):
    user = User(email=f"notify-{suffix}-{uuid4().hex[:8]}@example.com", display_name=suffix, password_hash=hash_password("Password123!"))
    db.add(user)
    db.flush()
    db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role="OWNER"))
    return user


def test_notification_inbox_preferences_and_tenant_isolation():
    db = SessionLocal()
    first_org, second_org = Organization(name=f"N1-{uuid4().hex[:6]}"), Organization(name=f"N2-{uuid4().hex[:6]}")
    db.add_all([first_org, second_org]); db.flush()
    sender, recipient, outsider = _member(db, first_org, "sender"), _member(db, first_org, "recipient"), _member(db, second_org, "outsider")
    db.commit()
    sender_headers = {"Authorization": f"Bearer {create_access_token(str(sender.id), str(first_org.id), 'OWNER')}"}
    recipient_headers = {"Authorization": f"Bearer {create_access_token(str(recipient.id), str(first_org.id), 'OWNER')}"}
    outsider_headers = {"Authorization": f"Bearer {create_access_token(str(outsider.id), str(second_org.id), 'OWNER')}"}
    db.close()

    created = client.post("/api/v1/notifications", headers=sender_headers, json={
        "recipient_user_id": str(recipient.id), "title": "Assigned", "message": "A task is ready.",
        "idempotency_key": "assignment:abc",
    })
    assert created.status_code == 201
    notification_id = created.json()["id"]
    duplicate = client.post("/api/v1/notifications", headers=sender_headers, json={
        "recipient_user_id": str(recipient.id), "title": "Changed", "message": "Ignored", "idempotency_key": "assignment:abc",
    })
    assert duplicate.status_code == 201 and duplicate.json()["id"] == notification_id

    assert client.get("/api/v1/notifications/unread-count", headers=recipient_headers).json() == {"count": 1}
    assert len(client.get("/api/v1/notifications", headers=recipient_headers).json()) == 1
    assert client.post(f"/api/v1/notifications/{notification_id}/read", headers=outsider_headers).status_code == 404
    assert client.post(f"/api/v1/notifications/{notification_id}/read", headers=recipient_headers).status_code == 200
    assert client.get("/api/v1/notifications/unread-count", headers=recipient_headers).json() == {"count": 0}

    preferences = client.patch("/api/v1/notification-preferences", headers=recipient_headers, json={"in_app_enabled": False})
    assert preferences.status_code == 200 and preferences.json()["in_app_enabled"] is False
    suppressed = client.post("/api/v1/notifications", headers=sender_headers, json={
        "recipient_user_id": str(recipient.id), "title": "Muted", "message": "No delivery", "idempotency_key": "muted:1",
    })
    assert suppressed.status_code == 201 and suppressed.json()["status"] == "SUPPRESSED"


def test_thread_job_runner_deduplicates_work():
    calls: list[str] = []
    runner = ThreadJobRunner()
    assert runner.run_now(lambda: calls.append("done"), idempotency_key="job:1") is None
    assert runner.run_now(lambda: calls.append("again"), idempotency_key="job:1") is None
    assert calls == ["done"]
