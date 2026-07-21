"""Trading strategies package."""
from .base import BaseStrategy
from .ema_cross import EmaCrossStrategy
from .mean_reversion import MeanReversionStrategy

__all__ = ["BaseStrategy", "EmaCrossStrategy", "MeanReversionStrategy"]
