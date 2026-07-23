"""SentOrder model — идемпотентность ордеров.

Ключевая проблема: race condition при одновременной обработке одного сигнала.
Решение: уникальный order_id на уровне БД + upsert.
"""

from datetime import datetime
from app import db


class SentOrder(db.Model):  # type: ignore[name-defined]
    __tablename__ = "sent_orders"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    exchange_id = db.Column(db.Integer, db.ForeignKey("exchanges.id"), nullable=False)

    # Уникальный ID для идемпотентности: user_id + exchange_id + symbol + side + timestamp_rounded
    order_idempotency_key = db.Column(db.String(255), unique=True, nullable=False, index=True)

    symbol = db.Column(db.String(50), nullable=False)
    side = db.Column(db.String(10), nullable=False)  # BUY / SELL
    order_type = db.Column(db.String(20), nullable=False)  # MARKET / LIMIT
    size = db.Column(db.Numeric(20, 8), nullable=False)
    price = db.Column(db.Numeric(20, 8), nullable=True)

    status = db.Column(db.String(20), default="PENDING")  # PENDING, FILLED, REJECTED, CANCELLED
    exchange_order_id = db.Column(db.String(100), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def generate_idempotency_key(user_id: int, exchange_id: int, symbol: str, side: str, timestamp_minute: int) -> str:
        """Generate unique key rounded to minute to prevent duplicate orders."""
        return f"{user_id}:{exchange_id}:{symbol}:{side}:{timestamp_minute}"
