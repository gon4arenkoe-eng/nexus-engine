import pandas as pd
from typing import Dict, Any

from strategies.base import BaseStrategy
from utils.indicators import Indicators


class TrendFollowingChopStrategy(BaseStrategy):
    """
    Trend Following strategy with Choppiness Index filter.

    Signals:
    - BUY: Fast EMA crosses above Slow EMA, RSI > 50, and Choppiness Index indicates trending market.
    - SELL: Fast EMA crosses below Slow EMA, and Choppiness Index indicates trending market.
    - NEUTRAL: No cross, or Choppiness Index indicates ranging market.
    """

    description = "Trend Following with Choppiness Index filter"

    def __init__(
        self,
        fast_ema: int = 9,
        slow_ema: int = 21,
        rsi_period: int = 14,
        chop_period: int = 14,
        chop_threshold_trend: float = 50.0,
    ):
        self.fast_ema = fast_ema
        self.slow_ema = slow_ema
        self.rsi_period = rsi_period
        self.chop_period = chop_period
        self.chop_threshold_trend = chop_threshold_trend

    def analyze(self, data: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        if not self._validate_data(
            data, min_rows=max(self.slow_ema, self.rsi_period, self.chop_period) + 2
        ):
            return self._neutral("Insufficient data", self.description)

        df = data.copy()

        # Calculate indicators
        df["ema_fast"] = Indicators.calculate_ema(df["close"], self.fast_ema)
        df["ema_slow"] = Indicators.calculate_ema(df["close"], self.slow_ema)
        df["rsi"] = Indicators.calculate_rsi(df["close"], self.rsi_period)
        df["chop"] = Indicators.calculate_choppiness_index(
            df["high"], df["low"], df["close"], self.chop_period
        )

        # Get current and previous values
        current = df.iloc[-1]
        previous = df.iloc[-2]

        signal = "NEUTRAL"
        confidence = 0
        reason = ""

        is_trending = current["chop"] < self.chop_threshold_trend

        if is_trending:
            # Buy signal: fast EMA crosses above slow EMA, RSI is bullish
            if (
                previous["ema_fast"] <= previous["ema_slow"]
                and current["ema_fast"] > current["ema_slow"]
                and current["rsi"] > 50
            ):
                signal = "BUY"
                confidence = 70  # Примерное значение
                reason = "EMA cross up in trending market with bullish RSI"
            # Sell signal: fast EMA crosses below slow EMA
            elif (
                previous["ema_fast"] >= previous["ema_slow"]
                and current["ema_fast"] < current["ema_slow"]
            ):
                signal = "SELL"
                confidence = 70  # Примерное значение
                reason = "EMA cross down in trending market"
        else:
            reason = f"Market is ranging (Choppiness Index: {current['chop']:.2f} >= {self.chop_threshold_trend})"

        return {
            "signal": signal,
            "confidence": confidence,
            "strategy": self.description,
            "metadata": {
                "symbol": kwargs.get("symbol", ""),
                "current_price": float(current["close"]),
                "indicators": {
                    "ema_fast": float(current["ema_fast"]),
                    "ema_slow": float(current["ema_slow"]),
                    "rsi": float(current["rsi"]),
                    "chop": float(current["chop"]),
                },
                "reason": reason,
            },
        }

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "fast_ema": {"value": self.fast_ema, "type": "int", "min": 5, "max": 50},
            "slow_ema": {"value": self.slow_ema, "type": "int", "min": 10, "max": 100},
            "rsi_period": {
                "value": self.rsi_period,
                "type": "int",
                "min": 7,
                "max": 30,
            },
            "chop_period": {
                "value": self.chop_period,
                "type": "int",
                "min": 7,
                "max": 30,
            },
            "chop_threshold_trend": {
                "value": self.chop_threshold_trend,
                "type": "float",
                "min": 30.0,
                "max": 70.0,
            },
        }
