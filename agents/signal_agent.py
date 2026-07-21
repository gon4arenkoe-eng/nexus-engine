"""
V10 NEXUS Swarm — Signal Agent
================================
Генерация торговых сигналов.
"""

import logging
from typing import Dict, Any, Optional, List
import pandas as pd

from agents.base_agent import BaseAgent
from strategies.base import BaseStrategy
from strategies.ema_cross import EmaCrossStrategy
from strategies.mean_reversion import MeanReversionStrategy

logger = logging.getLogger(__name__)


class SignalAgent(BaseAgent):
    """Generates trading signals using configured strategies."""

    def __init__(self):
        super().__init__("signal")
        self._strategies: Dict[str, BaseStrategy] = {
            "ema_cross": EmaCrossStrategy(),
            "mean_reversion": MeanReversionStrategy(),
        }

    def run(self, market_data: pd.DataFrame, strategy_name: str = "ema_cross",
            confidence_threshold: int = 50) -> Optional[Dict[str, Any]]:
        """Generate trading signal from market data."""
        try:
            strategy = self._strategies.get(strategy_name)
            if not strategy:
                raise ValueError(f"Unknown strategy: {strategy_name}")

            if market_data is None or len(market_data) < 50:
                logger.warning("Insufficient market data for signal generation")
                return None

            result = strategy.analyze(market_data)

            if result["confidence"] < confidence_threshold:
                result["signal"] = "NEUTRAL"

            self._record_run()
            return result

        except Exception as e:
            self._handle_error(e)
            return None

    def get_available_strategies(self) -> List[str]:
        """List available strategy names."""
        return list(self._strategies.keys())

    def add_strategy(self, name: str, strategy: BaseStrategy) -> None:
        """Register a new strategy."""
        self._strategies[name] = strategy
        logger.info(f"Registered strategy: {name}")

    def get_strategy_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get strategy description and parameters."""
        strategy = self._strategies.get(name)
        if strategy:
            return {
                "name": name,
                "description": strategy.description,
                "parameters": strategy.get_parameters(),
            }
        return None
