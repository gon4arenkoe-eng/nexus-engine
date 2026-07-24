import pandas as pd
from typing import Dict, Any, Optional

from strategies.base import BaseStrategy
from utils.indicators import Indicators


class StatisticalArbitrageStrategy(BaseStrategy):
    """
    Statistical Arbitrage (Pairs Trading) strategy using Z-Score.

    Signals:
    - BUY_A_SELL_B: Z-Score falls below lower threshold (pair is oversold, expect mean reversion).
    - SELL_A_BUY_B: Z-Score rises above upper threshold (pair is overbought, expect mean reversion).
    - CLOSE_POSITIONS: Z-Score returns to neutral zone.
    - NEUTRAL: Z-Score within thresholds or insufficient data.
    """

    description = "Statistical Arbitrage (Pairs Trading)"

    def __init__(
        self,
        z_score_period: int = 60,
        entry_threshold: float = 2.0,
        exit_threshold: float = 0.5,
    ):
        self.z_score_period = z_score_period
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold

    def analyze(
        self, data: pd.DataFrame, data_b: Optional[pd.DataFrame] = None, **kwargs
    ) -> Dict[str, Any]:
        # For statistical arbitrage, we need data for two symbols
        if data_b is None or not self._validate_data(
            data, min_rows=self.z_score_period + 2
        ) or not self._validate_data(data_b, min_rows=self.z_score_period + 2):
            return self._neutral("Insufficient data for pair trading", self.description)

        # Ensure dataframes are aligned by index (time)
        common_index = data.index.intersection(data_b.index)
        if len(common_index) < self.z_score_period + 2:
            return self._neutral(
                "Insufficient common data for pair trading", self.description
            )

        df_a = data.loc[common_index].copy()
        df_b = data_b.loc[common_index].copy()

        # Calculate spread (simple difference for now, can be log ratio)
        spread = df_a["close"] - df_b["close"]
        df_a["z_score"] = Indicators.calculate_z_score(spread, self.z_score_period)

        current_z_score = df_a["z_score"].iloc[-1]
        previous_z_score = df_a["z_score"].iloc[-2]

        signal = "NEUTRAL"
        confidence = 0
        reason = ""

        # Entry signals
        if (
            current_z_score < -self.entry_threshold
            and previous_z_score >= -self.entry_threshold
        ):
            signal = "BUY_A_SELL_B"  # Pair is oversold, buy A, sell B
            confidence = 80
            reason = f"Z-Score ({current_z_score:.2f}) crossed below -{self.entry_threshold} (oversold)"
        elif (
            current_z_score > self.entry_threshold
            and previous_z_score <= self.entry_threshold
        ):
            signal = "SELL_A_BUY_B"  # Pair is overbought, sell A, buy B
            confidence = 80
            reason = f"Z-Score ({current_z_score:.2f}) crossed above {self.entry_threshold} (overbought)"

        # Exit signals (mean reversion)
        elif -self.exit_threshold < current_z_score < self.exit_threshold:
            # Only generate close signal if there was an open position (handled by PortfolioManager)
            signal = "CLOSE_POSITIONS"
            confidence = 60
            reason = f"Z-Score ({current_z_score:.2f}) returned to neutral zone"

        return {
            "signal": signal,
            "confidence": confidence,
            "strategy": self.description,
            "metadata": {
                "symbol_a": kwargs.get("symbol_a", ""),
                "symbol_b": kwargs.get("symbol_b", ""),
                "current_z_score": float(current_z_score),
                "current_price_a": float(df_a["close"].iloc[-1]),
                "current_price_b": float(df_b["close"].iloc[-1]),
                "reason": reason,
            },
        }

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "z_score_period": {
                "value": self.z_score_period,
                "type": "int",
                "min": 30,
                "max": 120,
            },
            "entry_threshold": {
                "value": self.entry_threshold,
                "type": "float",
                "min": 1.0,
                "max": 3.0,
            },
            "exit_threshold": {
                "value": self.exit_threshold,
                "type": "float",
                "min": 0.1,
                "max": 1.0,
            },
        }
