import io
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def get_authenticated_user(label: str):
    email = f"{label}-{uuid4().hex[:8]}@example.com"
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "validPassword123!",
            "display_name": f"{label} Admin",
            "organization_name": f"{label} Centre",
        },
    )
    assert reg_res.status_code == 201, reg_res.text
    tokens = reg_res.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    return email, tokens, headers


class TestAuthLifecycle:
    def test_registration_validation(self):
        # Short password
        res = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "short",
                "display_name": "Test",
                "organization_name": "Test Org",
            },
        )
        assert res.status_code == 422

        # Invalid email
        res = client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "validPassword123!",
                "display_name": "Test",
                "organization_name": "Test Org",
            },
        )
        assert res.status_code == 422

    def test_duplicate_registration_conflict(self):
        email = f"dup-{uuid4().hex[:8]}@example.com"
        payload = {
            "email": email,
            "password": "validPassword123!",
            "display_name": "Duplicate User",
            "organization_name": "Duplicate Centre",
        }
        res1 = client.post("/api/v1/auth/register", json=payload)
        assert res1.status_code == 201

        res2 = client.post("/api/v1/auth/register", json=payload)
        assert res2.status_code == 409
        body = res2.json()
        assert body["error"]["code"] == "EMAIL_ALREADY_REGISTERED"

    def test_login_success_and_failure(self):
        email, _, _ = get_authenticated_user("login-test")

        # Success
        login_res = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "validPassword123!"},
        )
        assert login_res.status_code == 200
        assert "access_token" in login_res.json()
        assert "refresh_token" in login_res.json()

        # Wrong password
        bad_pw = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "wrongPassword123!"},
        )
        assert bad_pw.status_code == 401
        assert bad_pw.json()["error"]["code"] == "INVALID_CREDENTIALS"

        # Nonexistent email
        no_user = client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "password123"},
        )
        assert no_user.status_code == 401

    def test_me_endpoint_security(self):
        email, _, headers = get_authenticated_user("me-test")
        res = client.get("/api/v1/me", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["email"] == email
        assert data["role"] == "OWNER"

        # No auth header
        unauth = client.get("/api/v1/me")
        assert unauth.status_code == 401

        # Bad token
        bad_token = client.get("/api/v1/me", headers={"Authorization": "Bearer not-a-token"})
        assert bad_token.status_code == 401

    def test_refresh_and_logout(self):
        _, tokens, _ = get_authenticated_user("refresh-logout")
        refresh_token = tokens["refresh_token"]

        # Valid refresh
        ref_res = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert ref_res.status_code == 200
        new_refresh = ref_res.json()["refresh_token"]
        assert new_refresh != refresh_token

        # Old refresh is revoked
        revoked_res = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert revoked_res.status_code == 401

        # Logout revokes the new refresh token
        logout_res = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": new_refresh},
        )
        assert logout_res.status_code == 204

        after_logout = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": new_refresh},
        )
        assert after_logout.status_code == 401


class TestAcademicAndFinancialWorkflows:
    def test_complete_student_parent_class_fee_workflow(self):
        _, _, headers = get_authenticated_user("full-flow")

        # 1. Create Student
        student_payload = {
            "student_number": f"STU-{uuid4().hex[:6].upper()}",
            "first_name": "Aarav",
            "last_name": "Sharma",
            "school": "St. Xavier's",
            "grade": "10",
        }
        stu_res = client.post("/api/v1/students", headers=headers, json=student_payload)
        assert stu_res.status_code == 201
        student = stu_res.json()
        student_id = student["id"]

        # 2. Update Student
        update_res = client.patch(
            f"/api/v1/students/{student_id}",
            headers=headers,
            json={
                "student_number": student["student_number"],
                "first_name": "Aarav",
                "last_name": "Kumar",
                "notes": "Top student",
            },
        )
        assert update_res.status_code == 200
        assert update_res.json()["last_name"] == "Kumar"

        # 3. Create Parent & Link
        parent_payload = {
            "name": "Ramesh Kumar",
            "phone": "+919876543210",
            "email": "ramesh@example.com",
            "relationship": "Father",
        }
        par_res = client.post("/api/v1/parents", headers=headers, json=parent_payload)
        assert par_res.status_code == 201
        parent_id = par_res.json()["id"]

        link_res = client.post(
            f"/api/v1/students/{student_id}/parents",
            headers=headers,
            json={"parent_id": parent_id, "is_primary": True},
        )
        assert link_res.status_code == 201

        # Check parent's linked students
        linked = client.get(f"/api/v1/parents/{parent_id}/students", headers=headers)
        assert linked.status_code == 200
        assert len(linked.json()) == 1

        # 4. Create Class & Enroll
        class_res = client.post(
            "/api/v1/classes",
            headers=headers,
            json={"name": "Grade 10 Mathematics", "subject": "Math", "fee_amount": 2500},
        )
        assert class_res.status_code == 201
        class_id = class_res.json()["id"]

        enroll_res = client.post(
            f"/api/v1/classes/{class_id}/students",
            headers=headers,
            json={"record_id": student_id},
        )
        assert enroll_res.status_code == 201

        # 5. Record Attendance Session
        att_res = client.post(
            "/api/v1/attendance/sessions",
            headers=headers,
            json={
                "class_id": class_id,
                "session_date": "2026-09-26",
                "records": [{"student_id": student_id, "status": "PRESENT"}],
            },
        )
        assert att_res.status_code == 201

        # 6. Add Homework
        hw_res = client.post(
            "/api/v1/homework",
            headers=headers,
            json={
                "class_id": class_id,
                "title": "Trigonometry Chapter 4 Exercises",
                "due_date": "2026-10-01",
            },
        )
        assert hw_res.status_code == 201

        # 7. Add Test & Record Marks
        test_res = client.post(
            "/api/v1/tests",
            headers=headers,
            json={
                "class_id": class_id,
                "name": "Mid-term Assessment",
                "test_date": "2026-09-25",
                "maximum_marks": "100",
            },
        )
        assert test_res.status_code == 201
        test_id = test_res.json()["id"]

        marks_res = client.post(
            f"/api/v1/tests/{test_id}/marks",
            headers=headers,
            json={"student_id": student_id, "marks": "92", "grade": "A+"},
        )
        assert marks_res.status_code == 201

        # 8. Create Timetable Schedule
        sched_res = client.post(
            "/api/v1/schedule",
            headers=headers,
            json={
                "class_id": class_id,
                "day_of_week": 1,
                "start_time": "16:00",
                "end_time": "17:30",
                "room": "Room 101",
            },
        )
        assert sched_res.status_code == 201

        # 9. Generate Monthly Fee
        fee_gen_res = client.post(
            "/api/v1/fees/generate",
            headers=headers,
            json={"billing_period": "2026-09", "amount": "2500", "due_date": "2026-09-30"},
        )
        assert fee_gen_res.status_code == 200
        assert fee_gen_res.json()["created"] >= 1

        # Idempotency check: Generating again creates 0 duplicates
        fee_gen_again = client.post(
            "/api/v1/fees/generate",
            headers=headers,
            json={"billing_period": "2026-09", "amount": "2500", "due_date": "2026-09-30"},
        )
        assert fee_gen_again.status_code == 200
        assert fee_gen_again.json()["created"] == 0

        # Retrieve generated fee
        fees_res = client.get("/api/v1/fees", headers=headers)
        assert fees_res.status_code == 200
        fee = next(f for f in fees_res.json() if f["student_id"] == student_id)
        assert fee["status"] == "PENDING"
        assert fee["amount"] == 2500

        # 10. Record Partial Payment (1000)
        pay1_res = client.post(
            "/api/v1/payments",
            headers=headers,
            json={"fee_id": fee["id"], "amount": "1000", "payment_method": "CASH"},
        )
        assert pay1_res.status_code == 201
        assert pay1_res.json()["fee_status"] == "PARTIAL"

        # 11. Record Remainder Payment (1500)
        pay2_res = client.post(
            "/api/v1/payments",
            headers=headers,
            json={"fee_id": fee["id"], "amount": "1500", "payment_method": "BANK_TRANSFER"},
        )
        assert pay2_res.status_code == 201
        pay2_data = pay2_res.json()
        assert pay2_data["fee_status"] == "PAID"
        receipt = pay2_data["receipt"]
        assert receipt["receipt_number"].startswith("TUIRO-")

        # 12. Download PDF Receipt
        pdf_res = client.get(f"/api/v1/receipts/{receipt['id']}/pdf", headers=headers)
        assert pdf_res.status_code == 200
        assert pdf_res.headers["content-type"] == "application/pdf"
        assert pdf_res.content.startswith(b"%PDF")

        # 13. Dashboard Verification
        dash_res = client.get("/api/v1/dashboard", headers=headers)
        assert dash_res.status_code == 200
        dash = dash_res.json()
        assert dash["students"] >= 1
