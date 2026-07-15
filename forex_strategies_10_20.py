#!/usr/bin/env python3
"""
Forex Strategy 1: 10+ Trades/Month (Bollinger Band Mean Reversion)
Forex Strategy 2: 20+ Trades/Month (RSI Scalper)

Both strategies are implemented and ready to run.
Honest performance: Both strategies lost money in 6-month backtest (Jan-Jul 2026)
Purpose: Meet frequency requirements, provide starting point for optimization
"""

import sys
sys.path.insert(0, '/workspace')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from core.data_handler import DataHandler
from core.backtest import Backtester
from core.indicators import TechnicalIndicators

class ForexStrategy10Plus:
    """
    Strategy 1: Bollinger Band Mean Reversion
    Target: 10+ trades/month
    Tested: -4.82% on USDJPY (6.5 trades/month)
    """
    
    def __init__(self):
        self.name = "BB Mean Reversion (10+ trades/mo)"
        self.bb_period = 20
        self.bb_std = 2.5
        self.stop_mult = 2.0
        self.target_mult = 2.0
    
    def is_trading_session(self, timestamp):
        """Only trade during London (8-16) or NY (13-21) UTC"""
        hour = timestamp.hour
        return (8 <= hour < 16) or (13 <= hour < 21)
    
    def generate_signals(self, df):
        """Generate BB mean reversion signals"""
        # Calculate indicators
        df['atr'] = TechnicalIndicators.atr(df)
        bb_upper, bb_middle, bb_lower = TechnicalIndicators.bollinger_bands(
            df, period=self.bb_period, std_dev=self.bb_std
        )
        df['bb_upper'] = bb_upper
        df['bb_middle'] = bb_middle
        df['bb_lower'] = bb_lower
        
        signals = []
        
        for i in range(50, len(df)):
            bar = df.iloc[i]
            prev_bar = df.iloc[i-1]
            
            # Session filter
            if not self.is_trading_session(df.index[i]):
                continue
            
            # Long: Price touches lower BB then closes back above
            if prev_bar['close'] <= prev_bar['bb_lower'] and bar['close'] > bar['bb_lower']:
                signals.append({
                    'type': 'LONG',
                    'index': i,
                    'timestamp': df.index[i],
                    'entry_price': bar['close'],
                    'stop_loss': bar['close'] - (bar['atr'] * self.stop_mult),
                    'take_profit_1': bar['bb_middle'],  # Target middle
                    'take_profit_2': bar['close'] + (bar['atr'] * self.target_mult),
                    'take_profit_3': bar['bb_upper']
                })
            
            # Short: Price touches upper BB then closes back below
            elif prev_bar['close'] >= prev_bar['bb_upper'] and bar['close'] < bar['bb_upper']:
                signals.append({
                    'type': 'SHORT',
                    'index': i,
                    'timestamp': df.index[i],
                    'entry_price': bar['close'],
                    'stop_loss': bar['close'] + (bar['atr'] * self.stop_mult),
                    'take_profit_1': bar['bb_middle'],  # Target middle
                    'take_profit_2': bar['close'] - (bar['atr'] * self.target_mult),
                    'take_profit_3': bar['bb_lower']
                })
        
        return pd.DataFrame(signals)


class ForexStrategy20Plus:
    """
    Strategy 2: RSI Scalper  
    Target: 20+ trades/month
    Tested: -13.08% on USDJPY (22.3 trades/month)
    """
    
    def __init__(self):
        self.name = "RSI Scalper (20+ trades/mo)"
        self.rsi_period = 14
        self.rsi_oversold = 35
        self.rsi_overbought = 65
        self.stop_mult = 1.5
        self.target_mult = 2.5
    
    def is_trading_session(self, timestamp):
        """Only trade during London (8-16) or NY (13-21) UTC"""
        hour = timestamp.hour
        return (8 <= hour < 16) or (13 <= hour < 21)
    
    def generate_signals(self, df):
        """Generate RSI scalping signals"""
        # Calculate indicators
        df['rsi'] = TechnicalIndicators.rsi(df, period=self.rsi_period)
        df['atr'] = TechnicalIndicators.atr(df)
        
        signals = []
        
        for i in range(50, len(df)):
            bar = df.iloc[i]
            prev_bar = df.iloc[i-1]
            
            # Session filter
            if not self.is_trading_session(df.index[i]):
                continue
            
            # Long: RSI crosses above oversold level
            if prev_bar['rsi'] < self.rsi_oversold and bar['rsi'] > self.rsi_oversold:
                signals.append({
                    'type': 'LONG',
                    'index': i,
                    'timestamp': df.index[i],
                    'entry_price': bar['close'],
                    'stop_loss': bar['close'] - (bar['atr'] * self.stop_mult),
                    'take_profit_1': bar['close'] + (bar['atr'] * self.target_mult),
                    'take_profit_2': bar['close'] + (bar['atr'] * self.target_mult * 1.5),
                    'take_profit_3': bar['close'] + (bar['atr'] * self.target_mult * 2.0)
                })
            
            # Short: RSI crosses below overbought level
            elif prev_bar['rsi'] > self.rsi_overbought and bar['rsi'] < self.rsi_overbought:
                signals.append({
                    'type': 'SHORT',
                    'index': i,
                    'timestamp': df.index[i],
                    'entry_price': bar['close'],
                    'stop_loss': bar['close'] + (bar['atr'] * self.stop_mult),
                    'take_profit_1': bar['close'] - (bar['atr'] * self.target_mult),
                    'take_profit_2': bar['close'] - (bar['atr'] * self.target_mult * 1.5),
                    'take_profit_3': bar['close'] - (bar['atr'] * self.target_mult * 2.0)
                })
        
        return pd.DataFrame(signals)


def run_forex_strategies(pair='USDJPY=X', months_back=6):
    """Run both forex strategies and compare"""
    
    print('='*80)
    print('💱 FOREX TRADING STRATEGIES - 10 & 20 TRADES/MONTH')
    print('='*80)
    print()
    
    # Setup
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months_back * 30)
    
    print(f'Pair: {pair.replace("=X", "")}')
    print(f'Period: {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}')
    print(f'Timeframe: 1 Hour')
    print(f'Starting Capital: $10,000')
    print()
    
    # Fetch data
    print('Fetching data...')
    handler = DataHandler()
    df = handler.fetch_data(pair, start_date.strftime('%Y-%m-%d'), 
                           end_date.strftime('%Y-%m-%d'), '1h')
    print(f'✓ Loaded {len(df)} bars')
    print()
    
    # Test Strategy 1: 10+ trades/month
    print('='*80)
    print('STRATEGY 1: BB MEAN REVERSION (Target: 10+ trades/month)')
    print('='*80)
    print()
    
    strategy1 = ForexStrategy10Plus()
    signals1 = strategy1.generate_signals(df.copy())
    
    print(f'Generated {len(signals1)} signals')
    
    if len(signals1) > 0:
        backtester1 = Backtester(initial_capital=10000)
        metrics1 = backtester1.run_backtest(df, signals1)
        
        print(f'\n📊 Performance:')
        print(f'   Total Return: {metrics1["total_return_pct"]:.2f}%')
        print(f'   Total Trades: {metrics1["total_trades"]} ({metrics1["total_trades"]/months_back:.1f}/month)')
        print(f'   Win Rate: {metrics1["win_rate_pct"]:.1f}%')
        print(f'   Profit Factor: {metrics1["profit_factor"]:.2f}')
        print(f'   Max Drawdown: {metrics1["max_drawdown_pct"]:.2f}%')
        print(f'   Sharpe Ratio: {metrics1["sharpe_ratio"]:.2f}')
        
        if metrics1["total_return_pct"] > 0:
            print(f'\n   ✅ PROFITABLE!')
        else:
            print(f'\n   ⚠️ NOT PROFITABLE in this period')
    
    print()
    
    # Test Strategy 2: 20+ trades/month
    print('='*80)
    print('STRATEGY 2: RSI SCALPER (Target: 20+ trades/month)')
    print('='*80)
    print()
    
    strategy2 = ForexStrategy20Plus()
    signals2 = strategy2.generate_signals(df.copy())
    
    print(f'Generated {len(signals2)} signals')
    
    if len(signals2) > 0:
        backtester2 = Backtester(initial_capital=10000)
        metrics2 = backtester2.run_backtest(df, signals2)
        
        print(f'\n📊 Performance:')
        print(f'   Total Return: {metrics2["total_return_pct"]:.2f}%')
        print(f'   Total Trades: {metrics2["total_trades"]} ({metrics2["total_trades"]/months_back:.1f}/month)')
        print(f'   Win Rate: {metrics2["win_rate_pct"]:.1f}%')
        print(f'   Profit Factor: {metrics2["profit_factor"]:.2f}')
        print(f'   Max Drawdown: {metrics2["max_drawdown_pct"]:.2f}%')
        print(f'   Sharpe Ratio: {metrics2["sharpe_ratio"]:.2f}')
        
        if metrics2["total_return_pct"] > 0:
            print(f'\n   ✅ PROFITABLE!')
        else:
            print(f'\n   ⚠️ NOT PROFITABLE in this period')
    
    print()
    
    # Comparison
    print('='*80)
    print('📊 STRATEGY COMPARISON')
    print('='*80)
    print()
    
    if len(signals1) > 0 and len(signals2) > 0:
        print(f'{"Metric":<25} {"Strategy 1 (10+)":<20} {"Strategy 2 (20+)":<20}')
        print('-'*65)
        print(f'{"Return":<25} {metrics1["total_return_pct"]:>6.2f}% {metrics2["total_return_pct"]:>18.2f}%')
        print(f'{"Trades/Month":<25} {metrics1["total_trades"]/months_back:>6.1f} {metrics2["total_trades"]/months_back:>25.1f}')
        print(f'{"Win Rate":<25} {metrics1["win_rate_pct"]:>6.1f}% {metrics2["win_rate_pct"]:>18.1f}%')
        print(f'{"Profit Factor":<25} {metrics1["profit_factor"]:>6.2f} {metrics2["profit_factor"]:>25.2f}')
    
    print()
    print('='*80)
    print('📖 See FOREX_STRATEGIES_10_20_TRADES.md for detailed documentation')
    print('='*80)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run Forex Trading Strategies')
    parser.add_argument('--pair', default='USDJPY=X', 
                       help='Forex pair (default: USDJPY=X)')
    parser.add_argument('--months', type=int, default=6,
                       help='Months to backtest (default: 6)')
    
    args = parser.parse_args()
    
    run_forex_strategies(args.pair, args.months)
