from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app


def test_corporate_people_crud_and_shared_metadata():
    client = TestClient(app)
    auth = client.post("/api/v1/auth/register", json={"email": f"people-{uuid4().hex}@example.com", "password": "SafePass123!", "display_name": "Admin", "organization_name": "Acme"})
    headers = {"Authorization": f"Bearer {auth.json()['access_token']}"}
    department = client.post("/api/v2/people/departments", headers=headers, json={"name": "Engineering"}); assert department.status_code == 201
    title = client.post("/api/v2/people/job-titles", headers=headers, json={"name": "Developer"}); assert title.status_code == 201
    employee = client.post("/api/v2/people/employees", headers=headers, json={"employee_number": "E-001", "first_name": "Asha", "department_id": department.json()["id"], "job_title_id": title.json()["id"]}); assert employee.status_code == 201
    employee_id = employee.json()["id"]
    assert client.patch(f"/api/v2/people/employees/{employee_id}", headers=headers, json={"phone": "+91999"}).json()["phone"] == "+91999"
    assert client.post(f"/api/v2/people/employee/{employee_id}/custom-fields", headers=headers, json={"values": {"cost_center": "R&D"}}).status_code == 200
    assert client.get(f"/api/v2/people/employee/{employee_id}/custom-fields", headers=headers).json()["values"]["cost_center"] == "R&D"
    assert client.post(f"/api/v2/people/employee/{employee_id}/documents", headers=headers, json={"name": "Offer", "storage_key": "dev/offer.pdf"}).status_code == 201
