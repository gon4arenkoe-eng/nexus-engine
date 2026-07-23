import logging
"""
V10 NEXUS Swarm — Exchange Service
===================================
Управление подключениями к биржам.
Шифрование/дешифрование API ключей через crypto_utils.
"""

from typing import Dict, Any, List, Optional
from models import Exchange
from utils.crypto_utils import get_crypto_manager
from clients import BingXClient, BinanceClient, BybitClient, OKXClient
from app import db
logger = logging.getLogger(__name__)


class ExchangeService:
    """
    Manages exchange connections.

    Features:
    - Encrypt API keys before storage
    - Decrypt on-the-fly for trading
    - Support multiple exchanges per user
    """

    CLIENT_MAP = {
        "bingx": BingXClient,
        "binance": BinanceClient,
        "bybit": BybitClient,
        "okx": OKXClient,
    }

    def __init__(self):
        self._clients: Dict[int, Any] = {}  # exchange_id -> client instance

    def add_exchange(self, user_id: int, name: str, api_key: str, api_secret: str,
                     passphrase: Optional[str] = None, is_demo: bool = True) -> Dict[str, Any]:
        """
        Add new exchange connection.

        Returns:
            {"success": bool, "exchange_id": int, "error": str}
        """
        try:
            # Validate exchange name
            if name not in self.CLIENT_MAP:
                return {"success": False, "error": f"Unsupported exchange: {name}"}

            # Encrypt credentials
            crypto = get_crypto_manager()
            encrypted_key = crypto.encrypt(api_key.strip())
            encrypted_secret = crypto.encrypt(api_secret.strip())
            encrypted_passphrase = crypto.encrypt(passphrase.strip()) if passphrase else None

            # Create exchange record
            exchange = Exchange(
                user_id=user_id,
                name=name,
                api_key_encrypted=encrypted_key,
                api_secret_encrypted=encrypted_secret,
                passphrase_encrypted=encrypted_passphrase,
                is_demo=is_demo,
            )

            db.session.add(exchange)
            db.session.commit()

            return {
                "success": True,
                "exchange_id": exchange.id,
                "error": None,
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Exchange add error: {e}")
            return {"success": False, "error": str(e)}

    def get_user_exchanges(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all exchanges for a user."""
        exchanges = Exchange.query.filter_by(user_id=user_id).all()
        return [ex.to_dict() for ex in exchanges]

    def get_active_exchange(self, user_id: int) -> Optional[Exchange]:
        """Get first active exchange for a user."""
        return Exchange.query.filter_by(user_id=user_id, is_active=True).first()

    def toggle_exchange(self, exchange_id: int, user_id: int) -> bool:
        """Toggle exchange active/inactive."""
        exchange = Exchange.query.filter_by(id=exchange_id, user_id=user_id).first()
        if not exchange:
            return False

        exchange.is_active = not exchange.is_active
        db.session.commit()
        return True

    def delete_exchange(self, exchange_id: int, user_id: int) -> bool:
        """Delete exchange connection."""
        exchange = Exchange.query.filter_by(id=exchange_id, user_id=user_id).first()
        if not exchange:
            return False

        # Remove from cache
        self._clients.pop(exchange_id, None)

        db.session.delete(exchange)
        db.session.commit()
        return True

    async def get_client(self, exchange_id: int) -> Optional[Any]:
        """
        Get initialized exchange client with decrypted credentials.

        Returns:
            Exchange client instance or None
        """
        # Check cache
        if exchange_id in self._clients:
            return self._clients[exchange_id]

        # Load from database
        exchange = Exchange.query.get(exchange_id)
        if not exchange or not exchange.is_active:
            return None

        # Decrypt credentials
        crypto = get_crypto_manager()
        try:
            api_key = crypto.decrypt(exchange.api_key_encrypted)
            api_secret = crypto.decrypt(exchange.api_secret_encrypted)
            passphrase = crypto.decrypt(exchange.passphrase_encrypted) if exchange.passphrase_encrypted else None
        except Exception as e:
            logger.error(f"Client init error: {e}")
            return None

        # Create client
        client_class = self.CLIENT_MAP.get(exchange.name)
        if not client_class:
            return None

        client = client_class(
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            demo=exchange.is_demo,
        )  # type: ignore[abstract]

        # Cache
        self._clients[exchange_id] = client
        return client

    async def test_connection(self, exchange_id: int) -> Dict[str, Any]:
        """Test exchange connection by fetching balance."""
        client = await self.get_client(exchange_id)
        if not client:
            return {"success": False, "error": "Failed to initialize client"}

        try:
            balance = await client.get_balance()

            if isinstance(balance, dict) and "error" in balance:
                return {"success": False, "error": balance["error"]}

            # Update last connected
            exchange = Exchange.query.get(exchange_id)
            if exchange:
                from datetime import datetime
                exchange.last_connected = datetime.utcnow()
                db.session.commit()

            return {
                "success": True,
                "balance": balance,
                "error": None,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def close_all(self):
        """Close all cached client sessions."""
        for client in self._clients.values():
            await client.close()
        self._clients.clear()
