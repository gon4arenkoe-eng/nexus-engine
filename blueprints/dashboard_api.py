import asyncio
from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from services.trading_service import TradingService
from models import BotSettings

dashboard_api_bp = Blueprint("dashboard_api", __name__, url_prefix="/api/data")

@dashboard_api_bp.route("/overview")
@login_required
async def get_overview():
    user_id = current_user.id
    trading_service = TradingService()
    
    bot_status = await trading_service.get_status(user_id)
    
    # Placeholder for actual data retrieval
    # In a real scenario, you would fetch this from your database or agents
    overview_data = {
        "total_pnl": 0.00, # TODO: Fetch from PnLAgent or DB
        "daily_pnl": 0.00, # TODO: Fetch from PnLAgent or DB
        "total_trades": 0, # TODO: Fetch from ExecutionAgent or DB
        "win_rate": 0.0,   # TODO: Calculate from trade history
        "current_status": "Running" if bot_status.get("is_running") else "Stopped",
        "active_strategies": bot_status.get("symbols", []), # This is actually symbols, not strategies
        "balance": 0.00,   # TODO: Fetch from ExchangeService or DB
        "equity": 0.00,    # TODO: Calculate from balance + open PnL
        "started_at": bot_status.get("started_at"),
        "strategy_name": bot_status.get("strategy"),
    }
    
    return jsonify(overview_data)

# TODO: Implement other endpoints: /equity, /positions, /strategies, /logs
