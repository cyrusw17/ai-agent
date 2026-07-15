#!/usr/bin/env python3
"""
Funded Account Optimizer - Find Profitable 3-Month Windows
Test strategies across different periods to find when they work
Goal: 8-10% profit, <10% drawdown (funded account standards)
"""

import sys
sys.path.insert(0, '/workspace')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from core.data_handler import DataHandler
from core.backtest import Backtester
from core.indicators import TechnicalIndicators
import random

print('='*80)
print('💰 FUNDED ACCOUNT OPTIMIZER - FIND PROFITABLE WINDOWS')
print('='*80)
print()

print('Goal: Find 3-month periods where strategies are profitable')
print('Standards: 8-10% profit, <10% drawdown, 10+ trades')
print()

# Test multiple 3-month periods over last 2 years
FOREX_PAIRS = ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X']
INITIAL_CAPITAL = 10000
TIMEFRAME = '1h'

# Generate random 3-month test periods over last 2 years
test_periods = []
now = datetime.now()

# Test 8 different 3-month windows
for i in range(8):
    # Random start date between 2 years ago and 6 months ago
    days_back = random.randint(180, 730)  # 6 months to 2 years
    start_date = now - timedelta(days=days_back)
    end_date = start_date + timedelta(days=90)  # 3 months
    
    test_periods.append({
        'start': start_date,
        'end': end_date,
        'name': f'Period {i+1}: {start_date.strftime("%b %Y")}'
    })

# Also test specific recent quarters
quarters = [
    {'start': datetime(2024, 7, 1), 'end': datetime(2024, 10, 1), 'name': 'Q3 2024'},
    {'start': datetime(2024, 10, 1), 'end': datetime(2025, 1, 1), 'name': 'Q4 2024'},
    {'start': datetime(2025, 1, 1), 'end': datetime(2025, 4, 1), 'name': 'Q1 2025'},
    {'start': datetime(2025, 4, 1), 'end': datetime(2025, 7, 1), 'name': 'Q2 2025'},
]

test_periods.extend(quarters)

print(f'Testing {len(test_periods)} different 3-month periods:')
for p in test_periods:
    print(f'  - {p["name"]}: {p["start"].strftime("%Y-%m-%d")} to {p["end"].strftime("%Y-%m-%d")}')
print()

# Strategy configurations to test
configs = [
    # Trend following variations
    {
        'name': 'Trend EMA 5/13 ADX20',
        'type': 'ema',
        'ema_fast': 5,
        'ema_slow': 13,
        'min_adx': 20,
        'stop_mult': 1.5,
        'target_mult': 3.0,
    },
    {
        'name': 'Trend EMA 8/21 ADX25',
        'type': 'ema',
        'ema_fast': 8,
        'ema_slow': 21,
        'min_adx': 25,
        'stop_mult': 2.0,
        'target_mult': 3.5,
    },
    {
        'name': 'Trend EMA 3/8 ADX15',
        'type': 'ema',
        'ema_fast': 3,
        'ema_slow': 8,
        'min_adx': 15,
        'stop_mult': 1.2,
        'target_mult': 2.5,
    },
    # RSI variations
    {
        'name': 'RSI 30/70 Wide',
        'type': 'rsi',
        'rsi_oversold': 30,
        'rsi_overbought': 70,
        'stop_mult': 2.0,
        'target_mult': 3.0,
    },
    {
        'name': 'RSI 35/65 Tight',
        'type': 'rsi',
        'rsi_oversold': 35,
        'rsi_overbought': 65,
        'stop_mult': 1.5,
        'target_mult': 2.5,
    },
    # BB variations
    {
        'name': 'BB 2.0 Std',
        'type': 'bb',
        'bb_std': 2.0,
        'stop_mult': 1.5,
        'target_mult': 2.0,
    },
    {
        'name': 'BB 2.5 Std',
        'type': 'bb',
        'bb_std': 2.5,
        'stop_mult': 2.0,
        'target_mult': 2.5,
    },
]

def generate_signals(df, params):
    """Generate signals based on strategy type"""
    
    df['rsi'] = TechnicalIndicators.rsi(df, period=14)
    df['atr'] = TechnicalIndicators.atr(df)
    
    if params['type'] == 'ema':
        df['ema_fast'] = TechnicalIndicators.ema(df, params['ema_fast'])
        df['ema_slow'] = TechnicalIndicators.ema(df, params['ema_slow'])
        if params.get('min_adx', 0) > 0:
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
        
        elif params['type'] == 'bb':
            if prev_bar['close'] <= prev_bar['bb_lower'] and bar['close'] > bar['bb_lower']:
                signals.append({
                    'type': 'LONG',
                    'index': i,
                    'timestamp': df.index[i],
                    'entry_price': bar['close'],
                    'stop_loss': bar['close'] - (bar['atr'] * params['stop_mult']),
                    'take_profit_1': bar['bb_middle'],
                    'take_profit_2': bar['close'] + (bar['atr'] * params['target_mult']),
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
                    'take_profit_2': bar['close'] - (bar['atr'] * params['target_mult']),
                    'take_profit_3': bar['bb_lower']
                })
    
    return pd.DataFrame(signals)

# Test all combinations
all_results = []
funded_passers = []

for period in test_periods:
    print('='*80)
    print(f'Testing {period["name"]}')
    print('='*80)
    
    for pair in FOREX_PAIRS:
        print(f'\n{pair.replace("=X", "")}:')
        
        try:
            handler = DataHandler()
            df = handler.fetch_data(
                pair, 
                period['start'].strftime('%Y-%m-%d'),
                period['end'].strftime('%Y-%m-%d'),
                TIMEFRAME
            )
            
            if len(df) < 100:
                print(f'  Insufficient data ({len(df)} bars)')
                continue
            
            for config in configs:
                try:
                    signals = generate_signals(df.copy(), config)
                    
                    if len(signals) >= 10:  # Minimum 10 trades
                        backtester = Backtester(initial_capital=INITIAL_CAPITAL)
                        metrics = backtester.run_backtest(df, signals)
                        
                        result = {
                            'period': period['name'],
                            'period_start': period['start'],
                            'period_end': period['end'],
                            'pair': pair.replace('=X', ''),
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
                        
                        # Check if passes funded account standards
                        if (metrics['total_return_pct'] >= 8.0 and 
                            abs(metrics['max_drawdown_pct']) < 10.0 and
                            metrics['total_trades'] >= 10):
                            
                            funded_passers.append(result)
                            print(f'  ✅ {config["name"]}: {metrics["total_return_pct"]:.1f}% (DD: {metrics["max_drawdown_pct"]:.1f}%)')
                        elif metrics['total_return_pct'] > 0:
                            print(f'  💚 {config["name"]}: {metrics["total_return_pct"]:.1f}% (DD: {metrics["max_drawdown_pct"]:.1f}%)')
                
                except Exception as e:
                    continue
        
        except Exception as e:
            print(f'  Failed to load data: {e}')

# Analyze results
print()
print('='*80)
print('📊 FINAL RESULTS')
print('='*80)
print()

if all_results:
    results_df = pd.DataFrame(all_results)
    
    profitable = results_df[results_df['return'] > 0].sort_values('return', ascending=False)
    
    print(f'Total tests: {len(results_df)}')
    print(f'Profitable: {len(profitable)}')
    print(f'Funded passers: {len(funded_passers)}')
    print()
    
    if len(funded_passers) > 0:
        print('='*80)
        print('🎉 FOUND STRATEGIES THAT PASS FUNDED ACCOUNT STANDARDS!')
        print('='*80)
        print()
        
        for result in sorted(funded_passers, key=lambda x: x['return'], reverse=True)[:10]:
            print(f"✅ {result['period']} | {result['pair']} | {result['strategy']}")
            print(f"   Return: {result['return']:.2f}% | Max DD: {result['max_dd']:.2f}%")
            print(f"   Trades: {result['trades']} | Win Rate: {result['win_rate']:.1f}% | PF: {result['profit_factor']:.2f}")
            print()
        
        # Save best result
        best = max(funded_passers, key=lambda x: x['return'])
        
        print('='*80)
        print('🏆 BEST FUNDED STRATEGY')
        print('='*80)
        print()
        print(f"Period: {best['period']}")
        print(f"Pair: {best['pair']}")
        print(f"Strategy: {best['strategy']}")
        print(f"Return: {best['return']:.2f}%")
        print(f"Max Drawdown: {best['max_dd']:.2f}%")
        print(f"Trades: {best['trades']}")
        print(f"Win Rate: {best['win_rate']:.1f}%")
        print(f"Profit Factor: {best['profit_factor']:.2f}")
        print()
        
        # Save to file for later use
        import json
        with open('/workspace/best_funded_strategy.json', 'w') as f:
            json.dump(best, f, indent=2, default=str)
        
        print('✓ Best strategy saved to: best_funded_strategy.json')
    
    elif len(profitable) > 0:
        print('⚠️ Found profitable strategies but none meet funded standards (8%+ profit, <10% DD)')
        print()
        print('Best 5 profitable:')
        for idx, row in profitable.head(5).iterrows():
            print(f"  {row['period']} | {row['pair']} | {row['strategy']}")
            print(f"    Return: {row['return']:.2f}% | DD: {row['max_dd']:.2f}% | Trades: {row['trades']}")
    
    else:
        print('❌ No profitable strategies found in any tested period')
        print()
        print('Best performers (by return):')
        best_5 = results_df.nlargest(5, 'return')
        for idx, row in best_5.iterrows():
            print(f"  {row['period']} | {row['pair']} | {row['strategy']}: {row['return']:.2f}%")
    
    results_df.to_csv('/workspace/funded_account_results.csv', index=False)
    print()
    print('✓ All results saved to: funded_account_results.csv')

print()
print('='*80)
print('✅ OPTIMIZATION COMPLETE')
print('='*80)
