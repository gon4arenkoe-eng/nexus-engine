"""
V10 NEXUS Swarm — NEXUS Bus
===========================
Простая in-memory шина данных для взаимодействия агентов.
НЕ Kafka, НЕ RabbitMQ — просто Python dict + callbacks.

Для масштаба >10 пользователей → миграция на Redis Pub/Sub.
Для масштаба >1000 пользователей → Kafka.
"""

import logging
from collections import defaultdict
from typing import Callable, Dict, List, Any

logger = logging.getLogger(__name__)

class NexusBus:
    """
    In-memory event bus for agent communication.

    Usage:
        bus = NexusBus()
        bus.subscribe("market.data", my_callback)
        bus.publish("market.data", {"symbol": "BTCUSDT", "price": 65000})
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._message_count = 0
        self._error_count = 0

    def subscribe(self, topic: str, callback: Callable[[Any], None]) -> None:
        """Subscribe callback to a topic."""
        self._subscribers[topic].append(callback)
        logger.debug(f"Subscribed to topic \'{topic}\': {callback.__name__}")

    def unsubscribe(self, topic: str, callback: Callable[[Any], None]) -> None:
        """Unsubscribe callback from a topic."""
        if callback in self._subscribers[topic]:
            self._subscribers[topic].remove(callback)
            logger.debug(f"Unsubscribed from topic \'{topic}\': {callback.__name__}")

    def publish(self, topic: str, message: Any) -> None:
        """
        Publish message to all subscribers of a topic.
        Errors in individual callbacks don\'t break others.
        """
        self._message_count += 1
        callbacks = self._subscribers.get(topic, [])

        if not callbacks:
            logger.warning(f"No subscribers for topic \'{topic}\'")
            return

        for callback in callbacks:
            try:
                callback(message)
            except Exception as e:
                self._error_count += 1
                logger.error(f"Error in callback for topic \'{topic}\': {e}", exc_info=True)

    def get_stats(self) -> Dict[str, Any]:
        """Return bus statistics."""
        return {
            "topics": list(self._subscribers.keys()),
            "subscriber_counts": {t: len(c) for t, c in self._subscribers.items()},
            "total_messages": self._message_count,
            "total_errors": self._error_count,
        }

# Singleton instance
_bus: NexusBus | None = None

def get_bus() -> NexusBus:
    """Get or create global bus instance."""
    global _bus
    if _bus is None:
        _bus = NexusBus()
    return _bus
