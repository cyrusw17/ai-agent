#!/usr/bin/env python3
"""
Adaptive Strategy Optimizer - Iterate Until Profitable
Tests multiple configurations and parameters to find winning setups
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
print('🤖 ADAPTIVE STRATEGY OPTIMIZER - FINDING WINNING CONFIGURATION')
print('='*80)
print()

# Initialize
handler = DataHandler()
end_date = datetime.now()
start_date = end_date - timedelta(days=365)  # Use 1 year for better optimization

print(f'📊 Symbol: SPY (Robinhood friendly)')
print(f'📅 Period: {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")} (1 year)')
print(f'⏰ Timeframe: 1 Hour')
print(f'💰 Starting Capital: $10,000 (Robinhood typical)')
print(f'🎯 Goal: Find profitable configuration')
print()

# Fetch data
print('Fetching market data...')
df = handler.fetch_data('SPY', start_date.strftime('%Y-%m-%d'), 
                       end_date.strftime('%Y-%m-%d'), '1h')
print(f'✓ Loaded {len(df)} bars')
print()

# Calculate all indicators
print('Calculating indicators...')
df['rsi'] = TechnicalIndicators.rsi(df, period=14)
df['rsi_fast'] = TechnicalIndicators.rsi(df, period=9)

macd, macd_signal, macd_hist = TechnicalIndicators.macd(df)
df['macd'] = macd
df['macd_signal'] = macd_signal
df['macd_histogram'] = macd_hist

df['ema_9'] = TechnicalIndicators.ema(df, 9)
df['ema_21'] = TechnicalIndicators.ema(df, 21)
df['ema_50'] = TechnicalIndicators.ema(df, 50)
df['ema_200'] = TechnicalIndicators.ema(df, 200)

df['atr'] = TechnicalIndicators.atr(df)
df['vwap'] = TechnicalIndicators.vwap(df)

adx, plus_di, minus_di = TechnicalIndicators.adx(df)
df['adx'] = adx

df['rvol'] = TechnicalIndicators.relative_volume(df)

bb_upper, bb_middle, bb_lower = TechnicalIndicators.bollinger_bands(df)
df['bb_upper'] = bb_upper
df['bb_middle'] = bb_middle
df['bb_lower'] = bb_lower

print('✓ All indicators calculated')
print()

# Configuration space to test
configs = []

# Config 1: Trend + ADX Filter (Conservative)
configs.append({
    'name': 'Trend + ADX Filter',
    'description': 'EMA crossover with strong trend requirement',
    'params': {
        'min_adx': 25,
        'ema_fast': 9,
        'ema_slow': 21,
        'stop_mult': 1.5,
        'target_mult': 3.0,
        'use_rvol': True,
        'min_rvol': 1.0
    }
})

# Config 2: Trend + ADX + RVOL (Aggressive)
configs.append({
    'name': 'Trend + ADX + Volume',
    'description': 'Strong trends with high volume',
    'params': {
        'min_adx': 30,
        'ema_fast': 9,
        'ema_slow': 21,
        'stop_mult': 1.2,
        'target_mult': 2.5,
        'use_rvol': True,
        'min_rvol': 1.5
    }
})

# Config 3: Fast EMA with loose ADX
configs.append({
    'name': 'Fast Trend Following',
    'description': 'Quick entries with momentum',
    'params': {
        'min_adx': 20,
        'ema_fast': 5,
        'ema_slow': 13,
        'stop_mult': 1.5,
        'target_mult': 2.0,
        'use_rvol': True,
        'min_rvol': 0.8
    }
})

# Config 4: Slow EMA with tight stops
configs.append({
    'name': 'Slow Trend + Tight Stops',
    'description': 'Patient entries with quick exits',
    'params': {
        'min_adx': 25,
        'ema_fast': 13,
        'ema_slow': 34,
        'stop_mult': 1.0,
        'target_mult': 3.0,
        'use_rvol': True,
        'min_rvol': 1.2
    }
})

# Config 5: VWAP + Trend
configs.append({
    'name': 'VWAP Pullback',
    'description': 'Pullbacks to VWAP in strong trends',
    'params': {
        'min_adx': 25,
        'ema_fast': 9,
        'ema_slow': 21,
        'stop_mult': 1.5,
        'target_mult': 2.5,
        'use_vwap': True,
        'use_rvol': True,
        'min_rvol': 1.0
    }
})

# Config 6: RSI + Trend Filter
configs.append({
    'name': 'RSI Momentum',
    'description': 'RSI confirmation with trend',
    'params': {
        'min_adx': 20,
        'ema_fast': 9,
        'ema_slow': 21,
        'stop_mult': 1.5,
        'target_mult': 2.5,
        'use_rsi': True,
        'rsi_bull_min': 50,
        'rsi_bear_max': 50,
        'use_rvol': True,
        'min_rvol': 1.0
    }
})

# Config 7: MACD + ADX
configs.append({
    'name': 'MACD Trend',
    'description': 'MACD crossover in strong trends',
    'params': {
        'min_adx': 28,
        'use_macd': True,
        'stop_mult': 1.5,
        'target_mult': 3.0,
        'use_rvol': True,
        'min_rvol': 1.3
    }
})

# Test all configurations
print('='*80)
print('🧪 TESTING CONFIGURATIONS')
print('='*80)
print()

results = []

for idx, config in enumerate(configs):
    print(f'[{idx+1}/{len(configs)}] Testing: {config["name"]}')
    print(f'    Description: {config["description"]}')
    
    params = config['params']
    signals = []
    
    # Generate signals based on configuration
    for i in range(200, len(df)):
        bar = df.iloc[i]
        
        # Skip if ADX too low
        if bar['adx'] < params.get('min_adx', 20):
            continue
        
        # Skip if volume too low
        if params.get('use_rvol', False):
            if bar['rvol'] < params.get('min_rvol', 1.0):
                continue
        
        # MACD-based signals
        if params.get('use_macd', False):
            # Long: MACD crosses above signal
            if (bar['macd'] > bar['macd_signal'] and
                df['macd'].iloc[i-1] <= df['macd_signal'].iloc[i-1]):
                
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
            
            # Short: MACD crosses below signal
            elif (bar['macd'] < bar['macd_signal'] and
                  df['macd'].iloc[i-1] >= df['macd_signal'].iloc[i-1]):
                
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
        
        # EMA-based signals
        elif 'ema_fast' in params:
            ema_fast = TechnicalIndicators.ema(df, params['ema_fast']).iloc[i]
            ema_fast_prev = TechnicalIndicators.ema(df, params['ema_fast']).iloc[i-1]
            ema_slow = TechnicalIndicators.ema(df, params['ema_slow']).iloc[i]
            ema_slow_prev = TechnicalIndicators.ema(df, params['ema_slow']).iloc[i-1]
            
            # Additional filters
            vwap_ok = True
            if params.get('use_vwap', False):
                # Only trade pullbacks to VWAP
                vwap_ok = False
                if ema_fast > ema_slow and abs(bar['close'] - bar['vwap']) < bar['atr'] * 0.5:
                    vwap_ok = True
            
            rsi_ok = True
            if params.get('use_rsi', False):
                if ema_fast > ema_slow:
                    rsi_ok = bar['rsi'] > params.get('rsi_bull_min', 50)
                else:
                    rsi_ok = bar['rsi'] < params.get('rsi_bear_max', 50)
            
            # Long: Fast EMA crosses above slow EMA
            if (ema_fast > ema_slow and ema_fast_prev <= ema_slow_prev and 
                vwap_ok and rsi_ok):
                
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
            
            # Short: Fast EMA crosses below slow EMA
            elif (ema_fast < ema_slow and ema_fast_prev >= ema_slow_prev and 
                  vwap_ok and rsi_ok):
                
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
    
    signals_df = pd.DataFrame(signals)
    
    if len(signals_df) > 0:
        # Run backtest
        backtester = Backtester(initial_capital=10000)
        metrics = backtester.run_backtest(df, signals_df)
        
        result = {
            'name': config['name'],
            'description': config['description'],
            'signals': len(signals_df),
            'trades': metrics['total_trades'],
            'return': metrics['total_return_pct'],
            'win_rate': metrics['win_rate_pct'],
            'profit_factor': metrics['profit_factor'],
            'sharpe': metrics['sharpe_ratio'],
            'max_dd': metrics['max_drawdown_pct'],
            'expectancy': metrics['expectancy'],
            'params': params
        }
        
        results.append(result)
        
        print(f'    ✓ Signals: {len(signals_df)}')
        print(f'    ✓ Return: {metrics["total_return_pct"]:.2f}%')
        print(f'    ✓ Win Rate: {metrics["win_rate_pct"]:.1f}%')
        print(f'    ✓ Profit Factor: {metrics["profit_factor"]:.2f}')
        print(f'    ✓ Sharpe: {metrics["sharpe_ratio"]:.2f}')
    else:
        print(f'    ✗ No signals generated')
    
    print()

# Find best configuration
if results:
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('return', ascending=False)
    
    print('='*80)
    print('📊 ALL CONFIGURATIONS TESTED')
    print('='*80)
    print()
    
    print(results_df[['name', 'signals', 'return', 'win_rate', 'profit_factor', 'sharpe']].to_string(index=False))
    print()
    
    # Find profitable ones
    profitable = results_df[results_df['return'] > 0]
    
    if len(profitable) > 0:
        print('='*80)
        print('🏆 WINNING CONFIGURATIONS FOUND!')
        print('='*80)
        print()
        
        for idx, row in profitable.iterrows():
            print(f"✅ {row['name']}")
            print(f"   Return: {row['return']:.2f}%")
            print(f"   Win Rate: {row['win_rate']:.1f}%")
            print(f"   Profit Factor: {row['profit_factor']:.2f}")
            print(f"   Trades: {row['trades']}")
            print(f"   Expectancy: ${row['expectancy']:.2f}")
            print()
        
        # Best strategy
        best = profitable.iloc[0]
        
        print('='*80)
        print('🎯 BEST STRATEGY FOR ROBINHOOD')
        print('='*80)
        print()
        print(f"Strategy: {best['name']}")
        print(f"Description: {best['description']}")
        print()
        print(f"📈 Performance:")
        print(f"   Return: {best['return']:.2f}%")
        print(f"   Win Rate: {best['win_rate']:.1f}%")
        print(f"   Profit Factor: {best['profit_factor']:.2f}")
        print(f"   Sharpe Ratio: {best['sharpe']:.2f}")
        print(f"   Max Drawdown: {best['max_dd']:.2f}%")
        print(f"   Expectancy: ${best['expectancy']:.2f} per trade")
        print(f"   Total Trades: {best['trades']}")
        print()
        print(f"⚙️ Parameters:")
        for key, value in best['params'].items():
            print(f"   {key}: {value}")
        
        # Save best strategy
        results_df.to_csv('/workspace/optimization_results.csv', index=False)
        print()
        print('✓ Results saved to: optimization_results.csv')
        
    else:
        print('='*80)
        print('⚠️ NO PROFITABLE CONFIGURATIONS IN THIS PERIOD')
        print('='*80)
        print()
        print('Best performing (least loss):')
        best = results_df.iloc[0]
        print(f"   {best['name']}: {best['return']:.2f}%")
        print()
        print('💡 Recommendations:')
        print('   1. Test on different time period')
        print('   2. Try different symbols (QQQ, IWM)')
        print('   3. Use longer timeframe (4H, Daily)')
        print('   4. Add more filters (session, market regime)')

else:
    print('No configurations produced signals')

print()
print('='*80)
print('✅ OPTIMIZATION COMPLETE')
print('='*80)
