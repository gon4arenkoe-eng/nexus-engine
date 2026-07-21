"""Auth blueprint with rate limiting."""
import os
from flask import Blueprint, request, jsonify, make_response
from services.auth_service import AuthService, require_auth
from app import limiter

auth_bp = Blueprint("auth", __name__)

def get_auth_service():
    return AuthService(os.environ.get("SECRET_KEY", ""))

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password", "")

    if not username or not email or not password:
        return jsonify({"error": "Username, email and password required"}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    auth_service = get_auth_service()
    success, message = auth_service.register(username, email, password)
    if not success:
        return jsonify({"error": message}), 409
    return jsonify({"message": message}), 201

@auth_bp.route("/login", methods=["POST"])
@limiter.limit("5 per minute")
def login():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    auth_service = get_auth_service()
    user, tokens = auth_service.login(username, password)

    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    response = make_response(jsonify({"message": "Login successful", "user": user.to_dict()}))
    auth_service.set_auth_cookies(response, tokens)
    return response, 200

@auth_bp.route("/logout", methods=["POST"])
def logout():
    auth_service = get_auth_service()
    response = make_response(jsonify({"message": "Logout successful"}))
    auth_service.clear_auth_cookies(response)
    return response

@auth_bp.route("/me", methods=["GET"])
@require_auth
def me():
    return jsonify({"user": request.current_user.to_dict()})

@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        return jsonify({"error": "No refresh token"}), 401

    auth_service = get_auth_service()
    tokens = auth_service.refresh_access_token(refresh_token)

    if not tokens:
        return jsonify({"error": "Invalid or expired refresh token"}), 401

    response = make_response(jsonify({"message": "Token refreshed"}))
    auth_service.set_auth_cookies(response, tokens)
    return response
