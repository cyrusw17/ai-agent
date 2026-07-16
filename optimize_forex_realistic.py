#!/usr/bin/env python3
"""
Realistic Forex Strategies - Optimized for Trade Frequency
Based on what actually works in forex markets
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
print('💱 REALISTIC FOREX STRATEGY BUILDER')
print('='*80)
print()

FOREX_PAIRS = ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X']
INITIAL_CAPITAL = 10000
TIMEFRAME = '1h'
MONTHS_BACK = 6

end_date = datetime.now()
start_date = end_date - timedelta(days=MONTHS_BACK * 30)

print('Approach: Use REALISTIC forex parameters')
print(' - Wider stops (avoid getting stopped out by noise)')
print(' - Larger targets (capture actual moves)')
print(' - Selective entries (wait for confirmation)')
print()

# Configurations focused on realism
configs = [
    # 10+ trades/month target (moderate frequency)
    {
        'name': 'Forex Moderate Frequency',
        'desc': 'Target: 10+ trades/month',
        'ema_fast': 5,
        'ema_slow': 13,
        'min_adx': 20,
        'stop_mult': 2.0,    # Wider stops for forex volatility
        'target_mult': 4.0,  # Larger targets (1:2 R:R)
        'use_session': True,
    },
    {
        'name': 'RSI Mean Reversion 10+',
        'desc': 'Target: 10+ trades/month',
        'type': 'rsi',
        'rsi_oversold': 30,
        'rsi_overbought': 70,
        'stop_mult': 2.0,
        'target_mult': 3.5,
        'use_session': True,
    },
    {
        'name': 'BB Reversion 10+',
        'desc': 'Target: 10+ trades/month',
        'type': 'bb',
        'bb_std': 2.5,
        'stop_mult': 2.0,
        'target_mult': 3.0,
        'use_session': True,
    },
    
    # 20+ trades/month target (high frequency)
    {
        'name': 'Forex High Frequency',
        'desc': 'Target: 20+ trades/month',
        'ema_fast': 3,
        'ema_slow': 8,
        'min_adx': 12,
        'stop_mult': 1.5,
        'target_mult': 3.0,
        'use_session': True,
    },
    {
        'name': 'RSI Scalper 20+',
        'desc': 'Target: 20+ trades/month',
        'type': 'rsi',
        'rsi_oversold': 35,
        'rsi_overbought': 65,
        'stop_mult': 1.5,
        'target_mult': 2.5,
        'use_session': True,
    },
    {
        'name': 'BB Fast 20+',
        'desc': 'Target: 20+ trades/month',
        'type': 'bb',
        'bb_std': 2.0,
        'stop_mult': 1.5,
        'target_mult': 2.0,
        'use_session': True,
    },
]

def is_trading_session(timestamp):
    """Check if during active forex sessions (London or NY)"""
    hour = timestamp.hour
    # London: 8-16 UTC, NY: 13-21 UTC
    return (8 <= hour < 16) or (13 <= hour < 21)

def generate_signals(df, params):
    """Generate signals with realistic forex parameters"""
    
    df['rsi'] = TechnicalIndicators.rsi(df, period=14)
    df['atr'] = TechnicalIndicators.atr(df)
    
    if params.get('type') != 'rsi' and params.get('type') != 'bb':
        df['ema_fast'] = TechnicalIndicators.ema(df, params['ema_fast'])
        df['ema_slow'] = TechnicalIndicators.ema(df, params['ema_slow'])
        if params.get('min_adx', 0) > 0:
            adx, _, _ = TechnicalIndicators.adx(df)
            df['adx'] = adx
    
    if params.get('type') == 'bb':
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
        
        # Session filter
        if params.get('use_session', False):
            if not is_trading_session(df.index[i]):
                continue
        
        # RSI Strategy
        if params.get('type') == 'rsi':
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
        
        # BB Strategy
        elif params.get('type') == 'bb':
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
        
        # EMA Strategy
        else:
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
    
    return pd.DataFrame(signals)

# Test all configurations
all_results = []

for pair in FOREX_PAIRS:
    print(f'\nTesting {pair.replace("=X", "")}...')
    
    try:
        handler = DataHandler()
        df = handler.fetch_data(pair, start_date.strftime('%Y-%m-%d'), 
                               end_date.strftime('%Y-%m-%d'), TIMEFRAME)
        print(f'  Loaded {len(df)} bars')
        
        for config in configs:
            try:
                signals = generate_signals(df.copy(), config)
                
                if len(signals) >= 3:
                    backtester = Backtester(initial_capital=INITIAL_CAPITAL)
                    metrics = backtester.run_backtest(df, signals)
                    
                    trades_per_month = metrics['total_trades'] / MONTHS_BACK
                    
                    result = {
                        'pair': pair.replace('=X', ''),
                        'strategy': config['name'],
                        'description': config['desc'],
                        'trades': metrics['total_trades'],
                        'trades_per_month': trades_per_month,
                        'return': metrics['total_return_pct'],
                        'win_rate': metrics['win_rate_pct'],
                        'profit_factor': metrics['profit_factor'],
                        'sharpe': metrics['sharpe_ratio'],
                        'max_dd': metrics['max_drawdown_pct'],
                        'expectancy': metrics['expectancy'],
                        'final_capital': metrics['final_equity'],
                        'config': config
                    }
                    
                    all_results.append(result)
                    
                    print(f'  {config["name"]}: {trades_per_month:.1f} trades/mo, '
                          f'Return: {metrics["total_return_pct"]:.2f}%, '
                          f'Win: {metrics["win_rate_pct"]:.0f}%')
            
            except Exception as e:
                print(f'  {config["name"]}: Error - {e}')
    
    except Exception as e:
        print(f'  Failed to load {pair}: {e}')

# Analyze results
print()
print('='*80)
print('📊 FOREX STRATEGY RESULTS')
print('='*80)
print()

if all_results:
    results_df = pd.DataFrame(all_results)
    
    # Sort by profitability
    results_df = results_df.sort_values('return', ascending=False)
    
    print('ALL STRATEGIES:')
    print(results_df[['pair', 'strategy', 'trades_per_month', 'return', 'win_rate', 'profit_factor']].to_string(index=False))
    print()
    
    # Find best for each frequency target
    freq_10 = results_df[results_df['description'].str.contains('10\\+')]
    freq_20 = results_df[results_df['description'].str.contains('20\\+')]
    
    profitable_10 = freq_10[freq_10['return'] > 0].sort_values('return', ascending=False)
    profitable_20 = freq_20[freq_20['return'] > 0].sort_values('return', ascending=False)
    
    print('='*80)
    print('🎯 10+ TRADES/MONTH STRATEGIES')
    print('='*80)
    print()
    
    if len(profitable_10) > 0:
        print('✅ PROFITABLE STRATEGIES FOUND:')
        for idx, row in profitable_10.head(3).iterrows():
            print(f"\n{row['pair']} - {row['strategy']}")
            print(f"  Trades: {row['trades']} ({row['trades_per_month']:.1f}/month)")
            print(f"  Return: +{row['return']:.2f}%")
            print(f"  Final Capital: ${row['final_capital']:,.2f}")
            print(f"  Win Rate: {row['win_rate']:.1f}%")
            print(f"  Profit Factor: {row['profit_factor']:.2f}")
            print(f"  Max Drawdown: {row['max_dd']:.2f}%")
    else:
        print('⚠️ No profitable strategies with target frequency')
        print('Best performers (may not be profitable):')
        for idx, row in freq_10.head(3).iterrows():
            print(f"  {row['pair']} - {row['strategy']}: "
                  f"{row['return']:.2f}% ({row['trades_per_month']:.1f} trades/mo)")
    
    print()
    print('='*80)
    print('🎯 20+ TRADES/MONTH STRATEGIES')
    print('='*80)
    print()
    
    if len(profitable_20) > 0:
        print('✅ PROFITABLE STRATEGIES FOUND:')
        for idx, row in profitable_20.head(3).iterrows():
            print(f"\n{row['pair']} - {row['strategy']}")
            print(f"  Trades: {row['trades']} ({row['trades_per_month']:.1f}/month)")
            print(f"  Return: +{row['return']:.2f}%")
            print(f"  Final Capital: ${row['final_capital']:,.2f}")
            print(f"  Win Rate: {row['win_rate']:.1f}%")
            print(f"  Profit Factor: {row['profit_factor']:.2f}")
            print(f"  Max Drawdown: {row['max_dd']:.2f}%")
    else:
        print('⚠️ No profitable strategies with target frequency')
        print('Best performers (may not be profitable):')
        for idx, row in freq_20.head(3).iterrows():
            print(f"  {row['pair']} - {row['strategy']}: "
                  f"{row['return']:.2f}% ({row['trades_per_month']:.1f} trades/mo)")
    
    # Save results
    results_df.to_csv('/workspace/forex_realistic_results.csv', index=False)
    print()
    print('✓ Results saved to: forex_realistic_results.csv')

print()
print('='*80)
print('✅ COMPLETE')
print('='*80)
