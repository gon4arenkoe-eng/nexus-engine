"""
V10 NEXUS Swarm — Position Agent
=================================
Управление открытыми позициями.
"""

import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal

from agents.base_agent import BaseAgent
from models import Position
from clients.base import BaseExchangeClient

logger = logging.getLogger(__name__)


class PositionAgent(BaseAgent):
    """Tracks and manages open positions."""

    def __init__(self):
        super().__init__("position")

    async def run(self, user_id: int, exchange_id: int,
                  client: Optional[BaseExchangeClient]) -> List[Dict[str, Any]]:
        """Sync positions with exchange and return current positions."""
        try:
            if client:
                exchange_positions = await client.get_positions()

                if exchange_positions is not None:
                    positions = []
                    for pos_data in exchange_positions:
                        position = self._sync_position(user_id, exchange_id, pos_data)
                        if position:
                            positions.append(position.to_dict())

                    self._record_run()
                    return positions

            return self._get_local_positions(user_id)

        except Exception as e:
            self._handle_error(e)
            return self._get_local_positions(user_id)

    def _sync_position(self, user_id: int, exchange_id: int,
                       pos_data: Dict[str, Any]) -> Optional[Position]:
        """Sync single position with database."""
        symbol = pos_data.get("symbol")
        if not symbol:
            return None

        position = Position.query.filter_by(
            user_id=user_id,
            exchange_id=exchange_id,
            symbol=symbol,
            status="OPEN"
        ).first()

        if position:
            position.size = Decimal(str(pos_data.get("size", 0)))
            position.unrealized_pnl = Decimal(str(pos_data.get("unrealized_pnl", 0)))
        else:
            if float(pos_data.get("size", 0)) > 0:
                position = Position(
                    user_id=user_id,
                    exchange_id=exchange_id,
                    symbol=symbol,
                    side=pos_data.get("side", "LONG"),
                    size=Decimal(str(pos_data.get("size", 0))),
                    entry_price=Decimal(str(pos_data.get("entry_price", 0))),
                    leverage=pos_data.get("leverage", 1),
                    unrealized_pnl=Decimal(str(pos_data.get("unrealized_pnl", 0))),
                    exchange_order_id=pos_data.get("order_id"),
                )
                from app import db
                db.session.add(position)
                db.session.commit()

        return position

    def _get_local_positions(self, user_id: int) -> List[Dict[str, Any]]:
        """Get positions from local database (fallback)."""
        positions = Position.query.filter_by(user_id=user_id, status="OPEN").all()
        return [p.to_dict() for p in positions]

    def update_unrealized_pnl(self, position_id: int,
                              current_price: float) -> Optional[Decimal]:
        """Update unrealized PnL for a position."""
        try:
            position = Position.query.get(position_id)
            if not position or position.status != "OPEN":
                return None

            entry = float(position.entry_price)
            size = float(position.size)

            if position.side == "LONG":
                pnl = (current_price - entry) * size
            else:
                pnl = (entry - current_price) * size

            position.unrealized_pnl = Decimal(str(pnl))
            from app import db
            db.session.commit()

            return position.unrealized_pnl

        except Exception as e:
            self._handle_error(e)
            return None
