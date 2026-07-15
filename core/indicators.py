"""
Technical Indicators Module
Implements various technical indicators for trading analysis
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional
import config


class TechnicalIndicators:
    """Collection of technical indicators"""
    
    @staticmethod
    def rsi(df: pd.DataFrame, period: int = None, column: str = 'close') -> pd.Series:
        """
        Calculate Relative Strength Index (RSI)
        
        Args:
            df: Input dataframe
            period: RSI period (default from config)
            column: Column to calculate RSI on
            
        Returns:
            RSI values
        """
        if period is None:
            period = config.INDICATORS['RSI']['period']
            
        delta = df[column].diff()
        
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def macd(df: pd.DataFrame, fast: int = None, slow: int = None, 
             signal: int = None, column: str = 'close') -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate MACD (Moving Average Convergence Divergence)
        
        Returns:
            macd_line, signal_line, histogram
        """
        if fast is None:
            fast = config.INDICATORS['MACD']['fast']
        if slow is None:
            slow = config.INDICATORS['MACD']['slow']
        if signal is None:
            signal = config.INDICATORS['MACD']['signal']
            
        ema_fast = df[column].ewm(span=fast, adjust=False).mean()
        ema_slow = df[column].ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def ema(df: pd.DataFrame, period: int, column: str = 'close') -> pd.Series:
        """Calculate Exponential Moving Average"""
        return df[column].ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def sma(df: pd.DataFrame, period: int, column: str = 'close') -> pd.Series:
        """Calculate Simple Moving Average"""
        return df[column].rolling(window=period).mean()
    
    @staticmethod
    def bollinger_bands(df: pd.DataFrame, period: int = None, 
                       std_dev: float = None, column: str = 'close') -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate Bollinger Bands
        
        Returns:
            upper_band, middle_band, lower_band
        """
        if period is None:
            period = config.INDICATORS['BOLLINGER']['period']
        if std_dev is None:
            std_dev = config.INDICATORS['BOLLINGER']['std_dev']
            
        middle_band = df[column].rolling(window=period).mean()
        std = df[column].rolling(window=period).std()
        
        upper_band = middle_band + (std * std_dev)
        lower_band = middle_band - (std * std_dev)
        
        return upper_band, middle_band, lower_band
    
    @staticmethod
    def atr(df: pd.DataFrame, period: int = None) -> pd.Series:
        """
        Calculate Average True Range (ATR)
        """
        if period is None:
            period = config.INDICATORS['ATR']['period']
            
        high = df['high']
        low = df['low']
        close = df['close'].shift(1)
        
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    @staticmethod
    def supertrend(df: pd.DataFrame, period: int = None, 
                   multiplier: float = None) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate SuperTrend indicator
        
        Returns:
            supertrend, direction (1 = bullish, -1 = bearish)
        """
        if period is None:
            period = config.INDICATORS['SUPERTREND']['period']
        if multiplier is None:
            multiplier = config.INDICATORS['SUPERTREND']['multiplier']
            
        hl2 = (df['high'] + df['low']) / 2
        atr = TechnicalIndicators.atr(df, period)
        
        upper_band = hl2 + (multiplier * atr)
        lower_band = hl2 - (multiplier * atr)
        
        supertrend = pd.Series(index=df.index, dtype=float)
        direction = pd.Series(index=df.index, dtype=float)
        
        supertrend.iloc[0] = lower_band.iloc[0]
        direction.iloc[0] = 1
        
        for i in range(1, len(df)):
            if df['close'].iloc[i] > supertrend.iloc[i-1]:
                supertrend.iloc[i] = lower_band.iloc[i]
                direction.iloc[i] = 1
            elif df['close'].iloc[i] < supertrend.iloc[i-1]:
                supertrend.iloc[i] = upper_band.iloc[i]
                direction.iloc[i] = -1
            else:
                supertrend.iloc[i] = supertrend.iloc[i-1]
                direction.iloc[i] = direction.iloc[i-1]
                
                if direction.iloc[i] == 1 and lower_band.iloc[i] < supertrend.iloc[i-1]:
                    supertrend.iloc[i] = lower_band.iloc[i]
                elif direction.iloc[i] == -1 and upper_band.iloc[i] > supertrend.iloc[i-1]:
                    supertrend.iloc[i] = upper_band.iloc[i]
        
        return supertrend, direction
    
    @staticmethod
    def vwap(df: pd.DataFrame) -> pd.Series:
        """
        Calculate Volume Weighted Average Price (VWAP)
        Resets daily
        """
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        
        df_copy = df.copy()
        df_copy['tp_volume'] = typical_price * df['volume']
        
        df_copy['date'] = df_copy.index.date
        
        cum_tp_volume = df_copy.groupby('date')['tp_volume'].cumsum()
        cum_volume = df_copy.groupby('date')['volume'].cumsum()
        
        vwap = cum_tp_volume / cum_volume
        
        return vwap
    
    @staticmethod
    def adx(df: pd.DataFrame, period: int = None) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate Average Directional Index (ADX)
        
        Returns:
            adx, +DI, -DI
        """
        if period is None:
            period = config.INDICATORS['ADX']['period']
            
        high = df['high']
        low = df['low']
        close = df['close']
        
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        tr = TechnicalIndicators.atr(df, period) * period
        
        plus_di = 100 * (plus_dm.rolling(window=period).sum() / tr)
        minus_di = 100 * (minus_dm.rolling(window=period).sum() / tr)
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        return adx, plus_di, minus_di
    
    @staticmethod
    def obv(df: pd.DataFrame) -> pd.Series:
        """Calculate On-Balance Volume (OBV)"""
        obv = pd.Series(index=df.index, dtype=float)
        obv.iloc[0] = df['volume'].iloc[0]
        
        for i in range(1, len(df)):
            if df['close'].iloc[i] > df['close'].iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] + df['volume'].iloc[i]
            elif df['close'].iloc[i] < df['close'].iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] - df['volume'].iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]
        
        return obv
    
    @staticmethod
    def volume_profile(df: pd.DataFrame, bins: int = 50) -> pd.DataFrame:
        """
        Calculate Volume Profile
        
        Returns:
            DataFrame with price levels and volume at each level
        """
        min_price = df['low'].min()
        max_price = df['high'].max()
        
        price_levels = np.linspace(min_price, max_price, bins)
        volume_at_price = np.zeros(bins - 1)
        
        for i in range(len(df)):
            bar_volume = df['volume'].iloc[i]
            bar_low = df['low'].iloc[i]
            bar_high = df['high'].iloc[i]
            
            for j in range(len(price_levels) - 1):
                if bar_low <= price_levels[j+1] and bar_high >= price_levels[j]:
                    volume_at_price[j] += bar_volume / bins
        
        profile = pd.DataFrame({
            'price_level': price_levels[:-1],
            'volume': volume_at_price
        })
        
        profile['poc'] = profile['volume'] == profile['volume'].max()
        
        return profile
    
    @staticmethod
    def relative_volume(df: pd.DataFrame, period: int = None) -> pd.Series:
        """
        Calculate Relative Volume (RVOL)
        Current volume / average volume
        """
        if period is None:
            period = config.INDICATORS['VOLUME']['lookback']
            
        avg_volume = df['volume'].rolling(window=period).mean()
        rvol = df['volume'] / avg_volume
        
        return rvol
    
    @staticmethod
    def volume_zscore(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Calculate Volume Z-Score"""
        mean_vol = df['volume'].rolling(window=period).mean()
        std_vol = df['volume'].rolling(window=period).std()
        
        zscore = (df['volume'] - mean_vol) / std_vol
        
        return zscore
