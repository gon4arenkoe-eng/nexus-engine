"""
V10 NEXUS Swarm — BingX Client
===============================
Асинхронный клиент BingX API.
Поддерживает VST (DEMO) и REAL режимы.
"""

import hmac
import hashlib
import time
import urllib.parse
from typing import Dict, Any, Optional, List
import logging

from clients.base import BaseExchangeClient

logger = logging.getLogger(__name__)


class BingXClient(BaseExchangeClient):
    """
    BingX API client for perpetual futures trading.

    API Docs: https://bingx-api.github.io/docs/
    """

    def _get_base_url(self) -> str:
        # VST (Virtual Simulation Trading) for demo mode
        if self.demo:
            return "https://open-api-vst.bingx.com"
        return "https://open-api.bingx.com"

    def _sign_request(self, method: str, endpoint: str, params: Dict[str, Any]) -> Dict[str, str]:
        """Generate BingX signature."""
        timestamp = str(int(time.time() * 1000))

        # Build query string
        params = params.copy()
        params["timestamp"] = timestamp

        query_string = urllib.parse.urlencode(sorted(params.items()))

        # Create signature
        signature_payload = f"{method.upper()}{endpoint}?{query_string}"
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            signature_payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        return {
            "X-BX-APIKEY": self.api_key,
            "X-BX-SIGNATURE": signature,
            "X-BX-TIMESTAMP": timestamp,
        }

    # === Market Data (Public) ===
    async def get_klines(self, symbol: str, interval: str, limit: int = 100) -> List[List]:
        """Fetch klines/candles."""
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        }
        result = await self._request("GET", "/openApi/swap/v2/quote/klines", params)

        if "error" in result:
            return []

        return result.get("data", [])

    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Fetch ticker price."""
        params = {"symbol": symbol}
        result = await self._request("GET", "/openApi/swap/v2/quote/ticker", params)

        if "error" in result:
            return result

        data = result.get("data", {})
        if isinstance(data, list) and len(data) > 0:
            data = data[0]

        return {
            "symbol": data.get("symbol", symbol),
            "last_price": float(data.get("lastPrice", 0)),
            "high_24h": float(data.get("highPrice", 0)),
            "low_24h": float(data.get("lowPrice", 0)),
            "volume_24h": float(data.get("volume", 0)),
            "price_change_24h": float(data.get("priceChange", 0)),
        }

    # === Trading (Signed) ===
    async def place_order(self, symbol: str, side: str, size: float,
                          order_type: str = "MARKET", price: Optional[float] = None,
                          leverage: int = 1) -> Dict[str, Any]:
        """Place order on BingX."""
        params = {
            "symbol": symbol,
            "side": side.upper(),
            "positionSide": "LONG" if side.upper() == "BUY" else "SHORT",
            "type": order_type.upper(),
            "quantity": size,
        }

        if order_type.upper() == "LIMIT" and price:
            params["price"] = price

        result = await self._request("POST", "/openApi/swap/v2/trade/order", params, signed=True)

        if "error" in result:
            return result

        data = result.get("data", {})
        order = data.get("order", {})

        return {
            "order_id": order.get("orderId"),
            "avg_price": float(order.get("avgPrice", 0) or 0),
            "size": float(order.get("executedQty", 0) or size),
            "commission": float(order.get("commission", 0) or 0),
            "status": order.get("status", "UNKNOWN"),
        }

    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Cancel open order."""
        params = {
            "symbol": symbol,
            "orderId": order_id,
        }
        return await self._request("DELETE", "/openApi/swap/v2/trade/order", params, signed=True)

    # === Account (Signed) ===
    async def get_balance(self) -> Dict[str, Any]:
        """Fetch account balance."""
        result = await self._request("GET", "/openApi/swap/v2/user/balance", {}, signed=True)

        if "error" in result:
            return result

        balances = {}
        data = result.get("data", {})
        balance_list = data.get("balance", []) if isinstance(data, dict) else []

        for bal in balance_list:
            asset = bal.get("asset", "")
            available = float(bal.get("available", 0) or 0)
            if available > 0:
                balances[asset] = available

        return balances

    async def get_positions(self) -> Optional[List[Dict[str, Any]]]:
        """Fetch open positions."""
        result = await self._request("GET", "/openApi/swap/v2/user/positions", {}, signed=True)

        if "error" in result:
            logger.error(f"Failed to fetch positions: {result['error']}")
            return None

        data = result.get("data", [])
        if not isinstance(data, list):
            data = [data] if data else []

        positions = []
        for pos in data:
            size = float(pos.get("positionAmt", 0) or 0)
            if size == 0:
                continue

            positions.append({
                "symbol": pos.get("symbol", ""),
                "side": "LONG" if size > 0 else "SHORT",
                "size": abs(size),
                "entry_price": float(pos.get("avgPrice", 0) or pos.get("entryPrice", 0) or 0),
                "leverage": int(pos.get("leverage", 1) or 1),
                "unrealized_pnl": float(pos.get("unrealizedProfit", 0) or 0),
                "order_id": pos.get("positionId", ""),
            })

        return positions

    async def get_income(self, start_time: Optional[int] = None, 
                         end_time: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch income history (for PnL calculation).
        Includes: REALIZED_PNL, FUNDING_FEE, COMMISSION
        """
        params = {"limit": limit}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time

        result = await self._request("GET", "/openApi/swap/v2/user/income", params, signed=True)

        if "error" in result:
            return []

        data = result.get("data", [])
        if not isinstance(data, list):
            data = [data] if data else []

        return data
