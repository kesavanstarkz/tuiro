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


def test_i3_group_fees_create_payments_receipts_and_dashboard_totals(client: TestClient = None):
    c = client or TestClient(app)
    email = f"i3-{uuid4().hex}@example.com"
    reg = c.post("/api/v1/auth/register", json={
        "email": email,
        "password": "password123",
        "display_name": "I3 Owner",
        "organization_name": "I3 Fee Org",
    })
    assert reg.status_code == 201, reg.text
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a group and student
    grp_res = c.post("/api/v1/groups", json={"name": "Math Grade 10"}, headers=headers)
    assert grp_res.status_code == 201
    group_id = grp_res.json()["id"]

    stud_res = c.post("/api/v1/students", json={
        "student_number": "STU-003",
        "first_name": "Charlie",
        "last_name": "Brown",
    }, headers=headers)
    assert stud_res.status_code == 201
    student_id = stud_res.json()["id"]

    add_mem = c.post(f"/api/v1/groups/{group_id}/members/{student_id}", headers=headers)
    assert add_mem.status_code == 201

    # 2. Create a group fee
    fee_res = c.post("/api/v1/groups/fees", json={
        "group_id": group_id,
        "amount": 250.0,
        "due_date": "2026-11-01",
    }, headers=headers)
    assert fee_res.status_code == 201
    fee_id = fee_res.json()["id"]

    # 3. Check dashboard before payment
    dash_before = c.get("/api/v1/dashboard", headers=headers)
    assert dash_before.status_code == 200
    assert float(dash_before.json()["pending_fees"]) == 250.0
    assert float(dash_before.json()["todays_collections"]) == 0.0

    # 4. Check /fees/pending
    pending_res = c.get("/api/v1/fees/pending", headers=headers)
    assert pending_res.status_code == 200
    assert any(float(item["outstanding_amount"]) == 250.0 for item in pending_res.json())

    # 5. Pay the fee via /groups/fees/{fee_id}/payments
    pay_res = c.post(f"/api/v1/groups/fees/{fee_id}/payments", json={
        "student_id": student_id,
        "amount_paid": 250.0,
    }, headers=headers)
    assert pay_res.status_code == 201

    # 6. Check dashboard after payment
    dash_after = c.get("/api/v1/dashboard", headers=headers)
    assert dash_after.status_code == 200
    assert float(dash_after.json()["pending_fees"]) == 0.0
    assert float(dash_after.json()["todays_collections"]) == 250.0
    assert len(dash_after.json()["recent_payments"]) >= 1

    # 7. Check /reports/fees
    rep_fees = c.get("/api/v1/reports/fees", headers=headers)
    assert rep_fees.status_code == 200
    assert float(rep_fees.json()["collected_amount"]) == 250.0
    assert float(rep_fees.json()["pending_amount"]) == 0.0
    assert rep_fees.json()["payment_count"] == 1

    # 8. Check receipts
    receipts_res = c.get("/api/v1/receipts", headers=headers)
    assert receipts_res.status_code == 200
    assert len(receipts_res.json()) == 1
    assert receipts_res.json()[0]["receipt_number"].startswith("TUIRO-")

    # 9. Check student merged view
    view_res = c.get(f"/api/v1/groups/students/{student_id}/view", headers=headers)
    assert view_res.status_code == 200
    student_fees = view_res.json()["fees"]
    matching_fee = next((f for f in student_fees if f["id"] == fee_id), None)
    assert matching_fee is not None
    assert matching_fee["status"] == "PAID"

    # 10. Check /groups/fees/needs-attention (should not include settled fee)
    attn_res = c.get("/api/v1/groups/fees/needs-attention", headers=headers)
    assert attn_res.status_code == 200
    assert not any(f["fee_id"] == fee_id and f["student_id"] == student_id for f in attn_res.json())


def test_i5_transaction_reference_unique_per_org(client: TestClient = None):
    c = client or TestClient(app)

    # 1. Register Org 1
    reg1 = c.post("/api/v1/auth/register", json={
        "email": f"i5-org1-{uuid4().hex}@example.com",
        "password": "password123",
        "display_name": "Org1 Owner",
        "organization_name": "Org 1",
    })
    assert reg1.status_code == 201
    h1 = {"Authorization": f"Bearer {reg1.json()['access_token']}"}

    s1 = c.post("/api/v1/students", json={
        "student_number": "STU-I5-1",
        "first_name": "Student",
        "last_name": "One",
    }, headers=h1).json()["id"]

    f1 = c.post("/api/v1/fees", json={
        "student_id": s1,
        "billing_period": "2026-10",
        "amount": 100.0,
        "due_date": "2026-10-30",
    }, headers=h1).json()["id"]

    # 2. Register Org 2
    reg2 = c.post("/api/v1/auth/register", json={
        "email": f"i5-org2-{uuid4().hex}@example.com",
        "password": "password123",
        "display_name": "Org2 Owner",
        "organization_name": "Org 2",
    })
    assert reg2.status_code == 201
    h2 = {"Authorization": f"Bearer {reg2.json()['access_token']}"}

    s2 = c.post("/api/v1/students", json={
        "student_number": "STU-I5-2",
        "first_name": "Student",
        "last_name": "Two",
    }, headers=h2).json()["id"]

    f2 = c.post("/api/v1/fees", json={
        "student_id": s2,
        "billing_period": "2026-10",
        "amount": 100.0,
        "due_date": "2026-10-30",
    }, headers=h2).json()["id"]

    # 3. Pay in Org 1 with REF-1
    pay1 = c.post("/api/v1/payments", json={
        "fee_id": f1,
        "amount": 50.0,
        "transaction_reference": "REF-1",
    }, headers=h1)
    assert pay1.status_code == 201, pay1.text

    # 4. Same org uses REF-1 again -> 409 Conflict
    dup_org1 = c.post("/api/v1/payments", json={
        "fee_id": f1,
        "amount": 50.0,
        "transaction_reference": "REF-1",
    }, headers=h1)
    assert dup_org1.status_code == 409

    # 5. Org 2 uses REF-1 -> should succeed (201)
    pay2 = c.post("/api/v1/payments", json={
        "fee_id": f2,
        "amount": 50.0,
        "transaction_reference": "REF-1",
    }, headers=h2)
    assert pay2.status_code == 201, pay2.text


def test_i7_concurrency_and_side_effects(client: TestClient = None):
    c = client or TestClient(app)
    email = f"i7-{uuid4().hex}@example.com"
    reg = c.post("/api/v1/auth/register", json={
        "email": email,
        "password": "password123",
        "display_name": "I7 Owner",
        "organization_name": "I7 Concurrency Org",
    })
    assert reg.status_code == 201
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    stud = c.post("/api/v1/students", json={
        "student_number": "STU-I7",
        "first_name": "Diana",
        "last_name": "Prince",
    }, headers=headers).json()["id"]

    fee = c.post("/api/v1/fees", json={
        "student_id": stud,
        "billing_period": "2026-10",
        "amount": 200.0,
        "due_date": "2026-10-31",
    }, headers=headers).json()["id"]

    # 1. First payment
    p1 = c.post("/api/v1/payments", json={
        "fee_id": fee,
        "amount": 50.0,
    }, headers=headers)
    assert p1.status_code == 201
    r1_num = p1.json()["receipt"]["receipt_number"]

    # 2. Second payment - receipts must increment atomically
    p2 = c.post("/api/v1/payments", json={
        "fee_id": fee,
        "amount": 50.0,
    }, headers=headers)
    assert p2.status_code == 201
    r2_num = p2.json()["receipt"]["receipt_number"]

    # Sequence numbers
    seq1 = int(r1_num.split("-")[-1])
    seq2 = int(r2_num.split("-")[-1])
    assert seq2 == seq1 + 1

    # 3. Verify GET /chats/direct does not create thread side-effect
    from app.models import ChatThread
    from app.db import SessionLocal
    with SessionLocal() as db:
        initial_threads = db.query(ChatThread).count()

    # Query direct chat for a non-existing thread
    res = c.get(f"/api/v1/groups/chats/direct/{uuid4()}", headers=headers)
    assert res.status_code in (200, 404)
    with SessionLocal() as db:
        after_threads = db.query(ChatThread).count()
        assert after_threads == initial_threads, "GET /chats/direct must not mutate database"


def test_i8_patch_accepts_partial_body(client: TestClient = None):
    c = client or TestClient(app)
    reg = c.post("/api/v1/auth/register", json={
        "email": f"i8-{uuid4().hex}@example.com",
        "password": "password123",
        "display_name": "I8 Owner",
        "organization_name": "I8 Patch Org",
    })
    assert reg.status_code == 201
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    # 1. Student: create and partial patch
    stu = c.post("/api/v1/students", json={
        "student_number": "STU-888",
        "first_name": "OriginalFirst",
        "last_name": "OriginalLast",
    }, headers=headers).json()
    stu_id = stu["id"]

    stu_patch = c.patch(f"/api/v1/students/{stu_id}", json={
        "first_name": "UpdatedFirst"
    }, headers=headers)
    assert stu_patch.status_code == 200, stu_patch.text
    assert stu_patch.json()["first_name"] == "UpdatedFirst"
    assert stu_patch.json()["last_name"] == "OriginalLast"
    assert stu_patch.json()["student_number"] == "STU-888"

    # 2. Class: create and partial patch
    cls = c.post("/api/v1/classes", json={
        "name": "Math Grade 11",
        "subject": "Mathematics",
        "fee_amount": 120.0,
    }, headers=headers).json()
    cls_id = cls["id"]

    cls_patch = c.patch(f"/api/v1/classes/{cls_id}", json={
        "name": "Advanced Math Grade 11"
    }, headers=headers)
    assert cls_patch.status_code == 200, cls_patch.text
    assert cls_patch.json()["name"] == "Advanced Math Grade 11"
    assert cls_patch.json()["subject"] == "Mathematics"

    # 3. Parent: create and partial patch
    par = c.post("/api/v1/parents", json={
        "name": "Bruce Wayne",
        "phone": "+1234567890",
    }, headers=headers).json()
    par_id = par["id"]

    par_patch = c.patch(f"/api/v1/parents/{par_id}", json={
        "phone": "+9876543210"
    }, headers=headers)
    assert par_patch.status_code == 200, par_patch.text
    assert par_patch.json()["phone"] == "+9876543210"
    assert par_patch.json()["name"] == "Bruce Wayne"

    # 4. Teacher: create and partial patch
    tch = c.post("/api/v1/teachers", json={
        "employee_number": "TCH-001",
        "specialization": "Physics",
    }, headers=headers).json()
    tch_id = tch["id"]

    tch_patch = c.patch(f"/api/v1/teachers/{tch_id}", json={
        "specialization": "Quantum Physics"
    }, headers=headers)
    assert tch_patch.status_code == 200, tch_patch.text
    assert tch_patch.json()["specialization"] == "Quantum Physics"
    assert tch_patch.json()["employee_number"] == "TCH-001"

    # 5. Homework: create and partial patch
    hw = c.post("/api/v1/homework", json={
        "class_id": cls_id,
        "title": "Exercise 1.1",
        "due_date": "2026-10-15",
    }, headers=headers).json()
    hw_id = hw["id"]

    hw_patch = c.patch(f"/api/v1/homework/{hw_id}", json={
        "title": "Exercise 1.1 & 1.2"
    }, headers=headers)
    assert hw_patch.status_code == 200, hw_patch.text
    assert hw_patch.json()["title"] == "Exercise 1.1 & 1.2"
    assert hw_patch.json()["due_date"] == "2026-10-15"

    # 6. Test: create and partial patch
    test_obj = c.post("/api/v1/tests", json={
        "class_id": cls_id,
        "name": "Midterm Exam",
        "test_date": "2026-10-20",
        "maximum_marks": 100.0,
    }, headers=headers).json()
    test_id = test_obj["id"]

    test_patch = c.patch(f"/api/v1/tests/{test_id}", json={
        "name": "Midterm Exam - Revised"
    }, headers=headers)
    assert test_patch.status_code == 200, test_patch.text
    assert test_patch.json()["name"] == "Midterm Exam - Revised"
    assert float(test_patch.json()["maximum_marks"]) == 100.0

    # 7. Schedule: create and partial patch
    sch = c.post("/api/v1/schedule", json={
        "class_id": cls_id,
        "day_of_week": 1,
        "start_time": "10:00",
        "end_time": "11:00",
        "room": "Room A",
    }, headers=headers).json()
    sch_id = sch["id"]

    sch_patch = c.patch(f"/api/v1/schedule/{sch_id}", json={
        "room": "Room B"
    }, headers=headers)
    assert sch_patch.status_code == 200, sch_patch.text
    assert sch_patch.json()["room"] == "Room B"
    assert sch_patch.json()["start_time"] == "10:00"

    # 8. Settings: partial patch
    set_patch = c.patch("/api/v1/settings", json={
        "currency_code": "USD"
    }, headers=headers)
    assert set_patch.status_code == 200, set_patch.text
    assert set_patch.json()["currency_code"] == "USD"


def test_i9_withdrawn_students_hidden_by_default(client: TestClient = None):
    c = client or TestClient(app)
    email = f"i9-{uuid4().hex}@example.com"
    reg = c.post("/api/v1/auth/register", json={
        "organization_name": "I9 Center",
        "email": email,
        "password": "Password123!",
        "display_name": "I9 Owner",
    })
    assert reg.status_code == 201
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    # Create active student
    stu1 = c.post("/api/v1/students", json={
        "student_number": "ACT-001",
        "first_name": "Active",
        "last_name": "Student",
        "status": "ACTIVE",
    }, headers=headers)
    assert stu1.status_code == 201

    # Create withdrawn student
    stu2 = c.post("/api/v1/students", json={
        "student_number": "WTH-001",
        "first_name": "Withdrawn",
        "last_name": "Student",
        "status": "WITHDRAWN",
    }, headers=headers)
    assert stu2.status_code == 201

    # Default listing (no status param) -> must only return ACTIVE students
    res_default = c.get("/api/v1/students", headers=headers)
    assert res_default.status_code == 200
    names_default = [s["student_number"] for s in res_default.json()]
    assert names_default == ["ACT-001"]

    # Explicit ACTIVE status -> must only return ACTIVE students
    res_active = c.get("/api/v1/students?status=ACTIVE", headers=headers)
    assert res_active.status_code == 200
    names_active = [s["student_number"] for s in res_active.json()]
    assert names_active == ["ACT-001"]

    # Explicit WITHDRAWN status -> must only return WITHDRAWN students
    res_withdrawn = c.get("/api/v1/students?status=WITHDRAWN", headers=headers)
    assert res_withdrawn.status_code == 200
    names_withdrawn = [s["student_number"] for s in res_withdrawn.json()]
    assert names_withdrawn == ["WTH-001"]

    # Explicit ALL status -> must return both
    res_all = c.get("/api/v1/students?status=ALL", headers=headers)
    assert res_all.status_code == 200
    names_all = [s["student_number"] for s in res_all.json()]
    assert "ACT-001" in names_all and "WTH-001" in names_all


def test_i11_no_migration_drift():
    from alembic import command
    from alembic.config import Config
    import os

    ini_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic.ini")
    config = Config(ini_path)
    command.check(config)








