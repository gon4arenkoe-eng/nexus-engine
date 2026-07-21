"""BotSettings model — настройки торгового бота."""

from datetime import datetime
from app import db


class BotSettings(db.Model):
    __tablename__ = "bot_settings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)

    # Trading parameters
    symbols = db.Column(db.Text, default="BTCUSDT,ETHUSDT")  # Comma-separated
    timeframe = db.Column(db.String(10), default="4h")
    confidence_threshold = db.Column(db.Integer, default=50)  # 0-100

    # Risk management
    max_positions = db.Column(db.Integer, default=5)
    max_leverage = db.Column(db.Integer, default=10)
    daily_loss_limit = db.Column(db.Numeric(20, 8), default=500)
    position_size_pct = db.Column(db.Numeric(5, 2), default=10.0)  # % of balance

    # Strategy settings
    strategy = db.Column(db.String(50), default="ema_cross")
    use_ml_filter = db.Column(db.Boolean, default=False)
    use_sentiment = db.Column(db.Boolean, default=False)

    # Bot state
    is_running = db.Column(db.Boolean, default=False)
    started_at = db.Column(db.DateTime, nullable=True)
    stopped_at = db.Column(db.DateTime, nullable=True)

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_symbols_list(self) -> list:
        return [s.strip() for s in (self.symbols or "").split(",") if s.strip()]

    def to_dict(self) -> dict:
        return {
            "symbols": self.get_symbols_list(),
            "timeframe": self.timeframe,
            "confidence_threshold": self.confidence_threshold,
            "max_positions": self.max_positions,
            "max_leverage": self.max_leverage,
            "daily_loss_limit": float(self.daily_loss_limit),
            "position_size_pct": float(self.position_size_pct),
            "strategy": self.strategy,
            "use_ml_filter": self.use_ml_filter,
            "use_sentiment": self.use_sentiment,
            "is_running": self.is_running,
        }
