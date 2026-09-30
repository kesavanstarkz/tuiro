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
