"""
Data Loading and Preprocessing Utilities
"""

import pandas as pd
import numpy as np
import yfinance as yf
from typing import List, Optional, Dict, Union
from datetime import datetime, timedelta


class DataLoader:
    """Load and preprocess market data"""
    
    def __init__(self, symbols: Union[str, List[str]], start_date: str, end_date: str, interval: str = '1d'):
        """
        Initialize data loader
        
        Args:
            symbols: Ticker symbol(s)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            interval: Data interval ('1d', '1h', '15m', etc.)
        """
        self.symbols = [symbols] if isinstance(symbols, str) else symbols
        self.start_date = start_date
        self.end_date = end_date
        self.interval = interval
        self.data = {}
        
    def load_data(self, include_volume: bool = True) -> Dict[str, pd.DataFrame]:
        """
        Load historical data from Yahoo Finance
        
        Args:
            include_volume: Whether to include volume data
            
        Returns:
            Dictionary of DataFrames keyed by symbol
        """
        for symbol in self.symbols:
            try:
                ticker = yf.Ticker(symbol)
                df = ticker.history(start=self.start_date, end=self.end_date, interval=self.interval)
                
                if df.empty:
                    print(f"Warning: No data found for {symbol}")
                    continue
                
                df.columns = df.columns.str.lower()
                
                if 'dividends' in df.columns:
                    df = df.drop(['dividends', 'stock splits'], axis=1, errors='ignore')
                
                df = self._add_derived_features(df)
                
                self.data[symbol] = df
                print(f"Loaded {len(df)} bars for {symbol}")
                
            except Exception as e:
                print(f"Error loading {symbol}: {str(e)}")
        
        return self.data
    
    def _add_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add commonly used derived features"""
        
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        
        if 'volume' in df.columns:
            df['dollar_volume'] = df['close'] * df['volume']
            df['volume_ma_20'] = df['volume'].rolling(window=20).mean()
        
        df['high_low_range'] = df['high'] - df['low']
        df['high_low_pct'] = (df['high'] - df['low']) / df['close']
        
        return df
    
    def get_symbol_data(self, symbol: str) -> pd.DataFrame:
        """Get data for a specific symbol"""
        return self.data.get(symbol, pd.DataFrame())
    
    def get_multiple_symbols(self) -> pd.DataFrame:
        """Get all symbols as a multi-index DataFrame"""
        if not self.data:
            return pd.DataFrame()
        
        combined = pd.concat(self.data.values(), keys=self.data.keys(), names=['symbol', 'date'])
        return combined
    
    @staticmethod
    def prepare_ml_features(df: pd.DataFrame, lookback_periods: List[int] = [5, 10, 20]) -> pd.DataFrame:
        """
        Prepare features for machine learning models
        
        Args:
            df: Input DataFrame with OHLCV data
            lookback_periods: Periods for lag features
            
        Returns:
            DataFrame with ML features
        """
        features_df = df.copy()
        
        for period in lookback_periods:
            features_df[f'returns_lag_{period}'] = features_df['returns'].shift(period)
            features_df[f'volume_lag_{period}'] = features_df['volume'].shift(period)
            features_df[f'close_ma_{period}'] = features_df['close'].rolling(window=period).mean()
            features_df[f'volume_ma_{period}'] = features_df['volume'].rolling(window=period).mean()
            features_df[f'volatility_{period}'] = features_df['returns'].rolling(window=period).std()
        
        features_df = features_df.dropna()
        
        return features_df
    
    @staticmethod
    def split_train_test(df: pd.DataFrame, train_ratio: float = 0.7) -> tuple:
        """
        Split data into train and test sets
        
        Args:
            df: Input DataFrame
            train_ratio: Ratio of training data
            
        Returns:
            train_df, test_df
        """
        split_idx = int(len(df) * train_ratio)
        train_df = df.iloc[:split_idx].copy()
        test_df = df.iloc[split_idx:].copy()
        
        return train_df, test_df
    
    @staticmethod
    def walk_forward_split(df: pd.DataFrame, n_splits: int = 5, train_size: int = 252) -> List[tuple]:
        """
        Walk-forward validation splits
        
        Args:
            df: Input DataFrame
            n_splits: Number of splits
            train_size: Size of training window
            
        Returns:
            List of (train_df, test_df) tuples
        """
        splits = []
        test_size = (len(df) - train_size) // n_splits
        
        for i in range(n_splits):
            train_start = i * test_size
            train_end = train_start + train_size
            test_end = train_end + test_size
            
            if test_end > len(df):
                break
            
            train_df = df.iloc[train_start:train_end].copy()
            test_df = df.iloc[train_end:test_end].copy()
            
            splits.append((train_df, test_df))
        
        return splits


class SyntheticDataGenerator:
    """Generate synthetic market data for testing"""
    
    @staticmethod
    def generate_trending_market(n_periods: int = 1000, drift: float = 0.0005, volatility: float = 0.02) -> pd.DataFrame:
        """Generate trending market data"""
        np.random.seed(42)
        
        returns = np.random.normal(drift, volatility, n_periods)
        prices = 100 * np.exp(np.cumsum(returns))
        
        dates = pd.date_range(start='2020-01-01', periods=n_periods, freq='D')
        
        df = pd.DataFrame({
            'date': dates,
            'close': prices,
            'returns': returns,
            'volume': np.random.randint(1000000, 5000000, n_periods)
        })
        
        df['high'] = df['close'] * (1 + np.random.uniform(0, 0.02, n_periods))
        df['low'] = df['close'] * (1 - np.random.uniform(0, 0.02, n_periods))
        df['open'] = df['close'].shift(1).fillna(df['close'].iloc[0])
        
        return df.set_index('date')
    
    @staticmethod
    def generate_mean_reverting_pair(n_periods: int = 1000, correlation: float = 0.8) -> tuple:
        """Generate cointegrated pair for pairs trading"""
        np.random.seed(42)
        
        x = np.random.normal(0, 1, n_periods).cumsum()
        noise = np.random.normal(0, 0.5, n_periods)
        y = correlation * x + noise
        
        dates = pd.date_range(start='2020-01-01', periods=n_periods, freq='D')
        
        df1 = pd.DataFrame({
            'date': dates,
            'close': 100 + x,
            'volume': np.random.randint(1000000, 5000000, n_periods)
        }).set_index('date')
        
        df2 = pd.DataFrame({
            'date': dates,
            'close': 100 + y,
            'volume': np.random.randint(1000000, 5000000, n_periods)
        }).set_index('date')
        
        return df1, df2
    
    @staticmethod
    def generate_ranging_market(n_periods: int = 1000, volatility: float = 0.02) -> pd.DataFrame:
        """Generate range-bound market data"""
        np.random.seed(42)
        
        returns = np.random.normal(0, volatility, n_periods)
        prices = 100 + 10 * np.sin(np.linspace(0, 4*np.pi, n_periods)) + np.cumsum(returns)
        
        dates = pd.date_range(start='2020-01-01', periods=n_periods, freq='D')
        
        df = pd.DataFrame({
            'date': dates,
            'close': prices,
            'returns': returns,
            'volume': np.random.randint(1000000, 5000000, n_periods)
        })
        
        df['high'] = df['close'] * (1 + np.random.uniform(0, 0.02, n_periods))
        df['low'] = df['close'] * (1 - np.random.uniform(0, 0.02, n_periods))
        df['open'] = df['close'].shift(1).fillna(df['close'].iloc[0])
        
        return df.set_index('date')
