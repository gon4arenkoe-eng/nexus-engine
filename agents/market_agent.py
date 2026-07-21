"""
V10 NEXUS Swarm — Market Agent
==============================
Сбор рыночных данных через асинхронные HTTP запросы (aiohttp).
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

import aiohttp
import pandas as pd

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class MarketAgent(BaseAgent):
    """Fetches and caches market data from exchanges."""

    def __init__(self):
        super().__init__("market")
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 60
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Lazy initialization of aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"User-Agent": "NEXUS-Swarm/1.0"},
            )
        return self._session

    async def run(self, symbol: str, timeframe: str,
                  exchange: str = "bingx", limit: int = 100) -> Optional[pd.DataFrame]:
        """Fetch OHLCV candles for a symbol."""
        cache_key = f"{exchange}:{symbol}:{timeframe}"

        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if datetime.utcnow() - cached["timestamp"] < timedelta(seconds=self._cache_ttl):
                self._record_run()
                return cached["data"]

        try:
            if exchange == "bingx":
                data = await self._fetch_bingx_klines(symbol, timeframe, limit)
            elif exchange == "binance":
                data = await self._fetch_binance_klines(symbol, timeframe, limit)
            else:
                raise ValueError(f"Unsupported exchange: {exchange}")

            if data is None or len(data) == 0:
                logger.warning(f"No data returned for {symbol} {timeframe}")
                return None

            df = self._normalize_ohlcv(data, exchange)

            self._cache[cache_key] = {
                "data": df,
                "timestamp": datetime.utcnow(),
            }

            self._record_run()
            return df

        except Exception as e:
            self._handle_error(e)
            return None

    async def _fetch_bingx_klines(self, symbol: str,
                                  timeframe: str, limit: int) -> List[List]:
        """Fetch klines from BingX API."""
        session = await self._get_session()

        url = "https://open-api.bingx.com/openApi/swap/v2/quote/klines"
        params = {
            "symbol": symbol,
            "interval": self._convert_timeframe(timeframe),
            "limit": limit,
        }

        async with session.get(url, params=params) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"BingX API error {response.status}: {text}")

            result = await response.json()
            return result.get("data", [])

    async def _fetch_binance_klines(self, symbol: str,
                                      timeframe: str, limit: int) -> List[List]:
        """Fetch klines from Binance API."""
        session = await self._get_session()

        url = "https://fapi.binance.com/fapi/v1/klines"
        params = {
            "symbol": symbol,
            "interval": timeframe,
            "limit": limit,
        }

        async with session.get(url, params=params) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"Binance API error {response.status}: {text}")

            return await response.json()

    def _normalize_ohlcv(self, data: List[List], exchange: str) -> pd.DataFrame:
        """Normalize exchange-specific format to standard DataFrame."""
        if exchange == "bingx":
            df = pd.DataFrame(data, columns=[
                "timestamp", "open", "high", "low", "close", "volume",
                "quote_volume", "taker_buy_volume", "taker_buy_quote", "ignore"
            ])
        else:
            df = pd.DataFrame(data, columns=[
                "timestamp", "open", "high", "low", "close", "volume",
                "close_time", "quote_volume", "trades", "taker_buy_volume",
                "taker_buy_quote", "ignore"
            ])

        numeric_cols = ["open", "high", "low", "close", "volume"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.set_index("timestamp")

        return df[["open", "high", "low", "close", "volume"]].dropna()

    def _convert_timeframe(self, tf: str) -> str:
        """Convert timeframe to exchange-specific format."""
        mapping = {
            "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m",
            "1h": "1h", "2h": "2h", "4h": "4h", "6h": "6h", "8h": "8h",
            "12h": "12h", "1d": "1d", "3d": "3d", "1w": "1w", "1M": "1M",
        }
        return mapping.get(tf, tf)

    async def get_current_price(self, symbol: str,
                                exchange: str = "bingx") -> Optional[float]:
        """Get current market price."""
        try:
            session = await self._get_session()

            if exchange == "bingx":
                url = "https://open-api.bingx.com/openApi/swap/v2/quote/ticker"
                params = {"symbol": symbol}

                async with session.get(url, params=params) as response:
                    result = await response.json()
                    return float(result["data"][0].get("lastPrice", 0))

            return None

        except Exception as e:
            self._handle_error(e)
            return None

    async def close(self):
        """Close aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
