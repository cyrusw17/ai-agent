"""
Technical Indicators and Market Microstructure Metrics
Implements various technical indicators and advanced market metrics
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Tuple, Optional


class TechnicalIndicators:
    """Standard technical indicators for trading strategies"""
    
    @staticmethod
    def rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Relative Strength Index
        
        Args:
            prices: Price series
            period: RSI period (default 14)
            
        Returns:
            RSI values (0-100)
        """
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        MACD (Moving Average Convergence Divergence)
        
        Args:
            prices: Price series
            fast: Fast EMA period
            slow: Slow EMA period
            signal: Signal line period
            
        Returns:
            macd_line, signal_line, histogram
        """
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def bollinger_bands(prices: pd.Series, period: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Bollinger Bands
        
        Args:
            prices: Price series
            period: Moving average period
            std_dev: Number of standard deviations
            
        Returns:
            upper_band, middle_band, lower_band
        """
        middle_band = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        
        upper_band = middle_band + (std * std_dev)
        lower_band = middle_band - (std * std_dev)
        
        return upper_band, middle_band, lower_band
    
    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """
        Average True Range
        
        Args:
            high: High prices
            low: Low prices
            close: Close prices
            period: ATR period
            
        Returns:
            ATR values
        """
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    @staticmethod
    def ema(prices: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average"""
        return prices.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def sma(prices: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average"""
        return prices.rolling(window=period).mean()


class MarketMicrostructure:
    """Advanced market microstructure indicators"""
    
    @staticmethod
    def amihud_illiquidity(returns: pd.Series, volume: pd.Series, dollar_volume: Optional[pd.Series] = None) -> pd.Series:
        """
        Amihud (2002) Illiquidity Ratio
        Measures price impact per unit of dollar volume
        
        Formula: ILLIQ = |Return| / DollarVolume
        
        Args:
            returns: Return series
            volume: Volume series
            dollar_volume: Pre-calculated dollar volume (optional)
            
        Returns:
            Illiquidity ratio (higher = more illiquid)
        """
        if dollar_volume is None:
            dollar_volume = volume
        
        illiquidity = abs(returns) / dollar_volume
        illiquidity = illiquidity.replace([np.inf, -np.inf], np.nan)
        
        return illiquidity.rolling(window=20).mean()
    
    @staticmethod
    def volume_ratio(volume: pd.Series, period: int = 20) -> pd.Series:
        """
        Volume Ratio = Current Volume / Average Volume
        
        Ratios > 1.5 indicate strong conviction
        Ratios < 0.8 indicate thin trading
        
        Args:
            volume: Volume series
            period: Lookback period for average
            
        Returns:
            Volume ratio
        """
        avg_volume = volume.rolling(window=period).mean()
        ratio = volume / avg_volume
        return ratio
    
    @staticmethod
    def order_flow_imbalance(bid_volume: pd.Series, ask_volume: pd.Series) -> pd.Series:
        """
        Order Flow Imbalance (OFI)
        
        OFI = Buy Volume - Sell Volume
        Positive OFI suggests buying pressure
        
        Args:
            bid_volume: Buy-initiated volume
            ask_volume: Sell-initiated volume
            
        Returns:
            OFI series
        """
        ofi = bid_volume - ask_volume
        return ofi
    
    @staticmethod
    def kyle_lambda(price_changes: pd.Series, order_flow: pd.Series, window: int = 100) -> pd.Series:
        """
        Kyle's Lambda - Price impact coefficient
        
        Measures: ΔP = λ × OrderFlow
        
        Args:
            price_changes: Price change series
            order_flow: Signed order flow
            window: Rolling window for estimation
            
        Returns:
            Kyle's lambda estimates
        """
        lambda_estimates = []
        
        for i in range(len(price_changes)):
            if i < window:
                lambda_estimates.append(np.nan)
                continue
            
            window_prices = price_changes.iloc[i-window:i]
            window_flow = order_flow.iloc[i-window:i]
            
            if window_flow.std() > 0:
                coef = np.cov(window_prices, window_flow)[0, 1] / window_flow.var()
                lambda_estimates.append(coef)
            else:
                lambda_estimates.append(np.nan)
        
        return pd.Series(lambda_estimates, index=price_changes.index)
    
    @staticmethod
    def cumulative_volume_delta(buy_volume: pd.Series, sell_volume: pd.Series) -> pd.Series:
        """
        Cumulative Volume Delta (CVD)
        
        Tracks running net buying/selling pressure
        
        Args:
            buy_volume: Buy volume series
            sell_volume: Sell volume series
            
        Returns:
            Cumulative delta
        """
        delta = buy_volume - sell_volume
        cvd = delta.cumsum()
        return cvd
    
    @staticmethod
    def vwap(prices: pd.Series, volume: pd.Series) -> pd.Series:
        """
        Volume Weighted Average Price
        
        Args:
            prices: Price series (typically close or typical price)
            volume: Volume series
            
        Returns:
            VWAP series
        """
        pv = prices * volume
        vwap = pv.cumsum() / volume.cumsum()
        return vwap
    
    @staticmethod
    def typical_price(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
        """Typical Price = (High + Low + Close) / 3"""
        return (high + low + close) / 3


class StatisticalTests:
    """Statistical tests for trading strategies"""
    
    @staticmethod
    def adf_test(series: pd.Series) -> Tuple[float, float, bool]:
        """
        Augmented Dickey-Fuller test for stationarity
        
        Args:
            series: Time series to test
            
        Returns:
            adf_statistic, p_value, is_stationary
        """
        from statsmodels.tsa.stattools import adfuller
        
        result = adfuller(series.dropna(), autolag='AIC')
        adf_stat = result[0]
        p_value = result[1]
        is_stationary = p_value < 0.05
        
        return adf_stat, p_value, is_stationary
    
    @staticmethod
    def cointegration_test(series1: pd.Series, series2: pd.Series) -> Tuple[float, float, float, bool]:
        """
        Engle-Granger cointegration test
        
        Args:
            series1: First price series
            series2: Second price series
            
        Returns:
            beta (hedge ratio), adf_stat, p_value, is_cointegrated
        """
        from statsmodels.regression.linear_model import OLS
        from statsmodels.tsa.stattools import adfuller
        
        model = OLS(series1, series2).fit()
        beta = model.params[0]
        
        spread = series1 - beta * series2
        adf_stat, p_value, *_ = adfuller(spread.dropna())
        
        is_cointegrated = p_value < 0.05
        
        return beta, adf_stat, p_value, is_cointegrated
    
    @staticmethod
    def half_life_mean_reversion(spread: pd.Series) -> float:
        """
        Calculate half-life of mean reversion using Ornstein-Uhlenbeck
        
        Args:
            spread: Spread series
            
        Returns:
            Half-life in periods
        """
        spread_lag = spread.shift(1).dropna()
        spread_diff = spread.diff().dropna()
        
        # Align indices
        spread_lag = spread_lag[spread_diff.index]
        
        model = OLS(spread_diff, spread_lag).fit()
        theta = -model.params[0]
        
        if theta > 0:
            half_life = -np.log(2) / np.log(1 - theta)
            return half_life
        else:
            return np.nan
    
    @staticmethod
    def z_score(series: pd.Series, window: int = 20) -> pd.Series:
        """
        Rolling Z-score
        
        Args:
            series: Input series
            window: Rolling window
            
        Returns:
            Z-score series
        """
        mean = series.rolling(window=window).mean()
        std = series.rolling(window=window).std()
        z_score = (series - mean) / std
        return z_score


class VolatilityMetrics:
    """Volatility and regime detection metrics"""
    
    @staticmethod
    def historical_volatility(returns: pd.Series, window: int = 20) -> pd.Series:
        """Annualized historical volatility"""
        return returns.rolling(window=window).std() * np.sqrt(252)
    
    @staticmethod
    def parkinson_volatility(high: pd.Series, low: pd.Series, window: int = 20) -> pd.Series:
        """
        Parkinson's volatility estimator (uses high-low range)
        More efficient than close-to-close
        """
        hl_ratio = np.log(high / low)
        parkinson_vol = np.sqrt(1 / (4 * np.log(2)) * (hl_ratio ** 2))
        return parkinson_vol.rolling(window=window).mean() * np.sqrt(252)
    
    @staticmethod
    def volatility_regime(returns: pd.Series, threshold: float = 1.5) -> pd.Series:
        """
        Classify volatility regime
        
        Returns:
            1 = High volatility, 0 = Normal/Low volatility
        """
        vol = returns.rolling(window=20).std()
        vol_percentile = vol / vol.rolling(window=100).median()
        
        regime = (vol_percentile > threshold).astype(int)
        return regime
