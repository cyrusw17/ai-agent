"""
Market Structure Analysis Module
Implements Break of Structure (BOS) and Change of Character (CHoCH) detection
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
import config
from core.indicators import TechnicalIndicators


class MarketStructure:
    """Analyzes market structure and detects structural breaks"""
    
    def __init__(self):
        self.swing_highs = []
        self.swing_lows = []
        self.bos_events = []
        self.choch_events = []
        
    def identify_swing_points(self, df: pd.DataFrame, 
                             lookback: int = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Identify swing highs and swing lows
        
        Args:
            df: OHLCV dataframe
            lookback: Bars on each side to confirm swing
            
        Returns:
            swing_highs, swing_lows DataFrames
        """
        if lookback is None:
            lookback = config.STRUCTURE['swing_lookback']
        
        swing_highs = []
        swing_lows = []
        
        for i in range(lookback, len(df) - lookback):
            is_swing_high = True
            is_swing_low = True
            
            current_high = df['high'].iloc[i]
            current_low = df['low'].iloc[i]
            
            for j in range(i - lookback, i + lookback + 1):
                if j == i:
                    continue
                    
                if df['high'].iloc[j] >= current_high:
                    is_swing_high = False
                    
                if df['low'].iloc[j] <= current_low:
                    is_swing_low = False
            
            if is_swing_high:
                swing_highs.append({
                    'price': current_high,
                    'index': i,
                    'timestamp': df.index[i]
                })
            
            if is_swing_low:
                swing_lows.append({
                    'price': current_low,
                    'index': i,
                    'timestamp': df.index[i]
                })
        
        self.swing_highs = pd.DataFrame(swing_highs)
        self.swing_lows = pd.DataFrame(swing_lows)
        
        return self.swing_highs, self.swing_lows
    
    def detect_break_of_structure(self, df: pd.DataFrame,
                                  swing_highs: pd.DataFrame = None,
                                  swing_lows: pd.DataFrame = None,
                                  min_momentum: float = None) -> pd.DataFrame:
        """
        Detect Break of Structure (BOS)
        
        BOS confirms trend continuation:
        - Bullish BOS: Price breaks above previous swing high
        - Bearish BOS: Price breaks below previous swing low
        
        Args:
            df: OHLCV dataframe
            swing_highs: DataFrame of swing highs
            swing_lows: DataFrame of swing lows
            min_momentum: Minimum momentum threshold for valid BOS
            
        Returns:
            DataFrame with BOS events
        """
        if swing_highs is None or swing_lows is None:
            swing_highs, swing_lows = self.identify_swing_points(df)
        
        if min_momentum is None:
            min_momentum = config.STRUCTURE['min_momentum']
        
        bos_events = []
        
        momentum = df['close'].pct_change(periods=5).abs() * 100
        
        for i in range(len(df)):
            current_high = df['high'].iloc[i]
            current_low = df['low'].iloc[i]
            current_close = df['close'].iloc[i]
            
            if i < len(df) - 1:
                recent_swings_high = swing_highs[swing_highs['index'] < i]
                if not recent_swings_high.empty:
                    last_swing_high = recent_swings_high.iloc[-1]
                    
                    if (current_close > last_swing_high['price'] and 
                        momentum.iloc[i] >= min_momentum):
                        
                        displacement = current_close - df['close'].iloc[i-5] if i >= 5 else 0
                        
                        bos_events.append({
                            'type': 'bullish_bos',
                            'price': current_close,
                            'broken_level': last_swing_high['price'],
                            'index': i,
                            'timestamp': df.index[i],
                            'momentum': momentum.iloc[i],
                            'displacement': displacement,
                            'confidence': 'high'
                        })
                
                recent_swings_low = swing_lows[swing_lows['index'] < i]
                if not recent_swings_low.empty:
                    last_swing_low = recent_swings_low.iloc[-1]
                    
                    if (current_close < last_swing_low['price'] and 
                        momentum.iloc[i] >= min_momentum):
                        
                        displacement = df['close'].iloc[i-5] - current_close if i >= 5 else 0
                        
                        bos_events.append({
                            'type': 'bearish_bos',
                            'price': current_close,
                            'broken_level': last_swing_low['price'],
                            'index': i,
                            'timestamp': df.index[i],
                            'momentum': momentum.iloc[i],
                            'displacement': displacement,
                            'confidence': 'high'
                        })
        
        self.bos_events = pd.DataFrame(bos_events)
        return self.bos_events
    
    def detect_change_of_character(self, df: pd.DataFrame,
                                   swing_highs: pd.DataFrame = None,
                                   swing_lows: pd.DataFrame = None) -> pd.DataFrame:
        """
        Detect Change of Character (CHoCH)
        
        CHoCH signals potential trend reversal:
        - In uptrend: Price breaks below last higher low
        - In downtrend: Price breaks above last lower high
        
        Returns:
            DataFrame with CHoCH events
        """
        if swing_highs is None or swing_lows is None:
            swing_highs, swing_lows = self.identify_swing_points(df)
        
        choch_events = []
        
        trend = self.identify_trend(df)
        
        for i in range(len(df)):
            current_close = df['close'].iloc[i]
            current_trend = trend.iloc[i]
            
            if current_trend == 'uptrend':
                recent_swings_low = swing_lows[swing_lows['index'] < i]
                if not recent_swings_low.empty:
                    last_higher_low = recent_swings_low.iloc[-1]
                    
                    if current_close < last_higher_low['price']:
                        choch_events.append({
                            'type': 'bearish_choch',
                            'price': current_close,
                            'broken_level': last_higher_low['price'],
                            'index': i,
                            'timestamp': df.index[i],
                            'previous_trend': 'uptrend',
                            'signal': 'potential_reversal_down'
                        })
            
            elif current_trend == 'downtrend':
                recent_swings_high = swing_highs[swing_highs['index'] < i]
                if not recent_swings_high.empty:
                    last_lower_high = recent_swings_high.iloc[-1]
                    
                    if current_close > last_lower_high['price']:
                        choch_events.append({
                            'type': 'bullish_choch',
                            'price': current_close,
                            'broken_level': last_lower_high['price'],
                            'index': i,
                            'timestamp': df.index[i],
                            'previous_trend': 'downtrend',
                            'signal': 'potential_reversal_up'
                        })
        
        self.choch_events = pd.DataFrame(choch_events)
        return self.choch_events
    
    def identify_trend(self, df: pd.DataFrame, 
                      ema_fast: int = None,
                      ema_slow: int = None) -> pd.Series:
        """
        Identify overall trend using EMAs and price structure
        
        Returns:
            Series with trend labels: 'uptrend', 'downtrend', 'ranging'
        """
        if ema_fast is None:
            ema_fast = config.INDICATORS['EMA']['fast']
        if ema_slow is None:
            ema_slow = config.INDICATORS['EMA']['slow']
        
        ema_f = TechnicalIndicators.ema(df, ema_fast)
        ema_s = TechnicalIndicators.ema(df, ema_slow)
        
        adx, _, _ = TechnicalIndicators.adx(df)
        adx_threshold = config.INDICATORS['ADX']['threshold']
        
        trend = pd.Series(index=df.index, dtype=str)
        
        for i in range(len(df)):
            if pd.isna(adx.iloc[i]):
                trend.iloc[i] = 'ranging'
                continue
            
            if ema_f.iloc[i] > ema_s.iloc[i] and adx.iloc[i] > adx_threshold:
                trend.iloc[i] = 'uptrend'
            elif ema_f.iloc[i] < ema_s.iloc[i] and adx.iloc[i] > adx_threshold:
                trend.iloc[i] = 'downtrend'
            else:
                trend.iloc[i] = 'ranging'
        
        return trend
    
    def score_bos(self, df: pd.DataFrame, bos_idx: int,
                  order_blocks: pd.DataFrame = None) -> Dict[str, float]:
        """
        Score a Break of Structure event
        
        Uses momentum, volume, and alignment with order blocks
        
        Returns:
            Dictionary with scoring metrics (0-100)
        """
        if bos_idx >= len(df):
            return {'composite_score': 0}
        
        bar = df.iloc[bos_idx]
        
        momentum = abs(df['close'].pct_change(periods=5).iloc[bos_idx]) * 100
        momentum_score = min(100, momentum * 20)
        
        volume_zscore = TechnicalIndicators.volume_zscore(df, period=20).iloc[bos_idx]
        volume_score = min(100, max(0, (volume_zscore + 2) * 25))
        
        rsi = TechnicalIndicators.rsi(df).iloc[bos_idx]
        
        if rsi > 50:
            rsi_score = min(100, (rsi - 50) * 2)
        else:
            rsi_score = min(100, (50 - rsi) * 2)
        
        ob_score = 50
        if order_blocks is not None and not order_blocks.empty:
            recent_obs = order_blocks[order_blocks['index'] < bos_idx]
            if not recent_obs.empty:
                last_ob = recent_obs.iloc[-1]
                if last_ob['index'] > bos_idx - 10:
                    ob_score = 100
        
        composite_score = (
            momentum_score * 0.35 +
            volume_score * 0.30 +
            rsi_score * 0.20 +
            ob_score * 0.15
        )
        
        return {
            'momentum_score': momentum_score,
            'volume_score': volume_score,
            'rsi_score': rsi_score,
            'order_block_score': ob_score,
            'composite_score': composite_score
        }
    
    def identify_higher_highs_lows(self, df: pd.DataFrame,
                                   swing_highs: pd.DataFrame = None,
                                   swing_lows: pd.DataFrame = None) -> Dict[str, List]:
        """
        Identify Higher Highs (HH), Higher Lows (HL), Lower Highs (LH), Lower Lows (LL)
        
        Returns:
            Dictionary with lists of each pattern
        """
        if swing_highs is None or swing_lows is None:
            swing_highs, swing_lows = self.identify_swing_points(df)
        
        patterns = {
            'higher_highs': [],
            'higher_lows': [],
            'lower_highs': [],
            'lower_lows': []
        }
        
        for i in range(1, len(swing_highs)):
            if swing_highs.iloc[i]['price'] > swing_highs.iloc[i-1]['price']:
                patterns['higher_highs'].append(swing_highs.iloc[i].to_dict())
            else:
                patterns['lower_highs'].append(swing_highs.iloc[i].to_dict())
        
        for i in range(1, len(swing_lows)):
            if swing_lows.iloc[i]['price'] > swing_lows.iloc[i-1]['price']:
                patterns['higher_lows'].append(swing_lows.iloc[i].to_dict())
            else:
                patterns['lower_lows'].append(swing_lows.iloc[i].to_dict())
        
        return patterns
    
    def calculate_structure_strength(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate overall market structure strength
        
        Strong structure = consistent HH/HL (uptrend) or LH/LL (downtrend)
        
        Returns:
            Series with structure strength score (0-100)
        """
        strength = pd.Series(index=df.index, dtype=float)
        
        swing_highs, swing_lows = self.identify_swing_points(df)
        patterns = self.identify_higher_highs_lows(df, swing_highs, swing_lows)
        
        for i in range(len(df)):
            recent_hh = len([p for p in patterns['higher_highs'] 
                           if p['index'] > i - 20 and p['index'] <= i])
            recent_hl = len([p for p in patterns['higher_lows'] 
                           if p['index'] > i - 20 and p['index'] <= i])
            recent_lh = len([p for p in patterns['lower_highs'] 
                           if p['index'] > i - 20 and p['index'] <= i])
            recent_ll = len([p for p in patterns['lower_lows'] 
                           if p['index'] > i - 20 and p['index'] <= i])
            
            uptrend_consistency = (recent_hh + recent_hl) / max(1, recent_hh + recent_hl + recent_lh + recent_ll)
            downtrend_consistency = (recent_lh + recent_ll) / max(1, recent_hh + recent_hl + recent_lh + recent_ll)
            
            strength.iloc[i] = max(uptrend_consistency, downtrend_consistency) * 100
        
        return strength
