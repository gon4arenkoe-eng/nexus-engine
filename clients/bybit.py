"""
V10 NEXUS Swarm — Bybit Client
===============================
Асинхронный клиент Bybit API v5.
"""

import hmac
import hashlib
import time
import json
from typing import Dict, Any, Optional, List
import logging

from clients.base import BaseExchangeClient

logger = logging.getLogger(__name__)


class BybitClient(BaseExchangeClient):
    """
    Bybit API v5 client for perpetual futures.

    API Docs: https://bybit-exchange.github.io/docs/v5/intro
    """

    def _get_base_url(self) -> str:
        if self.demo:
            return "https://api-testnet.bybit.com"
        return "https://api.bybit.com"

    def _sign_request(
        self, method: str, endpoint: str, params: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate Bybit v5 signature."""
        timestamp = str(int(time.time() * 1000))
        recv_window = "5000"

        # Build payload
        if method.upper() == "GET":
            payload = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
            if payload:
                payload = timestamp + self.api_key + recv_window + payload
            else:
                payload = timestamp + self.api_key + recv_window
        else:
            payload = timestamp + self.api_key + recv_window + json.dumps(params)

        signature = hmac.new(
            self.api_secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        return {
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-SIGN": signature,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-RECV-WINDOW": recv_window,
        }

    async def get_klines(
        self, symbol: str, interval: str, limit: int = 100
    ) -> List[List]:
        params = {
            "category": "linear",
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        }
        result = await self._request("GET", "/v5/market/kline", params)

        if isinstance(result, dict) and "error" not in result:
            data = result.get("result", {}).get("list", [])
            # Bybit format: [[timestamp, open, high, low, close, volume, turnover], ...]
            return data
        return []

    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        params = {
            "category": "linear",
            "symbol": symbol,
        }
        result = await self._request("GET", "/v5/market/tickers", params)

        if isinstance(result, dict) and "error" not in result:
            data = result.get("result", {}).get("list", [{}])[0]
            return {
                "symbol": data.get("symbol", symbol),
                "last_price": float(data.get("lastPrice", 0)),
                "high_24h": float(data.get("highPrice24h", 0)),
                "low_24h": float(data.get("lowPrice24h", 0)),
                "volume_24h": float(data.get("volume24h", 0)),
                "price_change_24h": float(data.get("price24hPcnt", 0)),
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
            "category": "linear",
            "symbol": symbol,
            "side": side.capitalize(),  # Buy / Sell
            "orderType": order_type.capitalize(),
            "qty": str(size),
        }

        if order_type.upper() == "LIMIT" and price:
            params["price"] = str(price)

        result = await self._request("POST", "/v5/order/create", params, signed=True)

        if isinstance(result, dict) and "error" not in result:
            data = result.get("result", {})
            return {
                "order_id": data.get("orderId", ""),
                "avg_price": 0,  # Bybit returns this separately
                "size": size,
                "commission": 0,
                "status": "NEW",
            }
        return result if isinstance(result, dict) else {"error": "Invalid response"}

    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        params = {
            "category": "linear",
            "symbol": symbol,
            "orderId": order_id,
        }
        return await self._request("POST", "/v5/order/cancel", params, signed=True)

    async def get_balance(self) -> Dict[str, Any]:
        params = {"accountType": "UNIFIED"}
        result = await self._request(
            "GET", "/v5/account/wallet-balance", params, signed=True
        )

        if isinstance(result, dict) and "error" not in result:
            balances = {}
            coins = result.get("result", {}).get("list", [{}])[0].get("coin", [])
            for coin in coins:
                asset = coin.get("coin", "")
                available = float(coin.get("availableToWithdraw", 0) or 0)
                if available > 0:
                    balances[asset] = available
            return balances

        return result if isinstance(result, dict) else {"error": "Invalid response"}

    async def get_positions(self) -> Optional[List[Dict[str, Any]]]:
        params = {
            "category": "linear",
            "settleCoin": "USDT",
        }
        result = await self._request("GET", "/v5/position/list", params, signed=True)

        if isinstance(result, dict) and "error" not in result:
            positions = []
            for pos in result.get("result", {}).get("list", []):
                size = float(pos.get("size", 0) or 0)
                if size == 0:
                    continue

                positions.append(
                    {
                        "symbol": pos.get("symbol", ""),
                        "side": pos.get("side", "").upper(),
                        "size": size,
                        "entry_price": float(pos.get("avgPrice", 0) or 0),
                        "leverage": int(pos.get("leverage", 1) or 1),
                        "unrealized_pnl": float(pos.get("unrealisedPnl", 0) or 0),
                        "order_id": pos.get("positionIdx", ""),
                    }
                )
            return positions

        logger.error(f"Failed to fetch positions: {result}")
        return None
