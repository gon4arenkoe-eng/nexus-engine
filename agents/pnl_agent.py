"""
V10 NEXUS Swarm — PnL Agent
============================
Расчёт прибыли и убытков.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal

from agents.base_agent import BaseAgent
from models import TradeHistory

logger = logging.getLogger(__name__)


class PnLAgent(BaseAgent):
    """Calculates profit and loss for positions and daily totals."""

    def __init__(self):
        super().__init__("pnl")
        self._daily_pnl_cache: Dict[int, Decimal] = {}
        self._last_update: Dict[int, datetime] = {}

    def run(self, user_id: int, positions: List[Dict[str, Any]]) -> Optional[Decimal]:
        """Calculate total unrealized PnL for open positions."""
        try:
            total_pnl = Decimal("0")

            for pos in positions:
                unrealized = pos.get("unrealized_pnl", 0)
                total_pnl += Decimal(str(unrealized))

            self._record_run()
            return total_pnl

        except Exception as e:
            self._handle_error(e)
            return None

    def get_daily_pnl(self, user_id: int) -> Decimal:
        """Calculate daily realized PnL from trade history."""
        now = datetime.utcnow()

        if user_id in self._last_update:
            if now - self._last_update[user_id] < timedelta(minutes=1):
                return self._daily_pnl_cache.get(user_id, Decimal("0"))

        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        trades = TradeHistory.query.filter(
            TradeHistory.user_id == user_id, TradeHistory.executed_at >= today
        ).all()

        total_pnl = sum(
            (t.pnl or 0) + (t.commission or 0) + (t.funding_fee or 0) for t in trades
        )

        self._daily_pnl_cache[user_id] = Decimal(str(total_pnl))
        self._last_update[user_id] = now

        return self._daily_pnl_cache[user_id]

    def get_total_pnl(self, user_id: int) -> Decimal:
        """Calculate total realized PnL for all time."""
        trades = TradeHistory.query.filter_by(user_id=user_id).all()

        total_pnl = sum(
            (t.pnl or 0) + (t.commission or 0) + (t.funding_fee or 0) for t in trades
        )

        return Decimal(str(total_pnl))

    def reset_cache(self, user_id: int) -> None:
        """Reset PnL cache for a user."""
        self._daily_pnl_cache.pop(user_id, None)
        self._last_update.pop(user_id, None)
