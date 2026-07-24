import pandas as pd
from typing import Dict, Any

from strategies.base import BaseStrategy
from utils.indicators import Indicators


class BollingerSqueezeStrategy(BaseStrategy):
    """
    Bollinger Bands Squeeze strategy.

    Signals:
    - BUY: Price breaks above Upper Bollinger Band after a squeeze (BB inside KC).
    - SELL: Price breaks below Lower Bollinger Band after a squeeze (BB inside KC).
    - NEUTRAL: No squeeze or no breakout.
    """

    description = "Bollinger Bands Squeeze"

    def __init__(
        self,
        bb_period: int = 20,
        bb_std_dev: int = 2,
        kc_period: int = 20,
        kc_atr_multiplier: float = 1.5,
    ):
        self.bb_period = bb_period
        self.bb_std_dev = bb_std_dev
        self.kc_period = kc_period
        self.kc_atr_multiplier = kc_atr_multiplier

    def analyze(self, data: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        if not self._validate_data(
            data, min_rows=max(self.bb_period, self.kc_period) + 2
        ):
            return self._neutral("Insufficient data", self.description)

        df = data.copy()

        # Calculate Bollinger Bands
        df["bb_sma"], df["upper_bb"], df["lower_bb"] = (
            Indicators.calculate_bollinger_bands(
                df["close"], self.bb_period, self.bb_std_dev
            )
        )

        # Calculate Keltner Channels
        df["kc_ema"], df["upper_kc"], df["lower_kc"] = (
            Indicators.calculate_keltner_channels(
                df["high"],
                df["low"],
                df["close"],
                self.kc_period,
                self.kc_atr_multiplier,
            )
        )

        # Get current and previous values
        current = df.iloc[-1]
        previous = df.iloc[-2]

        signal = "NEUTRAL"
        confidence = 0
        reason = ""

        # Check for squeeze condition: Bollinger Bands are inside Keltner Channels
        is_squeeze = (current["lower_bb"] > current["lower_kc"]) and (
            current["upper_bb"] < current["upper_kc"]
        )

        if is_squeeze:
            reason = f"Squeeze detected. Current BB width: {current['upper_bb'] - current['lower_bb']:.2f}"
            # Check for breakout after squeeze
            if (
                current["close"] > current["upper_bb"]
                and previous["close"] <= previous["upper_bb"]
            ):
                signal = "BUY"
                confidence = 85  # Высокая уверенность в прорыве вверх
                reason += ", Price broke above Upper BB"
            elif (
                current["close"] < current["lower_bb"]
                and previous["close"] >= previous["lower_bb"]
            ):
                signal = "SELL"
                confidence = 85  # Высокая уверенность в прорыве вниз
                reason += ", Price broke below Lower BB"
        else:
            reason = f"No squeeze. Current BB width: {current['upper_bb'] - current['lower_bb']:.2f}"

        return {
            "signal": signal,
            "confidence": confidence,
            "strategy": self.description,
            "metadata": {
                "symbol": kwargs.get("symbol", ""),
                "current_price": float(current["close"]),
                "indicators": {
                    "upper_bb": float(current["upper_bb"]),
                    "lower_bb": float(current["lower_bb"]),
                    "upper_kc": float(current["upper_kc"]),
                    "lower_kc": float(current["lower_kc"]),
                    "is_squeeze": is_squeeze,
                },
                "reason": reason,
            },
        }

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "bb_period": {"value": self.bb_period, "type": "int", "min": 10, "max": 50},
            "bb_std_dev": {"value": self.bb_std_dev, "type": "int", "min": 1, "max": 3},
            "kc_period": {"value": self.kc_period, "type": "int", "min": 10, "max": 50},
            "kc_atr_multiplier": {
                "value": self.kc_atr_multiplier,
                "type": "float",
                "min": 1.0,
                "max": 3.0,
            },
        }
