from abc import ABC, abstractmethod
from typing import Any, Dict
from nexus_bus import get_bus

class BaseAgent(ABC):
    """
    V10 NEXUS Swarm — Base Agent
    ===========================
    Базовый абстрактный класс для всех агентов.
    Включает автоматический доступ к шине данных (NexusBus).
    """

    def __init__(self):
        self.bus = get_bus()

    @abstractmethod
    async def run(self, *args, **kwargs) -> Any:
        """Основная логика агента, которую должен реализовать каждый потомок."""
        pass

    def health_check(self) -> Dict[str, Any]:
        """Возвращает статус здоровья агента. Требуется для TradingService."""
        return {
            "status": "ok",
            "message": f"{self.__class__.__name__} is operational"
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
