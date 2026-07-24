"""
V10 NEXUS Swarm — Sentiment Agent
==================================
Анализ настроений рынка.

Источники:
- Fear & Greed Index (alternative.me)
- (Future) Twitter/X sentiment
- (Future) News sentiment
"""

import aiohttp
from typing import Dict, Any, Optional
from agents.base_agent import BaseAgent


class SentimentAgent(BaseAgent):
    """
    Market sentiment analysis.

    Current: Fear & Greed Index from alternative.me
    """

    def __init__(self):
        super().__init__("sentiment")
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 3600  # 1 hour
        self._last_fetch = None

    async def run(self) -> Optional[Dict[str, Any]]:
        """
        Fetch current market sentiment.

        Returns:
            {
                "fear_greed_index": 75,  # 0-100
                "classification": "Greed",  # Extreme Fear, Fear, Neutral, Greed, Extreme Greed
                "timestamp": "..."
            }
        """
        try:
            self._record_run()

            # Check cache
            if self._cache and self._last_fetch:
                from datetime import datetime, timedelta

                if datetime.utcnow() - self._last_fetch < timedelta(
                    seconds=self._cache_ttl
                ):
                    return self._cache

            # Fetch Fear & Greed Index
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.alternative.me/fng/",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"Fear & Greed API error: {resp.status}")

                    data = await resp.json()

                    result = {
                        "fear_greed_index": int(data["data"][0]["value"]),
                        "classification": data["data"][0]["value_classification"],
                        "timestamp": data["data"][0]["timestamp"],
                        "source": "alternative.me",
                    }

                    self._cache = result
                    self._last_fetch = datetime.utcnow()
                    return result

        except Exception as e:
            self._handle_error(e)
            # Return neutral if API fails
            return {
                "fear_greed_index": 50,
                "classification": "Neutral",
                "timestamp": datetime.utcnow().isoformat(),
                "source": "fallback",
                "error": str(e),
            }

    def is_bullish(self, sentiment: Dict) -> bool:
        """Check if sentiment is bullish (Greed or Extreme Greed)."""
        classification = sentiment.get("classification", "Neutral")
        return classification in ["Greed", "Extreme Greed"]

    def is_bearish(self, sentiment: Dict) -> bool:
        """Check if sentiment is bearish (Fear or Extreme Fear)."""
        classification = sentiment.get("classification", "Neutral")
        return classification in ["Fear", "Extreme Fear"]
