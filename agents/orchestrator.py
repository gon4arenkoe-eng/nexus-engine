"""
V10 NEXUS Swarm — Orchestrator
=================================
Управление жизненным циклом всех агентов.
Запускает агентов по расписанию, мониторит health.
"""

import asyncio
import logging
from typing import Dict, Any, cast
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

from services.exchange_service import ExchangeService

logger = logging.getLogger(__name__)


class Orchestrator(BaseAgent):
    """
    Central orchestrator for NEXUS Swarm.
    Manages agent lifecycle, scheduling, and coordination.
    """

    def __init__(self):
        super().__init__("orchestrator")
        self.agents: Dict[str, BaseAgent] = {}
        self.exchange_service = ExchangeService()
        self._running = False
        self._task = None

    def register_agent(self, name: str, agent: BaseAgent) -> None:
        """Register an agent with the orchestrator."""
        self.agents[name] = agent
        logger.info(f"Registered agent: {name}")

    def initialize_default_agents(self) -> None:
        """Initialize all default agents."""
        self.register_agent("config", ConfigAgent())
        self.register_agent("market", MarketAgent())
        self.register_agent("signal", SignalAgent())
        self.register_agent("risk", RiskAgent())
        self.register_agent("execution", ExecutionAgent())
        self.register_agent("position", PositionAgent())
        self.register_agent("pnl", PnLAgent())
        self.register_agent("ml", MLAgent())
        self.register_agent("sentiment", SentimentAgent())
        self.register_agent("notification", NotificationAgent())

    async def run(self, user_id: int, exchange_id: int) -> Dict[str, Any]:
        """Execute one full trading cycle."""
        if not self.agents:
            self.initialize_default_agents()

        results: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "exchange_id": exchange_id,
            "steps": {},
            "success": False,
        }

        try:
            # Step 1: Configuration
            config_result = await self.agents["config"].run(user_id)
            config = cast(Dict[str, Any], config_result)
            steps = cast(Dict[str, Any], results["steps"])
            steps["config"] = {"status": "ok", "symbols": config.get("symbols", [])}

            # Step 2: Get exchange client
            client = self.exchange_service.get_client(exchange_id)
            if not client:
                steps["exchange"] = {
                    "status": "error",
                    "message": "Failed to initialize client",
                }
                return results

            # Step 3: Fetch market data
            symbols = config.get("symbols", ["BTCUSDT", "ETHUSDT"])
            timeframe = config.get("timeframe", "4h")

            market_tasks = [
                await self.agents["market"].run(symbol, timeframe, exchange="bingx")
                for symbol in symbols
            ]
            market_data_list = asyncio.gather(
                *market_tasks, return_exceptions=True
            )

            # Step 4: Process signals
            signals_executed: list[Dict[str, Any]] = []
            for symbol, market_data in zip(symbols, market_data_list):
                if isinstance(market_data, Exception) or market_data is None:
                    continue

                signal = await self.agents["signal"].run(
                    market_data,
                    strategy_name=config.get("strategy", "ema_cross"),
                    confidence_threshold=config.get("confidence_threshold", 50),
                )

                if not signal or signal["signal"] == "NEUTRAL":
                    continue

                # ML filter
                if config.get("use_ml_filter", False):
                    if not self.agents["ml"].run(signal, market_data):
                        continue

                # Risk check
                positions = await self.agents["position"].run(
                    user_id, exchange_id, client
                )
                balance = client.get_balance()
                usdt_balance = (
                    balance.get("USDT", 0) if isinstance(balance, dict) else 0
                )

                risk_result = self.agents["risk"].run(
                    signal, user_id, balance=usdt_balance, open_positions=positions
                )

                if not risk_result.get("approved"):
                    signals_executed.append(
                        {
                            "symbol": symbol,
                            "signal": signal["signal"],
                            "status": "rejected",
                            "reason": risk_result.get("reason"),
                        }
                    )
                    continue

                # Execute
                order = await self.agents["execution"].run(
                    signal, risk_result, user_id, exchange_id, client, symbol
                )

                if order:
                    signals_executed.append(
                        {
                            "symbol": symbol,
                            "signal": signal["signal"],
                            "status": "executed",
                            "order_id": order.get("order_id"),
                        }
                    )

                    notification_agent = self.agents["notification"]
                    if hasattr(notification_agent, "send_trade_notification"):
                        notification_agent.send_trade_notification(
                            user_id=user_id,
                            symbol=symbol,
                            side=signal["signal"],
                            size=order.get("size", 0),
                            price=order.get("price", 0),
                        )

            steps["signals"] = {
                "status": "ok",
                "count": len(signals_executed),
                "executed": signals_executed,
            }

            # Update positions and PnL
            positions = await self.agents["position"].run(user_id, exchange_id, client)
            pnl = self.agents["pnl"].run(user_id, positions)

            steps["positions"] = {"status": "ok", "count": len(positions)}
            steps["pnl"] = {"status": "ok", "daily_pnl": float(pnl) if pnl else 0}
            results["success"] = True

        except Exception as e:
            logger.error(f"Orchestrator error: {e}", exc_info=True)
            steps = cast(Dict[str, Any], results["steps"])
            steps["error"] = str(e)

        return results

    async def start(self, user_id: int, exchange_id: int, interval: int = 60):
        """Start continuous trading loop."""
        self._running = True
        logger.info(f"Orchestrator started for user {user_id}")

        while self._running:
            try:
                await self.run(user_id, exchange_id)
await                 await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Cycle error: {e}")
await                 await asyncio.sleep(5)

    def stop(self):
        """Stop trading loop."""
        self._running = False
        logger.info("Orchestrator stopped")

    def health_check(self) -> Dict[str, Any]:
        """Check health of all agents."""
        health: Dict[str, Any] = {
            "name": self.name,
            "status": self._status,
            "agents": {},
            "healthy": True,
        }

        agents_health = cast(Dict[str, Any], health["agents"])
        for name, agent in self.agents.items():
            agent_health = agent.health_check()
            agents_health[name] = agent_health
            if not agent_health["healthy"]:
                health["healthy"] = False

        return health
