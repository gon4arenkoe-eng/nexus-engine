"""Auth tests."""
import pytest
from app import create_app


@pytest.fixture
def app():
    """Create test app."""
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


def test_register_success(client):
    """Test successful registration."""
    response = client.post("/api/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "securepassword123",
    })
    assert response.status_code == 201


def test_register_duplicate(client):
    """Test duplicate username rejection."""
    client.post("/api/auth/register", json={
        "username": "testuser",
        "email": "test1@example.com",
        "password": "securepassword123",
    })
    response = client.post("/api/auth/register", json={
        "username": "testuser",
        "email": "test2@example.com",
        "password": "securepassword123",
    })
    assert response.status_code == 409


def test_login_success(client):
    """Test successful login with cookies."""
    client.post("/api/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "securepassword123",
    })
    response = client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "securepassword123",
    })
    assert response.status_code == 200
    set_cookie_headers = response.headers.getlist("Set-Cookie")
    assert any("access_token" in h for h in set_cookie_headers)


def test_login_invalid(client):
    """Test login with wrong password."""
    response = client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "wrongpassword",
    })
    assert response.status_code == 401


def test_protected_without_auth(client):
    """Test accessing protected route without login."""
    response = client.get("/api/trading/positions")
    assert response.status_code == 401
