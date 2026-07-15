"""
Liquidity Analysis Module
Implements institutional liquidity detection and analysis
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
import config
from core.indicators import TechnicalIndicators


class LiquidityAnalysis:
    """Analyzes market liquidity patterns and institutional order flow"""
    
    def __init__(self):
        self.liquidity_pools = []
        self.sweeps = []
        
    def identify_liquidity_pools(self, df: pd.DataFrame, 
                                 lookback: int = None,
                                 min_touches: int = None) -> pd.DataFrame:
        """
        Identify liquidity pools at significant highs/lows
        
        Args:
            df: OHLCV dataframe
            lookback: Bars to look back for identifying pools
            min_touches: Minimum touches to qualify as liquidity pool
            
        Returns:
            DataFrame with liquidity pool data
        """
        if lookback is None:
            lookback = config.LIQUIDITY['pool_lookback']
        if min_touches is None:
            min_touches = config.LIQUIDITY['min_touches']
            
        pools = []
        
        rolling_highs = df['high'].rolling(window=lookback, center=True).max()
        rolling_lows = df['low'].rolling(window=lookback, center=True).min()
        
        df['is_high_pool'] = df['high'] == rolling_highs
        df['is_low_pool'] = df['low'] == rolling_lows
        
        threshold = df['close'] * config.LIQUIDITY['sweep_threshold']
        
        for i in range(lookback, len(df) - lookback):
            if df['is_high_pool'].iloc[i]:
                price_level = df['high'].iloc[i]
                
                touches = 0
                for j in range(max(0, i - lookback), min(len(df), i + lookback)):
                    if abs(df['high'].iloc[j] - price_level) < threshold.iloc[j]:
                        touches += 1
                
                if touches >= min_touches:
                    pools.append({
                        'type': 'resistance',
                        'price': price_level,
                        'index': i,
                        'timestamp': df.index[i],
                        'touches': touches,
                        'strength': touches / lookback
                    })
            
            if df['is_low_pool'].iloc[i]:
                price_level = df['low'].iloc[i]
                
                touches = 0
                for j in range(max(0, i - lookback), min(len(df), i + lookback)):
                    if abs(df['low'].iloc[j] - price_level) < threshold.iloc[j]:
                        touches += 1
                
                if touches >= min_touches:
                    pools.append({
                        'type': 'support',
                        'price': price_level,
                        'index': i,
                        'timestamp': df.index[i],
                        'touches': touches,
                        'strength': touches / lookback
                    })
        
        self.liquidity_pools = pd.DataFrame(pools)
        return self.liquidity_pools
    
    def detect_liquidity_sweep(self, df: pd.DataFrame, 
                               pools: pd.DataFrame = None) -> pd.DataFrame:
        """
        Detect liquidity sweeps (stop hunts)
        
        A sweep occurs when price briefly moves beyond a liquidity pool
        then quickly reverses, indicating institutional stop-loss hunting
        
        Returns:
            DataFrame with sweep events
        """
        if pools is None:
            pools = self.liquidity_pools
            
        if pools.empty:
            return pd.DataFrame()
        
        sweeps = []
        
        for idx in range(len(df)):
            bar = df.iloc[idx]
            
            for _, pool in pools.iterrows():
                if pool['type'] == 'resistance':
                    if bar['high'] > pool['price']:
                        wick_size = bar['high'] - max(bar['open'], bar['close'])
                        total_range = bar['high'] - bar['low']
                        
                        if total_range > 0:
                            wick_rejection_purity = wick_size / total_range
                        else:
                            wick_rejection_purity = 0
                        
                        if bar['close'] < pool['price']:
                            sweeps.append({
                                'type': 'resistance_sweep',
                                'pool_price': pool['price'],
                                'sweep_price': bar['high'],
                                'close_price': bar['close'],
                                'index': idx,
                                'timestamp': df.index[idx],
                                'wick_rejection': wick_rejection_purity,
                                'bearish': True
                            })
                
                elif pool['type'] == 'support':
                    if bar['low'] < pool['price']:
                        wick_size = min(bar['open'], bar['close']) - bar['low']
                        total_range = bar['high'] - bar['low']
                        
                        if total_range > 0:
                            wick_rejection_purity = wick_size / total_range
                        else:
                            wick_rejection_purity = 0
                        
                        if bar['close'] > pool['price']:
                            sweeps.append({
                                'type': 'support_sweep',
                                'pool_price': pool['price'],
                                'sweep_price': bar['low'],
                                'close_price': bar['close'],
                                'index': idx,
                                'timestamp': df.index[idx],
                                'wick_rejection': wick_rejection_purity,
                                'bullish': True
                            })
        
        self.sweeps = pd.DataFrame(sweeps)
        return self.sweeps
    
    def calculate_cvd(self, df: pd.DataFrame, window: int = None) -> pd.Series:
        """
        Calculate Cumulative Volume Delta (CVD)
        Approximation using price movement and volume
        
        In real trading, use actual bid/ask volume data
        """
        if window is None:
            window = config.LIQUIDITY['cvd_window']
        
        df['price_change'] = df['close'].diff()
        
        df['buy_volume'] = np.where(df['price_change'] > 0, df['volume'], 0)
        df['sell_volume'] = np.where(df['price_change'] < 0, df['volume'], 0)
        
        df['delta'] = df['buy_volume'] - df['sell_volume']
        
        cvd = df['delta'].cumsum()
        
        df['cvd_ma'] = cvd.rolling(window=window).mean()
        df['cvd_std'] = cvd.rolling(window=window).std()
        
        cvd_zscore = (cvd - df['cvd_ma']) / df['cvd_std']
        
        return cvd_zscore
    
    def score_liquidity_sweep(self, df: pd.DataFrame, 
                             sweep_idx: int,
                             session_weight: float = 1.0) -> Dict[str, float]:
        """
        Score a liquidity sweep using institutional factors
        
        Based on 5-factor model:
        1. Wick Rejection Purity (28%)
        2. Volume Participation (20%)
        3. CVD Net Absorption (25%)
        4. Structural Recovery (17%)
        5. Session Window (10%)
        
        Returns:
            Dictionary with factor scores and composite score (0-100)
        """
        bar = df.iloc[sweep_idx]
        
        total_range = bar['high'] - bar['low']
        if total_range == 0:
            return {'composite_score': 0}
        
        if 'bullish_candle' in df.columns and bar['bullish_candle']:
            wick_size = min(bar['open'], bar['close']) - bar['low']
        else:
            wick_size = bar['high'] - max(bar['open'], bar['close'])
        
        f1_wick_rejection = (wick_size / total_range) * 100
        
        volume_zscore = TechnicalIndicators.volume_zscore(df, period=20).iloc[sweep_idx]
        f2_volume_participation = min(100, max(0, (volume_zscore + 2) * 25))
        
        if 'cvd_zscore' in df.columns:
            cvd_value = abs(df['cvd_zscore'].iloc[sweep_idx])
            f3_cvd_absorption = min(100, cvd_value * 33.33)
        else:
            f3_cvd_absorption = 50
        
        lookback = 5
        if sweep_idx >= lookback:
            recent_swing = df['high'].iloc[sweep_idx-lookback:sweep_idx].max()
            recovery = (bar['close'] - bar['low']) / (recent_swing - bar['low'])
            f4_structural_recovery = min(100, max(0, recovery * 100))
        else:
            f4_structural_recovery = 50
        
        f5_session = session_weight * 100
        
        composite_score = (
            f1_wick_rejection * config.SCORING_WEIGHTS['wick_rejection'] +
            f2_volume_participation * config.SCORING_WEIGHTS['volume_participation'] +
            f3_cvd_absorption * config.SCORING_WEIGHTS['cvd_absorption'] +
            f4_structural_recovery * config.SCORING_WEIGHTS['structural_recovery'] +
            f5_session * config.SCORING_WEIGHTS['session_timing']
        )
        
        return {
            'f1_wick_rejection': f1_wick_rejection,
            'f2_volume_participation': f2_volume_participation,
            'f3_cvd_absorption': f3_cvd_absorption,
            'f4_structural_recovery': f4_structural_recovery,
            'f5_session': f5_session,
            'composite_score': composite_score
        }
    
    def identify_order_blocks(self, df: pd.DataFrame, 
                             lookback: int = 3) -> pd.DataFrame:
        """
        Identify Order Blocks (OB)
        
        Order blocks are the last bullish/bearish candle before a strong move
        They represent institutional positioning
        """
        order_blocks = []
        
        for i in range(lookback, len(df) - 1):
            current_move = df['close'].iloc[i+1] - df['close'].iloc[i]
            avg_move = df['close'].diff().iloc[i-lookback:i].abs().mean()
            
            if abs(current_move) > avg_move * config.STRUCTURE['displacement_threshold']:
                ob_bar = df.iloc[i]
                
                if current_move > 0:
                    order_blocks.append({
                        'type': 'bullish_ob',
                        'high': ob_bar['high'],
                        'low': ob_bar['low'],
                        'index': i,
                        'timestamp': df.index[i],
                        'strength': abs(current_move) / avg_move
                    })
                else:
                    order_blocks.append({
                        'type': 'bearish_ob',
                        'high': ob_bar['high'],
                        'low': ob_bar['low'],
                        'index': i,
                        'timestamp': df.index[i],
                        'strength': abs(current_move) / avg_move
                    })
        
        return pd.DataFrame(order_blocks)
