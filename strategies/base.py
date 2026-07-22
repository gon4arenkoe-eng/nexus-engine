"""
V10 NEXUS Swarm — Base Strategy
================================
Интерфейс для всех торговых стратегий.
Каждая стратегия реализует analyze() и возвращает сигнал.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import pandas as pd


class BaseStrategy(ABC):
    """
    Base class for all trading strategies.

    Each strategy must implement:
    - analyze(): Analyze market data and return signal
    - get_parameters(): Return configurable parameters
    """

    description: str = "Base strategy"

    @abstractmethod
    def analyze(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze market data and generate trading signal.

        Args:
            data: DataFrame with OHLCV columns (open, high, low, close, volume)

        Returns:
            {
                "signal": "BUY" | "SELL" | "NEUTRAL",
                "confidence": int (0-100),
                "strategy": str,
                "metadata": {
                    "symbol": str,
                    "current_price": float,
                    "indicators": dict,
                    "levels": dict,  # SL, TP, etc.
                }
            }
        """
        pass

    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """Return strategy parameters for configuration."""
        pass

    def _validate_data(self, data: pd.DataFrame, min_rows: int = 50) -> bool:
        """Validate that data has required columns and enough rows."""
        required = ["open", "high", "low", "close", "volume"]
        if not all(col in data.columns for col in required):
            return False
        if len(data) < min_rows:
            return False
        return True
