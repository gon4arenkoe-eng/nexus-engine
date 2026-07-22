"""
V10 NEXUS Swarm — Risk Agent
============================
Управление торговыми рисками.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal

from agents.base_agent import BaseAgent
from models import BotSettings, TradeHistory

logger = logging.getLogger(__name__)


class RiskAgent(BaseAgent):
    """Risk management agent."""

    def __init__(self):
        super().__init__("risk")
        self._daily_pnl_cache: Dict[int, Decimal] = {}
        self._last_pnl_update: Dict[int, datetime] = {}

    def run(self, signal: Dict[str, Any], user_id: int,
            balance: float = 0, open_positions: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Evaluate signal against risk rules."""
        try:
            settings = BotSettings.query.filter_by(user_id=user_id).first()
            if not settings:
                return self._reject("No bot settings found")

            symbol = signal.get("metadata", {}).get("symbol", "UNKNOWN")
            side = signal["signal"]

            # Check 1: Max positions
            current_positions = open_positions or []
            if len(current_positions) >= settings.max_positions:
                return self._reject(f"Max positions reached: {settings.max_positions}")

            # Check 2: Duplicate position
            for pos in current_positions:
                if (pos["symbol"] == symbol and
                        pos["side"] == ("LONG" if side == "BUY" else "SHORT")):
                    return self._reject(f"Position already exists: {symbol} {side}")

            # Check 3: Daily loss limit
            daily_pnl = self._get_daily_pnl(user_id)
            if daily_pnl <= -settings.daily_loss_limit:
                return self._reject(f"Daily loss limit reached: {daily_pnl}")

            # Check 4: Position size
            position_size_pct = float(settings.position_size_pct) / 100
            position_size = balance * position_size_pct

            if position_size <= 0:
                return self._reject("Insufficient balance")

            # Calculate SL/TP
            metadata = signal.get("metadata", {})
            current_price = metadata.get("current_price", 0)

            if current_price > 0:
                sl_pct = 0.02
                tp_pct = 0.04

                if side == "BUY":
                    stop_loss = current_price * (1 - sl_pct)
                    take_profit = current_price * (1 + tp_pct)
                else:
                    stop_loss = current_price * (1 + sl_pct)
                    take_profit = current_price * (1 - tp_pct)
            else:
                stop_loss = None
                take_profit = None

            self._record_run()
            return {
                "approved": True,
                "reason": "",
                "position_size": position_size,
                "leverage": min(settings.max_leverage, 10),
                "stop_loss": stop_loss,
                "take_profit": take_profit,
            }

        except Exception as e:
            self._handle_error(e)
            return self._reject(f"Risk check error: {str(e)}")

    def _reject(self, reason: str) -> Dict[str, Any]:
        """Return rejection response."""
        return {
            "approved": False,
            "reason": reason,
            "position_size": 0,
            "leverage": 0,
            "stop_loss": None,
            "take_profit": None,
        }

    def _get_daily_pnl(self, user_id: int) -> Decimal:
        """Calculate daily realized PnL."""
        now = datetime.utcnow()
        if user_id in self._last_pnl_update:
            if now - self._last_pnl_update[user_id] < timedelta(minutes=1):
                return self._daily_pnl_cache.get(user_id, Decimal("0"))

        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        trades = TradeHistory.query.filter(
            TradeHistory.user_id == user_id,
            TradeHistory.executed_at >= today
        ).all()

        total_pnl = sum(
            (t.pnl or 0) + (t.commission or 0) + (t.funding_fee or 0)
            for t in trades
        )
        self._daily_pnl_cache[user_id] = Decimal(str(total_pnl))
        self._last_pnl_update[user_id] = now

        return self._daily_pnl_cache[user_id]

    def reset_daily_pnl(self, user_id: int) -> None:
        """Reset daily PnL cache."""
        self._daily_pnl_cache.pop(user_id, None)
        self._last_pnl_update.pop(user_id, None)
