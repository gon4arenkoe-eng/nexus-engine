"""Exchanges blueprint."""
import asyncio
from flask import Blueprint, request, jsonify
from services.auth_service import require_auth
from services.exchange_service import ExchangeService


exchanges_bp = Blueprint("exchanges", __name__)
exchange_service = ExchangeService()


@exchanges_bp.route("/", methods=["GET"])
@require_auth
def list_exchanges():
    """Get user's exchanges."""
    exchanges = exchange_service.get_user_exchanges(request.current_user.id)
    return jsonify({"exchanges": exchanges})


@exchanges_bp.route("/", methods=["POST"])
@require_auth
def add_exchange():
    """Add new exchange connection."""
    data = request.get_json() or {}

    name = (data.get("name") or "").strip().lower()
    api_key = (data.get("api_key") or "").strip()
    api_secret = (data.get("api_secret") or "").strip()
    passphrase = (data.get("passphrase") or "").strip() or None
    is_demo = data.get("is_demo", True)

    if not name or not api_key or not api_secret:
        return jsonify({"error": "Name, API key and secret required"}), 400

    result = exchange_service.add_exchange(
        user_id=request.current_user.id,
        name=name, api_key=api_key, api_secret=api_secret,
        passphrase=passphrase, is_demo=is_demo,
    )

    if not result["success"]:
        return jsonify({"error": result["error"]}), 400

    return jsonify({
        "message": "Exchange added successfully",
        "exchange_id": result["exchange_id"],
    }), 201


@exchanges_bp.route("/<int:exchange_id>/test", methods=["POST"])
@require_auth
def test_exchange(exchange_id):
    """Test exchange connection."""
    result = asyncio.run(exchange_service.test_connection(exchange_id))

    if not result["success"]:
        return jsonify({"error": result["error"]}), 400

    return jsonify({
        "message": "Connection successful",
        "balance": result["balance"],
    })


@exchanges_bp.route("/<int:exchange_id>/toggle", methods=["POST"])
@require_auth
def toggle_exchange(exchange_id):
    """Toggle exchange active/inactive."""
    success = exchange_service.toggle_exchange(exchange_id, request.current_user.id)

    if not success:
        return jsonify({"error": "Exchange not found"}), 404

    return jsonify({"message": "Exchange toggled"})


@exchanges_bp.route("/<int:exchange_id>", methods=["DELETE"])
@require_auth
def delete_exchange(exchange_id):
    """Delete exchange connection."""
    success = exchange_service.delete_exchange(exchange_id, request.current_user.id)

    if not success:
        return jsonify({"error": "Exchange not found"}), 404

    return jsonify({"message": "Exchange deleted"})
