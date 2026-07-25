"""Phase 9 — Authentication Tests"""

from tests.conftest import auth_header, CUSTOMER_DATA, ADMIN_DATA


class TestRegistration:
    def test_register_customer(self, client):
        data = {
            "full_name": "New User",
            "email": "newuser@test.com",
            "phone": "9100000001",
            "password": "Secure123!",
            "role": "Customer",
        }
        res = client.post("/api/auth/register", json=data)
        assert res.status_code == 201
        body = res.json()
        assert body["email"] == "newuser@test.com"
        assert body["role"] == "Customer"
        assert "password" not in body
        assert "password_hash" not in body

    def test_register_duplicate_email(self, client):
        data = {
            "full_name": "Dup User",
            "email": "dup@test.com",
            "phone": "9100000010",
            "password": "Secure123!",
            "role": "Customer",
        }
        client.post("/api/auth/register", json=data)
        res = client.post("/api/auth/register", json=data)
        assert res.status_code == 400
        assert "already exists" in res.json()["detail"]

    def test_register_missing_fields(self, client):
        res = client.post("/api/auth/register", json={"email": "x@x.com"})
        assert res.status_code == 422  # Pydantic validation error


class TestLogin:
    def test_login_success(self, client, customer_token):
        assert customer_token is not None
        assert len(customer_token) > 10

    def test_login_wrong_password(self, client):
        # Ensure user exists
        client.post("/api/auth/register", json=CUSTOMER_DATA)
        res = client.post("/api/auth/login", json={
            "email": CUSTOMER_DATA["email"],
            "password": "WrongPassword!",
            "role": "Customer",
        })
        assert res.status_code == 400

    def test_login_nonexistent_user(self, client):
        res = client.post("/api/auth/login", json={
            "email": "nobody@test.com",
            "password": "whatever",
            "role": "Customer",
        })
        assert res.status_code == 400


class TestProfile:
    def test_get_profile(self, client, customer_token):
        res = client.get("/api/auth/profile", headers=auth_header(customer_token))
        assert res.status_code == 200
        assert res.json()["email"] == CUSTOMER_DATA["email"]

    def test_profile_no_token(self, client):
        res = client.get("/api/auth/profile")
        assert res.status_code in [401, 403]


class TestHealthCheck:
    def test_health(self, client):
        res = client.get("/api/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"
