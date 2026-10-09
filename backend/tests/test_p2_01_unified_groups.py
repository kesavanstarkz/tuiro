from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def register(client: TestClient):
    response = client.post("/api/v1/auth/register", json={
        "email": f"p2-group-{uuid4().hex}@example.com", "password": "SafePass123!",
        "display_name": "Platform Admin", "organization_name": "Northstar", "timezone": "UTC",
    })
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_v2_group_membership_preserves_history_and_legacy_projection():
    client = TestClient(app); headers = register(client)
    student = client.post("/api/v1/students", headers=headers, json={"student_number": f"P2-{uuid4().hex[:8]}", "first_name": "Mina"}).json()
    group = client.post("/api/v2/groups", headers=headers, json={"name": "Engineering", "kind": "team"})
    assert group.status_code == 201, group.text
    group_id = group.json()["id"]
    added = client.post(f"/api/v2/groups/{group_id}/members", headers=headers, json={"member_type": "student", "member_id": student["id"], "member_role": "coordinator"})
    assert added.status_code == 201, added.text
    assert client.get(f"/api/v2/groups/{group_id}/members", headers=headers).json()[0]["member_role"] == "coordinator"
    assert len(client.get(f"/api/v1/groups/{group_id}/members", headers=headers).json()) == 1
    assert client.delete(f"/api/v2/groups/{group_id}/members/{added.json()['id']}", headers=headers).status_code == 204
    assert client.get(f"/api/v2/groups/{group_id}/members", headers=headers).json() == []
    assert len(client.get(f"/api/v2/groups/{group_id}/members?include_removed=true", headers=headers).json()) == 1


def test_v2_group_is_tenant_scoped():
    client = TestClient(app); first = register(client); second = register(client)
    group = client.post("/api/v2/groups", headers=first, json={"name": "Private", "kind": "department"}).json()
    assert client.get(f"/api/v2/groups/{group['id']}", headers=second).status_code == 404
