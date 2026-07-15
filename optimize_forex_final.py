#!/usr/bin/env python3
"""
Final Forex Optimizer - Find ANYTHING That Works First
Then increase frequency from there
"""

import sys
sys.path.insert(0, '/workspace')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from core.data_handler import DataHandler
from core.backtest import Backtester
from core.indicators import TechnicalIndicators

print('='*80)
print('💱 COMPREHENSIVE FOREX OPTIMIZER - FIND ANYTHING PROFITABLE')
print('='*80)
print()

FOREX_PAIRS = ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'AUDUSD=X']
INITIAL_CAPITAL = 10000
TIMEFRAME = '1h'
MONTHS_BACK = 6

end_date = datetime.now()
start_date = end_date - timedelta(days=MONTHS_BACK * 30)

print('Strategy: Try EVERYTHING - trend, reversion, breakout, range')
print('Goal: Find profitable setups, ANY frequency')
print()

# Massive configuration space
configs = []

# 1. Varied stop/target ratios (key to profitability)
for ema_f, ema_s in [(3,8), (5,13), (8,21)]:
    for stop in [0.8, 1.0, 1.2, 1.5, 2.0]:
        for target in [2.0, 2.5, 3.0, 3.5, 4.0]:
            if target > stop * 1.5:  # Only valid R:R ratios
                for adx_min in [0, 15, 20, 25]:
                    configs.append({
                        'name': f'EMA{ema_f}/{ema_s} S{stop}T{target} ADX{adx_min}',
                        'type': 'ema',
                        'ema_fast': ema_f,
                        'ema_slow': ema_s,
                        'min_adx': adx_min,
                        'stop_mult': stop,
                        'target_mult': target,
                    })

# 2. RSI with different levels
for os in [20, 25, 30, 35]:
    for ob in [65, 70, 75, 80]:
        for stop in [1.0, 1.5, 2.0]:
            for target in [2.0, 2.5, 3.0]:
                configs.append({
                    'name': f'RSI{os}/{ob} S{stop}T{target}',
                    'type': 'rsi',
                    'rsi_oversold': os,
                    'rsi_overbought': ob,
                    'stop_mult': stop,
                    'target_mult': target,
                })

# 3. BB with different settings
for bb_std in [2.0, 2.5, 3.0]:
    for stop in [1.0, 1.5, 2.0]:
        for target in [1.5, 2.0, 2.5]:
            configs.append({
                'name': f'BB{bb_std} S{stop}T{target}',
                'type': 'bb',
                'bb_std': bb_std,
                'stop_mult': stop,
                'target_mult': target,
            })

print(f'Total configurations: {len(configs)}')
print('Testing on 4 forex pairs...')
print()

def generate_signals(df, params):
    """Generate signals based on type"""
    
    df['rsi'] = TechnicalIndicators.rsi(df, period=14)
    df['atr'] = TechnicalIndicators.atr(df)
    
    if params['type'] == 'ema':
        df['ema_fast'] = TechnicalIndicators.ema(df, params['ema_fast'])
        df['ema_slow'] = TechnicalIndicators.ema(df, params['ema_slow'])
        if params['min_adx'] > 0:
            adx, _, _ = TechnicalIndicators.adx(df)
            df['adx'] = adx
    
    if params['type'] == 'bb':
        bb_upper, bb_middle, bb_lower = TechnicalIndicators.bollinger_bands(
            df, period=20, std_dev=params['bb_std']
        )
        df['bb_upper'] = bb_upper
        df['bb_middle'] = bb_middle
        df['bb_lower'] = bb_lower
    
    signals = []
    
    for i in range(50, len(df)):
        bar = df.iloc[i]
        prev_bar = df.iloc[i-1]
        
        # EMA Trend
        if params['type'] == 'ema':
            if params['min_adx'] > 0:
                if 'adx' not in df.columns or bar['adx'] < params['min_adx']:
                    continue
            
            if bar['ema_fast'] > bar['ema_slow'] and prev_bar['ema_fast'] <= prev_bar['ema_slow']:
                signals.append({
                    'type': 'LONG',
                    'index': i,
                    'timestamp': df.index[i],
                    'entry_price': bar['close'],
                    'stop_loss': bar['close'] - (bar['atr'] * params['stop_mult']),
                    'take_profit_1': bar['close'] + (bar['atr'] * params['target_mult']),
                    'take_profit_2': bar['close'] + (bar['atr'] * params['target_mult'] * 1.5),
                    'take_profit_3': bar['close'] + (bar['atr'] * params['target_mult'] * 2.0)
                })
            elif bar['ema_fast'] < bar['ema_slow'] and prev_bar['ema_fast'] >= prev_bar['ema_slow']:
                signals.append({
                    'type': 'SHORT',
                    'index': i,
                    'timestamp': df.index[i],
                    'entry_price': bar['close'],
                    'stop_loss': bar['close'] + (bar['atr'] * params['stop_mult']),
                    'take_profit_1': bar['close'] - (bar['atr'] * params['target_mult']),
                    'take_profit_2': bar['close'] - (bar['atr'] * params['target_mult'] * 1.5),
                    'take_profit_3': bar['close'] - (bar['atr'] * params['target_mult'] * 2.0)
                })
        
        # RSI
        elif params['type'] == 'rsi':
            if prev_bar['rsi'] < params['rsi_oversold'] and bar['rsi'] > params['rsi_oversold']:
                signals.append({
                    'type': 'LONG',
                    'index': i,
                    'timestamp': df.index[i],
                    'entry_price': bar['close'],
                    'stop_loss': bar['close'] - (bar['atr'] * params['stop_mult']),
                    'take_profit_1': bar['close'] + (bar['atr'] * params['target_mult']),
                    'take_profit_2': bar['close'] + (bar['atr'] * params['target_mult'] * 1.5),
                    'take_profit_3': bar['close'] + (bar['atr'] * params['target_mult'] * 2.0)
                })
            elif prev_bar['rsi'] > params['rsi_overbought'] and bar['rsi'] < params['rsi_overbought']:
                signals.append({
                    'type': 'SHORT',
                    'index': i,
                    'timestamp': df.index[i],
                    'entry_price': bar['close'],
                    'stop_loss': bar['close'] + (bar['atr'] * params['stop_mult']),
                    'take_profit_1': bar['close'] - (bar['atr'] * params['target_mult']),
                    'take_profit_2': bar['close'] - (bar['atr'] * params['target_mult'] * 1.5),
                    'take_profit_3': bar['close'] - (bar['atr'] * params['target_mult'] * 2.0)
                })
        
        # BB
        elif params['type'] == 'bb':
            if prev_bar['close'] <= prev_bar['bb_lower'] and bar['close'] > bar['bb_lower']:
                signals.append({
                    'type': 'LONG',
                    'index': i,
                    'timestamp': df.index[i],
                    'entry_price': bar['close'],
                    'stop_loss': bar['close'] - (bar['atr'] * params['stop_mult']),
                    'take_profit_1': bar['bb_middle'],
                    'take_profit_2': bar['close'] + (bar['atr'] * params['target_mult'] * 1.5),
                    'take_profit_3': bar['bb_upper']
                })
            elif prev_bar['close'] >= prev_bar['bb_upper'] and bar['close'] < bar['bb_upper']:
                signals.append({
                    'type': 'SHORT',
                    'index': i,
                    'timestamp': df.index[i],
                    'entry_price': bar['close'],
                    'stop_loss': bar['close'] + (bar['atr'] * params['stop_mult']),
                    'take_profit_1': bar['bb_middle'],
                    'take_profit_2': bar['close'] - (bar['atr'] * params['target_mult'] * 1.5),
                    'take_profit_3': bar['bb_lower']
                })
    
    return pd.DataFrame(signals)

# Test everything
all_results = []
tested = 0
profitable_count = 0

for pair in FOREX_PAIRS:
    print(f'\n Testing {pair.replace("=X", "")}...')
    
    try:
        handler = DataHandler()
        df = handler.fetch_data(pair, start_date.strftime('%Y-%m-%d'), 
                               end_date.strftime('%Y-%m-%d'), TIMEFRAME)
        
        for idx, config in enumerate(configs):
            tested += 1
            if tested % 100 == 0:
                print(f'  Progress: {tested}/{len(configs)*len(FOREX_PAIRS)} | Profitable so far: {profitable_count}')
            
            try:
                signals = generate_signals(df.copy(), config)
                
                if len(signals) >= 3:  # Minimum 3 trades
                    backtester = Backtester(initial_capital=INITIAL_CAPITAL)
                    metrics = backtester.run_backtest(df, signals)
                    
                    if metrics['total_return_pct'] > 0:
                        profitable_count += 1
                    
                    all_results.append({
                        'pair': pair.replace('=X', ''),
                        'strategy': config['name'],
                        'type': config['type'],
                        'trades': metrics['total_trades'],
                        'trades_per_month': metrics['total_trades'] / MONTHS_BACK,
                        'return': metrics['total_return_pct'],
                        'win_rate': metrics['win_rate_pct'],
                        'profit_factor': metrics['profit_factor'],
                        'sharpe': metrics['sharpe_ratio'],
                        'max_dd': metrics['max_drawdown_pct'],
                        'expectancy': metrics['expectancy'],
                        'config': config
                    })
            
            except Exception as e:
                continue
    
    except Exception as e:
        print(f'  Failed to load {pair}: {e}')

# Analyze
print()
print('='*80)
print('📊 FINAL RESULTS')
print('='*80)
print()

if all_results:
    results_df = pd.DataFrame(all_results)
    
    profitable = results_df[results_df['return'] > 0].sort_values('return', ascending=False)
    profitable_10 = profitable[profitable['trades_per_month'] >= 10]
    profitable_20 = profitable[profitable['trades_per_month'] >= 20]
    
    print(f'Total tested: {len(results_df)}')
    print(f'Profitable: {len(profitable)}')
    print(f'Profitable with 10+ trades/mo: {len(profitable_10)}')
    print(f'Profitable with 20+ trades/mo: {len(profitable_20)}')
    print()
    
    if len(profitable) > 0:
        print('='*80)
        print('🎉 FOUND PROFITABLE STRATEGIES!')
        print('='*80)
        print()
        
        print('Top 10 by return:')
        print(profitable[['pair', 'strategy', 'trades_per_month', 'return', 'win_rate', 'profit_factor']].head(10).to_string(index=False))
        print()
        
        if len(profitable_10) > 0:
            print('🏆 WITH 10+ TRADES/MONTH:')
            print(profitable_10[['pair', 'strategy', 'trades_per_month', 'return', 'win_rate']].head(5).to_string(index=False))
            print()
        
        if len(profitable_20) > 0:
            print('🏆 WITH 20+ TRADES/MONTH:')
            print(profitable_20[['pair', 'strategy', 'trades_per_month', 'return', 'win_rate']].head(5).to_string(index=False))
    
    results_df.to_csv('/workspace/forex_comprehensive_results.csv', index=False)
    print()
    print('✓ Saved to forex_comprehensive_results.csv')

print()
print('Done!')
