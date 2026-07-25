"""
Phase 9 — Test Configuration & Fixtures

Sets up an isolated in-memory SQLite database for each test session and
provides reusable fixtures for the FastAPI test client, sample users,
and auth tokens.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.api.deps import get_db
from app.main import app
from app.core.security import get_password_hash

# ── In-memory SQLite for tests ──────────────────────────────────────
SQLALCHEMY_TEST_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    """Create tables once at the start, drop at the end."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    """Provide a clean DB session for each test."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client():
    """FastAPI TestClient."""
    return TestClient(app)


# ── User fixtures ───────────────────────────────────────────────────

CUSTOMER_DATA = {
    "full_name": "Test Customer",
    "email": "customer@test.com",
    "phone": "9000000001",
    "password": "TestPass123!",
    "role": "Customer",
}

DRIVER_DATA = {
    "full_name": "Test Driver",
    "email": "driver@test.com",
    "phone": "9000000002",
    "password": "TestPass123!",
    "role": "Driver",
}

ADMIN_DATA = {
    "full_name": "Test Admin",
    "email": "admin@test.com",
    "phone": "9000000003",
    "password": "TestPass123!",
    "role": "Admin",
}


def _register_and_login(client, data):
    """Helper: register a user and return the auth token."""
    client.post("/api/auth/register", json=data)
    res = client.post("/api/auth/login", json={
        "email": data["email"],
        "password": data["password"],
        "role": data["role"],
    })
    return res.json()["access_token"]


@pytest.fixture()
def customer_token(client):
    return _register_and_login(client, CUSTOMER_DATA)


@pytest.fixture()
def driver_token(client):
    return _register_and_login(client, DRIVER_DATA)


@pytest.fixture()
def admin_token(client, db):
    # Admins cannot be registered via API. Create directly in DB.
    from app.db.models import User
    admin = db.query(User).filter(User.email == ADMIN_DATA["email"]).first()
    if not admin:
        admin = User(
            full_name=ADMIN_DATA["full_name"],
            email=ADMIN_DATA["email"],
            phone=ADMIN_DATA["phone"],
            password_hash=get_password_hash(ADMIN_DATA["password"]),
            role="Admin"
        )
        db.add(admin)
        db.commit()
    
    res = client.post("/api/auth/login", json={
        "email": ADMIN_DATA["email"],
        "password": ADMIN_DATA["password"],
        "role": ADMIN_DATA["role"],
    })
    return res.json()["access_token"]


def auth_header(token):
    """Build Authorization header dict."""
    return {"Authorization": f"Bearer {token}"}
