"""TradeHistory model — история сделок для PnL расчёта."""

from datetime import datetime
from app import db


class TradeHistory(db.Model):  # type: ignore[name-defined]
    __tablename__ = "trade_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    exchange_id = db.Column(db.Integer, db.ForeignKey("exchanges.id"), nullable=False)
    position_id = db.Column(db.Integer, db.ForeignKey("positions.id"), nullable=True)

    symbol = db.Column(db.String(50), nullable=False)
    side = db.Column(db.String(10), nullable=False)
    size = db.Column(db.Numeric(20, 8), nullable=False)
    price = db.Column(db.Numeric(20, 8), nullable=False)
    pnl = db.Column(db.Numeric(20, 8), default=0)
    commission = db.Column(db.Numeric(20, 8), default=0)
    funding_fee = db.Column(db.Numeric(20, 8), default=0)

    trade_type = db.Column(db.String(20), default="CLOSE")  # OPEN, CLOSE, TP, SL
    executed_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "size": float(self.size),
            "price": float(self.price),
            "pnl": float(self.pnl),
            "commission": float(self.commission),
            "funding_fee": float(self.funding_fee),
            "trade_type": self.trade_type,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
        }
