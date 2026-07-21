"""
V10 NEXUS Swarm — Notification Agent
=======================================
Уведомления пользователю.

Каналы:
- Telegram (основной)
- (Future) Email
- (Future) SMS
"""

import aiohttp
from typing import Dict, Any, Optional
from agents.base_agent import BaseAgent


class NotificationAgent(BaseAgent):
    """
    Sends notifications to user via configured channels.
    """

    def __init__(self):
        super().__init__("notification")
        self._telegram_token = None
        self._telegram_chat_id = None
        self._enabled = False

    def configure(self, telegram_token: str, telegram_chat_id: str) -> None:
        """Configure notification channels."""
        self._telegram_token = telegram_token
        self._telegram_chat_id = telegram_chat_id
        self._enabled = bool(telegram_token and telegram_chat_id)

    async def run(self, event_type: str, data: Dict[str, Any]) -> bool:
        """
        Send notification for event.

        Event types:
        - "signal": New trading signal generated
        - "order_executed": Order filled
        - "position_closed": Position closed with PnL
        - "risk_alert": Risk limit triggered
        - "daily_summary": Daily PnL report
        """
        try:
            self._record_run()

            if not self._enabled:
                return False

            message = self._format_message(event_type, data)

            if self._telegram_token:
                await self._send_telegram(message)

            return True

        except Exception as e:
            self._handle_error(e)
            return False

    def _format_message(self, event_type: str, data: Dict) -> str:
        """Format notification message based on event type."""
        if event_type == "signal":
            return (
                f"🎯 <b>New Signal</b>
"
                f"Symbol: {data.get('symbol')}
"
                f"Direction: {data.get('direction')}
"
                f"Confidence: {data.get('confidence')}%
"
                f"Strategy: {data.get('strategy')}"
            )
        elif event_type == "order_executed":
            return (
                f"✅ <b>Order Executed</b>
"
                f"Symbol: {data.get('symbol')}
"
                f"Side: {data.get('side')}
"
                f"Size: {data.get('size', 0):.4f}
"
                f"Price: {data.get('price', 0):.2f}"
            )
        elif event_type == "position_closed":
            pnl = data.get('realized_pnl', 0)
            emoji = "🟢" if pnl >= 0 else "🔴"
            return (
                f"{emoji} <b>Position Closed</b>
"
                f"Symbol: {data.get('symbol')}
"
                f"PnL: ${pnl:+.2f}
"
                f"Duration: {data.get('duration', 'N/A')}"
            )
        elif event_type == "risk_alert":
            return (
                f"⚠️ <b>Risk Alert</b>
"
                f"{data.get('reason', 'Unknown risk event')}"
            )
        elif event_type == "daily_summary":
            return (
                f"📊 <b>Daily Summary</b>
"
                f"Net PnL: ${data.get('net_pnl', 0):+.2f}
"
                f"Trades: {data.get('trade_count', 0)}
"
                f"Realized: ${data.get('realized_pnl', 0):+.2f}
"
                f"Unrealized: ${data.get('unrealized_pnl', 0):+.2f}"
            )
        else:
            return f"NEXUS Swarm Alert: {event_type}
{str(data)}"

    async def _send_telegram(self, message: str) -> None:
        """Send message via Telegram Bot API."""
        url = f"https://api.telegram.org/bot{self._telegram_token}/sendMessage"
        payload = {
            "chat_id": self._telegram_chat_id,
            "text": message,
            "parse_mode": "HTML"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Telegram API error: {resp.status}")
