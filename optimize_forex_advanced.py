#!/usr/bin/env python3
"""
Advanced Forex Optimizer - Round 2
Adding session filters, better stops, and more configurations
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
print('💱 ADVANCED FOREX OPTIMIZER - ROUND 2')
print('='*80)
print()

# Focus on most liquid pair for faster testing
FOREX_PAIRS = ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X']

INITIAL_CAPITAL = 10000
TIMEFRAME = '1h'
MONTHS_BACK = 6

end_date = datetime.now()
start_date = end_date - timedelta(days=MONTHS_BACK * 30)

print(f'📊 Pairs: {", ".join([p.replace("=X", "") for p in FOREX_PAIRS])}')
print(f'📅 Period: {MONTHS_BACK} months')
print(f'🎯 Goal: Find 10+ and 20+ trades/month strategies that are PROFITABLE')
print()

# More sophisticated configurations
configs = []

# Config 1-5: Different session filters
for session in ['all', 'london_ny', 'london', 'ny', 'asian']:
    configs.append({
        'name': f'Fast Trend {session.title()}',
        'ema_fast': 5,
        'ema_slow': 13,
        'min_adx': 15,
        'stop_mult': 1.2,
        'target_mult': 2.5,
        'session_filter': session,
    })

# Config 6-10: Tighter stops with higher targets
for stop, target in [(0.8, 2.0), (1.0, 2.5), (1.2, 3.0), (1.5, 3.5), (1.8, 4.0)]:
    configs.append({
        'name': f'EMA S{stop}T{target}',
        'ema_fast': 5,
        'ema_slow': 13,
        'min_adx': 18,
        'stop_mult': stop,
        'target_mult': target,
        'session_filter': 'london_ny',
    })

# Config 11-15: Different EMA combinations
for fast, slow in [(3, 8), (5, 13), (8, 21), (9, 21), (13, 34)]:
    configs.append({
        'name': f'EMA {fast}/{slow}',
        'ema_fast': fast,
        'ema_slow': slow,
        'min_adx': 15,
        'stop_mult': 1.2,
        'target_mult': 2.5,
        'session_filter': 'london_ny',
    })

# Config 16-20: Partial scaling strategies
for i in range(5):
    configs.append({
        'name': f'Scale {i+1}',
        'ema_fast': 5 + i,
        'ema_slow': 13 + i*2,
        'min_adx': 15 + i*2,
        'stop_mult': 1.0 + i*0.2,
        'target_mult': 2.0 + i*0.5,
        'session_filter': 'london_ny',
        'scale_out': True,
    })

def get_session_filter(timestamp):
    """Determine trading session"""
    hour = timestamp.hour
    
    # London: 8:00-16:00 UTC
    london = 8 <= hour < 16
    
    # NY: 13:00-21:00 UTC
    ny = 13 <= hour < 21
    
    # Asian: 0:00-8:00 UTC
    asian = 0 <= hour < 8
    
    return {
        'london': london,
        'ny': ny,
        'asian': asian,
        'london_ny': london or ny,
        'all': True
    }

def generate_signals(df, params):
    """Generate signals with session filtering"""
    
    # Calculate indicators
    df['rsi'] = TechnicalIndicators.rsi(df, period=14)
    df['atr'] = TechnicalIndicators.atr(df)
    df['ema_fast'] = TechnicalIndicators.ema(df, params['ema_fast'])
    df['ema_slow'] = TechnicalIndicators.ema(df, params['ema_slow'])
    
    if params.get('min_adx', 0) > 0:
        adx, _, _ = TechnicalIndicators.adx(df)
        df['adx'] = adx
    
    signals = []
    
    for i in range(50, len(df)):
        bar = df.iloc[i]
        prev_bar = df.iloc[i-1]
        
        # Session filter
        session_ok = get_session_filter(df.index[i])
        if not session_ok.get(params.get('session_filter', 'all'), False):
            continue
        
        # ADX filter
        if params.get('min_adx', 0) > 0:
            if 'adx' in df.columns and bar['adx'] < params['min_adx']:
                continue
        
        # EMA crossover
        if (bar['ema_fast'] > bar['ema_slow'] and 
            prev_bar['ema_fast'] <= prev_bar['ema_slow']):
            
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
        
        elif (bar['ema_fast'] < bar['ema_slow'] and 
              prev_bar['ema_fast'] >= prev_bar['ema_slow']):
            
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

# Test configurations
all_results = []

for pair in FOREX_PAIRS:
    print(f'Testing {pair.replace("=X", "")}...')
    
    try:
        handler = DataHandler()
        df = handler.fetch_data(pair, start_date.strftime('%Y-%m-%d'), 
                               end_date.strftime('%Y-%m-%d'), TIMEFRAME)
        
        for config in configs:
            try:
                signals = generate_signals(df.copy(), config)
                
                if len(signals) > 0:
                    backtester = Backtester(initial_capital=INITIAL_CAPITAL)
                    metrics = backtester.run_backtest(df, signals)
                    
                    trades_per_month = metrics['total_trades'] / MONTHS_BACK
                    
                    result = {
                        'pair': pair.replace('=X', ''),
                        'strategy': config['name'],
                        'trades': metrics['total_trades'],
                        'trades_per_month': trades_per_month,
                        'return': metrics['total_return_pct'],
                        'win_rate': metrics['win_rate_pct'],
                        'profit_factor': metrics['profit_factor'],
                        'sharpe': metrics['sharpe_ratio'],
                        'max_dd': metrics['max_drawdown_pct'],
                        'expectancy': metrics['expectancy'],
                        'config': config
                    }
                    
                    all_results.append(result)
            
            except Exception as e:
                continue
    
    except Exception as e:
        print(f'  Failed: {e}')
        continue

# Analyze results
if all_results:
    results_df = pd.DataFrame(all_results)
    
    print()
    print('='*80)
    print('🔍 SEARCHING FOR WINNERS...')
    print('='*80)
    print()
    
    # Find profitable with 10+ trades/month
    profitable_10 = results_df[
        (results_df['return'] > 0) & 
        (results_df['trades_per_month'] >= 10)
    ].sort_values('return', ascending=False)
    
    # Find profitable with 20+ trades/month
    profitable_20 = results_df[
        (results_df['return'] > 0) & 
        (results_df['trades_per_month'] >= 20)
    ].sort_values('return', ascending=False)
    
    print(f'✓ Tested {len(results_df)} configurations')
    print(f'✓ Profitable: {len(results_df[results_df["return"] > 0])}')
    print(f'✓ With 10+ trades/mo: {len(results_df[results_df["trades_per_month"] >= 10])}')
    print(f'✓ With 20+ trades/mo: {len(results_df[results_df["trades_per_month"] >= 20])}')
    print()
    
    if len(profitable_10) > 0:
        print('🏆 FOUND 10+ TRADES/MONTH WINNERS!')
        print()
        for idx, row in profitable_10.head(3).iterrows():
            print(f"✅ {row['pair']} - {row['strategy']}")
            print(f"   Trades: {row['trades']} ({row['trades_per_month']:.1f}/month)")
            print(f"   Return: {row['return']:.2f}%")
            print(f"   Win Rate: {row['win_rate']:.1f}%")
            print(f"   Profit Factor: {row['profit_factor']:.2f}")
            print()
    
    if len(profitable_20) > 0:
        print('🏆 FOUND 20+ TRADES/MONTH WINNERS!')
        print()
        for idx, row in profitable_20.head(3).iterrows():
            print(f"✅ {row['pair']} - {row['strategy']}")
            print(f"   Trades: {row['trades']} ({row['trades_per_month']:.1f}/month)")
            print(f"   Return: {row['return']:.2f}%")
            print(f"   Win Rate: {row['win_rate']:.1f}%")
            print(f"   Profit Factor: {row['profit_factor']:.2f}")
            print()
    
    if len(profitable_10) == 0 and len(profitable_20) == 0:
        print('⚠️ No profitable high-frequency strategies found')
        print()
        print('Best performers (by return):')
        best = results_df.nlargest(5, 'return')
        for idx, row in best.iterrows():
            print(f"   {row['pair']} - {row['strategy']}: {row['return']:.2f}% "
                  f"({row['trades_per_month']:.1f} trades/mo, {row['win_rate']:.0f}% win)")
        print()
        
        print('Best by trade frequency (10+ trades/mo):')
        freq_10 = results_df[results_df['trades_per_month'] >= 10].nlargest(5, 'return')
        if len(freq_10) > 0:
            for idx, row in freq_10.iterrows():
                print(f"   {row['pair']} - {row['strategy']}: {row['return']:.2f}% "
                      f"({row['trades_per_month']:.1f} trades/mo, {row['win_rate']:.0f}% win)")
        print()
        
        print('Best by trade frequency (20+ trades/mo):')
        freq_20 = results_df[results_df['trades_per_month'] >= 20].nlargest(5, 'return')
        if len(freq_20) > 0:
            for idx, row in freq_20.iterrows():
                print(f"   {row['pair']} - {row['strategy']}: {row['return']:.2f}% "
                      f"({row['trades_per_month']:.1f} trades/mo, {row['win_rate']:.0f}% win)")
    
    results_df.to_csv('/workspace/forex_advanced_results.csv', index=False)
    print()
    print('✓ Results saved to: forex_advanced_results.csv')

print()
print('='*80)
print('Continuing to Round 3 with win rate filters...')
print('='*80)
