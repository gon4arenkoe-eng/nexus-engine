from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging
from nexus_bus import get_bus

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    def __init__(self):
        self.bus = get_bus()
        self.name = self.__class__.__name__
        self._status = "initialized"

    @abstractmethod
    async def run(self, *args, **kwargs) -> Any:
        pass

    def health_check(self) -> Dict[str, Any]:
        return {"status": "ok", "message": f"{self.name} is operational"}

    def _record_run(self, *args, **kwargs):
        # Placeholder for recording agent execution
        logger.debug(f"Agent {self.name} run recorded")

    def _handle_error(self, error: Exception, context: Optional[str] = None):
        # Placeholder for error handling
        logger.error(f"Agent {self.name} error in {context or 'unknown context'}: {error}")

    def _validate_data(self, data: Any, min_rows: int) -> bool:
        if data is None: return False
        if hasattr(data, 'empty') and data.empty: return False
        if hasattr(data, '__len__') and len(data) < min_rows: return False
        return True
