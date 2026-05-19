from datetime import timedelta

from backend.auth import routes as auth_routes
from backend.utils.config import settings
from backend.utils.security import create_access_token


def test_signup_and_login_json(client):
    signup = client.post(
        "/auth/signup",
        json={"email": "user1@example.com", "password": "Secret123"},
    )
    assert signup.status_code == 200
    assert signup.headers.get("x-request-id")
    assert signup.json()["email"] == "user1@example.com"

    login = client.post(
        "/auth/login",
        json={"email": "user1@example.com", "password": "Secret123"},
    )
    assert login.status_code == 200
    payload = login.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]


def test_register_alias(client):
    register = client.post(
        "/auth/register",
        json={"email": "alias@example.com", "password": "Secret123"},
    )
    assert register.status_code == 200
    assert register.json()["email"] == "alias@example.com"


def test_signup_rejects_weak_password(client):
    response = client.post(
        "/auth/signup",
        json={"email": "weak@example.com", "password": "weak"},
    )
    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["message"] == "Validation failed"
    assert payload["error"]["request_id"]
    assert isinstance(payload["detail"], list)
    assert "Password must be at least 8 characters long" in str(response.json())


def test_protected_route_rejects_invalid_token(client):
    signup = client.post(
        "/auth/signup",
        json={"email": "secure@example.com", "password": "Secret123"},
    )
    assert signup.status_code == 200

    response = client.get(
        "/resumes",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
    assert response.json()["detail"] == "Invalid token"


def test_protected_route_rejects_expired_token(client):
    signup = client.post(
        "/auth/signup",
        json={"email": "expired@example.com", "password": "Secret123"},
    )
    assert signup.status_code == 200
    user_id = signup.json()["id"]

    expired_token = create_access_token(str(user_id), expires_delta=timedelta(minutes=-5))
    response = client.get(
        "/resumes",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
    assert response.json()["detail"] == "Token expired"


def test_login_rate_limit_after_repeated_failures(client, monkeypatch):
    signup = client.post(
        "/auth/signup",
        json={"email": "ratelimit@example.com", "password": "Secret123"},
    )
    assert signup.status_code == 200

    monkeypatch.setattr(settings, "LOGIN_RATE_LIMIT_ATTEMPTS", 2)
    monkeypatch.setattr(settings, "LOGIN_RATE_LIMIT_WINDOW_SECONDS", 600)
    auth_routes._LOGIN_FAILURES.clear()

    first = client.post(
        "/auth/login",
        json={"email": "ratelimit@example.com", "password": "WrongPass1"},
    )
    second = client.post(
        "/auth/login",
        json={"email": "ratelimit@example.com", "password": "WrongPass1"},
    )
    third = client.post(
        "/auth/login",
        json={"email": "ratelimit@example.com", "password": "WrongPass1"},
    )

    assert first.status_code == 401
    assert second.status_code == 401
    assert third.status_code == 429
    assert "Too many failed login attempts" in third.json()["detail"]
