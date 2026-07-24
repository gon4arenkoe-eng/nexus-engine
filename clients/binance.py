"""
V10 NEXUS Swarm — Binance Client
==================================
Асинхронный клиент Binance Futures API.
"""

import hmac
import hashlib
import time
from typing import Dict, Any, Optional, List
import logging

from clients.base import BaseExchangeClient

logger = logging.getLogger(__name__)


class BinanceClient(BaseExchangeClient):
    """
    Binance Futures API client.

    API Docs: https://binance-docs.github.io/apidocs/futures/en/
    """

    def _get_base_url(self) -> str:
        if self.demo:
            return "https://testnet.binancefuture.com"
        return "https://fapi.binance.com"

    def _sign_request(
        self, method: str, endpoint: str, params: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate Binance signature."""
        timestamp = str(int(time.time() * 1000))
        params = params.copy()
        params["timestamp"] = timestamp

        query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        params["signature"] = signature

        return {
            "X-MBX-APIKEY": self.api_key,
        }

    async def get_klines(
        self, symbol: str, interval: str, limit: int = 100
    ) -> List[List]:
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        }
        result = await self._request("GET", "/fapi/v1/klines", params)
        return result if isinstance(result, list) else []

    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        params = {"symbol": symbol}
        result = await self._request("GET", "/fapi/v1/ticker/24hr", params)

        if isinstance(result, dict) and "error" not in result:
            return {
                "symbol": result.get("symbol", symbol),
                "last_price": float(result.get("lastPrice", 0)),
                "high_24h": float(result.get("highPrice", 0)),
                "low_24h": float(result.get("lowPrice", 0)),
                "volume_24h": float(result.get("volume", 0)),
                "price_change_24h": float(result.get("priceChange", 0)),
            }
        return result if isinstance(result, dict) else {"error": "Invalid response"}

    async def place_order(
        self,
        symbol: str,
        side: str,
        size: float,
        order_type: str = "MARKET",
        price: Optional[float] = None,
        leverage: int = 1,
    ) -> Dict[str, Any]:
        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": size,
        }

        if order_type.upper() == "LIMIT" and price:
            params["price"] = price

        result = await self._request("POST", "/fapi/v1/order", params, signed=True)

        if isinstance(result, dict) and "error" not in result:
            return {
                "order_id": str(result.get("orderId", "")),
                "avg_price": float(result.get("avgPrice", 0) or 0),
                "size": float(result.get("executedQty", 0) or size),
                "commission": float(result.get("cumQuote", 0) or 0) * 0.0004,  # ~0.04%
                "status": result.get("status", "UNKNOWN"),
            }
        return result if isinstance(result, dict) else {"error": "Invalid response"}

    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        params = {
            "symbol": symbol,
            "orderId": order_id,
        }
        return await self._request("DELETE", "/fapi/v1/order", params, signed=True)

    async def get_balance(self) -> Dict[str, Any]:
        result = await self._request("GET", "/fapi/v2/balance", {}, signed=True)

        if isinstance(result, list):
            balances = {}
            for bal in result:
                asset = bal.get("asset", "")
                available = float(bal.get("availableBalance", 0) or 0)
                if available > 0:
                    balances[asset] = available
            return balances

        return result if isinstance(result, dict) else {"error": "Invalid response"}

    async def get_positions(self) -> Optional[List[Dict[str, Any]]]:
        result = await self._request("GET", "/fapi/v2/positionRisk", {}, signed=True)

        if isinstance(result, list):
            positions = []
            for pos in result:
                size = float(pos.get("positionAmt", 0) or 0)
                if size == 0:
                    continue

                positions.append(
                    {
                        "symbol": pos.get("symbol", ""),
                        "side": "LONG" if size > 0 else "SHORT",
                        "size": abs(size),
                        "entry_price": float(pos.get("entryPrice", 0) or 0),
                        "leverage": int(pos.get("leverage", 1) or 1),
                        "unrealized_pnl": float(pos.get("unRealizedProfit", 0) or 0),
                        "order_id": pos.get("positionId", ""),
                    }
                )
            return positions

        logger.error(f"Failed to fetch positions: {result}")
        return None
