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


def test_i4_role_matrix_enforcement(client: TestClient = None):
    import re
    from uuid import uuid4
    from app.db import SessionLocal
    from app.models import User, Organization, OrganizationMember
    from app.core.security import create_access_token, hash_password
    from app.core.permissions import PERMISSION_MATRIX

    c = client or TestClient(app)
    db = SessionLocal()
    org = Organization(name=f"I4 Org {uuid4().hex[:6]}", currency_code="USD")
    db.add(org)
    db.flush()

    tokens = {}
    for role in ["SUPER_ADMIN", "OWNER", "ADMIN", "TEACHER", "PARENT", "STUDENT"]:
        u = User(
            email=f"i4-{role.lower()}-{uuid4().hex}@example.com",
            display_name=f"I4 {role}",
            password_hash=hash_password("password123"),
        )
        db.add(u)
        db.flush()
        mem = OrganizationMember(organization_id=org.id, user_id=u.id, role=role)
        db.add(mem)
        db.flush()
        tokens[role] = create_access_token(user_id=str(u.id), organization_id=str(org.id), role=role)
    db.commit()
    db.close()

    dummy_id = str(uuid4())
    failures = []

    for (method, path_template), allowed_roles in PERMISSION_MATRIX.items():
        url = re.sub(r"\{[^}]+\}", dummy_id, path_template)
        params = {}
        if "attendance" in path_template:
            params["session_date"] = "2026-09-30"

        for role, token in tokens.items():
            headers = {"Authorization": f"Bearer {token}"}
            res = c.request(method, url, headers=headers, json={}, params=params)
            is_allowed = role in allowed_roles
            if not is_allowed and res.status_code != 403:
                failures.append(f"{method} {path_template} as {role}: expected 403, got {res.status_code}")
            elif is_allowed and res.status_code == 403:
                failures.append(f"{method} {path_template} as {role}: unexpected 403 ({res.text})")

    assert not failures, "Role matrix enforcement failed:\n" + "\n".join(failures[:20])


def test_i4_scoped_access_and_cross_tenant_isolation(client: TestClient = None):
    from uuid import uuid4
    from app.db import SessionLocal
    from app.models import (
        User, Organization, OrganizationMember, ClassGroup, Teacher, ClassTeacher,
        Student, Parent, StudentParent
    )
    from app.core.security import create_access_token, hash_password

    c = client or TestClient(app)
    db = SessionLocal()

    # Org 1
    org1 = Organization(name=f"Org1 {uuid4().hex[:6]}", currency_code="USD")
    db.add(org1)
    db.flush()

    # Teacher user in Org 1
    teacher_user = User(email=f"teach-{uuid4().hex}@example.com", display_name="Teacher 1", password_hash=hash_password("pw"))
    db.add(teacher_user)
    db.flush()
    db.add(OrganizationMember(organization_id=org1.id, user_id=teacher_user.id, role="TEACHER"))
    teacher_record = Teacher(organization_id=org1.id, user_id=teacher_user.id, employee_number="T-001")
    db.add(teacher_record)

    # Class 1 and Class 2 in Org 1
    cls1 = ClassGroup(organization_id=org1.id, name="Class Assigned", status="ACTIVE")
    cls2 = ClassGroup(organization_id=org1.id, name="Class Unassigned", status="ACTIVE")
    db.add_all([cls1, cls2])
    db.flush()

    # Assign teacher to Class 1 only
    db.add(ClassTeacher(organization_id=org1.id, class_id=cls1.id, teacher_id=teacher_record.id))

    # Student 1 and Parent 1 (linked) & Student 2 (unlinked)
    s1_user = User(email=f"s1-{uuid4().hex}@example.com", display_name="Student 1", password_hash=hash_password("pw"))
    p1_user = User(email=f"p1-{uuid4().hex}@example.com", display_name="Parent 1", password_hash=hash_password("pw"))
    s2_user = User(email=f"s2-{uuid4().hex}@example.com", display_name="Student 2", password_hash=hash_password("pw"))
    db.add_all([s1_user, p1_user, s2_user])
    db.flush()

    db.add(OrganizationMember(organization_id=org1.id, user_id=s1_user.id, role="STUDENT"))
    db.add(OrganizationMember(organization_id=org1.id, user_id=p1_user.id, role="PARENT"))
    db.add(OrganizationMember(organization_id=org1.id, user_id=s2_user.id, role="STUDENT"))

    s1 = Student(organization_id=org1.id, user_id=s1_user.id, student_number=f"S1-{uuid4().hex[:4]}", first_name="Alice", last_name="Student", status="ACTIVE")
    s2 = Student(organization_id=org1.id, user_id=s2_user.id, student_number=f"S2-{uuid4().hex[:4]}", first_name="Bob", last_name="Student", status="ACTIVE")
    p1 = Parent(organization_id=org1.id, user_id=p1_user.id, name="Carol Parent")
    db.add_all([s1, s2, p1])
    db.flush()

    db.add(StudentParent(organization_id=org1.id, student_id=s1.id, parent_id=p1.id, is_primary=True))

    # Org 2 (for cross-tenant tests)
    org2 = Organization(name=f"Org2 {uuid4().hex[:6]}", currency_code="USD")
    db.add(org2)
    db.flush()
    org2_user = User(email=f"org2-{uuid4().hex}@example.com", display_name="Org2 Owner", password_hash=hash_password("pw"))
    db.add(org2_user)
    db.flush()
    db.add(OrganizationMember(organization_id=org2.id, user_id=org2_user.id, role="OWNER"))

    db.commit()

    teacher_token = create_access_token(user_id=str(teacher_user.id), organization_id=str(org1.id), role="TEACHER")
    parent_token = create_access_token(user_id=str(p1_user.id), organization_id=str(org1.id), role="PARENT")
    student1_token = create_access_token(user_id=str(s1_user.id), organization_id=str(org1.id), role="STUDENT")
    org2_token = create_access_token(user_id=str(org2_user.id), organization_id=str(org2.id), role="OWNER")

    t_headers = {"Authorization": f"Bearer {teacher_token}"}
    p_headers = {"Authorization": f"Bearer {parent_token}"}
    s_headers = {"Authorization": f"Bearer {student1_token}"}
    org2_headers = {"Authorization": f"Bearer {org2_token}"}

    # 1. Scoped Teacher Access
    # Teacher can record attendance for assigned Class 1
    res_t_assigned = c.post("/api/v1/attendance/sessions", json={
        "class_id": str(cls1.id),
        "session_date": "2026-09-30",
        "records": []
    }, headers=t_headers)
    assert res_t_assigned.status_code == 201

    # Teacher CANNOT record attendance for unassigned Class 2 -> 403
    res_t_unassigned = c.post("/api/v1/attendance/sessions", json={
        "class_id": str(cls2.id),
        "session_date": "2026-09-30",
        "records": []
    }, headers=t_headers)
    assert res_t_unassigned.status_code == 403

    # Teacher CANNOT access fees -> 403
    res_t_fee = c.post("/api/v1/fees", json={
        "student_id": str(s1.id),
        "billing_period": "2026-09",
        "amount": 100.0,
        "due_date": "2026-10-05"
    }, headers=t_headers)
    assert res_t_fee.status_code == 403

    # 2. Scoped Parent Access
    # Parent can view linked child s1
    res_p_linked = c.get(f"/api/v1/students/{s1.id}", headers=p_headers)
    assert res_p_linked.status_code == 200

    # Parent CANNOT view unlinked child s2 -> 404
    res_p_unlinked = c.get(f"/api/v1/students/{s2.id}", headers=p_headers)
    assert res_p_unlinked.status_code == 404

    # 3. Scoped Student Access
    # Student can view self
    res_s_self = c.get(f"/api/v1/students/{s1.id}", headers=s_headers)
    assert res_s_self.status_code == 200

    # Student CANNOT view another student s2 -> 404
    res_s_other = c.get(f"/api/v1/students/{s2.id}", headers=s_headers)
    assert res_s_other.status_code == 404

    # 4. Cross-tenant Isolation
    # Org 2 owner cannot view Org 1 student -> 404
    res_cross = c.get(f"/api/v1/students/{s1.id}", headers=org2_headers)
    assert res_cross.status_code == 404

    db.close()


def test_i10_subscription_plans_requires_auth(client: TestClient = None):
    c = client or TestClient(app)

    # 1. Unauthenticated request -> 401
    res_unauth = c.get("/api/v1/subscription/plans")
    assert res_unauth.status_code == 401, f"Expected 401, got {res_unauth.status_code}"

    # Register an owner
    email = f"i10-{uuid4().hex}@example.com"
    reg = c.post("/api/v1/auth/register", json={
        "organization_name": "I10 Plans Org",
        "email": email,
        "password": "Password123!",
        "display_name": "I10 Owner",
    })
    assert reg.status_code == 201
    owner_token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {owner_token}"}

    # 2. Authenticated owner request -> 200
    res_auth = c.get("/api/v1/subscription/plans", headers=headers)
    assert res_auth.status_code == 200
    assert isinstance(res_auth.json(), list)


def test_i6_multi_org_login_refresh_and_switch(client: TestClient = None):
    from uuid import uuid4
    from app.db import SessionLocal
    from app.models import User, Organization, OrganizationMember
    from app.core.security import hash_password

    c = client or TestClient(app)
    db = SessionLocal()

    # User belongs to Org A and Org B
    email = f"i6-{uuid4().hex}@example.com"
    user = User(email=email, password_hash=hash_password("Password123!"), display_name="Multi User")
    org_a = Organization(name="Centre Alpha", currency_code="USD")
    org_b = Organization(name="Centre Beta", currency_code="USD")
    org_c = Organization(name="Centre Gamma (Unrelated)", currency_code="USD")
    db.add_all([user, org_a, org_b, org_c])
    db.flush()

    db.add(OrganizationMember(user_id=user.id, organization_id=org_a.id, role="OWNER"))
    db.add(OrganizationMember(user_id=user.id, organization_id=org_b.id, role="TEACHER"))
    db.commit()
    db.close()

    # 1. Login without organization_id -> returns organizations list and no tokens
    res_no_org = c.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    assert res_no_org.status_code == 200
    data_no_org = res_no_org.json()
    assert data_no_org["access_token"] is None
    assert data_no_org["refresh_token"] is None
    assert len(data_no_org["organizations"]) == 2
    org_names = {o["name"] for o in data_no_org["organizations"]}
    assert org_names == {"Centre Alpha", "Centre Beta"}

    # 2. Login with organization_id = org_a.id -> returns tokens for org_a
    res_a = c.post("/api/v1/auth/login", json={"email": email, "password": "Password123!", "organization_id": str(org_a.id)})
    assert res_a.status_code == 200
    data_a = res_a.json()
    assert data_a["access_token"] is not None
    assert data_a["refresh_token"] is not None

    me_a = c.get("/api/v1/me", headers={"Authorization": f"Bearer {data_a['access_token']}"})
    assert me_a.status_code == 200
    assert me_a.json()["organization_id"] == str(org_a.id)
    assert me_a.json()["role"] == "OWNER"

    # 3. Refresh token for org_a retains org_a
    res_ref = c.post("/api/v1/auth/refresh", json={"refresh_token": data_a["refresh_token"]})
    assert res_ref.status_code == 200
    data_ref = res_ref.json()
    me_ref = c.get("/api/v1/me", headers={"Authorization": f"Bearer {data_ref['access_token']}"})
    assert me_ref.status_code == 200
    assert me_ref.json()["organization_id"] == str(org_a.id)

    # 4. Switch to org_b
    res_switch = c.post("/api/v1/auth/switch-organization", json={
        "organization_id": str(org_b.id),
        "refresh_token": data_ref["refresh_token"]
    }, headers={"Authorization": f"Bearer {data_ref['access_token']}"})
    assert res_switch.status_code == 200
    data_b = res_switch.json()
    assert data_b["access_token"] is not None

    me_b = c.get("/api/v1/me", headers={"Authorization": f"Bearer {data_b['access_token']}"})
    assert me_b.status_code == 200
    assert me_b.json()["organization_id"] == str(org_b.id)
    assert me_b.json()["role"] == "TEACHER"

    # 5. Attempt switch to org_c (user is NOT a member) -> 403 Forbidden
    res_bad_switch = c.post("/api/v1/auth/switch-organization", json={
        "organization_id": str(org_c.id)
    }, headers={"Authorization": f"Bearer {data_b['access_token']}"})
    assert res_bad_switch.status_code == 403


def test_i12_secret_safeguards():
    import pytest
    from app.core.config import Settings, DEFAULT_JWT_SECRET

    # 1. In development, default secret is accepted
    dev_settings = Settings(environment="development", jwt_secret=DEFAULT_JWT_SECRET)
    assert dev_settings.environment == "development"

    # 2. In production with default secret, Settings raises ValueError
    with pytest.raises(ValueError, match="JWT_SECRET must be set to a secure"):
        Settings(environment="production", jwt_secret=DEFAULT_JWT_SECRET)

    # 3. In production with secure secret, Settings succeeds
    prod_settings = Settings(environment="production", jwt_secret="super-secure-production-secret-12345")
    assert prod_settings.jwt_secret == "super-secure-production-secret-12345"


def test_i13_timezone_handling_around_midnight(client: TestClient = None):
    from datetime import datetime, timezone as dt_timezone
    from unittest.mock import patch
    from uuid import uuid4
    from zoneinfo import ZoneInfo
    from app.core.timezone import get_org_now, get_org_today, get_org_timezone
    from app.db import SessionLocal
    from app.models import ClassGroup, Organization, OrganizationMember, ScheduleEntry, User
    from app.core.security import create_access_token, hash_password

    c = client or TestClient(app)
    db = SessionLocal()

    # 1. Organization defaults to Asia/Kolkata
    org_kolkata = Organization(
        name=f"Kolkata Center {uuid4().hex[:6]}",
        timezone="Asia/Kolkata",
        currency_code="INR",
    )
    db.add(org_kolkata)
    db.flush()

    user = User(
        email=f"owner-tz-{uuid4().hex}@example.com",
        display_name="Tz Owner",
        password_hash=hash_password("Password123!"),
    )
    db.add(user)
    db.flush()

    member = OrganizationMember(organization_id=org_kolkata.id, user_id=user.id, role="OWNER")
    db.add(member)
    db.flush()

    token = create_access_token(user_id=str(user.id), organization_id=str(org_kolkata.id), role="OWNER")

    # Class and Schedules:
    # 2026-09-30 was Wednesday (weekday 2)
    # 2026-10-01 was Thursday (weekday 3)
    cls = ClassGroup(organization_id=org_kolkata.id, name="Maths Batch")
    db.add(cls)
    db.flush()

    # Schedule for Wednesday (weekday 2)
    sched_wed = ScheduleEntry(
        organization_id=org_kolkata.id,
        class_id=cls.id,
        day_of_week=2,
        start_time="20:30",
        end_time="21:30",
    )
    # Schedule for Thursday (weekday 3) at 02:00
    sched_thu = ScheduleEntry(
        organization_id=org_kolkata.id,
        class_id=cls.id,
        day_of_week=3,
        start_time="02:00",
        end_time="03:00",
    )
    db.add_all([sched_wed, sched_thu])
    db.commit()

    # Freeze time at 2026-09-30 20:00:00 UTC
    # In Asia/Kolkata (+5:30), this is 2026-10-01 01:30:00 (Thursday)
    frozen_utc = datetime(2026, 9, 30, 20, 0, 0, tzinfo=dt_timezone.utc)

    class MockDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is not None:
                return frozen_utc.astimezone(tz)
            return frozen_utc.astimezone(ZoneInfo("Asia/Kolkata"))

    with patch("app.core.timezone.datetime", MockDatetime), \
         patch("app.api.workflows.datetime", MockDatetime):
        today_kolkata = get_org_today(org_kolkata)
        assert today_kolkata.day == 1
        assert today_kolkata.month == 10
        assert today_kolkata.year == 2026

        now_kolkata = get_org_now(org_kolkata)
        assert now_kolkata.strftime("%H:%M") == "01:30"

        # Check dashboard computes today and next class based on Asia/Kolkata
        res = c.get("/api/v1/dashboard", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        data = res.json()
        assert data["timezone"] == "Asia/Kolkata"
        # Since it is Thursday (weekday 3) in Kolkata, classes_today must be 1 (the Thursday class)
        assert data["classes_today"] == 1
        assert data["next_class"] is not None
        assert data["next_class"]["start_time"] == "02:00"

    # Also test America/New_York (UTC-4) at 2026-10-01 02:00:00 UTC
    # In New York, this is 2026-09-30 22:00:00 (Wednesday)
    org_ny = Organization(name="NY Center", timezone="America/New_York")
    frozen_utc_ny = datetime(2026, 10, 1, 2, 0, 0, tzinfo=dt_timezone.utc)

    class MockDatetimeNY(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is not None:
                return frozen_utc_ny.astimezone(tz)
            return frozen_utc_ny.astimezone(ZoneInfo("America/New_York"))

    with patch("app.core.timezone.datetime", MockDatetimeNY):
        today_ny = get_org_today(org_ny)
        assert today_ny.day == 30
        assert today_ny.month == 9

    # Update timezone via PATCH /settings
    patch_res = c.patch(
        "/api/v1/settings",
        json={"timezone": "Asia/Dubai"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["timezone"] == "Asia/Dubai"
    db.close()


def test_i14_organization_currency_settings(client: TestClient = None):
    from uuid import uuid4
    from app.db import SessionLocal
    from app.models import Organization, OrganizationMember, User
    from app.core.security import create_access_token, hash_password

    c = client or TestClient(app)
    db = SessionLocal()

    org = Organization(name=f"Currency Org {uuid4().hex[:6]}", currency_code="INR")
    db.add(org)
    db.flush()

    assert org.currency == "INR"

    user = User(
        email=f"owner-curr-{uuid4().hex}@example.com",
        display_name="Currency Owner",
        password_hash=hash_password("Password123!"),
    )
    db.add(user)
    db.flush()

    member = OrganizationMember(organization_id=org.id, user_id=user.id, role="OWNER")
    db.add(member)
    db.commit()

    token = create_access_token(user_id=str(user.id), organization_id=str(org.id), role="OWNER")

    # 1. Update currency via PATCH /settings with currency_code
    res1 = c.patch(
        "/api/v1/settings",
        json={"currency_code": "USD"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res1.status_code == 200
    assert res1.json()["currency_code"] == "USD"

    # 2. Update currency via PATCH /settings with currency alias
    res2 = c.patch(
        "/api/v1/settings",
        json={"currency": "EUR"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res2.status_code == 200
    assert res2.json()["currency_code"] == "EUR"

    # 3. GET /dashboard returns currency and currency_code
    dash_res = c.get("/api/v1/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert dash_res.status_code == 200
    assert dash_res.json()["currency"] == "EUR"
    assert dash_res.json()["currency_code"] == "EUR"

    db.close()










