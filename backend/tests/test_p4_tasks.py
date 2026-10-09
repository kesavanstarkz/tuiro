"""Phase 4 tests: tasks and work items management."""
from datetime import date, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


def _auth(client: TestClient, role: str = "OWNER", email_prefix: str = "p4"):
    email = f"{email_prefix}-{uuid4().hex[:8]}@example.com"
    res = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "password123",
        "display_name": f"{role} User",
        "organization_name": "Test Org P4",
    })
    assert res.status_code == 201, res.text
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_task_crud_and_status_transitions():
    client = TestClient(app)
    headers = _auth(client, "OWNER", "task-owner")

    # 1. Create task
    today = str(date.today())
    create_res = client.post("/api/v1/tasks", json={
        "title": "Prepare Quarterly Financial Report",
        "description": "Aggregate receipts and pending fees",
        "priority": "HIGH",
        "status": "TODO",
        "due_date": today,
    }, headers=headers)
    assert create_res.status_code == 201, create_res.text
    task_id = create_res.json()["id"]
    assert create_res.json()["title"] == "Prepare Quarterly Financial Report"
    assert create_res.json()["priority"] == "HIGH"

    # 2. Add checklist items
    chk1 = client.post(f"/api/v1/tasks/{task_id}/checklist", json={"title": "Export CSV from reports"}, headers=headers)
    assert chk1.status_code == 201
    item1_id = chk1.json()["id"]
    assert chk1.json()["is_completed"] is False

    chk2 = client.post(f"/api/v1/tasks/{task_id}/checklist", json={"title": "Review with center director"}, headers=headers)
    assert chk2.status_code == 201

    # 3. Toggle checklist item
    tog_res = client.post(f"/api/v1/tasks/{task_id}/checklist/{item1_id}/toggle", headers=headers)
    assert tog_res.status_code == 200
    assert tog_res.json()["is_completed"] is True

    # 4. Get task with checklist
    get_res = client.get(f"/api/v1/tasks/{task_id}", headers=headers)
    assert get_res.status_code == 200
    assert len(get_res.json()["checklist"]) == 2
    assert get_res.json()["checklist"][0]["is_completed"] is True

    # 5. Update status
    patch_res = client.patch(f"/api/v1/tasks/{task_id}", json={"status": "IN_PROGRESS"}, headers=headers)
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "IN_PROGRESS"

    # 6. List tasks
    list_res = client.get("/api/v1/tasks", params={"status": "IN_PROGRESS"}, headers=headers)
    assert list_res.status_code == 200
    assert any(t["id"] == task_id for t in list_res.json())

    # 7. Delete task
    del_res = client.delete(f"/api/v1/tasks/{task_id}", headers=headers)
    assert del_res.status_code == 204

    # 8. Verify deleted
    get_del = client.get(f"/api/v1/tasks/{task_id}", headers=headers)
    assert get_del.status_code == 404
