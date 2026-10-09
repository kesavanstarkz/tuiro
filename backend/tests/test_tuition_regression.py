"""End-to-end regression suite for Tuiro tuition centre workflows.

Covers the complete lifecycle:
- Create Class
- Add/Enroll Students
- Link Parents
- Mark Attendance
- Create Homework
- Create Tests & Record Marks
- Create Schedule Entry
- Generate Fees
- Process Payments & Issue Sequential Receipts
- Generate Receipt PDF
- Retrieve Dashboard & Verify Aggregated KPIs
- Verify Multi-Tenant Scoping (cross-tenant 404)

Must stay green across all subsequent migration phases.
"""
from __future__ import annotations

import io
from datetime import date, timedelta
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def create_tuition_tenant(name_prefix: str = "reg-tuition"):
    email = f"{name_prefix}-{uuid4().hex[:8]}@example.com"
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "RegressionPass123!",
            "display_name": f"{name_prefix.title()} Director",
            "organization_name": f"{name_prefix.title()} Academy",
        },
    )
    assert res.status_code == 201, f"Registration failed: {res.text}"
    data = res.json()
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    return email, data, headers


class TestTuitionEndToEndRegression:
    def test_complete_tuition_lifecycle_and_regression(self):
        # 1. Register Primary Organization
        _, auth_data, headers = create_tuition_tenant("apex")

        # 2. Create Class
        class_res = client.post(
            "/api/v1/classes",
            headers=headers,
            json={
                "name": "Grade 10 Physics",
                "subject": "Physics",
                "fee_amount": 3500.0,
                "status": "ACTIVE",
            },
        )
        assert class_res.status_code == 201
        cls = class_res.json()
        class_id = cls["id"]
        assert cls["name"] == "Grade 10 Physics"

        # 3. Create Student
        student_res = client.post(
            "/api/v1/students",
            headers=headers,
            json={
                "student_number": f"REG-{uuid4().hex[:6].upper()}",
                "first_name": "Rohan",
                "last_name": "Verma",
                "grade": "10",
                "school": "Delhi Public School",
            },
        )
        assert student_res.status_code == 201
        student = student_res.json()
        student_id = student["id"]

        # 4. Enroll Student in Class
        enroll_res = client.post(
            f"/api/v1/classes/{class_id}/students",
            headers=headers,
            json={"record_id": student_id},
        )
        assert enroll_res.status_code == 201

        # Verify class roster
        roster_res = client.get(f"/api/v1/classes/{class_id}/students", headers=headers)
        assert roster_res.status_code == 200
        assert len(roster_res.json()) >= 1

        # 5. Create Parent and Link
        parent_res = client.post(
            "/api/v1/parents",
            headers=headers,
            json={
                "name": "Sunil Verma",
                "phone": "+919876543999",
                "email": "sunil.verma@example.com",
                "relationship": "Father",
            },
        )
        assert parent_res.status_code == 201
        parent_id = parent_res.json()["id"]

        link_res = client.post(
            f"/api/v1/students/{student_id}/parents",
            headers=headers,
            json={"parent_id": parent_id, "is_primary": True},
        )
        assert link_res.status_code == 201

        # 6. Mark Attendance Session
        today_str = date.today().isoformat()
        att_res = client.post(
            "/api/v1/attendance/sessions",
            headers=headers,
            json={
                "class_id": class_id,
                "session_date": today_str,
                "records": [{"student_id": student_id, "status": "PRESENT"}],
            },
        )
        assert att_res.status_code == 201
        att_data = att_res.json()
        assert att_data["class_id"] == class_id

        # 7. Add Homework
        due_hw = (date.today() + timedelta(days=7)).isoformat()
        hw_res = client.post(
            "/api/v1/homework",
            headers=headers,
            json={
                "class_id": class_id,
                "title": "Electromagnetism Practice Set",
                "description": "Complete questions 1 to 20 from Chapter 6",
                "due_date": due_hw,
            },
        )
        assert hw_res.status_code == 201
        hw_id = hw_res.json()["id"]

        # Verify homework detail
        hw_get = client.get(f"/api/v1/homework/{hw_id}", headers=headers)
        assert hw_get.status_code == 200
        assert hw_get.json()["title"] == "Electromagnetism Practice Set"

        # 8. Create Academic Test & Record Marks
        test_date = (date.today() - timedelta(days=2)).isoformat()
        test_res = client.post(
            "/api/v1/tests",
            headers=headers,
            json={
                "class_id": class_id,
                "name": "Unit Test 1: Optics & Mechanics",
                "test_date": test_date,
                "maximum_marks": 50.0,
            },
        )
        assert test_res.status_code == 201
        test_id = test_res.json()["id"]

        marks_res = client.post(
            f"/api/v1/tests/{test_id}/marks",
            headers=headers,
            json={"student_id": student_id, "marks": 45.0, "grade": "A+"},
        )
        assert marks_res.status_code == 201

        # Verify report card
        rc_res = client.get(f"/api/v1/reports/students/{student_id}/report-card", headers=headers)
        assert rc_res.status_code == 200
        rc = rc_res.json()
        assert rc["student"]["id"] == student_id
        assert rc["summary"]["overall_percentage"] == 90.0

        # 9. Create Schedule Timetable Entry
        sched_res = client.post(
            "/api/v1/schedule",
            headers=headers,
            json={
                "class_id": class_id,
                "day_of_week": 1,
                "start_time": "17:00",
                "end_time": "18:30",
                "room": "Lab 2",
            },
        )
        assert sched_res.status_code == 201
        assert sched_res.json()["room"] == "Lab 2"

        # 10. Generate Fee & Validate Idempotency
        due_fee = (date.today() + timedelta(days=15)).isoformat()
        bp = f"2026-REG-{uuid4().hex[:4]}"
        fee_gen = client.post(
            "/api/v1/fees/generate",
            headers=headers,
            json={"billing_period": bp, "amount": 3500.0, "due_date": due_fee},
        )
        assert fee_gen.status_code == 200
        assert fee_gen.json()["created"] >= 1

        # Duplicate generate must be idempotent (0 created)
        fee_gen_dup = client.post(
            "/api/v1/fees/generate",
            headers=headers,
            json={"billing_period": bp, "amount": 3500.0, "due_date": due_fee},
        )
        assert fee_gen_dup.status_code == 200
        assert fee_gen_dup.json()["created"] == 0

        # Fetch fee
        fees_res = client.get(f"/api/v1/fees?student_id={student_id}", headers=headers)
        assert fees_res.status_code == 200
        fee_items = [f for f in fees_res.json() if f["billing_period"] == bp]
        assert len(fee_items) == 1
        fee_record = fee_items[0]
        fee_id = fee_record["id"]
        assert fee_record["status"] == "PENDING"
        assert fee_record["amount"] == 3500.0

        # 11. Partial Payment (1500)
        p1 = client.post(
            "/api/v1/payments",
            headers=headers,
            json={"fee_id": fee_id, "amount": 1500.0, "payment_method": "CASH"},
        )
        assert p1.status_code == 201
        p1_data = p1.json()
        assert p1_data["fee_status"] == "PARTIAL"

        # 12. Complete Remainder Payment (2000)
        p2 = client.post(
            "/api/v1/payments",
            headers=headers,
            json={"fee_id": fee_id, "amount": 2000.0, "payment_method": "UPI"},
        )
        assert p2.status_code == 201
        p2_data = p2.json()
        assert p2_data["fee_status"] == "PAID"
        receipt = p2_data["receipt"]
        assert receipt["receipt_number"].startswith("TUIRO-")
        receipt_id = receipt["id"]

        # 13. Download / Stream PDF Receipt
        receipt_pdf = client.get(f"/api/v1/receipts/{receipt_id}/pdf", headers=headers)
        assert receipt_pdf.status_code == 200
        assert receipt_pdf.headers["content-type"] == "application/pdf"
        assert receipt_pdf.content.startswith(b"%PDF")

        # 14. Verify Dashboard Aggregations
        dash_res = client.get("/api/v1/dashboard", headers=headers)
        assert dash_res.status_code == 200
        dash = dash_res.json()
        assert dash["students"] >= 1
        assert dash["active_classes"] >= 1
        assert float(dash["todays_collections"]) >= 3500.0

        # 15. Cross-Tenant Isolation: A second tenant must receive 404
        _, _, headers_other = create_tuition_tenant("other-tenant")
        assert client.get(f"/api/v1/classes/{class_id}", headers=headers_other).status_code == 404
        assert client.get(f"/api/v1/students/{student_id}", headers=headers_other).status_code == 404
        assert client.get(f"/api/v1/homework/{hw_id}", headers=headers_other).status_code == 404
        assert client.get(f"/api/v1/tests/{test_id}", headers=headers_other).status_code == 404
        assert client.get(f"/api/v1/fees/{fee_id}", headers=headers_other).status_code == 404
        assert client.get(f"/api/v1/receipts/{receipt_id}/pdf", headers=headers_other).status_code == 404
