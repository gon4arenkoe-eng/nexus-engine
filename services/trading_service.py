import asyncio
import logging
from typing import Dict, Any, cast
from datetime import datetime

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
from agents.market_regime_agent import MarketRegimeAgent  # Новый импорт

from services.exchange_service import ExchangeService
from models import BotSettings

logger = logging.getLogger(__name__)

class TradingService:
    """Orchestrates complete trading cycle."""

    def __init__(self):
        self.config_agent = ConfigAgent()
        self.market_agent = MarketAgent()
        self.signal_agent = SignalAgent()
        self.risk_agent = RiskAgent()
        self.execution_agent = ExecutionAgent()
        self.position_agent = PositionAgent()
        self.pnl_agent = PnLAgent()
        self.ml_agent = MLAgent()
        self.sentiment_agent = SentimentAgent()
        self.notification_agent = NotificationAgent()
        self.market_regime_agent = MarketRegimeAgent()  # Инициализация нового агента
        self.exchange_service = ExchangeService()

    async def run_cycle(self, user_id: int, exchange_id: int) -> Dict[str, Any]:
        """Execute one trading cycle."""
        start_time = datetime.utcnow()
        results: Dict[str, Any] = {
            "user_id": user_id,
            "exchange_id": exchange_id,
            "timestamp": start_time.isoformat(),
            "steps": {},
            "success": False,
        }

        try:
            config_raw = self.config_agent.run(user_id)
            config = cast(Dict[str, Any], config_raw)
            steps = cast(Dict[str, Any], results["steps"])
            steps["config"] = {
                "status": "ok",
                "symbols": config.get("symbols", [])
            }

            client = await self.exchange_service.get_client(exchange_id)
            if not client:
                steps["exchange"] = {
                    "status": "error",
                    "message": "Failed to initialize client"
                }
                return results

            symbols = config.get("symbols", ["BTCUSDT", "ETHUSDT"])
            timeframe = config.get("timeframe", "4h")

            market_tasks = [
                self.market_agent.run(symbol, timeframe)
                for symbol in symbols
            ]
            market_data_list = await asyncio.gather(
                *market_tasks, return_exceptions=True
            )

            signals_executed: list[Dict[str, Any]] = []
            for i, symbol in enumerate(symbols):
                market_data = market_data_list[i]
                if isinstance(market_data, Exception) or market_data is None or (hasattr(market_data, 'empty') and market_data.empty):
                    logger.warning(f"TradingService: Skipping {symbol} due to missing or erroneous market data.")
                    continue

                # 1. Определяем режим рынка (Trend, Range или Squeeze)
                await self.market_regime_agent.run(symbol, market_data)

                # 2. Генерируем сигнал (SignalAgent выберет стратегию на основе режима рынка)
                signal = await self.signal_agent.run(
                    symbol,
                    market_data,
                    strategy_name=config.get("strategy"), # Если None, выберет автоматически
                    confidence_threshold=config.get("confidence_threshold", 50)
                )

                if not signal or signal["signal"] == "NEUTRAL":
                    continue

                # 3. Дополнительные фильтры (ML и Sentiment)
                if config.get("use_ml_filter", False):
                    if not self.ml_agent.run(signal, market_data):
                        continue

                if config.get("use_sentiment", False):
                    sentiment = self.sentiment_agent.run()
                    if sentiment and sentiment.get("fear_greed_index", 50) < 20:
                        continue

                # 4. Проверка позиций и баланса
                positions = await self.position_agent.run(user_id, exchange_id, client)
                balance = await client.get_balance()
                usdt_balance = balance.get("USDT", 0) if isinstance(balance, dict) else 0

                # 5. Риск-менеджмент
                risk_result = self.risk_agent.run(
                    signal, user_id, balance=usdt_balance,
                    open_positions=positions
                )

                if not risk_result.get("approved"):
                    signals_executed.append({
                        "symbol": symbol,
                        "signal": signal["signal"],
                        "status": "rejected",
                        "reason": risk_result.get("reason")
                    })
                    continue

                # 6. Исполнение ордера
                order = await self.execution_agent.run(
                    signal, risk_result, user_id, exchange_id, client, symbol
                )

                if order:
                    signals_executed.append({
                        "symbol": symbol,
                        "signal": signal["signal"],
                        "status": "executed",
                        "order_id": order.get("order_id")
                    })

                    # 7. Уведомление
                    await self.notification_agent.send_trade_notification(
                        user_id=user_id,
                        symbol=symbol,
                        side=signal["signal"],
                        size=order.get("size", 0),
                        price=order.get("price", 0)
                    )

            steps["signals"] = {
                "status": "ok",
                "count": len(signals_executed),
                "executed": signals_executed
            }

            positions = await self.position_agent.run(user_id, exchange_id, client)
            pnl = self.pnl_agent.run(user_id, positions)

            steps["positions"] = {"status": "ok", "count": len(positions)}
            steps["pnl"] = {
                "status": "ok",
                "daily_pnl": float(pnl) if pnl else 0
            }
            results["success"] = True

        except Exception as e:
            logger.error("Trading cycle error: %s", e, exc_info=True)
            steps = cast(Dict[str, Any], results["steps"])
            steps["error"] = str(e)

        return results

    async def start_bot(self, user_id: int) -> bool:
        """Start trading bot."""
        from app import db
        settings = BotSettings.query.filter_by(user_id=user_id).first()
        if not settings:
            return False
        settings.is_running = True
        settings.started_at = datetime.utcnow()
        db.session.commit()
        return True

    async def stop_bot(self, user_id: int) -> bool:
        """Stop trading bot."""
        from app import db
        settings = BotSettings.query.filter_by(user_id=user_id).first()
        if not settings:
            return False
        settings.is_running = False
        settings.stopped_at = datetime.utcnow()
        db.session.commit()
        return True

    async def get_status(self, user_id: int) -> Dict[str, Any]:
        """Get bot status."""
        settings = BotSettings.query.filter_by(user_id=user_id).first()
        if not settings:
            return {"error": "No settings found"}

        agents_health: Dict[str, Any] = {
            "config": self.config_agent.health_check(),
            "market": self.market_agent.health_check(),
            "signal": self.signal_agent.health_check(),
            "risk": self.risk_agent.health_check(),
            "execution": self.execution_agent.health_check(),
        }

        return {
            "is_running": settings.is_running,
            "started_at": settings.started_at.isoformat() if settings.started_at else None,
            "strategy": settings.strategy,
            "symbols": settings.get_symbols_list(),
            "agents_health": agents_health,
        }
