"""Exchange model — подключения к биржам."""

from datetime import datetime
from app import db


class Exchange(db.Model):  # type: ignore[name-defined]
    __tablename__ = "exchanges"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    name = db.Column(db.String(50), nullable=False)  # bingx, binance, bybit, okx
    is_active = db.Column(db.Boolean, default=True)
    is_demo = db.Column(db.Boolean, default=True)  # DEMO mode by default

    # Encrypted API credentials
    api_key_encrypted = db.Column(db.Text, nullable=False)
    api_secret_encrypted = db.Column(db.Text, nullable=False)
    passphrase_encrypted = db.Column(db.Text, nullable=True)  # For OKX

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_connected = db.Column(db.DateTime, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "is_active": self.is_active,
            "is_demo": self.is_demo,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_connected": self.last_connected.isoformat() if self.last_connected else None,
        }
