"""
Example Trading Strategies
Demonstrates how to use the framework to build different trading strategies
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
sys.path.append('..')

from core.data_handler import DataHandler
from core.signals import SignalGenerator
from core.backtest import Backtester
import config


class TJRStrategy:
    """
    TJR Trading Strategy (Upgraded Version)
    
    Combines:
    - Market structure analysis (BOS/CHoCH)
    - Liquidity sweeps detection
    - Session-based timing
    - Momentum confirmation
    - Volume analysis
    """
    
    def __init__(self):
        self.signal_generator = SignalGenerator()
        self.name = "TJR Enhanced Strategy"
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals using TJR methodology"""
        df = self.signal_generator.analyze_complete(df)
        
        signals = self.signal_generator.generate_signals(df, strategy_type='comprehensive')
        
        filtered_signals = self.signal_generator.filter_signals(
            signals,
            min_score=65,
            min_risk_reward=2.0
        )
        
        return filtered_signals


class MomentumBreakoutStrategy:
    """
    Momentum Breakout Strategy
    
    Trades breakouts with strong momentum confirmation
    - SuperTrend for trend direction
    - RSI for momentum
    - High volume confirmation
    - ADX for trend strength
    """
    
    def __init__(self):
        self.signal_generator = SignalGenerator()
        self.name = "Momentum Breakout Strategy"
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate momentum breakout signals"""
        df = self.signal_generator.analyze_complete(df)
        
        signals = self.signal_generator.generate_signals(df, strategy_type='momentum')
        
        filtered = signals[
            (signals['adx'] > 25) &
            (signals['rvol'] > 1.3)
        ]
        
        return filtered.reset_index(drop=True)


class ReversalStrategy:
    """
    Reversal Trading Strategy
    
    Identifies high-probability reversal points using:
    - RSI/MACD divergence
    - Double tops/bottoms
    - Exhaustion candles
    - Overbought/oversold conditions
    """
    
    def __init__(self):
        self.signal_generator = SignalGenerator()
        self.name = "Reversal Strategy"
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate reversal signals"""
        df = self.signal_generator.analyze_complete(df)
        
        signals = self.signal_generator.generate_signals(df, strategy_type='reversal')
        
        return signals


class StructureStrategy:
    """
    Market Structure Strategy
    
    Pure market structure trading:
    - Break of Structure (BOS) for continuations
    - Change of Character (CHoCH) for reversals
    - Order block confirmation
    - Fair value gaps
    """
    
    def __init__(self):
        self.signal_generator = SignalGenerator()
        self.name = "Market Structure Strategy"
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate structure-based signals"""
        df = self.signal_generator.analyze_complete(df)
        
        signals = self.signal_generator.generate_signals(df, strategy_type='structure')
        
        return signals


class SessionBasedStrategy:
    """
    Session-Based Strategy
    
    Focuses on high-liquidity sessions:
    - London session (7-10 UTC)
    - New York session (13-16 UTC)
    - London/NY overlap (13-16 UTC)
    
    Only trades during high-participation windows
    """
    
    def __init__(self):
        self.signal_generator = SignalGenerator()
        self.name = "Session-Based Strategy"
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate session-based signals"""
        df = self.signal_generator.analyze_complete(df)
        
        signals = self.signal_generator.generate_signals(df, strategy_type='comprehensive')
        
        session_filtered = signals[
            signals['session'].isin(['LONDON', 'NEW_YORK'])
        ]
        
        return session_filtered.reset_index(drop=True)


class ScalpingStrategy:
    """
    Scalping Strategy (Short-term)
    
    For 1-5 minute timeframes:
    - Fast EMAs (5, 13)
    - Quick RSI (9)
    - VWAP as anchor
    - High volume confirmation
    - Tight stops, quick profits
    """
    
    def __init__(self):
        self.signal_generator = SignalGenerator()
        self.name = "Scalping Strategy"
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate scalping signals"""
        df = self.signal_generator.analyze_complete(df)
        
        signals = []
        
        for i in range(50, len(df)):
            bar = df.iloc[i]
            
            fast_ema = TechnicalIndicators.ema(df, 5).iloc[i]
            medium_ema = TechnicalIndicators.ema(df, 13).iloc[i]
            
            bullish_scalp = (
                bar['close'] > bar['vwap'] and
                fast_ema > medium_ema and
                bar['rsi_fast'] > 55 and bar['rsi_fast'] < 75 and
                bar['rvol'] > 1.2
            )
            
            bearish_scalp = (
                bar['close'] < bar['vwap'] and
                fast_ema < medium_ema and
                bar['rsi_fast'] < 45 and bar['rsi_fast'] > 25 and
                bar['rvol'] > 1.2
            )
            
            if bullish_scalp:
                signals.append({
                    'type': 'LONG',
                    'index': i,
                    'timestamp': df.index[i],
                    'entry_price': bar['close'],
                    'stop_loss': bar['close'] - bar['atr'] * 1.0,
                    'take_profit_1': bar['close'] + bar['atr'] * 1.5,
                    'take_profit_2': bar['close'] + bar['atr'] * 2.0,
                    'take_profit_3': bar['close'] + bar['atr'] * 2.5,
                    'rsi': bar['rsi_fast'],
                    'rvol': bar['rvol']
                })
            
            elif bearish_scalp:
                signals.append({
                    'type': 'SHORT',
                    'index': i,
                    'timestamp': df.index[i],
                    'entry_price': bar['close'],
                    'stop_loss': bar['close'] + bar['atr'] * 1.0,
                    'take_profit_1': bar['close'] - bar['atr'] * 1.5,
                    'take_profit_2': bar['close'] - bar['atr'] * 2.0,
                    'take_profit_3': bar['close'] - bar['atr'] * 2.5,
                    'rsi': bar['rsi_fast'],
                    'rvol': bar['rvol']
                })
        
        return pd.DataFrame(signals)


class SwingStrategy:
    """
    Swing Trading Strategy (Multi-day holds)
    
    For 4H - Daily timeframes:
    - Trend identification with 50/200 EMAs
    - Weekly structure analysis
    - Momentum with MACD
    - Entry on pullbacks to key levels
    """
    
    def __init__(self):
        self.signal_generator = SignalGenerator()
        self.name = "Swing Trading Strategy"
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate swing trading signals"""
        df = self.signal_generator.analyze_complete(df)
        
        signals = []
        
        for i in range(200, len(df)):
            bar = df.iloc[i]
            
            strong_uptrend = (
                bar['ema_50'] > bar['ema_200'] and
                bar['close'] > bar['ema_50'] and
                bar['adx'] > 25
            )
            
            strong_downtrend = (
                bar['ema_50'] < bar['ema_200'] and
                bar['close'] < bar['ema_50'] and
                bar['adx'] > 25
            )
            
            pullback_to_support = (
                strong_uptrend and
                bar['low'] <= bar['ema_21'] and
                bar['close'] > bar['ema_21'] and
                bar['rsi'] > 40 and bar['rsi'] < 60
            )
            
            pullback_to_resistance = (
                strong_downtrend and
                bar['high'] >= bar['ema_21'] and
                bar['close'] < bar['ema_21'] and
                bar['rsi'] < 60 and bar['rsi'] > 40
            )
            
            if pullback_to_support:
                signals.append({
                    'type': 'LONG',
                    'index': i,
                    'timestamp': df.index[i],
                    'entry_price': bar['close'],
                    'stop_loss': bar['close'] - bar['atr'] * 2.0,
                    'take_profit_1': bar['close'] + bar['atr'] * 3.0,
                    'take_profit_2': bar['close'] + bar['atr'] * 5.0,
                    'take_profit_3': bar['close'] + bar['atr'] * 7.0,
                    'trend': 'uptrend',
                    'adx': bar['adx']
                })
            
            elif pullback_to_resistance:
                signals.append({
                    'type': 'SHORT',
                    'index': i,
                    'timestamp': df.index[i],
                    'entry_price': bar['close'],
                    'stop_loss': bar['close'] + bar['atr'] * 2.0,
                    'take_profit_1': bar['close'] - bar['atr'] * 3.0,
                    'take_profit_2': bar['close'] - bar['atr'] * 5.0,
                    'take_profit_3': bar['close'] - bar['atr'] * 7.0,
                    'trend': 'downtrend',
                    'adx': bar['adx']
                })
        
        return pd.DataFrame(signals)


def run_strategy_comparison(symbol: str, start_date: str, end_date: str,
                           interval: str = '1h'):
    """
    Compare all strategies on the same data
    
    Args:
        symbol: Trading symbol (e.g., 'AAPL', 'BTC-USD')
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        interval: Data interval
    """
    print(f"\n{'='*80}")
    print(f"STRATEGY COMPARISON: {symbol}")
    print(f"Period: {start_date} to {end_date}")
    print(f"Interval: {interval}")
    print(f"{'='*80}\n")
    
    data_handler = DataHandler()
    df = data_handler.fetch_data(symbol, start_date, end_date, interval)
    
    from core.indicators import TechnicalIndicators
    
    strategies = [
        TJRStrategy(),
        MomentumBreakoutStrategy(),
        ReversalStrategy(),
        StructureStrategy(),
        SessionBasedStrategy(),
        SwingStrategy()
    ]
    
    results = []
    
    for strategy in strategies:
        print(f"\nTesting {strategy.name}...")
        
        try:
            signals = strategy.generate_signals(df)
            
            if len(signals) == 0:
                print(f"  No signals generated")
                continue
            
            backtester = Backtester()
            metrics = backtester.run_backtest(df, signals)
            
            results.append({
                'strategy': strategy.name,
                'total_return': metrics['total_return_pct'],
                'win_rate': metrics['win_rate_pct'],
                'profit_factor': metrics['profit_factor'],
                'sharpe_ratio': metrics['sharpe_ratio'],
                'max_drawdown': metrics['max_drawdown_pct'],
                'total_trades': metrics['total_trades']
            })
            
            print(f"  Signals: {len(signals)}")
            print(f"  Return: {metrics['total_return_pct']:.2f}%")
            print(f"  Win Rate: {metrics['win_rate_pct']:.2f}%")
            print(f"  Profit Factor: {metrics['profit_factor']:.2f}")
            
        except Exception as e:
            print(f"  Error: {str(e)}")
    
    if results:
        print(f"\n{'='*80}")
        print("STRATEGY COMPARISON SUMMARY")
        print(f"{'='*80}\n")
        
        results_df = pd.DataFrame(results)
        results_df = results_df.sort_values('total_return', ascending=False)
        
        print(results_df.to_string(index=False))
        print(f"\n{'='*80}\n")
        
        return results_df
    
    return None


if __name__ == "__main__":
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    run_strategy_comparison(
        symbol='SPY',
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d'),
        interval='1h'
    )
