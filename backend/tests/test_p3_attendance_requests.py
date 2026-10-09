"""Phase 3 tests: unified attendance & requests approval engine."""
from datetime import date, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


def _auth(client: TestClient, role: str = "OWNER", email_prefix: str = "p3"):
    email = f"{email_prefix}-{uuid4().hex[:8]}@example.com"
    res = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "password123",
        "display_name": f"{role} User",
        "organization_name": "Test Org P3",
    })
    assert res.status_code == 201, res.text
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_unified_attendance_returns_both_sources():
    client = TestClient(app)
    headers = _auth(client, "OWNER", "att-owner")

    # 1. Create class and student
    c_res = client.post("/api/v1/classes", json={"name": "Physics"}, headers=headers)
    assert c_res.status_code == 201
    class_id = c_res.json()["id"]

    s_res = client.post("/api/v1/students", json={
        "first_name": "Albert",
        "last_name": "Einstein",
        "student_number": f"P3-{uuid4().hex[:6]}",
    }, headers=headers)
    assert s_res.status_code == 201
    student_id = s_res.json()["id"]

    # 2. Add class attendance
    today = str(date.today())
    att_res = client.post("/api/v1/attendance/sessions", json={
        "class_id": class_id,
        "session_date": today,
        "records": [{"student_id": student_id, "status": "PRESENT"}],
    }, headers=headers)
    assert att_res.status_code == 201

    # 3. Add group attendance via v1 groups API
    g_res = client.post("/api/v1/groups", json={"name": "Math Group"}, headers=headers)
    assert g_res.status_code == 201
    group_id = g_res.json()["id"]

    # Add member to group
    client.post(f"/api/v1/groups/{group_id}/members/{student_id}", headers=headers)

    # Save group attendance
    gatt_res = client.post(f"/api/v1/groups/{group_id}/attendance", json={
        "session_date": today,
        "records": [{"student_id": student_id, "status": "PRESENT"}],
    }, headers=headers)
    assert gatt_res.status_code in (200, 201)

    # 4. Query unified attendance
    uni_res = client.get("/api/v1/attendance/unified", params={"session_date": today}, headers=headers)
    assert uni_res.status_code == 200
    sessions = uni_res.json()
    assert len(sessions) >= 2
    sources = {s["source"] for s in sessions}
    assert "class" in sources
    assert "group" in sources


def test_request_approval_lifecycle():
    client = TestClient(app)
    owner_headers = _auth(client, "OWNER", "req-owner")

    # 1. Create a request
    create_res = client.post("/api/v1/requests", json={
        "request_type": "LEAVE",
        "title": "Annual Vacation",
        "description": "Family trip to mountains",
        "start_date": str(date.today() + timedelta(days=5)),
        "end_date": str(date.today() + timedelta(days=10)),
    }, headers=owner_headers)
    assert create_res.status_code == 201, create_res.text
    req_id = create_res.json()["id"]
    assert create_res.json()["status"] == "PENDING"
    assert create_res.json()["request_type"] == "LEAVE"

    # 2. List requests
    list_res = client.get("/api/v1/requests", params={"scope": "my"}, headers=owner_headers)
    assert list_res.status_code == 200
    assert any(r["id"] == req_id for r in list_res.json())

    # 3. Add comment
    cmt_res = client.post(f"/api/v1/requests/{req_id}/comments", json={
        "comment": "All handover documents have been prepared.",
    }, headers=owner_headers)
    assert cmt_res.status_code == 201
    assert cmt_res.json()["comment"] == "All handover documents have been prepared."

    # 4. Get request with comments
    get_res = client.get(f"/api/v1/requests/{req_id}", headers=owner_headers)
    assert get_res.status_code == 200
    assert len(get_res.json()["comments"]) == 1

    # 5. Approve request
    dec_res = client.post(f"/api/v1/requests/{req_id}/decide", json={
        "status": "APPROVED",
        "decision_reason": "Approved, enjoy your vacation!",
    }, headers=owner_headers)
    assert dec_res.status_code == 200
    assert dec_res.json()["status"] == "APPROVED"
    assert dec_res.json()["decision_reason"] == "Approved, enjoy your vacation!"

    # 6. Check notification was sent to requester
    notif_res = client.get("/api/v1/notifications", headers=owner_headers)
    assert notif_res.status_code == 200
    notifs = notif_res.json()
    assert any("Approved" in n["title"] and req_id in n.get("deep_link", "") for n in notifs)

    # 7. Cannot decide already-decided request
    dup_dec = client.post(f"/api/v1/requests/{req_id}/decide", json={
        "status": "REJECTED",
    }, headers=owner_headers)
    assert dup_dec.status_code == 400


def test_request_cancellation():
    client = TestClient(app)
    headers = _auth(client, "OWNER", "cancel-owner")

    create_res = client.post("/api/v1/requests", json={
        "request_type": "WORK_FROM_HOME",
        "title": "WFH on Friday",
    }, headers=headers)
    assert create_res.status_code == 201
    req_id = create_res.json()["id"]

    cancel_res = client.post(f"/api/v1/requests/{req_id}/cancel", headers=headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"
