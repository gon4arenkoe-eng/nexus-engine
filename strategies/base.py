from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseStrategy(ABC):
    """
    V10 NEXUS Swarm — Base Strategy
    ==============================
    Базовый класс для всех торговых стратегий.
    """

    description: str = "Base Strategy"

    @abstractmethod
    def analyze(self, data: Any, **kwargs: Any) -> Dict[str, Any]:
        """
        Основной метод анализа данных и генерации сигнала.
        """
        pass

    def _neutral(self, reason: str, strategy_name: str = "") -> Dict[str, Any]:
        """Возвращает нейтральный сигнал."""
        return {
            "signal": "NEUTRAL",
            "confidence": 0,
            "strategy": strategy_name or self.description,
            "reason": reason,
        }

    def _validate_data(self, data: Any, min_rows: int) -> bool:
        """Вспомогательный метод для проверки наличия данных."""
        if data is None:
            return False
        if hasattr(data, 'empty') and data.empty:
            return False
        if hasattr(data, '__len__') and len(data) < min_rows:
            return False
        return True
