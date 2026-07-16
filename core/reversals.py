"""
Reversal Detection Module
Identifies potential market reversals using divergence and pattern analysis
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
import config
from core.indicators import TechnicalIndicators


class ReversalDetection:
    """Detects potential market reversals"""
    
    def __init__(self):
        self.divergences = []
        
    def detect_rsi_divergence(self, df: pd.DataFrame,
                             lookback: int = 14) -> pd.DataFrame:
        """
        Detect RSI divergence patterns
        
        Bullish divergence: Price makes lower low, RSI makes higher low
        Bearish divergence: Price makes higher high, RSI makes lower high
        
        Returns:
            DataFrame with divergence events
        """
        rsi = TechnicalIndicators.rsi(df)
        df['rsi'] = rsi
        
        divergences = []
        
        price_highs = []
        price_lows = []
        rsi_highs = []
        rsi_lows = []
        
        for i in range(lookback, len(df) - lookback):
            is_price_high = True
            is_price_low = True
            is_rsi_high = True
            is_rsi_low = True
            
            for j in range(i - lookback, i + lookback + 1):
                if j == i:
                    continue
                
                if df['high'].iloc[j] >= df['high'].iloc[i]:
                    is_price_high = False
                if df['low'].iloc[j] <= df['low'].iloc[i]:
                    is_price_low = False
                if rsi.iloc[j] >= rsi.iloc[i]:
                    is_rsi_high = False
                if rsi.iloc[j] <= rsi.iloc[i]:
                    is_rsi_low = False
            
            if is_price_high:
                price_highs.append({'index': i, 'price': df['high'].iloc[i]})
            if is_price_low:
                price_lows.append({'index': i, 'price': df['low'].iloc[i]})
            if is_rsi_high:
                rsi_highs.append({'index': i, 'rsi': rsi.iloc[i]})
            if is_rsi_low:
                rsi_lows.append({'index': i, 'rsi': rsi.iloc[i]})
        
        for i in range(1, len(price_highs)):
            curr_price_high = price_highs[i]
            prev_price_high = price_highs[i-1]
            
            matching_rsi_curr = [r for r in rsi_highs if abs(r['index'] - curr_price_high['index']) <= 3]
            matching_rsi_prev = [r for r in rsi_highs if abs(r['index'] - prev_price_high['index']) <= 3]
            
            if matching_rsi_curr and matching_rsi_prev:
                if (curr_price_high['price'] > prev_price_high['price'] and
                    matching_rsi_curr[0]['rsi'] < matching_rsi_prev[0]['rsi']):
                    
                    divergences.append({
                        'type': 'bearish_divergence',
                        'index': curr_price_high['index'],
                        'timestamp': df.index[curr_price_high['index']],
                        'price': curr_price_high['price'],
                        'rsi': matching_rsi_curr[0]['rsi'],
                        'strength': abs(matching_rsi_prev[0]['rsi'] - matching_rsi_curr[0]['rsi']),
                        'signal': 'potential_reversal_down'
                    })
        
        for i in range(1, len(price_lows)):
            curr_price_low = price_lows[i]
            prev_price_low = price_lows[i-1]
            
            matching_rsi_curr = [r for r in rsi_lows if abs(r['index'] - curr_price_low['index']) <= 3]
            matching_rsi_prev = [r for r in rsi_lows if abs(r['index'] - prev_price_low['index']) <= 3]
            
            if matching_rsi_curr and matching_rsi_prev:
                if (curr_price_low['price'] < prev_price_low['price'] and
                    matching_rsi_curr[0]['rsi'] > matching_rsi_prev[0]['rsi']):
                    
                    divergences.append({
                        'type': 'bullish_divergence',
                        'index': curr_price_low['index'],
                        'timestamp': df.index[curr_price_low['index']],
                        'price': curr_price_low['price'],
                        'rsi': matching_rsi_curr[0]['rsi'],
                        'strength': abs(matching_rsi_curr[0]['rsi'] - matching_rsi_prev[0]['rsi']),
                        'signal': 'potential_reversal_up'
                    })
        
        self.divergences = pd.DataFrame(divergences)
        return self.divergences
    
    def detect_macd_divergence(self, df: pd.DataFrame,
                              lookback: int = 14) -> pd.DataFrame:
        """
        Detect MACD divergence patterns
        
        Returns:
            DataFrame with MACD divergence events
        """
        macd_line, signal_line, histogram = TechnicalIndicators.macd(df)
        df['macd'] = macd_line
        df['macd_histogram'] = histogram
        
        divergences = []
        
        price_highs = []
        price_lows = []
        macd_highs = []
        macd_lows = []
        
        for i in range(lookback, len(df) - lookback):
            is_price_high = all(df['high'].iloc[i] >= df['high'].iloc[j] 
                              for j in range(i - lookback, i + lookback + 1) if j != i)
            is_price_low = all(df['low'].iloc[i] <= df['low'].iloc[j] 
                             for j in range(i - lookback, i + lookback + 1) if j != i)
            is_macd_high = all(macd_line.iloc[i] >= macd_line.iloc[j] 
                             for j in range(i - lookback, i + lookback + 1) if j != i)
            is_macd_low = all(macd_line.iloc[i] <= macd_line.iloc[j] 
                            for j in range(i - lookback, i + lookback + 1) if j != i)
            
            if is_price_high:
                price_highs.append({'index': i, 'price': df['high'].iloc[i]})
            if is_price_low:
                price_lows.append({'index': i, 'price': df['low'].iloc[i]})
            if is_macd_high:
                macd_highs.append({'index': i, 'macd': macd_line.iloc[i]})
            if is_macd_low:
                macd_lows.append({'index': i, 'macd': macd_line.iloc[i]})
        
        for i in range(1, len(price_highs)):
            curr_price_high = price_highs[i]
            prev_price_high = price_highs[i-1]
            
            matching_macd_curr = [m for m in macd_highs if abs(m['index'] - curr_price_high['index']) <= 3]
            matching_macd_prev = [m for m in macd_highs if abs(m['index'] - prev_price_high['index']) <= 3]
            
            if matching_macd_curr and matching_macd_prev:
                if (curr_price_high['price'] > prev_price_high['price'] and
                    matching_macd_curr[0]['macd'] < matching_macd_prev[0]['macd']):
                    
                    divergences.append({
                        'type': 'bearish_macd_divergence',
                        'index': curr_price_high['index'],
                        'timestamp': df.index[curr_price_high['index']],
                        'signal': 'potential_reversal_down',
                        'strength': abs(matching_macd_prev[0]['macd'] - matching_macd_curr[0]['macd'])
                    })
        
        for i in range(1, len(price_lows)):
            curr_price_low = price_lows[i]
            prev_price_low = price_lows[i-1]
            
            matching_macd_curr = [m for m in macd_lows if abs(m['index'] - curr_price_low['index']) <= 3]
            matching_macd_prev = [m for m in macd_lows if abs(m['index'] - prev_price_low['index']) <= 3]
            
            if matching_macd_curr and matching_macd_prev:
                if (curr_price_low['price'] < prev_price_low['price'] and
                    matching_macd_curr[0]['macd'] > matching_macd_prev[0]['macd']):
                    
                    divergences.append({
                        'type': 'bullish_macd_divergence',
                        'index': curr_price_low['index'],
                        'timestamp': df.index[curr_price_low['index']],
                        'signal': 'potential_reversal_up',
                        'strength': abs(matching_macd_curr[0]['macd'] - matching_macd_prev[0]['macd'])
                    })
        
        return pd.DataFrame(divergences)
    
    def detect_double_top_bottom(self, df: pd.DataFrame,
                                 tolerance: float = 0.02,
                                 min_distance: int = 10) -> pd.DataFrame:
        """
        Detect double top and double bottom patterns
        
        Args:
            df: OHLCV dataframe
            tolerance: Price tolerance for "equal" levels (2% default)
            min_distance: Minimum bars between tops/bottoms
            
        Returns:
            DataFrame with pattern events
        """
        patterns = []
        
        swing_highs = []
        swing_lows = []
        
        lookback = 5
        for i in range(lookback, len(df) - lookback):
            is_high = all(df['high'].iloc[i] >= df['high'].iloc[j] 
                         for j in range(i - lookback, i + lookback + 1) if j != i)
            is_low = all(df['low'].iloc[i] <= df['low'].iloc[j] 
                        for j in range(i - lookback, i + lookback + 1) if j != i)
            
            if is_high:
                swing_highs.append({'index': i, 'price': df['high'].iloc[i]})
            if is_low:
                swing_lows.append({'index': i, 'price': df['low'].iloc[i]})
        
        for i in range(1, len(swing_highs)):
            curr = swing_highs[i]
            prev = swing_highs[i-1]
            
            if curr['index'] - prev['index'] >= min_distance:
                price_diff = abs(curr['price'] - prev['price']) / prev['price']
                
                if price_diff <= tolerance:
                    neckline = df['low'].iloc[prev['index']:curr['index']].min()
                    
                    patterns.append({
                        'type': 'double_top',
                        'index': curr['index'],
                        'timestamp': df.index[curr['index']],
                        'first_top': prev['price'],
                        'second_top': curr['price'],
                        'neckline': neckline,
                        'signal': 'potential_reversal_down',
                        'target': neckline - (curr['price'] - neckline)
                    })
        
        for i in range(1, len(swing_lows)):
            curr = swing_lows[i]
            prev = swing_lows[i-1]
            
            if curr['index'] - prev['index'] >= min_distance:
                price_diff = abs(curr['price'] - prev['price']) / prev['price']
                
                if price_diff <= tolerance:
                    neckline = df['high'].iloc[prev['index']:curr['index']].max()
                    
                    patterns.append({
                        'type': 'double_bottom',
                        'index': curr['index'],
                        'timestamp': df.index[curr['index']],
                        'first_bottom': prev['price'],
                        'second_bottom': curr['price'],
                        'neckline': neckline,
                        'signal': 'potential_reversal_up',
                        'target': neckline + (neckline - curr['price'])
                    })
        
        return pd.DataFrame(patterns)
    
    def detect_exhaustion_candles(self, df: pd.DataFrame,
                                  volume_threshold: float = 2.0) -> pd.DataFrame:
        """
        Detect exhaustion candles (potential reversal signals)
        
        Characteristics:
        - Large range compared to recent candles
        - High volume
        - Long wicks in trend direction
        - Close near opposite end
        
        Returns:
            DataFrame with exhaustion candle events
        """
        exhaustion_candles = []
        
        avg_range = df['price_range'].rolling(window=20).mean()
        rvol = TechnicalIndicators.relative_volume(df)
        
        for i in range(20, len(df)):
            bar = df.iloc[i]
            
            if bar['price_range'] > avg_range.iloc[i] * 1.5:
                if rvol.iloc[i] > volume_threshold:
                    upper_wick_ratio = bar['upper_wick'] / bar['price_range'] if bar['price_range'] > 0 else 0
                    lower_wick_ratio = bar['lower_wick'] / bar['price_range'] if bar['price_range'] > 0 else 0
                    
                    if upper_wick_ratio > 0.5 and bar['close'] < bar['open']:
                        exhaustion_candles.append({
                            'type': 'bearish_exhaustion',
                            'index': i,
                            'timestamp': df.index[i],
                            'signal': 'potential_reversal_down',
                            'wick_ratio': upper_wick_ratio,
                            'rvol': rvol.iloc[i]
                        })
                    
                    elif lower_wick_ratio > 0.5 and bar['close'] > bar['open']:
                        exhaustion_candles.append({
                            'type': 'bullish_exhaustion',
                            'index': i,
                            'timestamp': df.index[i],
                            'signal': 'potential_reversal_up',
                            'wick_ratio': lower_wick_ratio,
                            'rvol': rvol.iloc[i]
                        })
        
        return pd.DataFrame(exhaustion_candles)
    
    def score_reversal_probability(self, df: pd.DataFrame,
                                   idx: int,
                                   divergences: pd.DataFrame = None,
                                   patterns: pd.DataFrame = None) -> Dict[str, float]:
        """
        Score the probability of a reversal at a given index
        
        Considers:
        - Divergence presence
        - Pattern confirmation
        - Overbought/oversold conditions
        - Volume characteristics
        
        Returns:
            Dictionary with probability scores
        """
        rsi = TechnicalIndicators.rsi(df).iloc[idx]
        
        if rsi > 70:
            rsi_score = min(100, (rsi - 70) * 3.33)
            reversal_direction = 'down'
        elif rsi < 30:
            rsi_score = min(100, (30 - rsi) * 3.33)
            reversal_direction = 'up'
        else:
            rsi_score = 0
            reversal_direction = 'neutral'
        
        divergence_score = 0
        if divergences is not None and not divergences.empty:
            recent_divs = divergences[
                (divergences['index'] >= idx - 5) & 
                (divergences['index'] <= idx + 5)
            ]
            if not recent_divs.empty:
                divergence_score = 70
        
        pattern_score = 0
        if patterns is not None and not patterns.empty:
            recent_patterns = patterns[
                (patterns['index'] >= idx - 10) & 
                (patterns['index'] <= idx + 10)
            ]
            if not recent_patterns.empty:
                pattern_score = 60
        
        rvol = TechnicalIndicators.relative_volume(df).iloc[idx]
        volume_score = min(100, (rvol - 1) * 50) if rvol > 1 else 0
        
        composite_probability = (
            rsi_score * 0.30 +
            divergence_score * 0.35 +
            pattern_score * 0.20 +
            volume_score * 0.15
        )
        
        return {
            'reversal_direction': reversal_direction,
            'rsi_score': rsi_score,
            'divergence_score': divergence_score,
            'pattern_score': pattern_score,
            'volume_score': volume_score,
            'composite_probability': composite_probability
        }
