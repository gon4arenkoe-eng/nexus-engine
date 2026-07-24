import numpy as np
import pandas as pd
import logging
from typing import Dict, Any

from agents.base_agent import BaseAgent
from nexus_bus import get_bus
from services.exchange_service import (
    ExchangeService,
)  # Assuming this exists for data fetching

logger = logging.getLogger(__name__)


class MarketDataAgent(BaseAgent):
    """
    Agent responsible for fetching market data and publishing it to the Nexus Bus.
    """

    def __init__(self):
        self.bus = get_bus()
        self.exchange_service = ExchangeService()  # Initialize ExchangeService
        self.data_cache: Dict[str, pd.DataFrame] = {}

    async def run(
        self, symbol: str, timeframe: str = "1h", limit: int = 100
    ) -> pd.DataFrame:
        logger.info(f"MarketDataAgent: Fetching data for {symbol} ({timeframe})")
        try:
            # In a real scenario, client would be passed or retrieved via user/exchange ID
            # For now, we'll simulate fetching data
            # This part needs actual integration with ExchangeService and a client
            # For demonstration, we'll use dummy data or a simplified fetch
            # Example: klines = await self.exchange_service.fetch_klines(client, symbol, timeframe, limit)

            # --- Dummy data generation for demonstration ---
            if symbol not in self.data_cache:
                self.data_cache[symbol] = pd.DataFrame(
                    columns=["open", "high", "low", "close", "volume"]
                )

            new_data = pd.DataFrame(
                {
                    "open": [np.random.rand() * 100 + 100],
                    "high": [np.random.rand() * 100 + 100 + 5],
                    "low": [np.random.rand() * 100 + 100 - 5],
                    "close": [np.random.rand() * 100 + 100],
                    "volume": [np.random.rand() * 10000],
                },
                index=[pd.Timestamp.now()],
            )

            self.data_cache[symbol] = pd.concat(
                [self.data_cache[symbol], new_data], ignore_index=True
            ).tail(limit)
            df = self.data_cache[symbol]
            # --- End dummy data generation ---

            if df.empty:
                logger.warning(f"MarketDataAgent: No data fetched for {symbol}")
                return pd.DataFrame()

            self.bus.publish(
                "market.data",
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "data": df.to_dict(orient="records"),
                },
            )
            return df
        except Exception as e:
            logger.error(
                f"MarketDataAgent: Error fetching data for {symbol}: {e}", exc_info=True
            )
            return pd.DataFrame()

    def health_check(self) -> Dict[str, Any]:
        return {"status": "ok", "message": "Market Data Agent is operational"}
