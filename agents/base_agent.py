"""
V10 NEXUS Swarm — Base Agent
=============================
Базовый класс для всех агентов.
Простой, без оверхеда. Прямые вызовы, не Pub/Sub.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base class for all NEXUS Swarm agents.

    Each agent:
    - Has a single responsibility
    - Can be tested independently
    - Reports health status
    - Logs all operations
    """

    def __init__(self, name: str):
        self.name = name
        self._status = "initialized"
        self._last_run: Optional[datetime] = None
        self._error_count = 0
        self._run_count = 0

    @abstractmethod
    def run(self, *args, **kwargs) -> Any:
        """
        Execute agent's main logic.
        Must be implemented by each agent.
        """
        pass

    def health_check(self) -> Dict[str, Any]:
        """Return agent health status."""
        return {
            "name": self.name,
            "status": self._status,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "run_count": self._run_count,
            "error_count": self._error_count,
            "healthy": self._status != "error",
        }

    def _set_status(self, status: str) -> None:
        """Update agent status with logging."""
        old_status = self._status
        self._status = status
        if status == "error":
            self._error_count += 1
        logger.info(f"Agent {self.name}: {old_status} -> {status}")

    def _record_run(self) -> None:
        """Record successful run."""
        self._last_run = datetime.utcnow()
        self._run_count += 1
        if self._status == "error":
            self._set_status("active")

    def _handle_error(self, error: Exception) -> None:
        """Handle and log agent error."""
        self._set_status("error")
        logger.error(f"Agent {self.name} error: {error}", exc_info=True)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name}, status={self._status})>"
