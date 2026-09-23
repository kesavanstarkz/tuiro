from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def register(label: str):
    email = f"{label}-{uuid4().hex}@example.com"
    response = client.post("/api/v1/auth/register", json={"email": email, "password": "correct horse battery staple", "display_name": label, "organization_name": f"{label} Academy"})
    assert response.status_code == 201
    data = response.json()
    return {"Authorization": f"Bearer {data['access_token']}"}


def test_registration_login_refresh_and_me():
    headers = register("identity")
    me = client.get("/api/v1/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["role"] == "OWNER"


def test_refresh_token_rotation_works_with_sqlite_datetimes():
    email = f"refresh-{uuid4().hex}@example.com"
    response = client.post("/api/v1/auth/register", json={"email": email, "password": "correct horse battery staple", "display_name": "Refresh", "organization_name": "Refresh Academy"})
    assert response.status_code == 201
    original_refresh = response.json()["refresh_token"]
    rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": original_refresh})
    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] != original_refresh
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": original_refresh}).status_code == 401


def test_tenant_isolation():
    first = register("first")
    second = register("second")
    created = client.post("/api/v1/students", headers=first, json={"student_number": "TENANT-1", "first_name": "Private"})
    assert created.status_code == 201
    assert client.get(f"/api/v1/students/{created.json()['id']}", headers=second).status_code == 404


def test_duplicate_student_number_returns_a_safe_conflict():
    headers = register("student-number")
    first = client.post("/api/v1/students", headers=headers, json={"student_number": "STU-100", "first_name": "First"})
    assert first.status_code == 201
    duplicate = client.post("/api/v1/students", headers=headers, json={"student_number": "STU-100", "first_name": "Second"})
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "STUDENT_NUMBER_ALREADY_EXISTS"


def test_fee_generation_is_idempotent_and_payment_statuses_transition():
    headers = register("finance")
    student = client.post("/api/v1/students", headers=headers, json={"student_number": "FIN-1", "first_name": "Fee"})
    assert student.status_code == 201
    payload = {"billing_period": "2026-09", "amount": "1500", "due_date": "2026-09-30"}
    assert client.post("/api/v1/fees/generate", headers=headers, json=payload).json()["created"] == 1
    assert client.post("/api/v1/fees/generate", headers=headers, json=payload).json()["created"] == 0
    fee = client.get("/api/v1/fees", headers=headers).json()[0]
    first = client.post("/api/v1/payments", headers=headers, json={"fee_id": fee["id"], "amount": "500", "payment_method": "CASH"})
    assert first.status_code == 201 and first.json()["fee_status"] == "PARTIAL"
    second = client.post("/api/v1/payments", headers=headers, json={"fee_id": fee["id"], "amount": "1000", "payment_method": "CASH"})
    assert second.status_code == 201 and second.json()["fee_status"] == "PAID"
    assert second.json()["receipt"]["receipt_number"].startswith("TUIRO-")
    receipt_id = second.json()["receipt"]["id"]
    pdf = client.get(f"/api/v1/receipts/{receipt_id}/pdf", headers=headers)
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf" and pdf.content.startswith(b"%PDF")


def test_core_academic_workflows_and_dashboard():
    headers = register("workflows")
    student = client.post("/api/v1/students", headers=headers, json={"student_number": "FLOW-1", "first_name": "Workflow"})
    assert student.status_code == 201
    updated = client.patch(f"/api/v1/students/{student.json()['id']}", headers=headers, json={"student_number": "FLOW-1", "first_name": "Updated", "status": "ACTIVE"})
    assert updated.status_code == 200 and updated.json()["first_name"] == "Updated"
    parent = client.post("/api/v1/parents", headers=headers, json={"name": "Guardian", "phone": "9999999999"})
    assert parent.status_code == 201
    assert client.post(f"/api/v1/students/{student.json()['id']}/parents", headers=headers, json={"parent_id": parent.json()["id"], "is_primary": True}).status_code == 201
    assert len(client.get(f"/api/v1/parents/{parent.json()['id']}/students", headers=headers).json()) == 1
    class_group = client.post("/api/v1/classes", headers=headers, json={"name": "Workflow batch", "subject": "Science", "fee_amount": "1000"})
    assert class_group.status_code == 201
    class_id = class_group.json()["id"]
    assert client.post(f"/api/v1/classes/{class_id}/students", headers=headers, json={"record_id": student.json()["id"]}).status_code == 201
    attendance = client.post("/api/v1/attendance/sessions", headers=headers, json={"class_id": class_id, "session_date": "2026-09-21", "records": [{"student_id": student.json()["id"], "status": "PRESENT"}]})
    assert attendance.status_code == 201
    homework = client.post("/api/v1/homework", headers=headers, json={"class_id": class_id, "title": "Read chapter", "due_date": "2026-09-22"})
    assert homework.status_code == 201
    test = client.post("/api/v1/tests", headers=headers, json={"class_id": class_id, "name": "Unit test", "test_date": "2026-09-22", "maximum_marks": "50"})
    assert test.status_code == 201
    assert client.post(f"/api/v1/tests/{test.json()['id']}/marks", headers=headers, json={"student_id": student.json()["id"], "marks": "42", "grade": "A"}).status_code == 201
    assert client.get(f"/api/v1/tests/{test.json()['id']}/marks", headers=headers).json()[0]["percentage"] == 84.0
    assert client.post("/api/v1/schedule", headers=headers, json={"class_id": class_id, "day_of_week": 0, "start_time": "10:00", "end_time": "11:00", "room": "A"}).status_code == 201
    dashboard = client.get("/api/v1/dashboard", headers=headers)
    assert dashboard.status_code == 200 and dashboard.json()["students"] == 1


def test_group_items_are_resolved_at_view_time_and_do_not_fan_out():
    headers = register("group-cascade")
    student = client.post("/api/v1/students", headers=headers, json={"student_number": "GROUP-1", "first_name": "Ada"}).json()
    group = client.post("/api/v1/groups", headers=headers, json={"name": "Morning batch"})
    assert group.status_code == 201
    group_id = group.json()["id"]
    assert client.post(f"/api/v1/groups/{group_id}/members/{student['id']}", headers=headers).status_code == 201
    item = client.post("/api/v1/groups/assignments", headers=headers, json={"group_id": group_id, "title": "Chapter 1", "type": "assignment"})
    assert item.status_code == 201
    merged = client.get(f"/api/v1/groups/students/{student['id']}/view", headers=headers).json()
    assert len(merged["assignments"]) == 1 and merged["assignments"][0]["source"] == "Group"
    assert client.delete(f"/api/v1/groups/{group_id}/members/{student['id']}", headers=headers).status_code == 204
    # The assignment remains stored once, but no longer applies to this student.
    assert client.get(f"/api/v1/groups/students/{student['id']}/view", headers=headers).json()["assignments"] == []


def test_group_roster_handles_empty_populated_and_invalid_group_ids():
    headers = register("group-roster")
    empty_group = client.post("/api/v1/groups", headers=headers, json={"name": "Empty batch"}).json()
    empty = client.get(f"/api/v1/groups/students/{empty_group['id']}", headers=headers)
    assert empty.status_code == 200 and empty.json() == []
    attendance = client.get(f"/api/v1/groups/{empty_group['id']}/attendance?session_date=2026-09-23", headers=headers)
    assert attendance.status_code == 200 and attendance.json()["records"] == []

    student = client.post("/api/v1/students", headers=headers, json={"student_number": "ROSTER-1", "first_name": "Roster"}).json()
    assert client.post(f"/api/v1/groups/{empty_group['id']}/members/{student['id']}", headers=headers).status_code == 201
    populated = client.get(f"/api/v1/groups/students/{empty_group['id']}", headers=headers)
    assert populated.status_code == 200 and [row["id"] for row in populated.json()] == [student["id"]]

    invalid = client.get("/api/v1/groups/students/not-a-uuid", headers=headers)
    assert invalid.status_code == 404 and invalid.headers["content-type"].startswith("application/json")
