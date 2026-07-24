import pandas as pd
import numpy as np


class Indicators:
    @staticmethod
    def calculate_ema(data: pd.Series, period: int) -> pd.Series:
        return data.ewm(span=period, adjust=False).mean()

    @staticmethod
    def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def calculate_atr(
        high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
    ) -> pd.Series:
        tr = pd.DataFrame(
            {
                "h-l": high - low,
                "h-pc": abs(high - close.shift()),
                "l-pc": abs(low - close.shift()),
            }
        ).max(axis=1)
        return tr.ewm(span=period, adjust=False).mean()

    @staticmethod
    def calculate_choppiness_index(
        high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
    ) -> pd.Series:
        atr1 = Indicators.calculate_atr(high, low, close, period=1)
        sum_atr1 = atr1.rolling(window=period).sum()
        highest_high = high.rolling(window=period).max()
        lowest_low = low.rolling(window=period).min()

        # Avoid division by zero
        denominator = highest_high - lowest_low
        denominator = denominator.replace(
            0, np.nan
        )  # Replace 0 with NaN to avoid division by zero

        ci = 100 * np.log10(sum_atr1 / denominator) / np.log10(period)
        return ci

    @staticmethod
    def calculate_bollinger_bands(
        data: pd.Series, period: int = 20, std_dev: int = 2
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        sma = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        return sma, upper_band, lower_band

    @staticmethod
    def calculate_keltner_channels(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 20,
        atr_multiplier: float = 1.5,
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        ema = Indicators.calculate_ema(close, period)
        atr = Indicators.calculate_atr(high, low, close, period)
        upper_channel = ema + (atr * atr_multiplier)
        lower_channel = ema - (atr * atr_multiplier)
        return ema, upper_channel, lower_channel

    @staticmethod
    def calculate_z_score(spread: pd.Series, period: int = 60) -> pd.Series:
        mean_spread = spread.rolling(window=period).mean()
        std_spread = spread.rolling(window=period).std()
        # Avoid division by zero
        std_spread = std_spread.replace(0, np.nan)
        return (spread - mean_spread) / std_spread
