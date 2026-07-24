import logging
from typing import Dict, Any, Optional
from strategies.base import BaseStrategy

logger = logging.getLogger(__name__)


class StatisticalArbitrageStrategy(BaseStrategy):
    """
    V10 NEXUS Swarm — Statistical Arbitrage (Pairs Trading)
    =======================================================
    Логика: Ищет отклонения в спреде между двумя коррелирующими активами.
    """

    description: str = "Statistical Arbitrage (Pairs Trading)"

    def __init__(
        self,
        z_score_period: int = 20,
        entry_threshold: float = 2.0,
        exit_threshold: float = 0.5,
    ):
        self.z_score_period = z_score_period
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold

    def analyze(self, data: Any, **kwargs: Any) -> Dict[str, Any]:
        data_b = kwargs.get('data_b')
        symbol = kwargs.get('symbol', 'Unknown')
        symbol_b = kwargs.get('symbol_b', 'Unknown')

        if data_b is None or not self._validate_data(data, min_rows=self.z_score_period + 2) or \
           not self._validate_data(data_b, min_rows=self.z_score_period + 2):
            return self._neutral("Insufficient data for pair trading", self.description)

        common_index = data.index.intersection(data_b.index)
        if len(common_index) < self.z_score_period:
            return self._neutral("Insufficient common historical data", self.description)

        df_a = data.loc[common_index].copy()
        df_b = data_b.loc[common_index].copy()
        ratio = df_a["close"] / df_b["close"]
        mean = ratio.rolling(window=self.z_score_period).mean()
        std = ratio.rolling(window=self.z_score_period).std()
        z_score = (ratio - mean) / std
        current_z = z_score.iloc[-1]
        
        signal = "NEUTRAL"
        confidence = 0
        if current_z > self.entry_threshold:
            signal = "SELL"
            confidence = min(100, int((abs(current_z) / self.entry_threshold) * 50))
        elif current_z < -self.entry_threshold:
            signal = "BUY"
            confidence = min(100, int((abs(current_z) / self.entry_threshold) * 50))
        elif abs(current_z) < self.exit_threshold:
            signal = "EXIT"
            confidence = 100

        return {
            "signal": signal,
            "confidence": confidence,
            "strategy": self.description,
            "metadata": {
                "z_score": round(current_z, 4),
                "symbol_a": symbol,
                "symbol_b": symbol_b,
                "ratio": round(ratio.iloc[-1], 4)
            },
        }
