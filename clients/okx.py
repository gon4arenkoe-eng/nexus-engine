"""
V10 NEXUS Swarm — OKX Client
============================
Асинхронный клиент OKX API v5.
"""

import hmac
import hashlib
import base64
import time
from typing import Dict, Any, Optional, List
import logging

from clients.base import BaseExchangeClient

logger = logging.getLogger(__name__)


class OKXClient(BaseExchangeClient):
    """
    OKX API v5 client for perpetual futures.

    API Docs: https://www.okx.com/docs-v5/en/
    """

    def _get_base_url(self) -> str:
        if self.demo:
            return "https://www.okx.com"
        return "https://www.okx.com"

    def _sign_request(self, method: str, endpoint: str, params: Dict[str, Any]) -> Dict[str, str]:
        """Generate OKX signature."""
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())

        if method.upper() == "GET":
            body = ""
        else:
            import json
            body = json.dumps(params) if params else ""

        message = timestamp + method.upper() + endpoint + body
        signature = base64.b64encode(
            hmac.new(
                self.api_secret.encode("utf-8"),
                message.encode("utf-8"),
                hashlib.sha256
            ).digest()
        ).decode("utf-8")

        headers = {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": signature,
            "OK-ACCESS-TIMESTAMP": timestamp,
        }

        if self.passphrase:
            headers["OK-ACCESS-PASSPHRASE"] = self.passphrase

        return headers

    async def get_klines(self, symbol: str, interval: str, limit: int = 100) -> List[List]:
        params = {
            "instId": symbol,
            "bar": interval,
            "limit": limit,
        }
        result = await self._request("GET", "/api/v5/market/candles", params)

        if isinstance(result, dict) and "error" not in result:
            return result.get("data", [])
        return []

    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        params = {"instId": symbol}
        result = await self._request("GET", "/api/v5/market/ticker", params)

        if isinstance(result, dict) and "error" not in result:
            data = result.get("data", [{}])[0]
            return {
                "symbol": data.get("instId", symbol),
                "last_price": float(data.get("last", 0)),
                "high_24h": float(data.get("high24h", 0)),
                "low_24h": float(data.get("low24h", 0)),
                "volume_24h": float(data.get("vol24h", 0)),
                "price_change_24h": float(data.get("chg24h", 0)),
            }
        return result if isinstance(result, dict) else {"error": "Invalid response"}

    async def place_order(self, symbol: str, side: str, size: float,
                          order_type: str = "MARKET", price: Optional[float] = None,
                          leverage: int = 1) -> Dict[str, Any]:
        params = {
            "instId": symbol,
            "tdMode": "cross",  # Cross margin
            "side": side.lower(),  # buy / sell
            "ordType": order_type.lower(),
            "sz": str(size),
        }

        if order_type.upper() == "LIMIT" and price:
            params["px"] = str(price)

        result = await self._request("POST", "/api/v5/trade/order", params, signed=True)

        if isinstance(result, dict) and "error" not in result:
            data = result.get("data", [{}])[0]
            return {
                "order_id": data.get("ordId", ""),
                "avg_price": 0,
                "size": size,
                "commission": 0,
                "status": data.get("state", "UNKNOWN"),
            }
        return result if isinstance(result, dict) else {"error": "Invalid response"}

    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        params = {
            "instId": symbol,
            "ordId": order_id,
        }
        return await self._request("POST", "/api/v5/trade/cancel-order", params, signed=True)

    async def get_balance(self) -> Dict[str, Any]:
        params = {"ccy": "USDT"}
        result = await self._request("GET", "/api/v5/account/balance", params, signed=True)

        if isinstance(result, dict) and "error" not in result:
            balances = {}
            for detail in result.get("data", [{}])[0].get("details", []):
                asset = detail.get("ccy", "")
                available = float(detail.get("availBal", 0) or 0)
                if available > 0:
                    balances[asset] = available
            return balances

        return result if isinstance(result, dict) else {"error": "Invalid response"}

    async def get_positions(self) -> Optional[List[Dict[str, Any]]]:
        params = {"instType": "SWAP"}
        result = await self._request("GET", "/api/v5/account/positions", params, signed=True)

        if isinstance(result, dict) and "error" not in result:
            positions = []
            for pos in result.get("data", []):
                size = float(pos.get("pos", 0) or 0)
                if size == 0:
                    continue

                positions.append({
                    "symbol": pos.get("instId", ""),
                    "side": "LONG" if size > 0 else "SHORT",
                    "size": abs(size),
                    "entry_price": float(pos.get("avgPx", 0) or 0),
                    "leverage": int(pos.get("lever", 1) or 1),
                    "unrealized_pnl": float(pos.get("upl", 0) or 0),
                    "order_id": pos.get("posId", ""),
                })
            return positions

        logger.error(f"Failed to fetch positions: {result}")
        return None
