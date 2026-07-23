import pandas as pd
from typing import Dict, Any

class BaseStrategy:
    """Base class for all trading strategies."""

    description: str = "Base Strategy"

    def analyze(self, data: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Analyzes market data and returns a trading signal."""
        raise NotImplementedError

    def _validate_data(self, data: pd.DataFrame, min_rows: int) -> bool:
        """Helper to validate if enough data is available."""
        if data is None or data.empty or len(data) < min_rows:
            return False
        return True

    def _neutral(self, reason: str, strategy_name: str) -> Dict[str, Any]:
        """Returns a neutral signal."""
        return {
            "signal": "NEUTRAL",
            "confidence": 0,
            "strategy": strategy_name,
            "metadata": {"reason": reason},
        }

    def get_parameters(self) -> Dict[str, Any]:
        """Returns strategy parameters for configuration."""
        return {}
