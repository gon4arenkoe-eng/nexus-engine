"""Auth tests."""
import pytest
from app import create_app, db
from models import User

@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_register_success(client):
    response = client.post("/api/auth/register", json={
        "username": "testuser", "email": "test@example.com", "password": "securepassword123",
    })
    assert response.status_code == 201

def test_register_duplicate(client):
    client.post("/api/auth/register", json={
        "username": "testuser", "email": "test1@example.com", "password": "securepassword123",
    })
    response = client.post("/api/auth/register", json={
        "username": "testuser", "email": "test2@example.com", "password": "securepassword123",
    })
    assert response.status_code == 409

def test_login_success(client):
    client.post("/api/auth/register", json={
        "username": "testuser", "email": "test@example.com", "password": "securepassword123",
    })
    response = client.post("/api/auth/login", json={
        "username": "testuser", "password": "securepassword123",
    })
    assert response.status_code == 200
    assert "access_token" in [c.key for c in response.response.cookies]

def test_login_invalid(client):
    response = client.post("/api/auth/login", json={
        "username": "testuser", "password": "wrong",
    })
    assert response.status_code == 401

def test_protected_without_auth(client):
    response = client.get("/api/trading/positions")
    assert response.status_code == 401
