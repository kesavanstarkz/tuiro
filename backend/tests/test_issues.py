from uuid import UUID, uuid4
from fastapi.testclient import TestClient

from app.main import app


def test_i1_group_and_class_id_sync_and_endpoints(client: TestClient = None):
    c = client or TestClient(app)
    email = f"i1-{uuid4().hex}@example.com"
    reg = c.post("/api/v1/auth/register", json={
        "email": email,
        "password": "password123",
        "display_name": "I1 Owner",
        "organization_name": "I1 Suite Org",
    })
    assert reg.status_code == 201, reg.text
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create via /groups
    grp_res = c.post("/api/v1/groups", json={"name": "Science Batch"}, headers=headers)
    assert grp_res.status_code == 201, grp_res.text
    group_id = grp_res.json()["id"]

    # Check GET /classes to verify matching class exists with the same ID
    classes_res = c.get("/api/v1/classes", headers=headers)
    assert classes_res.status_code == 200
    matching_class = next((cls for cls in classes_res.json() if cls["id"] == group_id), None)
    assert matching_class is not None, "ClassGroup must exist with exact same ID as Group"
    assert matching_class["name"] == "Science Batch"

    # 2. Create homework on that ID
    hw_res = c.post("/api/v1/homework", json={"class_id": group_id, "title": "Science HW 1"}, headers=headers)
    assert hw_res.status_code == 201, hw_res.text
    assert hw_res.json()["class_id"] == group_id

    # 3. Create test on that ID
    test_res = c.post("/api/v1/tests", json={
        "class_id": group_id,
        "name": "Midterm Exam",
        "test_date": "2026-10-15",
        "maximum_marks": 100,
    }, headers=headers)
    assert test_res.status_code == 201, test_res.text
    assert test_res.json()["class_id"] == group_id

    # 4. Create schedule on that ID
    sched_res = c.post("/api/v1/schedule", json={
        "class_id": group_id,
        "day_of_week": 3,
        "start_time": "14:00",
        "end_time": "15:30",
    }, headers=headers)
    assert sched_res.status_code == 201, sched_res.text
    assert sched_res.json()["class_id"] == group_id

    # 5. Reverse: Create via /classes and verify matching group exists with same ID
    cls_create_res = c.post("/api/v1/classes", json={"name": "Math Batch", "fee_amount": 150.0}, headers=headers)
    assert cls_create_res.status_code == 201
    class_id = cls_create_res.json()["id"]

    grp_get_res = c.get(f"/api/v1/groups/{class_id}", headers=headers)
    assert grp_get_res.status_code == 200
    assert grp_get_res.json()["id"] == class_id
    assert grp_get_res.json()["name"] == "Math Batch"


def test_i2_dashboard_and_reports_include_group_attendance(client: TestClient = None):
    from datetime import date
    c = client or TestClient(app)
    email = f"i2-{uuid4().hex}@example.com"
    reg = c.post("/api/v1/auth/register", json={
        "email": email,
        "password": "password123",
        "display_name": "I2 Owner",
        "organization_name": "I2 Attendance Org",
    })
    assert reg.status_code == 201, reg.text
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a group
    grp_res = c.post("/api/v1/groups", json={"name": "History Batch"}, headers=headers)
    assert grp_res.status_code == 201
    group_id = grp_res.json()["id"]

    # 2. Create a student
    stud_res = c.post("/api/v1/students", json={
        "student_number": "STU-001",
        "first_name": "Alice",
        "last_name": "Wonderland",
    }, headers=headers)
    assert stud_res.status_code == 201
    student_id = stud_res.json()["id"]

    # 3. Add student to group
    add_mem = c.post(f"/api/v1/groups/{group_id}/members/{student_id}", headers=headers)
    assert add_mem.status_code == 201

    # Check dashboard before attendance: should have 0 attendance percentage
    dash_before = c.get("/api/v1/dashboard", headers=headers)
    assert dash_before.status_code == 200
    assert dash_before.json()["attendance_percentage"] == 0

    today_str = date.today().isoformat()

    # 4. Mark attendance via /groups/{group_id}/attendance
    att_res = c.post(f"/api/v1/groups/{group_id}/attendance", json={
        "session_date": today_str,
        "records": [{"student_id": student_id, "status": "PRESENT"}]
    }, headers=headers)
    assert att_res.status_code == 201, att_res.text

    # 5. Check dashboard: should now reflect group attendance
    dash_after = c.get("/api/v1/dashboard", headers=headers)
    assert dash_after.status_code == 200
    assert dash_after.json()["attendance_percentage"] == 100.0

    # 6. Check /reports/attendance
    rep_res = c.get("/api/v1/reports/attendance", headers=headers)
    assert rep_res.status_code == 200
    assert rep_res.json()["total_records"] == 1
    assert rep_res.json()["present_records"] == 1
    assert rep_res.json()["attendance_percentage"] == 100.0

    # 7. Check /reports/attendance/export.csv
    csv_res = c.get("/api/v1/reports/attendance/export.csv", headers=headers)
    assert csv_res.status_code == 200
    csv_text = csv_res.text
    assert "date,class_id,student_id,status" in csv_text
    assert student_id in csv_text
    assert "PRESENT" in csv_text

    # 8. Test deduplication: record class attendance for same class_id (which is group_id) and same date
    class_att = c.post("/api/v1/attendance/sessions", json={
        "class_id": group_id,
        "session_date": today_str,
        "records": [{"student_id": student_id, "status": "PRESENT"}]
    }, headers=headers)
    assert class_att.status_code == 201

    # Total should still be 1 (deduplicated), not 2
    rep_res_dedup = c.get("/api/v1/reports/attendance", headers=headers)
    assert rep_res_dedup.status_code == 200
    assert rep_res_dedup.json()["total_records"] == 1
    assert rep_res_dedup.json()["present_records"] == 1

