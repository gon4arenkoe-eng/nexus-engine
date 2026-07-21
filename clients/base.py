"""
V10 NEXUS Swarm — Base Exchange Client
=======================================
Абстрактный базовый класс для всех API клиентов бирж.
Все клиенты используют aiohttp для асинхронных запросов.
"""

import aiohttp
import hmac
import hashlib
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class BaseExchangeClient(ABC):
    """
    Abstract base class for exchange API clients.

    All exchange clients must implement:
    - Authentication
    - Market data fetching
    - Order placement
    - Position management
    - Balance fetching
    """

    def __init__(self, api_key: str, api_secret: str, passphrase: Optional[str] = None,
                 demo: bool = True, base_url: Optional[str] = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.demo = demo
        self.base_url = base_url or self._get_base_url()
        self._session: Optional[aiohttp.ClientSession] = None

    @abstractmethod
    def _get_base_url(self) -> str:
        """Return base API URL for the exchange."""
        pass

    async def _get_session(self) -> aiohttp.ClientSession:
        """Lazy aiohttp session initialization."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"User-Agent": "NEXUS-Swarm/1.0"},
            )
        return self._session

    @abstractmethod
    def _sign_request(self, method: str, endpoint: str, params: Dict[str, Any]) -> Dict[str, str]:
        """Generate authentication headers for the request."""
        pass

    async def _request(self, method: str, endpoint: str, params: Optional[Dict] = None,
                       signed: bool = False) -> Dict[str, Any]:
        """
        Make HTTP request to exchange API.

        Returns:
            Parsed JSON response or {"error": str}
        """
        try:
            session = await self._get_session()
            url = f"{self.base_url}{endpoint}"
            headers = {}

            if signed:
                headers.update(self._sign_request(method, endpoint, params or {}))

            async with session.request(method, url, params=params, headers=headers) as response:
                text = await response.text()

                if response.status >= 400:
                    logger.error(f"API error {response.status}: {text[:500]}")
                    return {"error": f"HTTP {response.status}: {text[:200]}"}

                try:
                    return await response.json()
                except:
                    return {"data": text}

        except aiohttp.ClientError as e:
            logger.error(f"Network error: {e}")
            return {"error": f"Network error: {str(e)}"}
        except Exception as e:
            logger.error(f"Request error: {e}")
            return {"error": f"Request error: {str(e)}"}

    # === Market Data ===
    @abstractmethod
    async def get_klines(self, symbol: str, interval: str, limit: int = 100) -> List[List]:
        """Fetch OHLCV candles."""
        pass

    @abstractmethod
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Fetch current ticker data."""
        pass

    # === Trading ===
    @abstractmethod
    async def place_order(self, symbol: str, side: str, size: float,
                          order_type: str = "MARKET", price: Optional[float] = None,
                          leverage: int = 1) -> Dict[str, Any]:
        """
        Place trading order.

        Returns:
            {
                "order_id": str,
                "avg_price": float,
                "size": float,
                "commission": float,
                "status": str,
            }
            or {"error": str}
        """
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Cancel an open order."""
        pass

    # === Account ===
    @abstractmethod
    async def get_balance(self) -> Dict[str, Any]:
        """
        Fetch account balance.

        Returns:
            {"USDT": float, "BTC": float, ...}
            or {"error": str}
        """
        pass

    @abstractmethod
    async def get_positions(self) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch open positions.

        Returns:
            List of position dicts or None
        """
        pass

    async def close(self):
        """Close aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info(f"Closed session for {self.__class__.__name__}")
