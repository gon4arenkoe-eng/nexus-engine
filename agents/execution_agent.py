"""
V10 NEXUS Swarm — Execution Agent
==================================
Исполнение торговых ордеров.
Ключевое улучшение: идемпотентность через SentOrder таблицу.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from agents.base_agent import BaseAgent
from models import SentOrder, Position, TradeHistory
from clients.base import BaseExchangeClient
from app import db

logger = logging.getLogger(__name__)


class ExecutionAgent(BaseAgent):
    """
    Executes trading orders on exchanges.

    Features:
    - Idempotent order placement (no duplicates)
    - Position tracking
    - Trade history logging
    """

    def __init__(self):
        super().__init__("execution")

    async def run(self, signal: Dict[str, Any], risk_result: Dict[str, Any],
                  user_id: int, exchange_id: int, client: BaseExchangeClient,
                  symbol: str) -> Optional[Dict[str, Any]]:
        """
        Execute order based on approved signal.

        Args:
            signal: Signal dict from SignalAgent
            risk_result: Risk approval from RiskAgent
            user_id: User ID
            exchange_id: Exchange ID
            client: Exchange API client
            symbol: Trading symbol

        Returns:
            Order result dict or None if failed
        """
        if not risk_result.get("approved"):
            logger.info(f"Signal rejected by risk: {risk_result.get('reason')}")
            return None

        try:
            side = signal["signal"]  # BUY or SELL
            size = risk_result["position_size"]
            leverage = risk_result["leverage"]

            # Generate idempotency key (rounded to minute)
            timestamp_minute = int(datetime.utcnow().timestamp() // 60)
            idempotency_key = SentOrder.generate_idempotency_key(
                user_id, exchange_id, symbol, side, timestamp_minute
            )

            # Check for existing order
            existing = SentOrder.query.filter_by(
                order_idempotency_key=idempotency_key
            ).first()

            if existing:
                logger.info(f"Order already exists: {idempotency_key}")
                return {
                    "status": "DUPLICATE",
                    "order_id": existing.exchange_order_id,
                    "idempotency_key": idempotency_key,
                }

            # Create pending order record
            sent_order = SentOrder(
                user_id=user_id,
                exchange_id=exchange_id,
                order_idempotency_key=idempotency_key,
                symbol=symbol,
                side=side,
                order_type="MARKET",
                size=size,
                status="PENDING",
            )
            db.session.add(sent_order)
            db.session.commit()

            # Place order on exchange
            order_result = await client.place_order(
                symbol=symbol,
                side=side,
                size=size,
                order_type="MARKET",
                leverage=leverage,
            )

            if order_result.get("error"):
                sent_order.status = "REJECTED"
                db.session.commit()
                logger.error(f"Order rejected by exchange: {order_result['error']}")
                return None

            # Update order status
            sent_order.status = "FILLED"
            sent_order.exchange_order_id = order_result.get("order_id")

            # Create position
            position = Position(
                user_id=user_id,
                exchange_id=exchange_id,
                symbol=symbol,
                side="LONG" if side == "BUY" else "SHORT",
                size=size,
                entry_price=order_result.get("avg_price", 0),
                leverage=leverage,
                stop_loss=risk_result.get("stop_loss"),
                take_profit=risk_result.get("take_profit"),
                exchange_order_id=order_result.get("order_id"),
            )
            db.session.add(position)

            # Log trade
            trade = TradeHistory(
                user_id=user_id,
                exchange_id=exchange_id,
                position_id=position.id,
                symbol=symbol,
                side=side,
                size=size,
                price=order_result.get("avg_price", 0),
                commission=order_result.get("commission", 0),
                trade_type="OPEN",
            )
            db.session.add(trade)
            db.session.commit()

            self._record_run()
            return {
                "status": "FILLED",
                "order_id": order_result.get("order_id"),
                "position_id": position.id,
                "symbol": symbol,
                "side": side,
                "size": size,
                "price": order_result.get("avg_price"),
            }

        except Exception as e:
            self._handle_error(e)
            db.session.rollback()
            return None

    async def close_position(self, position_id: int, client: BaseExchangeClient,
                             current_price: float) -> Optional[Dict[str, Any]]:
        """Close an open position."""
        try:
            position = Position.query.get(position_id)
            if not position or position.status != "OPEN":
                return None

            # Place closing order
            close_side = "SELL" if position.side == "LONG" else "BUY"
            order_result = await client.place_order(
                symbol=position.symbol,
                side=close_side,
                size=float(position.size),
                order_type="MARKET",
            )

            if order_result.get("error"):
                return None

            # Calculate PnL
            entry = float(position.entry_price)
            exit_price = order_result.get("avg_price", current_price)

            if position.side == "LONG":
                pnl = (exit_price - entry) * float(position.size)
            else:
                pnl = (entry - exit_price) * float(position.size)

            # Update position
            position.status = "CLOSED"
            position.closed_at = datetime.utcnow()
            position.realized_pnl = pnl
            db.session.commit()

            # Log closing trade
            trade = TradeHistory(
                user_id=position.user_id,
                exchange_id=position.exchange_id,
                position_id=position.id,
                symbol=position.symbol,
                side=close_side,
                size=float(position.size),
                price=exit_price,
                pnl=pnl,
                commission=order_result.get("commission", 0),
                trade_type="CLOSE",
            )
            db.session.add(trade)
            db.session.commit()

            self._record_run()
            return {
                "status": "CLOSED",
                "position_id": position.id,
                "pnl": pnl,
                "exit_price": exit_price,
            }

        except Exception as e:
            self._handle_error(e)
            db.session.rollback()
            return None
