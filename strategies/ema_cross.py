"""
V10 NEXUS Swarm — EMA Crossover Strategy
=========================================
Классическая стратегия пересечения EMA.
- EMA 12 / EMA 26 (стандарт)
- + ADX для фильтрации тренда/флэта
"""

import pandas as pd
import numpy as np
from typing import Dict, Any

from strategies.base import BaseStrategy


class EmaCrossStrategy(BaseStrategy):
    """
    EMA Crossover strategy with ADX trend filter.

    Signals:
    - BUY: EMA 12 crosses above EMA 26 + ADX > 20 (trending)
    - SELL: EMA 12 crosses below EMA 26 + ADX > 20
    - NEUTRAL: No cross or ADX <= 20 (ranging)
    """

    description = "EMA Crossover with ADX trend filter"

    def __init__(
        self,
        fast_ema: int = 12,
        slow_ema: int = 26,
        adx_period: int = 14,
        adx_threshold: int = 20,
    ):
        self.fast_ema = fast_ema
        self.slow_ema = slow_ema
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold

    def analyze(self, data: pd.DataFrame) -> Dict[str, Any]:
        if not self._validate_data(
            data, min_rows=max(self.slow_ema, self.adx_period) + 10
        ):
            return self._neutral("Insufficient data")

        df = data.copy()

        # Calculate EMAs
        df["ema_fast"] = df["close"].ewm(span=self.fast_ema, adjust=False).mean()
        df["ema_slow"] = df["close"].ewm(span=self.slow_ema, adjust=False).mean()

        # Calculate ADX
        df = self._calculate_adx(df, self.adx_period)

        # Get current and previous values
        current = df.iloc[-1]
        previous = df.iloc[-2]

        # Determine signal
        signal = "NEUTRAL"
        confidence = 0

        # Check for crossover
        prev_diff = previous["ema_fast"] - previous["ema_slow"]
        curr_diff = current["ema_fast"] - current["ema_slow"]

        is_trending = current["adx"] > self.adx_threshold

        if prev_diff <= 0 and curr_diff > 0 and is_trending:
            signal = "BUY"
            confidence = min(50 + int(current["adx"]), 95)
        elif prev_diff >= 0 and curr_diff < 0 and is_trending:
            signal = "SELL"
            confidence = min(50 + int(current["adx"]), 95)

        return {
            "signal": signal,
            "confidence": confidence,
            "strategy": "ema_cross",
            "metadata": {
                "symbol": "",  # filled by caller
                "current_price": float(current["close"]),
                "indicators": {
                    "ema_fast": float(current["ema_fast"]),
                    "ema_slow": float(current["ema_slow"]),
                    "adx": float(current["adx"]),
                    "di_plus": float(current["di_plus"]),
                    "di_minus": float(current["di_minus"]),
                },
                "levels": {
                    "sl_pct": 0.02,
                    "tp_pct": 0.04,
                },
            },
        }

    def _calculate_adx(self, df: pd.DataFrame, period: int) -> pd.DataFrame:
        """Calculate ADX, DI+, DI-."""
        # True Range
        df["tr1"] = df["high"] - df["low"]
        df["tr2"] = abs(df["high"] - df["close"].shift(1))
        df["tr3"] = abs(df["low"] - df["close"].shift(1))
        df["tr"] = df[["tr1", "tr2", "tr3"]].max(axis=1)

        # Directional Movement
        df["dm_plus"] = df["high"] - df["high"].shift(1)
        df["dm_minus"] = df["low"].shift(1) - df["low"]

        df["dm_plus"] = np.where(
            (df["dm_plus"] > df["dm_minus"]) & (df["dm_plus"] > 0), df["dm_plus"], 0
        )
        df["dm_minus"] = np.where(
            (df["dm_minus"] > df["dm_plus"]) & (df["dm_minus"] > 0), df["dm_minus"], 0
        )

        # Smoothed averages
        df["atr"] = df["tr"].ewm(span=period, adjust=False).mean()
        df["di_plus"] = 100 * (
            df["dm_plus"].ewm(span=period, adjust=False).mean() / df["atr"]
        )
        df["di_minus"] = 100 * (
            df["dm_minus"].ewm(span=period, adjust=False).mean() / df["atr"]
        )

        # ADX
        df["dx"] = (
            100 * abs(df["di_plus"] - df["di_minus"]) / (df["di_plus"] + df["di_minus"])
        )
        df["adx"] = df["dx"].ewm(span=period, adjust=False).mean()

        return df

    def _neutral(self, reason: str, strategy_name: str = "") -> Dict[str, Any]:
        return {
            "signal": "NEUTRAL",
            "confidence": 0,
            "strategy": "ema_cross",
            "metadata": {"reason": reason},
        }

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "fast_ema": {"value": self.fast_ema, "type": "int", "min": 5, "max": 50},
            "slow_ema": {"value": self.slow_ema, "type": "int", "min": 10, "max": 100},
            "adx_period": {
                "value": self.adx_period,
                "type": "int",
                "min": 7,
                "max": 30,
            },
            "adx_threshold": {
                "value": self.adx_threshold,
                "type": "int",
                "min": 10,
                "max": 50,
            },
        }
