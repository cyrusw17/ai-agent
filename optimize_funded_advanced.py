#!/usr/bin/env python3
"""
Advanced Funded Optimizer - Try Everything
- Different timeframes (4H, Daily)
- More aggressive parameters
- More strategy types
- Focus on trending periods
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
print('💰 ADVANCED FUNDED OPTIMIZER - TRY EVERYTHING')
print('='*80)
print()

FOREX_PAIRS = ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X']
INITIAL_CAPITAL = 10000

# Test different timeframes
TIMEFRAMES = ['4h', '1d']  # 4-hour and daily

# Test periods (3 months each, more recent = better data quality)
test_periods = [
    {'start': datetime(2025, 10, 1), 'end': datetime(2026, 1, 1), 'name': 'Q4 2025'},
    {'start': datetime(2026, 1, 1), 'end': datetime(2026, 4, 1), 'name': 'Q1 2026'},
    {'start': datetime(2026, 4, 1), 'end': datetime(2026, 7, 1), 'name': 'Q2 2026'},
    {'start': datetime(2025, 7, 1), 'end': datetime(2025, 10, 1), 'name': 'Q3 2025'},
]

# Expanded configuration space
configs = []

# EMA Trend Following - Wide range of parameters
for fast in [3, 5, 7, 9, 12]:
    for slow in [13, 21, 34]:
        if slow > fast * 1.5:
            for adx_min in [0, 15, 20, 25]:
                for stop in [0.8, 1.0, 1.5, 2.0]:
                    for target in [2.0, 2.5, 3.0, 4.0]:
                        if target >= stop * 1.5:
                            configs.append({
                                'name': f'EMA{fast}/{slow}_ADX{adx_min}_S{stop}_T{target}',
                                'type': 'ema',
                                'ema_fast': fast,
                                'ema_slow': slow,
                                'min_adx': adx_min,
                                'stop_mult': stop,
                                'target_mult': target,
                            })

# RSI - Wide range
for os in [20, 25, 30, 35, 40]:
    for ob in [60, 65, 70, 75, 80]:
        if ob > os + 20:
            for stop in [1.0, 1.5, 2.0, 2.5]:
                for target in [1.5, 2.0, 2.5, 3.0]:
                    configs.append({
                        'name': f'RSI{os}/{ob}_S{stop}_T{target}',
                        'type': 'rsi',
                        'rsi_oversold': os,
                        'rsi_overbought': ob,
                        'stop_mult': stop,
                        'target_mult': target,
                    })

print(f'Total configurations to test: {len(configs)}')
print(f'Timeframes: {TIMEFRAMES}')
print(f'Test periods: {len(test_periods)}')
print(f'Forex pairs: {len(FOREX_PAIRS)}')
print(f'Total combinations: {len(configs) * len(TIMEFRAMES) * len(test_periods) * len(FOREX_PAIRS)}')
print()
print('This will take a while... Testing the most promising combinations first.')
print()

def generate_signals(df, params):
    """Generate signals"""
    
    df['rsi'] = TechnicalIndicators.rsi(df, period=14)
    df['atr'] = TechnicalIndicators.atr(df)
    
    if params['type'] == 'ema':
        df['ema_fast'] = TechnicalIndicators.ema(df, params['ema_fast'])
        df['ema_slow'] = TechnicalIndicators.ema(df, params['ema_slow'])
        if params.get('min_adx', 0) > 0:
            adx, _, _ = TechnicalIndicators.adx(df)
            df['adx'] = adx
    
    signals = []
    
    for i in range(50, len(df)):
        bar = df.iloc[i]
        prev_bar = df.iloc[i-1]
        
        if params['type'] == 'ema':
            if params.get('min_adx', 0) > 0:
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
    
    return pd.DataFrame(signals)

# Sample configs (test most promising first)
priority_configs = [
    c for c in configs 
    if c['type'] == 'ema' and c.get('min_adx', 0) >= 20 and c['target_mult'] >= 3.0
][:50]  # Top 50 promising EMA configs

if len(priority_configs) < 50:
    priority_configs.extend([c for c in configs if c not in priority_configs][:50-len(priority_configs)])

print(f'Testing top {len(priority_configs)} configurations first...')
print()

all_results = []
funded_passers = []
tested = 0

for timeframe in TIMEFRAMES:
    print(f'\n{"="*80}')
    print(f'TIMEFRAME: {timeframe.upper()}')
    print(f'{"="*80}\n')
    
    for period in test_periods:
        print(f'\nPeriod: {period["name"]} ({period["start"].strftime("%b %d")} - {period["end"].strftime("%b %d %Y")})')
        
        for pair in FOREX_PAIRS:
            try:
                handler = DataHandler()
                df = handler.fetch_data(
                    pair,
                    period['start'].strftime('%Y-%m-%d'),
                    period['end'].strftime('%Y-%m-%d'),
                    timeframe
                )
                
                if len(df) < 50:
                    continue
                
                pair_name = pair.replace('=X', '')
                profitable_this_pair = 0
                
                for config in priority_configs:
                    tested += 1
                    
                    if tested % 100 == 0:
                        print(f'    Progress: {tested} tests | Profitable: {len([r for r in all_results if r["return"] > 0])} | Funded: {len(funded_passers)}')
                    
                    try:
                        signals = generate_signals(df.copy(), config)
                        
                        if len(signals) >= 5:
                            backtester = Backtester(initial_capital=INITIAL_CAPITAL)
                            metrics = backtester.run_backtest(df, signals)
                            
                            result = {
                                'timeframe': timeframe,
                                'period': period['name'],
                                'pair': pair_name,
                                'strategy': config['name'],
                                'trades': metrics['total_trades'],
                                'return': metrics['total_return_pct'],
                                'max_dd': metrics['max_drawdown_pct'],
                                'win_rate': metrics['win_rate_pct'],
                                'profit_factor': metrics['profit_factor'],
                                'sharpe': metrics['sharpe_ratio'],
                                'config': config
                            }
                            
                            all_results.append(result)
                            
                            # Check funded standards
                            if (metrics['total_return_pct'] >= 8.0 and 
                                abs(metrics['max_drawdown_pct']) < 10.0 and
                                metrics['total_trades'] >= 5):
                                
                                funded_passers.append(result)
                                print(f'    ✅ {pair_name} | {config["name"][:30]:30s} | {metrics["total_return_pct"]:6.2f}% (DD: {metrics["max_drawdown_pct"]:.1f}%)')
                                profitable_this_pair += 1
                            
                            elif metrics['total_return_pct'] >= 5.0:
                                if profitable_this_pair == 0:  # Only print first few profitable
                                    print(f'    💚 {pair_name} | {config["name"][:30]:30s} | {metrics["total_return_pct"]:6.2f}%')
                                profitable_this_pair += 1
                    
                    except Exception as e:
                        continue
            
            except Exception as e:
                continue

# Results
print()
print('='*80)
print('📊 OPTIMIZATION RESULTS')
print('='*80)
print()

if all_results:
    results_df = pd.DataFrame(all_results)
    profitable = results_df[results_df['return'] > 0]
    
    print(f'Total tests: {len(results_df)}')
    print(f'Profitable: {len(profitable)} ({len(profitable)/len(results_df)*100:.1f}%)')
    print(f'Funded passers: {len(funded_passers)}')
    print()
    
    if len(funded_passers) > 0:
        print('='*80)
        print('🎉 FOUND FUNDED ACCOUNT WINNERS!')
        print('='*80)
        print()
        
        for result in sorted(funded_passers, key=lambda x: x['return'], reverse=True)[:5]:
            print(f"✅ {result['timeframe'].upper()} | {result['period']} | {result['pair']}")
            print(f"   Strategy: {result['strategy']}")
            print(f"   Return: {result['return']:.2f}% | Max DD: {result['max_dd']:.2f}%")
            print(f"   Trades: {result['trades']} | Win Rate: {result['win_rate']:.1f}% | PF: {result['profit_factor']:.2f}")
            print()
        
        # Save best
        best = max(funded_passers, key=lambda x: x['return'])
        
        import json
        with open('/workspace/best_funded_strategy.json', 'w') as f:
            json.dump(best, f, indent=2, default=str)
        
        print('✓ Best strategy saved to: best_funded_strategy.json')
    
    elif len(profitable) > 0:
        print('💚 Found profitable but need more optimization for funded standards')
        print()
        print('Top 10 profitable:')
        for idx, row in profitable.nlargest(10, 'return').iterrows():
            print(f"  {row['timeframe'].upper()} | {row['period']} | {row['pair']} | {row['strategy'][:40]}")
            print(f"    Return: {row['return']:.2f}% | DD: {row['max_dd']:.2f}% | Trades: {row['trades']}")
    
    else:
        print('⚠️ No profitable strategies found')
        print()
        print('Best 5 (least loss):')
        for idx, row in results_df.nlargest(5, 'return').iterrows():
            print(f"  {row['timeframe'].upper()} | {row['period']} | {row['pair']}: {row['return']:.2f}%")
    
    results_df.to_csv('/workspace/advanced_funded_results.csv', index=False)
    print()
    print('✓ Results saved to: advanced_funded_results.csv')

print()
print('✅ Complete')
