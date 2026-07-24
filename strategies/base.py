import pandas as pd
from typing import Dict, Any


class BaseStrategy:
    description: str = "Base Strategy"

    def analyze(self, data: Any, **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError

    def _validate_data(self, data: pd.DataFrame, min_rows: int) -> bool:
        if data is None or data.empty or len(data) < min_rows:
            return False
        return True

    def _neutral(self, reason: str, strategy_name: str = "") -> Dict[str, Any]:
        return {
            "signal": "NEUTRAL",
            "confidence": 0,
            "strategy": strategy_name or self.description,
            "metadata": {"reason": reason},
        }
