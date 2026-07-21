"""
V10 NEXUS Swarm — Notification Agent
======================================
Отправка уведомлений через Telegram, email.
"""

import logging
from typing import Dict, Any

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class NotificationAgent(BaseAgent):
    """Sends notifications about trading events."""

    def __init__(self):
        super().__init__("notification")
        self._telegram_enabled = False
        self._telegram_bot_token = None
        self._telegram_chat_id = None

    def run(self, event: Dict[str, Any]) -> bool:
        """Process and send notification for an event."""
        try:
            event_type = event.get("type", "unknown")

            if event_type == "trade":
                return self.send_trade_notification(**event.get("data", {}))
            elif event_type == "risk_alert":
                return self.send_risk_alert(**event.get("data", {}))
            elif event_type == "system":
                return self.send_system_notification(**event.get("data", {}))

            self._record_run()
            return True

        except Exception as e:
            self._handle_error(e)
            return False

    def send_trade_notification(self, user_id: int, symbol: str,
                               side: str, size: float, price: float) -> bool:
        """Send notification about executed trade."""
        message = (
            f"Trade Executed
"
            f"Symbol: {symbol}
"
            f"Side: {side}
"
            f"Size: {size}
"
            f"Price: ${price:.2f}"
        )

        logger.info(f"Trade notification: {message}")

        if self._telegram_enabled:
            return self._send_telegram(message)

        return True

    def send_risk_alert(self, user_id: int, alert_type: str,
                        message: str) -> bool:
        """Send risk management alert."""
        full_message = f"Risk Alert: {alert_type}
{message}"
        logger.warning(full_message)

        if self._telegram_enabled:
            return self._send_telegram(full_message)

        return True

    def send_system_notification(self, user_id: int, message: str) -> bool:
        """Send system-level notification."""
        logger.info(f"System notification: {message}")

        if self._telegram_enabled:
            return self._send_telegram(message)

        return True

    def _send_telegram(self, message: str) -> bool:
        """Send message via Telegram bot."""
        try:
            import requests

            url = f"https://api.telegram.org/bot{self._telegram_bot_token}/sendMessage"
            payload = {
                "chat_id": self._telegram_chat_id,
                "text": message,
                "parse_mode": "Markdown",
            }

            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200

        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    def configure_telegram(self, bot_token: str, chat_id: str) -> None:
        """Configure Telegram notifications."""
        self._telegram_bot_token = bot_token
        self._telegram_chat_id = chat_id
        self._telegram_enabled = bool(bot_token and chat_id)
        logger.info(f"Telegram notifications: {self._telegram_enabled}")
