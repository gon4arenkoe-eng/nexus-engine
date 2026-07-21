"""User model — аутентификация и профиль."""

from datetime import datetime
from app import db
import bcrypt


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    # Relationships
    exchanges = db.relationship("Exchange", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    bot_settings = db.relationship("BotSettings", backref="user", uselist=False, cascade="all, delete-orphan")
    positions = db.relationship("Position", backref="user", lazy="dynamic")
    trade_history = db.relationship("TradeHistory", backref="user", lazy="dynamic")

    def set_password(self, password: str) -> None:
        """Hash password with bcrypt."""
        self.password_hash = bcrypt.hashpw(
            password.encode("utf-8"), 
            bcrypt.gensalt(rounds=12)
        ).decode("utf-8")

    def check_password(self, password: str) -> bool:
        """Verify password against hash."""
        return bcrypt.checkpw(
            password.encode("utf-8"), 
            self.password_hash.encode("utf-8")
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
