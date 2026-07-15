"""
Data Handler Module
Handles fetching, cleaning, and preparing market data
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
from typing import Optional, Tuple


class DataHandler:
    """Handles market data operations"""
    
    def __init__(self):
        self.data = None
        self.symbol = None
        
    def fetch_data(self, symbol: str, start_date: str, end_date: str, 
                   interval: str = '1h') -> pd.DataFrame:
        """
        Fetch market data from Yahoo Finance
        
        Args:
            symbol: Trading symbol (e.g., 'AAPL', 'BTC-USD')
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            interval: Data interval (1m, 5m, 15m, 1h, 1d)
            
        Returns:
            DataFrame with OHLCV data
        """
        self.symbol = symbol
        ticker = yf.Ticker(symbol)
        
        df = ticker.history(start=start_date, end=end_date, interval=interval)
        
        if df.empty:
            raise ValueError(f"No data found for {symbol}")
            
        df.columns = [col.lower() for col in df.columns]
        
        self.data = self._prepare_data(df)
        return self.data
    
    def _prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare and clean data"""
        df = df.copy()
        
        if 'close' not in df.columns:
            raise ValueError("Data must contain 'close' column")
        
        df = df.dropna()
        
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        
        df['price_range'] = df['high'] - df['low']
        df['body_size'] = abs(df['close'] - df['open'])
        df['upper_wick'] = df['high'] - df[['open', 'close']].max(axis=1)
        df['lower_wick'] = df[['open', 'close']].min(axis=1) - df['low']
        
        df['bullish_candle'] = (df['close'] > df['open']).astype(int)
        
        df = df.dropna()
        
        return df
    
    def add_custom_data(self, df: pd.DataFrame, 
                       name: str, data: pd.Series) -> pd.DataFrame:
        """Add custom data column to dataframe"""
        df[name] = data
        return df
    
    def resample_data(self, df: pd.DataFrame, 
                      timeframe: str) -> pd.DataFrame:
        """
        Resample data to different timeframe
        
        Args:
            df: Input dataframe
            timeframe: Target timeframe (e.g., '15min', '1H', '1D')
            
        Returns:
            Resampled dataframe
        """
        ohlc_dict = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }
        
        resampled = df.resample(timeframe).agg(ohlc_dict)
        resampled = resampled.dropna()
        
        return self._prepare_data(resampled)
    
    def get_session_data(self, df: pd.DataFrame, 
                        session_start: int, 
                        session_end: int) -> pd.DataFrame:
        """
        Filter data for specific trading session
        
        Args:
            df: Input dataframe
            session_start: Session start hour (UTC)
            session_end: Session end hour (UTC)
            
        Returns:
            Filtered dataframe
        """
        df = df.copy()
        df['hour'] = df.index.hour
        
        if session_start < session_end:
            mask = (df['hour'] >= session_start) & (df['hour'] < session_end)
        else:
            mask = (df['hour'] >= session_start) | (df['hour'] < session_end)
            
        return df[mask]
    
    def split_train_test(self, df: pd.DataFrame, 
                        train_ratio: float = 0.8) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Split data into training and testing sets"""
        split_idx = int(len(df) * train_ratio)
        
        train = df.iloc[:split_idx].copy()
        test = df.iloc[split_idx:].copy()
        
        return train, test
    
    def get_latest_bar(self, df: pd.DataFrame) -> pd.Series:
        """Get the most recent bar"""
        return df.iloc[-1]
    
    def calculate_volatility(self, df: pd.DataFrame, 
                           window: int = 20) -> pd.Series:
        """Calculate rolling volatility"""
        return df['returns'].rolling(window=window).std() * np.sqrt(252)
