"""
V10 NEXUS Swarm — Auth Service
===============================
Сервис аутентификации.
JWT токены хранятся в httpOnly Secure cookies (НЕ localStorage).
"""

import os
import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Tuple
from functools import wraps
from flask import request, make_response

from models import User
from app import db


class AuthService:
    """
    Authentication service.

    Security:
    - JWT in httpOnly Secure cookies (XSS protection)
    - bcrypt password hashing (12 rounds)
    - Token expiration (access: 15min, refresh: 7 days)
    """

    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.access_token_expiry = timedelta(minutes=15)
        self.refresh_token_expiry = timedelta(days=7)

    def register(self, username: str, email: str, password: str) -> Tuple[bool, str]:
        """Register new user. Returns (success, message)."""
        # Check existing
        if User.query.filter_by(username=username).first():
            return False, "Username already exists"
        if User.query.filter_by(email=email).first():
            return False, "Email already exists"

        # Create user
        user = User(username=username, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        return True, "User registered successfully"

    def login(self, username: str, password: str) -> Tuple[Optional[User], Optional[Dict]]:
        """
        Authenticate user and generate tokens.

        Returns:
            (user, tokens_dict) or (None, None) if failed
        """
        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            return None, None

        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()

        tokens = self._generate_tokens(user)
        return user, tokens

    def refresh_access_token(self, refresh_token: str) -> Optional[Dict]:
        """Generate new access token from refresh token."""
        try:
            payload = jwt.decode(refresh_token, self.secret_key, algorithms=["HS256"])
            user_id = payload.get("user_id")
            token_type = payload.get("type")

            if token_type != "refresh":
                return None

            user = User.query.get(user_id)
            if not user:
                return None

            return self._generate_tokens(user)

        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify access token and return payload."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            if payload.get("type") != "access":
                return None
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def get_current_user(self) -> Optional[User]:
        """Get current user from request cookies."""
        token = request.cookies.get("access_token")
        if not token:
            return None

        payload = self.verify_token(token)
        if not payload:
            return None

        return User.query.get(payload.get("user_id"))

    def _generate_tokens(self, user: User) -> Dict[str, str]:
        """Generate access and refresh tokens."""
        now = datetime.now(timezone.utc)

        access_payload = {
            "user_id": user.id,
            "username": user.username,
            "type": "access",
            "iat": now,
            "exp": now + self.access_token_expiry,
        }

        refresh_payload = {
            "user_id": user.id,
            "type": "refresh",
            "iat": now,
            "exp": now + self.refresh_token_expiry,
        }

        return {
            "access_token": jwt.encode(access_payload, self.secret_key, algorithm="HS256"),
            "refresh_token": jwt.encode(refresh_payload, self.secret_key, algorithm="HS256"),
        }

    def set_auth_cookies(self, response, tokens: Dict[str, str]) -> None:
        """Set httpOnly Secure cookies with tokens."""
        response.set_cookie(
            "access_token",
            tokens["access_token"],
            httponly=True,
            secure=True,  # HTTPS only
            samesite="Lax",
            max_age=int(self.access_token_expiry.total_seconds()),
        )
        response.set_cookie(
            "refresh_token",
            tokens["refresh_token"],
            httponly=True,
            secure=True,
            samesite="Lax",
            max_age=int(self.refresh_token_expiry.total_seconds()),
        )

    def clear_auth_cookies(self, response) -> None:
        """Clear auth cookies (logout)."""
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")


def require_auth(f):
    """Decorator to require authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import request, jsonify

        token = request.cookies.get("access_token")
        if not token:
            return jsonify({"error": "Authentication required"}), 401

        # Verify token
        auth_service = AuthService(os.environ.get("SECRET_KEY", ""))
        payload = auth_service.verify_token(token)

        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401

        # Attach user to request
        request.current_user = User.query.get(payload["user_id"])
        if not request.current_user:
            return jsonify({"error": "User not found"}), 401

        return f(*args, **kwargs)
    return decorated
