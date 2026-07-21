"""
V10 NEXUS Swarm — Orchestrator
================================
Управление жизненным циклом всех агентов.
Запускает агентов по расписанию, мониторит health, обрабатывает ошибки.

Принцип: Прямые вызовы, НЕ Pub/Sub.
Порядок выполнения: Market -> Signal -> ML -> Risk -> Execution -> Position -> PnL -> Notification
"""

import asyncio
import threading
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from agents.base_agent import BaseAgent
from agents.config_agent import ConfigAgent
from agents.market_agent import MarketAgent
from agents.signal_agent import SignalAgent
from agents.risk_agent import RiskAgent
from agents.execution_agent import ExecutionAgent
from agents.position_agent import PositionAgent
from agents.pnl_agent import PnLAgent
from agents.ml_agent import MLAgent
from agents.sentiment_agent import SentimentAgent
from agents.notification_agent import NotificationAgent
from nexus_bus import NexusBus

import logging

logger = logging.getLogger(__name__)


class SwarmOrchestrator:
    """
    Central orchestrator for NEXUS Swarm agents.

    Manages:
    - Agent lifecycle (init, start, stop)
    - Trading tick execution
    - Health monitoring
    - Error recovery
    """

    def __init__(self):
        self.bus = NexusBus()

        # Initialize all agents
        self.agents: Dict[str, BaseAgent] = {
            "config": ConfigAgent(),
            "market": MarketAgent(),
            "signal": SignalAgent(),
            "ml": MLAgent(),
            "risk": RiskAgent(),
            "execution": ExecutionAgent(),
            "position": PositionAgent(),
            "pnl": PnLAgent(),
            "sentiment": SentimentAgent(),
            "notification": NotificationAgent(),
        }

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._tick_interval = 60  # seconds between ticks
        self._last_tick = None

        # Subscribe to bus events for logging
        self.bus.subscribe("order.executed", self._on_order_executed)
        self.bus.subscribe("position.updated", self._on_position_updated)

    # === Lifecycle Management ===

    def start(self, user_id: int, exchange_id: int) -> None:
        """Start trading loop in background thread."""
        if self._running:
            logger.warning("Orchestrator already running")
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop,
            args=(user_id, exchange_id),
            daemon=True,
            name="NEXUS-Swarm-Orchestrator"
        )
        self._thread.start()
        logger.info(f"Orchestrator started for user {user_id}, exchange {exchange_id}")

    def stop(self) -> None:
        """Stop trading loop."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info("Orchestrator stopped")

    def is_running(self) -> bool:
        """Check if orchestrator is running."""
        return self._running

    # === Main Trading Loop ===

    def _run_loop(self, user_id: int, exchange_id: int) -> None:
        """Main trading loop — runs in background thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            while self._running:
                start_time = time.time()

                try:
                    loop.run_until_complete(self._tick(user_id, exchange_id))
                    self._last_tick = datetime.utcnow()
                except Exception as e:
                    logger.error(f"Tick error: {e}", exc_info=True)

                # Adaptive sleep
                elapsed = time.time() - start_time
                sleep_time = max(1, self._tick_interval - elapsed)
                time.sleep(sleep_time)

        finally:
            loop.close()

    async def _tick(self, user_id: int, exchange_id: int) -> None:
        """
        Execute one trading tick.

        Flow:
        1. Get config
        2. Fetch market data (async)
        3. Generate signal
        4. ML filter
        5. Sentiment check (optional)
        6. Risk check
        7. Execute order (async)
        8. Update positions
        9. Calculate PnL
        10. Send notifications
        """
        # 1. Config
        config = self.agents["config"].run(user_id, action="get")
        if not config.get("is_running"):
            return

        symbols = config.get("symbols", [])
        timeframe = config.get("timeframe", "4h")
        confidence = config.get("confidence_threshold", 50)
        strategy = config.get("strategy", "ema_cross")
        use_ml = config.get("use_ml_filter", False)
        use_sentiment = config.get("use_sentiment", False)

        # Get exchange info
        from models import Exchange
        from app import db
        exchange = Exchange.query.get(exchange_id)
        if not exchange:
            logger.error(f"Exchange {exchange_id} not found")
            return

        # 2. Fetch market data for all symbols (parallel)
        market_tasks = [
            self.agents["market"].run(exchange.name, symbol, timeframe)
            for symbol in symbols
        ]
        market_results = await asyncio.gather(*market_tasks, return_exceptions=True)

        # 3-10. Process each symbol
        for symbol, market_data in zip(symbols, market_results):
            if isinstance(market_data, Exception):
                logger.error(f"Market data error for {symbol}: {market_data}")
                continue

            await self._process_symbol(
                user_id, exchange_id, symbol, market_data,
                strategy, confidence, use_ml, use_sentiment
            )

        # Update PnL for all positions
        # Get mark prices from market data
        mark_prices = {}
        for symbol, data in zip(symbols, market_results):
            if not isinstance(data, Exception):
                # Extract last price from ticker or candles
                mark_prices[symbol] = self._extract_price(data)

        self.agents["pnl"].run("calculate_unrealized", user_id, mark_prices=mark_prices)

    async def _process_symbol(self, user_id: int, exchange_id: int,
                             symbol: str, market_data: Dict,
                             strategy: str, confidence: int,
                             use_ml: bool, use_sentiment: bool) -> None:
        """Process single symbol through agent pipeline."""

        # 3. Generate signal
        signal = self.agents["signal"].run(
            market_data, strategy_name=strategy, confidence_threshold=confidence
        )

        if not signal:
            return  # No signal

        # 4. ML filter (if enabled)
        if use_ml:
            ml_pass = self.agents["ml"].run(signal, market_data)
            if not ml_pass:
                logger.info(f"Signal for {symbol} rejected by ML filter")
                return

        # 5. Sentiment check (if enabled)
        if use_sentiment:
            sentiment = await self.agents["sentiment"].run()
            if signal["direction"] == "LONG" and self.agents["sentiment"].is_bearish(sentiment):
                logger.info(f"LONG signal for {symbol} rejected due to bearish sentiment")
                return
            if signal["direction"] == "SHORT" and self.agents["sentiment"].is_bullish(sentiment):
                logger.info(f"SHORT signal for {symbol} rejected due to bullish sentiment")
                return

        # 6. Risk check
        # Get balance (simplified — in real implementation fetch from exchange)
        balance = 100000.0  # Placeholder
        risk_result = self.agents["risk"].run(signal, user_id, balance)

        if not risk_result.get("approved"):
            logger.info(f"Signal for {symbol} rejected by risk: {risk_result.get('reason')}")
            return

        # 7. Execute order (async)
        order_result = await self.agents["execution"].run(
            signal, user_id, exchange_id, risk_result
        )

        if not order_result or order_result.get("status") != "FILLED":
            logger.warning(f"Order execution failed for {symbol}: {order_result}")
            return

        # Publish event
        self.bus.publish("order.executed", order_result)

        # 8. Update positions
        position_data = {
            "exchange_id": exchange_id,
            **order_result,
            "stop_loss": signal.get("stop_loss"),
            "take_profit": signal.get("take_profit"),
            "leverage": risk_result.get("adjusted_leverage", 1),
        }
        self.agents["position"].run("open", user_id, position_data)

        # 9. Record realized PnL (if closing)
        # (For new positions, this is 0)

        # 10. Notify
        await self.agents["notification"].run("order_executed", order_result)
        await self.agents["notification"].run("signal", signal)

    def _extract_price(self, market_data: Dict) -> float:
        """Extract current price from market data."""
        # Try ticker first
        ticker = market_data.get("ticker", {})
        if ticker.get("lastPrice"):
            return float(ticker["lastPrice"])

        # Fallback to last candle close
        candles = market_data.get("candles", [])
        if candles:
            return float(candles[-1].get("close", 0))

        return 0.0

    # === Event Handlers ===

    def _on_order_executed(self, data: Dict) -> None:
        """Handle order executed event."""
        logger.info(f"Order executed: {data.get('symbol')} {data.get('side')}")

    def _on_position_updated(self, data: Dict) -> None:
        """Handle position updated event."""
        logger.info(f"Position updated: {data.get('symbol')} {data.get('status')}")

    # === Health & Status ===

    def get_health(self) -> Dict[str, Any]:
        """Get health status of all agents."""
        return {
            "orchestrator": {
                "running": self._running,
                "last_tick": self._last_tick.isoformat() if self._last_tick else None,
                "tick_interval": self._tick_interval,
            },
            "agents": {name: agent.health_check() for name, agent in self.agents.items()},
            "bus": self.bus.get_stats(),
        }

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get agent by name."""
        return self.agents.get(name)
