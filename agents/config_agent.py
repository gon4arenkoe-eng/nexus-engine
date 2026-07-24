from typing import Dict, Any
from agents.base_agent import BaseAgent


class ConfigAgent(BaseAgent):
    """
    Agent responsible for fetching and managing bot configuration.
    """

    async def run(self, user_id: int) -> Dict[str, Any]:
        # Placeholder for fetching user-specific configuration
        # In a real app, this would fetch from DB or a config file
        return {
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "timeframe": "4h",
            "strategy": None,  # Let SignalAgent decide
            "confidence_threshold": 50,
            "use_ml_filter": False,
            "use_sentiment": False,
        }

    def health_check(self) -> Dict[str, Any]:
        return {"status": "ok", "message": "Config Agent is operational"}
