"""Position model — открытые позиции."""

from datetime import datetime
from app import db


class Position(db.Model):
    __tablename__ = "positions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    exchange_id = db.Column(db.Integer, db.ForeignKey("exchanges.id"), nullable=False)

    symbol = db.Column(db.String(50), nullable=False, index=True)
    side = db.Column(db.String(10), nullable=False)  # LONG / SHORT
    size = db.Column(db.Numeric(20, 8), nullable=False)
    entry_price = db.Column(db.Numeric(20, 8), nullable=False)
    leverage = db.Column(db.Integer, default=1)

    stop_loss = db.Column(db.Numeric(20, 8), nullable=True)
    take_profit = db.Column(db.Numeric(20, 8), nullable=True)

    unrealized_pnl = db.Column(db.Numeric(20, 8), default=0)
    realized_pnl = db.Column(db.Numeric(20, 8), default=0)

    status = db.Column(db.String(20), default="OPEN")  # OPEN, CLOSED
    opened_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)

    # Exchange-specific order ID for tracking
    exchange_order_id = db.Column(db.String(100), nullable=True, index=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "side": self.side,
            "size": float(self.size),
            "entry_price": float(self.entry_price),
            "leverage": self.leverage,
            "unrealized_pnl": float(self.unrealized_pnl),
            "realized_pnl": float(self.realized_pnl),
            "status": self.status,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
        }
