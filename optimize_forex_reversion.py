#!/usr/bin/env python3
"""
Forex Mean Reversion & Range Trading Optimizer
Testing strategies that work BETTER in choppy forex markets
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
print('💱 FOREX MEAN REVERSION OPTIMIZER')
print('='*80)
print()

FOREX_PAIRS = ['EURUSD=X', 'GBPUSD=X']
INITIAL_CAPITAL = 10000
TIMEFRAME = '1h'
MONTHS_BACK = 6

end_date = datetime.now()
start_date = end_date - timedelta(days=MONTHS_BACK * 30)

print(f'📊 Strategy: MEAN REVERSION (works in ranging markets)')
print(f'📅 Period: {MONTHS_BACK} months')
print(f'🎯 Goal: 10+ and 20+ profitable trades/month')
print()

# Mean reversion configs
configs = []

# RSI Mean Reversion
for oversold, overbought in [(20, 80), (25, 75), (30, 70), (35, 65)]:
    configs.append({
        'type': 'rsi_reversion',
        'name': f'RSI {oversold}/{overbought}',
        'rsi_oversold': oversold,
        'rsi_overbought': overbought,
        'stop_mult': 1.5,
        'target_mult': 2.0,
    })

# Bollinger Band Mean Reversion
for bb_std in [2.0, 2.5, 3.0]:
    configs.append({
        'type': 'bb_reversion',
        'name': f'BB {bb_std} Std',
        'bb_std': bb_std,
        'stop_mult': 1.5,
        'target_mult': 2.0,
    })

# Price action at VWAP
configs.append({
    'type': 'vwap_reversion',
    'name': 'VWAP Reversion',
    'deviation': 0.002,  # 0.2% deviation
    'stop_mult': 1.0,
    'target_mult': 1.5,
})

# Support/Resistance bounces
configs.append({
    'type': 'sr_bounce',
    'name': 'S/R Bounce',
    'lookback': 20,
    'stop_mult': 1.2,
    'target_mult': 2.0,
})

# Double Top/Bottom
configs.append({
    'type': 'double_pattern',
    'name': 'Double Top/Bottom',
    'tolerance': 0.003,  # 0.3%
    'stop_mult': 1.5,
    'target_mult': 2.5,
})

# RSI Divergence
configs.append({
    'type': 'rsi_divergence',
    'name': 'RSI Divergence',
    'lookback': 14,
    'stop_mult': 1.5,
    'target_mult': 2.5,
})

# Overbought/Oversold + Trend Filter
configs.append({
    'type': 'rsi_trend',
    'name': 'RSI + EMA Filter',
    'rsi_oversold': 30,
    'rsi_overbought': 70,
    'ema_period': 50,
    'stop_mult': 1.2,
    'target_mult': 2.0,
})

def generate_signals(df, params):
    """Generate mean reversion signals"""
    
    df['rsi'] = TechnicalIndicators.rsi(df, period=14)
    df['atr'] = TechnicalIndicators.atr(df)
    
    if params['type'] in ['bb_reversion', 'double_pattern']:
        bb_upper, bb_middle, bb_lower = TechnicalIndicators.bollinger_bands(
            df, period=20, std_dev=params.get('bb_std', 2.0)
        )
        df['bb_upper'] = bb_upper
        df['bb_middle'] = bb_middle
        df['bb_lower'] = bb_lower
    
    if params['type'] in ['vwap_reversion']:
        df['vwap'] = TechnicalIndicators.vwap(df)
    
    if params['type'] in ['rsi_trend']:
        df['ema'] = TechnicalIndicators.ema(df, params['ema_period'])
    
    signals = []
    
    for i in range(50, len(df)):
        bar = df.iloc[i]
        prev_bar = df.iloc[i-1]
        
        # RSI Mean Reversion
        if params['type'] == 'rsi_reversion':
            # Oversold -> Long
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
            
            # Overbought -> Short
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
        
        # Bollinger Band Reversion
        elif params['type'] == 'bb_reversion':
            # Price touches lower band -> Long
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
            
            # Price touches upper band -> Short
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
        
        # VWAP Reversion
        elif params['type'] == 'vwap_reversion':
            vwap_dist = abs(bar['close'] - bar['vwap']) / bar['vwap']
            
            # Price far below VWAP -> Long
            if bar['close'] < bar['vwap'] and vwap_dist > params['deviation']:
                signals.append({
                    'type': 'LONG',
                    'index': i,
                    'timestamp': df.index[i],
                    'entry_price': bar['close'],
                    'stop_loss': bar['close'] - (bar['atr'] * params['stop_mult']),
                    'take_profit_1': bar['vwap'],
                    'take_profit_2': bar['close'] + (bar['atr'] * params['target_mult'] * 1.5),
                    'take_profit_3': bar['close'] + (bar['atr'] * params['target_mult'] * 2.0)
                })
            
            # Price far above VWAP -> Short
            elif bar['close'] > bar['vwap'] and vwap_dist > params['deviation']:
                signals.append({
                    'type': 'SHORT',
                    'index': i,
                    'timestamp': df.index[i],
                    'entry_price': bar['close'],
                    'stop_loss': bar['close'] + (bar['atr'] * params['stop_mult']),
                    'take_profit_1': bar['vwap'],
                    'take_profit_2': bar['close'] - (bar['atr'] * params['target_mult'] * 1.5),
                    'take_profit_3': bar['close'] - (bar['atr'] * params['target_mult'] * 2.0)
                })
        
        # RSI + Trend Filter
        elif params['type'] == 'rsi_trend':
            # Oversold in uptrend -> Long
            if (bar['close'] > bar['ema'] and 
                prev_bar['rsi'] < params['rsi_oversold'] and 
                bar['rsi'] > params['rsi_oversold']):
                
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
            
            # Overbought in downtrend -> Short
            elif (bar['close'] < bar['ema'] and 
                  prev_bar['rsi'] > params['rsi_overbought'] and 
                  bar['rsi'] < params['rsi_overbought']):
                
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
                    
                    all_results.append({
                        'pair': pair.replace('=X', ''),
                        'strategy': config['name'],
                        'type': config['type'],
                        'trades': metrics['total_trades'],
                        'trades_per_month': trades_per_month,
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
        print(f'  Failed: {e}')

# Analyze
if all_results:
    results_df = pd.DataFrame(all_results)
    
    print()
    print('='*80)
    print('📊 MEAN REVERSION RESULTS')
    print('='*80)
    print()
    
    profitable_10 = results_df[
        (results_df['return'] > 0) & 
        (results_df['trades_per_month'] >= 10)
    ].sort_values('return', ascending=False)
    
    profitable_20 = results_df[
        (results_df['return'] > 0) & 
        (results_df['trades_per_month'] >= 20)
    ].sort_values('return', ascending=False)
    
    print(f'Tested: {len(results_df)} configurations')
    print(f'Profitable: {len(results_df[results_df["return"] > 0])}')
    print()
    
    if len(profitable_10) > 0:
        print('🏆 WINNERS - 10+ TRADES/MONTH!')
        for idx, row in profitable_10.head(3).iterrows():
            print(f"✅ {row['pair']} - {row['strategy']}")
            print(f"   Return: {row['return']:.2f}% | Trades: {row['trades']} ({row['trades_per_month']:.1f}/mo)")
            print(f"   Win Rate: {row['win_rate']:.1f}% | PF: {row['profit_factor']:.2f}")
            print()
    
    if len(profitable_20) > 0:
        print('🏆 WINNERS - 20+ TRADES/MONTH!')
        for idx, row in profitable_20.head(3).iterrows():
            print(f"✅ {row['pair']} - {row['strategy']}")
            print(f"   Return: {row['return']:.2f}% | Trades: {row['trades']} ({row['trades_per_month']:.1f}/mo)")
            print(f"   Win Rate: {row['win_rate']:.1f}% | PF: {row['profit_factor']:.2f}")
            print()
    
    if len(profitable_10) == 0 and len(profitable_20) == 0:
        print('Still searching...')
        print()
        print('Best performers:')
        best = results_df.nlargest(10, 'return')
        print(best[['pair', 'strategy', 'trades_per_month', 'return', 'win_rate']].to_string(index=False))
    
    results_df.to_csv('/workspace/forex_mean_reversion_results.csv', index=False)

print()
print('✓ Complete')
