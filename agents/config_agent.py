"""
V10 NEXUS Swarm — Config Agent
==============================
Управление конфигурацией системы.
Читает/пишет настройки из БД. Централизованный доступ.
"""

from typing import Dict, Any, Optional
from agents.base_agent import BaseAgent
from models import BotSettings, User
from app import db


class ConfigAgent(BaseAgent):
    """
    Manages all configuration parameters:
    - User settings
    - Exchange settings
    - Strategy parameters
    - Risk parameters
    """

    def __init__(self):
        super().__init__("config")
        self._cache: Dict[int, Dict[str, Any]] = {}  # user_id -> settings cache

    def run(self, user_id: int) -> Dict[str, Any]:
        """Get full configuration for a user."""
        try:
            # Check cache first
            if user_id in self._cache:
                return self._cache[user_id]

            # Load from database
            settings = BotSettings.query.filter_by(user_id=user_id).first()
            if not settings:
                # Create default settings
                settings = BotSettings(user_id=user_id)
                db.session.add(settings)
                db.session.commit()

            config = settings.to_dict()
            self._cache[user_id] = config
            self._record_run()
            return config

        except Exception as e:
            self._handle_error(e)
            raise

    def get_setting(self, user_id: int, key: str, default: Any = None) -> Any:
        """Get single setting value."""
        config = self.run(user_id)
        return config.get(key, default)

    def update_setting(self, user_id: int, key: str, value: Any) -> bool:
        """Update a single setting."""
        try:
            settings = BotSettings.query.filter_by(user_id=user_id).first()
            if not settings:
                return False

            if hasattr(settings, key):
                setattr(settings, key, value)
                db.session.commit()
                # Invalidate cache
                self._cache.pop(user_id, None)
                self._record_run()
                return True
            return False

        except Exception as e:
            self._handle_error(e)
            return False

    def update_settings(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """Batch update settings."""
        try:
            settings = BotSettings.query.filter_by(user_id=user_id).first()
            if not settings:
                return False

            for key, value in updates.items():
                if hasattr(settings, key):
                    setattr(settings, key, value)

            db.session.commit()
            self._cache.pop(user_id, None)
            self._record_run()
            return True

        except Exception as e:
            self._handle_error(e)
            db.session.rollback()
            return False

    def invalidate_cache(self, user_id: int) -> None:
        """Clear cache for a user."""
        self._cache.pop(user_id, None)

    def get_symbols(self, user_id: int) -> list:
        """Get trading symbols list."""
        config = self.run(user_id)
        return config.get("symbols", ["BTCUSDT", "ETHUSDT"])

    def get_timeframe(self, user_id: int) -> str:
        """Get analysis timeframe."""
        return self.get_setting(user_id, "timeframe", "4h")

    def get_confidence_threshold(self, user_id: int) -> int:
        """Get minimum confidence for signals."""
        return self.get_setting(user_id, "confidence_threshold", 50)
