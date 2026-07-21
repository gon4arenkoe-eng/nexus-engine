"""
V10 NEXUS Swarm — Mean Reversion Strategy
==========================================
Стратегия возврата к среднему.
- RSI перекупленность/перепроданность
- Bollinger Bands (отскок от границ)
- Используется в боковом рынке (ADX < 20)
"""

import pandas as pd
import numpy as np
from typing import Dict, Any

from strategies.base import BaseStrategy


class MeanReversionStrategy(BaseStrategy):
    """
    Mean Reversion strategy using RSI and Bollinger Bands.

    Signals:
    - BUY: RSI < 30 AND price touches lower Bollinger Band
    - SELL: RSI > 70 AND price touches upper Bollinger Band
    - NEUTRAL: No extreme conditions

    Best for: Ranging markets (ADX < 20)
    """

    description = "Mean Reversion (RSI + Bollinger Bands)"

    def __init__(self, rsi_period: int = 14, rsi_oversold: int = 30, rsi_overbought: int = 70,
                 bb_period: int = 20, bb_std: float = 2.0):
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.bb_period = bb_period
        self.bb_std = bb_std

    def analyze(self, data: pd.DataFrame) -> Dict[str, Any]:
        if not self._validate_data(data, min_rows=self.bb_period + 10):
            return self._neutral("Insufficient data")

        df = data.copy()

        # Calculate RSI
        df = self._calculate_rsi(df, self.rsi_period)

        # Calculate Bollinger Bands
        df = self._calculate_bollinger(df, self.bb_period, self.bb_std)

        current = df.iloc[-1]

        signal = "NEUTRAL"
        confidence = 0

        # BUY: RSI oversold + price at lower band
        if current["rsi"] < self.rsi_oversold and current["close"] <= current["bb_lower"]:
            signal = "BUY"
            # Confidence based on how oversold
            confidence = min(50 + int(self.rsi_oversold - current["rsi"]) * 2, 95)

        # SELL: RSI overbought + price at upper band
        elif current["rsi"] > self.rsi_overbought and current["close"] >= current["bb_upper"]:
            signal = "SELL"
            confidence = min(50 + int(current["rsi"] - self.rsi_overbought) * 2, 95)

        return {
            "signal": signal,
            "confidence": confidence,
            "strategy": "mean_reversion",
            "metadata": {
                "symbol": "",
                "current_price": float(current["close"]),
                "indicators": {
                    "rsi": float(current["rsi"]),
                    "bb_upper": float(current["bb_upper"]),
                    "bb_middle": float(current["bb_middle"]),
                    "bb_lower": float(current["bb_lower"]),
                    "bb_width": float(current["bb_width"]),
                },
                "levels": {
                    "sl_pct": 0.015,  # Tighter SL for mean reversion
                    "tp_pct": 0.03,
                }
            }
        }

    def _calculate_rsi(self, df: pd.DataFrame, period: int) -> pd.DataFrame:
        """Calculate RSI indicator."""
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.ewm(span=period, adjust=False).mean()
        avg_loss = loss.ewm(span=period, adjust=False).mean()

        rs = avg_gain / avg_loss
        df["rsi"] = 100 - (100 / (1 + rs))

        return df

    def _calculate_bollinger(self, df: pd.DataFrame, period: int, std: float) -> pd.DataFrame:
        """Calculate Bollinger Bands."""
        df["bb_middle"] = df["close"].rolling(window=period).mean()
        df["bb_std"] = df["close"].rolling(window=period).std()
        df["bb_upper"] = df["bb_middle"] + (df["bb_std"] * std)
        df["bb_lower"] = df["bb_middle"] - (df["bb_std"] * std)
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_middle"]

        return df

    def _neutral(self, reason: str) -> Dict[str, Any]:
        return {
            "signal": "NEUTRAL",
            "confidence": 0,
            "strategy": "mean_reversion",
            "metadata": {"reason": reason},
        }

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "rsi_period": {"value": self.rsi_period, "type": "int", "min": 7, "max": 30},
            "rsi_oversold": {"value": self.rsi_oversold, "type": "int", "min": 10, "max": 40},
            "rsi_overbought": {"value": self.rsi_overbought, "type": "int", "min": 60, "max": 90},
            "bb_period": {"value": self.bb_period, "type": "int", "min": 10, "max": 50},
            "bb_std": {"value": self.bb_std, "type": "float", "min": 1.0, "max": 4.0},
        }
