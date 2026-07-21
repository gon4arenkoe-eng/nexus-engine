"""Trading blueprint."""
import asyncio
from flask import Blueprint, request, jsonify
from services.auth_service import require_auth
from services.exchange_service import ExchangeService
from services.trading_service import TradingService
from models import BotSettings


trading_bp = Blueprint("trading", __name__)
trading_service = TradingService()
exchange_service = ExchangeService()


@trading_bp.route("/positions", methods=["GET"])
@require_auth
def get_positions():
    """Get open positions."""
    exchange = exchange_service.get_active_exchange(request.current_user.id)
    if not exchange:
        return jsonify({"error": "No active exchange"}), 400

    positions = asyncio.run(
        trading_service.position_agent.run(
            request.current_user.id, exchange.id, None
        )
    )

    return jsonify({"positions": positions})


@trading_bp.route("/balance", methods=["GET"])
@require_auth
def get_balance():
    """Get account balance."""
    exchange = exchange_service.get_active_exchange(request.current_user.id)
    if not exchange:
        return jsonify({"error": "No active exchange"}), 400

    client = asyncio.run(exchange_service.get_client(exchange.id))

    if not client:
        return jsonify({"error": "Failed to initialize client"}), 500

    balance = asyncio.run(client.get_balance())

    if "error" in balance:
        return jsonify({"error": balance["error"]}), 400

    return jsonify({"balance": balance})


@trading_bp.route("/pnl", methods=["GET"])
@require_auth
def get_pnl():
    """Get PnL data."""
    exchange = exchange_service.get_active_exchange(request.current_user.id)
    if not exchange:
        return jsonify({"error": "No active exchange"}), 400

    positions = asyncio.run(
        trading_service.position_agent.run(
            request.current_user.id, exchange.id, None
        )
    )

    pnl = trading_service.pnl_agent.run(request.current_user.id, positions)

    return jsonify({
        "daily_pnl": float(pnl) if pnl else 0,
        "positions_count": len(positions),
    })


@trading_bp.route("/bot/start", methods=["POST"])
@require_auth
def start_bot():
    """Start trading bot."""
    success = asyncio.run(trading_service.start_bot(request.current_user.id))

    if not success:
        return jsonify({"error": "Failed to start bot"}), 400

    return jsonify({"message": "Bot started"})


@trading_bp.route("/bot/stop", methods=["POST"])
@require_auth
def stop_bot():
    """Stop trading bot."""
    success = asyncio.run(trading_service.stop_bot(request.current_user.id))

    if not success:
        return jsonify({"error": "Failed to stop bot"}), 400

    return jsonify({"message": "Bot stopped"})


@trading_bp.route("/bot/status", methods=["GET"])
@require_auth
def bot_status():
    """Get bot status."""
    status = asyncio.run(trading_service.get_status(request.current_user.id))

    if "error" in status:
        return jsonify({"error": status["error"]}), 400

    return jsonify(status)


@trading_bp.route("/settings", methods=["GET"])
@require_auth
def get_settings():
    """Get bot settings."""
    settings = BotSettings.query.filter_by(user_id=request.current_user.id).first()

    if not settings:
        return jsonify({"error": "No settings found"}), 404

    return jsonify(settings.to_dict())


@trading_bp.route("/settings", methods=["PUT"])
@require_auth
def update_settings():
    """Update bot settings."""
    data = request.get_json() or {}

    settings = BotSettings.query.filter_by(user_id=request.current_user.id).first()
    if not settings:
        return jsonify({"error": "No settings found"}), 404

    allowed = [
        "symbols", "timeframe", "confidence_threshold", "max_positions",
        "max_leverage", "daily_loss_limit", "position_size_pct",
        "strategy", "use_ml_filter", "use_sentiment",
    ]

    for key in allowed:
        if key in data:
            setattr(settings, key, data[key])

    from app import db
    db.session.commit()

    trading_service.config_agent.invalidate_cache(request.current_user.id)

    return jsonify({"message": "Settings updated", "settings": settings.to_dict()})
