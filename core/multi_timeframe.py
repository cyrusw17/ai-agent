"""
Multi-Timeframe Confluence Module
Implements HTF → ITF → LTF scaling strategies with confluence validation
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from core.indicators import TechnicalIndicators
from core.market_structure import MarketStructure
from core.liquidity import LiquidityAnalysis


class FairValueGap:
    """Detects and manages Fair Value Gaps (FVG)"""
    
    @staticmethod
    def detect_fvg(df: pd.DataFrame, min_gap_size: float = 0.0001) -> pd.DataFrame:
        """
        Detect Fair Value Gaps
        
        Bullish FVG: Gap between bar1.high and bar3.low (bar2 creates gap)
        Bearish FVG: Gap between bar1.low and bar3.high (bar2 creates gap)
        
        Args:
            df: OHLCV dataframe
            min_gap_size: Minimum gap size to qualify
            
        Returns:
            DataFrame with FVG events
        """
        fvgs = []
        
        for i in range(2, len(df)):
            bar1 = df.iloc[i-2]
            bar2 = df.iloc[i-1]
            bar3 = df.iloc[i]
            
            # Bullish FVG
            if bar1['high'] < bar3['low']:
                gap_size = bar3['low'] - bar1['high']
                
                if gap_size >= min_gap_size:
                    fvgs.append({
                        'type': 'bullish_fvg',
                        'index': i,
                        'timestamp': df.index[i],
                        'top': bar3['low'],
                        'bottom': bar1['high'],
                        'gap_size': gap_size,
                        'gap_percent': (gap_size / bar1['high']) * 100,
                        'filled': False
                    })
            
            # Bearish FVG
            elif bar1['low'] > bar3['high']:
                gap_size = bar1['low'] - bar3['high']
                
                if gap_size >= min_gap_size:
                    fvgs.append({
                        'type': 'bearish_fvg',
                        'index': i,
                        'timestamp': df.index[i],
                        'top': bar1['low'],
                        'bottom': bar3['high'],
                        'gap_size': gap_size,
                        'gap_percent': (gap_size / bar3['high']) * 100,
                        'filled': False
                    })
        
        return pd.DataFrame(fvgs)
    
    @staticmethod
    def check_fvg_fill(df: pd.DataFrame, fvg: Dict, current_idx: int) -> bool:
        """
        Check if FVG has been filled by price action
        
        Args:
            df: Price dataframe
            fvg: FVG dictionary
            current_idx: Current bar index
            
        Returns:
            True if FVG is filled
        """
        if current_idx <= fvg['index']:
            return False
        
        for i in range(fvg['index'] + 1, current_idx + 1):
            bar = df.iloc[i]
            
            if fvg['type'] == 'bullish_fvg':
                # Filled if price goes back into gap
                if bar['low'] <= fvg['top'] and bar['low'] >= fvg['bottom']:
                    return True
            else:  # bearish_fvg
                # Filled if price goes back into gap
                if bar['high'] >= fvg['bottom'] and bar['high'] <= fvg['top']:
                    return True
        
        return False
    
    @staticmethod
    def get_active_fvgs(df: pd.DataFrame, fvgs: pd.DataFrame, 
                       current_idx: int, lookback: int = 20) -> pd.DataFrame:
        """
        Get FVGs that are still active (unfilled) and recent
        
        Args:
            df: Price dataframe
            fvgs: All detected FVGs
            current_idx: Current bar index
            lookback: How far back to look for active FVGs
            
        Returns:
            DataFrame of active FVGs
        """
        if fvgs.empty:
            return pd.DataFrame()
        
        recent_fvgs = fvgs[
            (fvgs['index'] >= current_idx - lookback) & 
            (fvgs['index'] < current_idx)
        ]
        
        active = []
        for _, fvg in recent_fvgs.iterrows():
            if not FairValueGap.check_fvg_fill(df, fvg.to_dict(), current_idx):
                active.append(fvg.to_dict())
        
        return pd.DataFrame(active)


class EqualHighsLows:
    """Detects equal highs and equal lows"""
    
    @staticmethod
    def detect_equal_highs(df: pd.DataFrame, tolerance: float = 0.001,
                          lookback: int = 20) -> pd.DataFrame:
        """
        Detect equal highs (liquidity pools)
        
        Args:
            df: OHLCV dataframe
            tolerance: Price tolerance for "equal" (0.1% default)
            lookback: Bars to look back
            
        Returns:
            DataFrame with equal high events
        """
        equal_highs = []
        
        for i in range(lookback, len(df)):
            current_high = df['high'].iloc[i]
            
            # Look for equal highs in lookback period
            for j in range(i - lookback, i):
                compare_high = df['high'].iloc[j]
                
                price_diff = abs(current_high - compare_high) / compare_high
                
                if price_diff <= tolerance:
                    equal_highs.append({
                        'type': 'equal_high',
                        'index': i,
                        'timestamp': df.index[i],
                        'price': current_high,
                        'first_touch_index': j,
                        'touches': 2,
                        'tolerance': price_diff
                    })
                    break
        
        return pd.DataFrame(equal_highs)
    
    @staticmethod
    def detect_equal_lows(df: pd.DataFrame, tolerance: float = 0.001,
                         lookback: int = 20) -> pd.DataFrame:
        """
        Detect equal lows (liquidity pools)
        
        Args:
            df: OHLCV dataframe
            tolerance: Price tolerance for "equal" (0.1% default)
            lookback: Bars to look back
            
        Returns:
            DataFrame with equal low events
        """
        equal_lows = []
        
        for i in range(lookback, len(df)):
            current_low = df['low'].iloc[i]
            
            # Look for equal lows in lookback period
            for j in range(i - lookback, i):
                compare_low = df['low'].iloc[j]
                
                price_diff = abs(current_low - compare_low) / compare_low
                
                if price_diff <= tolerance:
                    equal_lows.append({
                        'type': 'equal_low',
                        'index': i,
                        'timestamp': df.index[i],
                        'price': current_low,
                        'first_touch_index': j,
                        'touches': 2,
                        'tolerance': price_diff
                    })
                    break
        
        return pd.DataFrame(equal_lows)


class MultiTimeframeAnalysis:
    """Analyzes multiple timeframes for confluence"""
    
    def __init__(self):
        self.structure = MarketStructure()
        self.liquidity = LiquidityAnalysis()
        self.fvg = FairValueGap()
        self.eq = EqualHighsLows()
        
    def analyze_timeframe(self, df: pd.DataFrame, 
                         timeframe: str) -> Dict[str, any]:
        """
        Complete analysis of a single timeframe
        
        Args:
            df: OHLCV dataframe
            timeframe: Timeframe label (e.g., '4H', '1H', '15M')
            
        Returns:
            Dictionary with all analysis results
        """
        # Trend/bias
        df['ema_9'] = TechnicalIndicators.ema(df, 9)
        df['ema_21'] = TechnicalIndicators.ema(df, 21)
        df['ema_50'] = TechnicalIndicators.ema(df, 50)
        
        trend = self.structure.identify_trend(df)
        
        # Structure
        swing_highs, swing_lows = self.structure.identify_swing_points(df)
        bos_events = self.structure.detect_break_of_structure(
            df, swing_highs, swing_lows
        )
        choch_events = self.structure.detect_change_of_character(
            df, swing_highs, swing_lows
        )
        
        # Liquidity
        order_blocks = self.liquidity.identify_order_blocks(df)
        liquidity_pools = self.liquidity.identify_liquidity_pools(df)
        
        # FVGs
        fvgs = self.fvg.detect_fvg(df)
        
        # Equal highs/lows
        equal_highs = self.eq.detect_equal_highs(df)
        equal_lows = self.eq.detect_equal_lows(df)
        
        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = TechnicalIndicators.bollinger_bands(df)
        df['bb_upper'] = bb_upper
        df['bb_middle'] = bb_middle
        df['bb_lower'] = bb_lower
        
        return {
            'timeframe': timeframe,
            'df': df,
            'trend': trend,
            'swing_highs': swing_highs,
            'swing_lows': swing_lows,
            'bos_events': bos_events,
            'choch_events': choch_events,
            'order_blocks': order_blocks,
            'liquidity_pools': liquidity_pools,
            'fvgs': fvgs,
            'equal_highs': equal_highs,
            'equal_lows': equal_lows
        }
    
    def check_trend_alignment(self, htf_trend: str, itf_trend: str) -> bool:
        """
        Check if HTF and ITF trends are aligned
        
        Args:
            htf_trend: Higher timeframe trend
            itf_trend: Intermediate timeframe trend
            
        Returns:
            True if aligned
        """
        return htf_trend == itf_trend
    
    def detect_confluence_hit(self, df: pd.DataFrame, current_idx: int,
                             confluence_type: str, analysis: Dict,
                             direction: str) -> Tuple[bool, Dict]:
        """
        Check if price has hit a confluence zone
        
        Args:
            df: Price dataframe
            current_idx: Current bar index
            confluence_type: Type of confluence (fvg, ob, bb, eq)
            analysis: Timeframe analysis results
            direction: 'bullish' or 'bearish'
            
        Returns:
            (hit: bool, confluence_data: dict)
        """
        bar = df.iloc[current_idx]
        
        if confluence_type == 'fvg':
            active_fvgs = self.fvg.get_active_fvgs(
                df, analysis['fvgs'], current_idx
            )
            
            for _, fvg in active_fvgs.iterrows():
                if direction == 'bullish' and fvg['type'] == 'bullish_fvg':
                    if bar['low'] <= fvg['top'] and bar['low'] >= fvg['bottom']:
                        return True, {'type': 'fvg', 'data': fvg.to_dict()}
                
                elif direction == 'bearish' and fvg['type'] == 'bearish_fvg':
                    if bar['high'] >= fvg['bottom'] and bar['high'] <= fvg['top']:
                        return True, {'type': 'fvg', 'data': fvg.to_dict()}
        
        elif confluence_type == 'ob':
            recent_obs = analysis['order_blocks'][
                (analysis['order_blocks']['index'] >= current_idx - 20) &
                (analysis['order_blocks']['index'] < current_idx)
            ]
            
            for _, ob in recent_obs.iterrows():
                if direction == 'bullish' and ob['type'] == 'bullish_ob':
                    if bar['low'] <= ob['high'] and bar['low'] >= ob['low']:
                        return True, {'type': 'ob', 'data': ob.to_dict()}
                
                elif direction == 'bearish' and ob['type'] == 'bearish_ob':
                    if bar['high'] >= ob['low'] and bar['high'] <= ob['high']:
                        return True, {'type': 'ob', 'data': ob.to_dict()}
        
        elif confluence_type == 'bb':
            if direction == 'bullish':
                if bar['low'] <= df['bb_lower'].iloc[current_idx]:
                    return True, {
                        'type': 'bb',
                        'data': {'level': df['bb_lower'].iloc[current_idx]}
                    }
            
            elif direction == 'bearish':
                if bar['high'] >= df['bb_upper'].iloc[current_idx]:
                    return True, {
                        'type': 'bb',
                        'data': {'level': df['bb_upper'].iloc[current_idx]}
                    }
        
        elif confluence_type == 'eq':
            if direction == 'bullish':
                recent_eq = analysis['equal_lows'][
                    (analysis['equal_lows']['index'] >= current_idx - 20) &
                    (analysis['equal_lows']['index'] < current_idx)
                ]
                
                for _, eq in recent_eq.iterrows():
                    price_diff = abs(bar['low'] - eq['price']) / eq['price']
                    if price_diff <= 0.002:  # Within 0.2%
                        return True, {'type': 'eq', 'data': eq.to_dict()}
            
            elif direction == 'bearish':
                recent_eq = analysis['equal_highs'][
                    (analysis['equal_highs']['index'] >= current_idx - 20) &
                    (analysis['equal_highs']['index'] < current_idx)
                ]
                
                for _, eq in recent_eq.iterrows():
                    price_diff = abs(bar['high'] - eq['price']) / eq['price']
                    if price_diff <= 0.002:  # Within 0.2%
                        return True, {'type': 'eq', 'data': eq.to_dict()}
        
        return False, {}
    
    def check_directional_candle(self, df: pd.DataFrame, idx: int,
                                 direction: str) -> bool:
        """
        Check if current candle is directional (bullish/bearish)
        
        Args:
            df: Price dataframe
            idx: Bar index
            direction: 'bullish' or 'bearish'
            
        Returns:
            True if candle matches direction
        """
        bar = df.iloc[idx]
        
        if direction == 'bullish':
            return bar['close'] > bar['open']
        else:
            return bar['close'] < bar['open']
