import pandas as pd
import logging
from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent
from strategies.ema_cross import EmaCrossStrategy
from strategies.trend_following_chop import TrendFollowingChopStrategy
from strategies.statistical_arbitrage import StatisticalArbitrageStrategy
from strategies.bollinger_squeeze import BollingerSqueezeStrategy
from nexus_bus import get_bus

logger = logging.getLogger(__name__)


class SignalAgent(BaseAgent):
    """
    Agent responsible for generating trading signals based on market data and selected strategy.
    It can dynamically choose a strategy based on the detected market regime.
    """

    def __init__(self):
        self.strategies = {
            "ema_cross": EmaCrossStrategy(),
            "trend_following_chop": TrendFollowingChopStrategy(),
            "statistical_arbitrage": StatisticalArbitrageStrategy(),
            "bollinger_squeeze": BollingerSqueezeStrategy(),
        }
        self.bus = get_bus()
        self.market_regimes: Dict[str, str] = {}
        self.bus.subscribe("market.regime", self._on_market_regime_update)

    def _on_market_regime_update(self, message: Dict[str, Any]):
        symbol = message.get("symbol")
        regime = message.get("regime")
        if symbol and regime:
            self.market_regimes[symbol] = regime
            logger.debug(f"SignalAgent: Updated market regime for {symbol} to {regime}")

    async def run(
        self,
        symbol: str,
        data: pd.DataFrame,
        pair_data: Optional[Dict[str, pd.DataFrame]] = None,
        strategy_name: Optional[str] = None,
        confidence_threshold: int = 50,
    ) -> Dict[str, Any]:
        current_regime = self.market_regimes.get(symbol, "NEUTRAL")
        selected_strategy_name = strategy_name

        # Dynamic strategy selection based on market regime if no specific strategy is provided
        if not selected_strategy_name:
            if current_regime == "TRENDING":
                selected_strategy_name = "trend_following_chop"
            elif current_regime == "RANGING":
                # Statistical arbitrage needs pair data, so ensure it's available
                if pair_data and len(pair_data) == 2:
                    selected_strategy_name = "statistical_arbitrage"
                else:
                    logger.warning(
                        f"SignalAgent: RANGING regime detected for {symbol}, but no pair data for statistical arbitrage. Falling back to EMA Cross."
                    )
                    selected_strategy_name = "ema_cross"  # Fallback
            elif current_regime == "VOLATILE_SQUEEZE":
                selected_strategy_name = "bollinger_squeeze"
            else:
                selected_strategy_name = "ema_cross"  # Default fallback

        strategy = self.strategies.get(selected_strategy_name)
        if not strategy:
            logger.error(f"SignalAgent: Strategy '{selected_strategy_name}' not found.")
            return self._neutral_signal(symbol, "Strategy not found")

        logger.info(
            f"SignalAgent: Analyzing {symbol} with {selected_strategy_name} in {current_regime} regime."
        )

        # Special handling for statistical arbitrage which requires two dataframes
        if selected_strategy_name == "statistical_arbitrage" and pair_data:
            symbol_a = list(pair_data.keys())[0]
            symbol_b = list(pair_data.keys())[1]
            signal_result = strategy.analyze(
                pair_data[symbol_a],
                pair_data[symbol_b],
                symbol_a=symbol_a,
                symbol_b=symbol_b,
            )
        else:
            signal_result = strategy.analyze(data, symbol=symbol)

        if signal_result["confidence"] >= confidence_threshold:
            self.bus.publish("signal.generated", signal_result)
            return signal_result
        else:
            return self._neutral_signal(
                symbol,
                f"Confidence below threshold ({signal_result["confidence"]} < {confidence_threshold})",
            )

    def _neutral_signal(self, symbol: str, reason: str) -> Dict[str, Any]:
        return {
            "signal": "NEUTRAL",
            "confidence": 0,
            "strategy": "",
            "metadata": {"symbol": symbol, "reason": reason},
        }

    def health_check(self) -> Dict[str, Any]:
        return {"status": "ok", "message": "Signal Agent is operational"}
