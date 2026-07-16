"""
Session Analysis Module
Analyzes trading sessions and time-based patterns
"""

import pandas as pd
import numpy as np
from datetime import time
from typing import Dict, Optional
import config


class SessionAnalysis:
    """Analyzes trading session patterns and timing"""
    
    def __init__(self):
        self.sessions = config.SESSIONS
        
    def identify_session(self, timestamp: pd.Timestamp) -> Dict[str, any]:
        """
        Identify which trading session a timestamp belongs to
        
        Args:
            timestamp: Pandas timestamp (should be UTC)
            
        Returns:
            Dictionary with session info
        """
        hour = timestamp.hour
        
        for session_name, session_info in self.sessions.items():
            start = session_info['start_hour']
            end = session_info['end_hour']
            
            if start < end:
                if start <= hour < end:
                    return {
                        'session': session_name,
                        'weight': session_info['weight'],
                        'name': session_info['name']
                    }
            else:
                if hour >= start or hour < end:
                    return {
                        'session': session_name,
                        'weight': session_info['weight'],
                        'name': session_info['name']
                    }
        
        return {
            'session': 'OFF_PEAK',
            'weight': 0.45,
            'name': 'Off Peak'
        }
    
    def add_session_info(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add session information to dataframe
        
        Adds columns: session, session_weight, session_name
        """
        df = df.copy()
        
        sessions = []
        weights = []
        names = []
        
        for timestamp in df.index:
            session_info = self.identify_session(timestamp)
            sessions.append(session_info['session'])
            weights.append(session_info['weight'])
            names.append(session_info['name'])
        
        df['session'] = sessions
        df['session_weight'] = weights
        df['session_name'] = names
        
        return df
    
    def calculate_session_statistics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate statistics for each trading session
        
        Returns:
            DataFrame with session statistics
        """
        df = self.add_session_info(df)
        
        stats = df.groupby('session').agg({
            'volume': ['mean', 'sum', 'std'],
            'price_range': ['mean', 'max'],
            'close': lambda x: (x.iloc[-1] / x.iloc[0] - 1) * 100 if len(x) > 0 else 0
        }).round(4)
        
        stats.columns = ['avg_volume', 'total_volume', 'volume_std', 
                        'avg_range', 'max_range', 'avg_return']
        
        return stats
    
    def identify_high_impact_times(self, df: pd.DataFrame, 
                                   volume_threshold: float = 1.5) -> pd.DataFrame:
        """
        Identify high-impact time periods based on volume and volatility
        
        Args:
            df: OHLCV dataframe with datetime index
            volume_threshold: Multiplier of average volume
            
        Returns:
            DataFrame with high-impact time periods
        """
        df = df.copy()
        df['hour'] = df.index.hour
        df['minute'] = df.index.minute
        df['time_window'] = df['hour'].astype(str).str.zfill(2) + ':' + df['minute'].astype(str).str.zfill(2)
        
        avg_volume = df['volume'].mean()
        avg_volatility = df['price_range'].mean()
        
        time_stats = df.groupby('time_window').agg({
            'volume': 'mean',
            'price_range': 'mean'
        }).reset_index()
        
        high_impact = time_stats[
            (time_stats['volume'] > avg_volume * volume_threshold) |
            (time_stats['price_range'] > avg_volatility * volume_threshold)
        ]
        
        return high_impact.sort_values('volume', ascending=False)
    
    def session_overlap_analysis(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Analyze session overlaps
        
        London/New York overlap is typically 13:00-16:00 UTC
        Most volatile and liquid period
        
        Returns:
            Dictionary with overlap statistics
        """
        df = self.add_session_info(df)
        
        london_ny_overlap = df[
            (df.index.hour >= 13) & (df.index.hour < 16)
        ]
        
        if len(london_ny_overlap) == 0:
            return {'overlap_percentage': 0}
        
        overlap_stats = {
            'overlap_percentage': len(london_ny_overlap) / len(df) * 100,
            'overlap_avg_volume': london_ny_overlap['volume'].mean(),
            'overall_avg_volume': df['volume'].mean(),
            'overlap_volume_ratio': london_ny_overlap['volume'].mean() / df['volume'].mean(),
            'overlap_avg_range': london_ny_overlap['price_range'].mean(),
            'overall_avg_range': df['price_range'].mean(),
            'overlap_range_ratio': london_ny_overlap['price_range'].mean() / df['price_range'].mean()
        }
        
        return overlap_stats
    
    def get_session_trend(self, df: pd.DataFrame, 
                         session: str) -> Dict[str, any]:
        """
        Get trend information for a specific session
        
        Args:
            df: OHLCV dataframe
            session: Session name (LONDON, NEW_YORK, ASIAN)
            
        Returns:
            Dictionary with session trend info
        """
        df = self.add_session_info(df)
        
        session_data = df[df['session'] == session]
        
        if len(session_data) == 0:
            return {'error': 'No data for this session'}
        
        first_price = session_data['open'].iloc[0]
        last_price = session_data['close'].iloc[-1]
        high_price = session_data['high'].max()
        low_price = session_data['low'].min()
        
        session_return = (last_price / first_price - 1) * 100
        
        trend = 'bullish' if session_return > 0.5 else 'bearish' if session_return < -0.5 else 'neutral'
        
        return {
            'session': session,
            'return': session_return,
            'trend': trend,
            'high': high_price,
            'low': low_price,
            'range': high_price - low_price,
            'total_volume': session_data['volume'].sum()
        }
    
    def mark_key_times(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Mark key times like market opens, closes, major news times
        
        Adds boolean columns for key time markers
        """
        df = df.copy()
        
        df['is_london_open'] = (df.index.hour == 7) & (df.index.minute == 0)
        df['is_ny_open'] = (df.index.hour == 13) & (df.index.minute == 30)
        df['is_asian_open'] = (df.index.hour == 0) & (df.index.minute == 0)
        
        df['is_london_close'] = (df.index.hour == 15) & (df.index.minute == 30)
        df['is_ny_close'] = (df.index.hour == 20) & (df.index.minute == 0)
        
        df['is_overlap'] = (df.index.hour >= 13) & (df.index.hour < 16)
        
        return df
