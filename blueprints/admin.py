"""Admin blueprint with secret key protection."""
import os
from functools import wraps
from flask import Blueprint, request, jsonify
from services.auth_service import require_auth
from app import db


admin_bp = Blueprint("admin", __name__)


def require_admin(f):
    """Decorator to require admin access with secret key."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not hasattr(request, "current_user") or not request.current_user.is_admin:
            return jsonify({"error": "Admin access required"}), 403

        admin_key = request.headers.get("X-Admin-Secret") or request.get_json().get("admin_secret")
        expected_key = os.environ.get("ADMIN_SECRET_KEY")

        if not expected_key or admin_key != expected_key:
            return jsonify({"error": "Invalid admin secret"}), 403

        return f(*args, **kwargs)
    return decorated


@admin_bp.route("/reset-db", methods=["POST"])
@require_auth
@require_admin
def reset_db():
    """Reset database (DANGER!)."""
    data = request.get_json() or {}
    confirmation = data.get("confirmation", "")

    if confirmation != "RESET_ALL_DATA_CONFIRM":
        return jsonify({
            "error": "Confirmation required",
            "message": "Send confirmation: 'RESET_ALL_DATA_CONFIRM'",
        }), 400

    db.drop_all()
    db.create_all()

    return jsonify({
        "message": "Database reset successfully",
        "warning": "All data has been deleted",
    })


@admin_bp.route("/health/agents", methods=["GET"])
@require_auth
@require_admin
def agents_health():
    """Get health status of all agents."""
    from services.trading_service import TradingService

    service = TradingService()

    health = {
        "config": service.config_agent.health_check(),
        "market": service.market_agent.health_check(),
        "signal": service.signal_agent.health_check(),
        "risk": service.risk_agent.health_check(),
        "execution": service.execution_agent.health_check(),
        "position": service.position_agent.health_check(),
        "pnl": service.pnl_agent.health_check(),
    }

    all_healthy = all(h["healthy"] for h in health.values())

    return jsonify({"all_healthy": all_healthy, "agents": health})
