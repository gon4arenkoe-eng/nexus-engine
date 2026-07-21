"""
V10 NEXUS Swarm — PnL Agent
============================
Расчёт прибыли и убытков.
Realized + Unrealized PnL. Daily tracking.
"""

from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime, date, timedelta
from agents.base_agent import BaseAgent
from models import Position, TradeHistory, BotSettings
from app import db


class PnLAgent(BaseAgent):
    """
    Calculates PnL for positions and daily totals.

    Realized PnL: from closed positions
    Unrealized PnL: from open positions (mark price - entry price)
    """

    def __init__(self):
        super().__init__("pnl")
        self._daily_cache: Dict[int, Dict] = {}  # user_id -> daily stats

    def run(self, action: str, user_id: int, 
            position_data: Optional[Dict] = None,
            mark_prices: Optional[Dict[str, float]] = None) -> Any:
        """
        Calculate PnL.

        Actions:
        - "calculate_unrealized": Update unrealized PnL for open positions
        - "record_realized": Record realized PnL from closed trade
        - "daily_summary": Get today's PnL summary
        - "history": Get PnL history for period
        """
        try:
            self._record_run()

            if action == "calculate_unrealized":
                return self._calculate_unrealized(user_id, mark_prices)
            elif action == "record_realized":
                return self._record_realized(user_id, position_data)
            elif action == "daily_summary":
                return self._daily_summary(user_id)
            elif action == "history":
                return self._get_history(user_id, position_data)
            else:
                raise ValueError(f"Unknown action: {action}")

        except Exception as e:
            self._handle_error(e)
            raise

    def _calculate_unrealized(self, user_id: int, 
                             mark_prices: Dict[str, float]) -> List[Dict]:
        """Calculate unrealized PnL for all open positions."""
        positions = Position.query.filter_by(
            user_id=user_id, status="OPEN"
        ).all()

        updated = []
        for pos in positions:
            mark_price = mark_prices.get(pos.symbol)
            if not mark_price:
                continue

            entry = float(pos.entry_price)
            size = float(pos.size)

            if pos.side == "LONG":
                pnl = (mark_price - entry) * size
            else:  # SHORT
                pnl = (entry - mark_price) * size

            pos.unrealized_pnl = Decimal(str(pnl))
            updated.append({
                "symbol": pos.symbol,
                "side": pos.side,
                "unrealized_pnl": pnl,
                "mark_price": mark_price,
                "entry_price": entry,
            })

        db.session.commit()
        return updated

    def _record_realized(self, user_id: int, 
                        trade_data: Dict) -> Dict[str, Any]:
        """Record realized PnL from closed trade."""
        trade = TradeHistory(
            user_id=user_id,
            exchange_id=trade_data.get("exchange_id"),
            position_id=trade_data.get("position_id"),
            symbol=trade_data["symbol"],
            side=trade_data["side"],
            size=Decimal(str(trade_data.get("size", 0))),
            price=Decimal(str(trade_data.get("price", 0))),
            pnl=Decimal(str(trade_data.get("realized_pnl", 0))),
            commission=Decimal(str(trade_data.get("commission", 0))),
            funding_fee=Decimal(str(trade_data.get("funding_fee", 0))),
            trade_type=trade_data.get("trade_type", "CLOSE"),
        )

        db.session.add(trade)
        db.session.commit()

        return trade.to_dict()

    def _daily_summary(self, user_id: int) -> Dict[str, Any]:
        """Get today's PnL summary."""
        today = date.today()
        tomorrow = today + timedelta(days=1)

        trades = TradeHistory.query.filter(
            TradeHistory.user_id == user_id,
            TradeHistory.executed_at >= today,
            TradeHistory.executed_at < tomorrow
        ).all()

        realized_pnl = sum(float(t.pnl) for t in trades)
        commission = sum(float(t.commission) for t in trades)
        funding_fee = sum(float(t.funding_fee) for t in trades)
        net_pnl = realized_pnl - commission - funding_fee

        # Unrealized from open positions
        open_positions = Position.query.filter_by(
            user_id=user_id, status="OPEN"
        ).all()
        unrealized_pnl = sum(float(p.unrealized_pnl) for p in open_positions)

        summary = {
            "date": today.isoformat(),
            "realized_pnl": realized_pnl,
            "unrealized_pnl": unrealized_pnl,
            "commission": commission,
            "funding_fee": funding_fee,
            "net_pnl": net_pnl,
            "total_pnl": realized_pnl + unrealized_pnl,
            "trade_count": len(trades),
        }

        self._daily_cache[user_id] = summary
        return summary

    def _get_history(self, user_id: int, 
                    params: Optional[Dict] = None) -> List[Dict]:
        """Get PnL history for a period."""
        params = params or {}
        days = params.get("days", 30)

        since = datetime.utcnow() - timedelta(days=days)

        trades = TradeHistory.query.filter(
            TradeHistory.user_id == user_id,
            TradeHistory.executed_at >= since
        ).order_by(TradeHistory.executed_at.desc()).all()

        return [t.to_dict() for t in trades]
