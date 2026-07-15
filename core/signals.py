"""
Signal Generator Module
Combines all analysis modules to generate trading signals
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import config
from core.indicators import TechnicalIndicators
from core.liquidity import LiquidityAnalysis
from core.market_structure import MarketStructure
from core.sessions import SessionAnalysis
from core.reversals import ReversalDetection


class SignalGenerator:
    """Generates trading signals by combining multiple analysis methods"""
    
    def __init__(self):
        self.liquidity_analyzer = LiquidityAnalysis()
        self.structure_analyzer = MarketStructure()
        self.session_analyzer = SessionAnalysis()
        self.reversal_detector = ReversalDetection()
        
        self.signals = []
        
    def analyze_complete(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run complete analysis on dataframe
        
        Adds all indicators, analysis, and scoring to the dataframe
        
        Returns:
            Enhanced dataframe with all analysis columns
        """
        df = df.copy()
        
        df['rsi'] = TechnicalIndicators.rsi(df)
        df['rsi_fast'] = TechnicalIndicators.rsi(df, period=config.INDICATORS['RSI']['fast_period'])
        
        macd_line, signal_line, histogram = TechnicalIndicators.macd(df)
        df['macd'] = macd_line
        df['macd_signal'] = signal_line
        df['macd_histogram'] = histogram
        
        df['ema_9'] = TechnicalIndicators.ema(df, config.INDICATORS['EMA']['fast'])
        df['ema_21'] = TechnicalIndicators.ema(df, config.INDICATORS['EMA']['medium'])
        df['ema_50'] = TechnicalIndicators.ema(df, config.INDICATORS['EMA']['slow'])
        df['ema_200'] = TechnicalIndicators.ema(df, config.INDICATORS['EMA']['very_slow'])
        
        df['supertrend'], df['supertrend_direction'] = TechnicalIndicators.supertrend(df)
        
        df['atr'] = TechnicalIndicators.atr(df)
        
        df['vwap'] = TechnicalIndicators.vwap(df)
        
        df['adx'], df['plus_di'], df['minus_di'] = TechnicalIndicators.adx(df)
        
        df['obv'] = TechnicalIndicators.obv(df)
        
        df['rvol'] = TechnicalIndicators.relative_volume(df)
        df['volume_zscore'] = TechnicalIndicators.volume_zscore(df)
        
        upper_bb, middle_bb, lower_bb = TechnicalIndicators.bollinger_bands(df)
        df['bb_upper'] = upper_bb
        df['bb_middle'] = middle_bb
        df['bb_lower'] = lower_bb
        df['bb_width'] = (upper_bb - lower_bb) / middle_bb
        
        df['cvd_zscore'] = self.liquidity_analyzer.calculate_cvd(df)
        
        df = self.session_analyzer.add_session_info(df)
        df = self.session_analyzer.mark_key_times(df)
        
        df['trend'] = self.structure_analyzer.identify_trend(df)
        
        return df
    
    def generate_signals(self, df: pd.DataFrame,
                        strategy_type: str = 'comprehensive') -> pd.DataFrame:
        """
        Generate trading signals based on strategy type
        
        Args:
            df: Dataframe with complete analysis
            strategy_type: 'comprehensive', 'momentum', 'reversal', 'structure'
            
        Returns:
            DataFrame with signals
        """
        if strategy_type == 'comprehensive':
            return self._generate_comprehensive_signals(df)
        elif strategy_type == 'momentum':
            return self._generate_momentum_signals(df)
        elif strategy_type == 'reversal':
            return self._generate_reversal_signals(df)
        elif strategy_type == 'structure':
            return self._generate_structure_signals(df)
        else:
            raise ValueError(f"Unknown strategy type: {strategy_type}")
    
    def _generate_comprehensive_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate comprehensive signals combining all factors
        
        Signal criteria:
        1. Trend alignment (EMA, SuperTrend, ADX)
        2. Momentum confirmation (RSI, MACD)
        3. Volume confirmation (RVOL, CVD)
        4. Structure alignment (BOS, Order Blocks)
        5. Session timing
        6. Liquidity considerations
        """
        signals = []
        
        swing_highs, swing_lows = self.structure_analyzer.identify_swing_points(df)
        liquidity_pools = self.liquidity_analyzer.identify_liquidity_pools(df)
        sweeps = self.liquidity_analyzer.detect_liquidity_sweep(df, liquidity_pools)
        bos_events = self.structure_analyzer.detect_break_of_structure(df, swing_highs, swing_lows)
        order_blocks = self.liquidity_analyzer.identify_order_blocks(df)
        
        for i in range(100, len(df)):
            signal_score = self._calculate_signal_score(df, i, {
                'swing_highs': swing_highs,
                'swing_lows': swing_lows,
                'liquidity_pools': liquidity_pools,
                'sweeps': sweeps,
                'bos_events': bos_events,
                'order_blocks': order_blocks
            })
            
            if signal_score['composite_score'] >= config.FILTERS['min_composite_score']:
                signal = self._create_signal(df, i, signal_score)
                if signal:
                    signals.append(signal)
        
        return pd.DataFrame(signals)
    
    def _generate_momentum_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate signals based on momentum indicators"""
        signals = []
        
        for i in range(50, len(df)):
            bar = df.iloc[i]
            
            bullish_momentum = (
                bar['rsi'] > 50 and bar['rsi'] < 70 and
                bar['macd'] > bar['macd_signal'] and
                bar['close'] > bar['ema_9'] and
                bar['ema_9'] > bar['ema_21'] and
                bar['adx'] > config.INDICATORS['ADX']['threshold']
            )
            
            bearish_momentum = (
                bar['rsi'] < 50 and bar['rsi'] > 30 and
                bar['macd'] < bar['macd_signal'] and
                bar['close'] < bar['ema_9'] and
                bar['ema_9'] < bar['ema_21'] and
                bar['adx'] > config.INDICATORS['ADX']['threshold']
            )
            
            if bullish_momentum and bar['rvol'] > 1.0:
                signals.append({
                    'type': 'LONG',
                    'index': i,
                    'timestamp': df.index[i],
                    'price': bar['close'],
                    'reason': 'bullish_momentum',
                    'rsi': bar['rsi'],
                    'adx': bar['adx'],
                    'rvol': bar['rvol']
                })
            
            elif bearish_momentum and bar['rvol'] > 1.0:
                signals.append({
                    'type': 'SHORT',
                    'index': i,
                    'timestamp': df.index[i],
                    'price': bar['close'],
                    'reason': 'bearish_momentum',
                    'rsi': bar['rsi'],
                    'adx': bar['adx'],
                    'rvol': bar['rvol']
                })
        
        return pd.DataFrame(signals)
    
    def _generate_reversal_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate signals based on reversal patterns"""
        signals = []
        
        divergences = self.reversal_detector.detect_rsi_divergence(df)
        patterns = self.reversal_detector.detect_double_top_bottom(df)
        exhaustion = self.reversal_detector.detect_exhaustion_candles(df)
        
        for _, div in divergences.iterrows():
            idx = div['index']
            bar = df.iloc[idx]
            
            if div['signal'] == 'potential_reversal_up':
                signals.append({
                    'type': 'LONG',
                    'index': idx,
                    'timestamp': div['timestamp'],
                    'price': bar['close'],
                    'reason': 'bullish_divergence',
                    'strength': div['strength']
                })
            elif div['signal'] == 'potential_reversal_down':
                signals.append({
                    'type': 'SHORT',
                    'index': idx,
                    'timestamp': div['timestamp'],
                    'price': bar['close'],
                    'reason': 'bearish_divergence',
                    'strength': div['strength']
                })
        
        for _, pattern in patterns.iterrows():
            idx = pattern['index']
            bar = df.iloc[idx]
            
            signals.append({
                'type': 'LONG' if pattern['type'] == 'double_bottom' else 'SHORT',
                'index': idx,
                'timestamp': pattern['timestamp'],
                'price': bar['close'],
                'reason': pattern['type'],
                'target': pattern['target']
            })
        
        return pd.DataFrame(signals)
    
    def _generate_structure_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate signals based on market structure"""
        signals = []
        
        swing_highs, swing_lows = self.structure_analyzer.identify_swing_points(df)
        bos_events = self.structure_analyzer.detect_break_of_structure(df, swing_highs, swing_lows)
        choch_events = self.structure_analyzer.detect_change_of_character(df, swing_highs, swing_lows)
        order_blocks = self.liquidity_analyzer.identify_order_blocks(df)
        
        for _, bos in bos_events.iterrows():
            idx = bos['index']
            bar = df.iloc[idx]
            
            recent_obs = order_blocks[
                (order_blocks['index'] < idx) & 
                (order_blocks['index'] > idx - 20)
            ]
            
            if not recent_obs.empty and bos['confidence'] == 'high':
                signals.append({
                    'type': 'LONG' if bos['type'] == 'bullish_bos' else 'SHORT',
                    'index': idx,
                    'timestamp': bos['timestamp'],
                    'price': bar['close'],
                    'reason': bos['type'],
                    'momentum': bos['momentum'],
                    'has_order_block': True
                })
        
        for _, choch in choch_events.iterrows():
            idx = choch['index']
            bar = df.iloc[idx]
            
            signals.append({
                'type': 'LONG' if choch['type'] == 'bullish_choch' else 'SHORT',
                'index': idx,
                'timestamp': choch['timestamp'],
                'price': bar['close'],
                'reason': choch['type'],
                'signal': choch['signal']
            })
        
        return pd.DataFrame(signals)
    
    def _calculate_signal_score(self, df: pd.DataFrame, idx: int,
                               analysis_data: Dict) -> Dict[str, float]:
        """
        Calculate comprehensive signal score at a given index
        
        Returns:
            Dictionary with factor scores and composite score
        """
        bar = df.iloc[idx]
        
        trend_score = 0
        if bar['trend'] == 'uptrend':
            if bar['close'] > bar['ema_9'] > bar['ema_21'] > bar['ema_50']:
                trend_score = 100
            elif bar['close'] > bar['ema_9'] > bar['ema_21']:
                trend_score = 70
        elif bar['trend'] == 'downtrend':
            if bar['close'] < bar['ema_9'] < bar['ema_21'] < bar['ema_50']:
                trend_score = 100
            elif bar['close'] < bar['ema_9'] < bar['ema_21']:
                trend_score = 70
        
        momentum_score = 0
        if 40 < bar['rsi'] < 60:
            momentum_score = 50
        elif bar['trend'] == 'uptrend' and 50 < bar['rsi'] < 70:
            momentum_score = 80
        elif bar['trend'] == 'downtrend' and 30 < bar['rsi'] < 50:
            momentum_score = 80
        
        if bar['macd'] > bar['macd_signal'] and bar['macd_histogram'] > 0:
            momentum_score += 20
        
        volume_score = min(100, (bar['rvol'] - 0.5) * 50) if bar['rvol'] > 0.5 else 0
        
        if bar['volume_zscore'] > 1.5:
            volume_score = min(100, volume_score + 20)
        
        structure_score = 50
        recent_bos = [b for b in analysis_data['bos_events'].to_dict('records')
                     if b['index'] > idx - 10 and b['index'] <= idx]
        if recent_bos:
            structure_score = 80
        
        recent_obs = [ob for ob in analysis_data['order_blocks'].to_dict('records')
                     if ob['index'] > idx - 20 and ob['index'] <= idx]
        if recent_obs:
            structure_score += 20
        structure_score = min(100, structure_score)
        
        session_score = bar['session_weight'] * 100
        
        liquidity_score = 50
        recent_sweeps = [s for s in analysis_data['sweeps'].to_dict('records')
                        if s['index'] > idx - 5 and s['index'] <= idx]
        if recent_sweeps:
            for sweep in recent_sweeps:
                if sweep.get('wick_rejection', 0) > 0.7:
                    liquidity_score = 90
                    break
        
        composite_score = (
            trend_score * 0.25 +
            momentum_score * 0.20 +
            volume_score * 0.20 +
            structure_score * 0.20 +
            session_score * 0.10 +
            liquidity_score * 0.05
        )
        
        return {
            'trend_score': trend_score,
            'momentum_score': momentum_score,
            'volume_score': volume_score,
            'structure_score': structure_score,
            'session_score': session_score,
            'liquidity_score': liquidity_score,
            'composite_score': composite_score
        }
    
    def _create_signal(self, df: pd.DataFrame, idx: int,
                      signal_score: Dict) -> Optional[Dict]:
        """
        Create a trading signal with entry, stop loss, and take profit levels
        """
        bar = df.iloc[idx]
        
        if bar['trend'] == 'uptrend' and bar['close'] > bar['vwap']:
            signal_type = 'LONG'
        elif bar['trend'] == 'downtrend' and bar['close'] < bar['vwap']:
            signal_type = 'SHORT'
        else:
            return None
        
        atr = bar['atr']
        
        if signal_type == 'LONG':
            entry_price = bar['close']
            stop_loss = entry_price - (atr * 1.5)
            take_profit_1 = entry_price + (atr * 2.0)
            take_profit_2 = entry_price + (atr * 3.0)
            take_profit_3 = entry_price + (atr * 4.0)
        else:
            entry_price = bar['close']
            stop_loss = entry_price + (atr * 1.5)
            take_profit_1 = entry_price - (atr * 2.0)
            take_profit_2 = entry_price - (atr * 3.0)
            take_profit_3 = entry_price - (atr * 4.0)
        
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit_1 - entry_price)
        risk_reward = reward / risk if risk > 0 else 0
        
        return {
            'type': signal_type,
            'index': idx,
            'timestamp': df.index[idx],
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit_1': take_profit_1,
            'take_profit_2': take_profit_2,
            'take_profit_3': take_profit_3,
            'risk_reward': risk_reward,
            'composite_score': signal_score['composite_score'],
            'trend': bar['trend'],
            'rsi': bar['rsi'],
            'adx': bar['adx'],
            'session': bar['session'],
            'rvol': bar['rvol']
        }
    
    def filter_signals(self, signals: pd.DataFrame, 
                      min_score: float = None,
                      min_risk_reward: float = None) -> pd.DataFrame:
        """
        Filter signals based on quality criteria
        """
        if min_score is None:
            min_score = config.FILTERS['min_composite_score']
        if min_risk_reward is None:
            min_risk_reward = config.RISK['risk_reward_ratio']
        
        filtered = signals.copy()
        
        if 'composite_score' in filtered.columns:
            filtered = filtered[filtered['composite_score'] >= min_score]
        
        if 'risk_reward' in filtered.columns:
            filtered = filtered[filtered['risk_reward'] >= min_risk_reward]
        
        if config.FILTERS['require_session_alignment'] and 'session' in filtered.columns:
            filtered = filtered[filtered['session'].isin(['LONDON', 'NEW_YORK'])]
        
        return filtered.reset_index(drop=True)
