import pandas as pd
from typing import Dict, Any
import logging

from agents.base_agent import BaseAgent
from utils.indicators import Indicators
from nexus_bus import get_bus

logger = logging.getLogger(__name__)


class MarketRegimeAgent(BaseAgent):
    """
    Agent responsible for detecting the current market regime (TRENDING, RANGING, VOLATILE_SQUEEZE).
    Publishes the detected regime to the Nexus Bus.
    """

    def __init__(
        self,
        chop_period: int = 14,
        chop_threshold_trend: float = 50.0,
        chop_threshold_range: float = 61.8,
        bb_period: int = 20,
        bb_std_dev: int = 2,
        kc_period: int = 20,
        kc_atr_multiplier: float = 1.5,
    ):
        self.chop_period = chop_period
        self.chop_threshold_trend = chop_threshold_trend
        self.chop_threshold_range = chop_threshold_range
        self.bb_period = bb_period
        self.bb_std_dev = bb_std_dev
        self.kc_period = kc_period
        self.kc_atr_multiplier = kc_atr_multiplier
        self.bus = get_bus()

    async def run(self, symbol: str, data: pd.DataFrame) -> Dict[str, Any]:
        if not self._validate_data(
            data, min_rows=max(self.chop_period, self.bb_period, self.kc_period) + 2
        ):
            logger.warning(f"MarketRegimeAgent: Insufficient data for {symbol}")
            self.bus.publish(
                "market.regime",
                {"symbol": symbol, "regime": "NEUTRAL", "reason": "Insufficient data"},
            )
            return {
                "symbol": symbol,
                "regime": "NEUTRAL",
                "reason": "Insufficient data",
            }

        df = data.copy()

        # Calculate indicators
        df["chop"] = Indicators.calculate_choppiness_index(
            df["high"], df["low"], df["close"], self.chop_period
        )
        df["bb_sma"], df["upper_bb"], df["lower_bb"] = (
            Indicators.calculate_bollinger_bands(
                df["close"], self.bb_period, self.bb_std_dev
            )
        )
        df["kc_ema"], df["upper_kc"], df["lower_kc"] = (
            Indicators.calculate_keltner_channels(
                df["high"],
                df["low"],
                df["close"],
                self.kc_period,
                self.kc_atr_multiplier,
            )
        )

        current = df.iloc[-1]

        regime = "NEUTRAL"
        reason = ""

        if current["chop"] < self.chop_threshold_trend:
            regime = "TRENDING"
            reason = (
                f"Choppiness Index ({current['chop']:.2f}) indicates trending market."
            )
        elif current["chop"] > self.chop_threshold_range:
            regime = "RANGING"
            reason = (
                f"Choppiness Index ({current['chop']:.2f}) indicates ranging market."
            )
        else:
            # Check for Bollinger Squeeze condition
            is_squeeze = (current["lower_bb"] > current["lower_kc"]) and (
                current["upper_bb"] < current["upper_kc"]
            )
            if is_squeeze:
                regime = "VOLATILE_SQUEEZE"
                reason = (
                    "Bollinger Bands are inside Keltner Channels (squeeze detected)."
                )
            else:
                regime = "NEUTRAL"
                reason = "Market regime is undefined."

        result = {"symbol": symbol, "regime": regime, "reason": reason}
        self.bus.publish("market.regime", result)
        logger.info(f"MarketRegimeAgent: {symbol} - Detected regime: {regime}")
        return result

    def health_check(self) -> Dict[str, Any]:
        return {"status": "ok", "message": "Market Regime Agent is operational"}

    def _validate_data(self, data: pd.DataFrame, min_rows: int) -> bool:
        return not (data is None or data.empty or len(data) < min_rows)
