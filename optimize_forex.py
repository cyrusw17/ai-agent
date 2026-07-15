#!/usr/bin/env python3
"""
Forex-Specific Strategy Optimizer
Goal: Find profitable strategies with 10 and 20 trades per month
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
print('💱 FOREX STRATEGY OPTIMIZER - HIGH FREQUENCY TRADING')
print('='*80)
print()

# Forex pairs to test
FOREX_PAIRS = [
    'EURUSD=X',  # EUR/USD
    'GBPUSD=X',  # GBP/USD
    'USDJPY=X',  # USD/JPY
    'AUDUSD=X',  # AUD/USD
]

# Test parameters
INITIAL_CAPITAL = 10000
TIMEFRAME = '1h'
MONTHS_BACK = 6  # 6 months for faster iteration

end_date = datetime.now()
start_date = end_date - timedelta(days=MONTHS_BACK * 30)

print(f'📊 Forex Pairs: {", ".join([p.replace("=X", "") for p in FOREX_PAIRS])}')
print(f'📅 Period: {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")} ({MONTHS_BACK} months)')
print(f'⏰ Timeframe: {TIMEFRAME}')
print(f'💰 Starting Capital: ${INITIAL_CAPITAL:,}')
print(f'🎯 Goals: 10 trades/month (60 total) and 20 trades/month (120 total)')
print()

# Configuration space for higher frequency
configs = []

# Config 1: Fast EMA with loose filters
configs.append({
    'name': 'Fast Scalper',
    'ema_fast': 5,
    'ema_slow': 13,
    'min_adx': 15,
    'stop_mult': 1.0,
    'target_mult': 2.0,
    'use_rvol': False,
})

# Config 2: Very fast with tight stops
configs.append({
    'name': 'Ultra Fast',
    'ema_fast': 3,
    'ema_slow': 8,
    'min_adx': 12,
    'stop_mult': 0.8,
    'target_mult': 1.5,
    'use_rvol': False,
})

# Config 3: RSI momentum with fast EMAs
configs.append({
    'name': 'RSI Scalper',
    'ema_fast': 5,
    'ema_slow': 13,
    'min_adx': 15,
    'stop_mult': 1.0,
    'target_mult': 2.0,
    'use_rsi': True,
    'rsi_oversold': 40,
    'rsi_overbought': 60,
    'use_rvol': False,
})

# Config 4: MACD with no ADX filter
configs.append({
    'name': 'MACD Fast',
    'use_macd': True,
    'min_adx': 10,
    'stop_mult': 1.0,
    'target_mult': 2.0,
    'use_rvol': False,
})

# Config 5: Bollinger Band breakouts
configs.append({
    'name': 'BB Breakout',
    'use_bb': True,
    'min_adx': 15,
    'stop_mult': 1.0,
    'target_mult': 2.0,
    'use_rvol': False,
})

# Config 6: Very loose filters (many trades)
configs.append({
    'name': 'High Frequency',
    'ema_fast': 5,
    'ema_slow': 10,
    'min_adx': 10,
    'stop_mult': 0.75,
    'target_mult': 1.5,
    'use_rvol': False,
})

# Config 7: Medium frequency
configs.append({
    'name': 'Medium Frequency',
    'ema_fast': 8,
    'ema_slow': 21,
    'min_adx': 15,
    'stop_mult': 1.0,
    'target_mult': 2.0,
    'use_rvol': False,
})

# Config 8: Fast trend following
configs.append({
    'name': 'Fast Trend',
    'ema_fast': 7,
    'ema_slow': 15,
    'min_adx': 12,
    'stop_mult': 0.9,
    'target_mult': 1.8,
    'use_rvol': False,
})

# Config 9: No ADX filter
configs.append({
    'name': 'No ADX Filter',
    'ema_fast': 5,
    'ema_slow': 13,
    'min_adx': 0,
    'stop_mult': 1.0,
    'target_mult': 2.0,
    'use_rvol': False,
})

# Config 10: RSI + BB
configs.append({
    'name': 'RSI + BB Combo',
    'ema_fast': 5,
    'ema_slow': 13,
    'min_adx': 12,
    'use_rsi': True,
    'rsi_oversold': 35,
    'rsi_overbought': 65,
    'use_bb': True,
    'stop_mult': 1.0,
    'target_mult': 2.0,
    'use_rvol': False,
})

def generate_signals(df, params):
    """Generate signals based on parameters"""
    
    # Calculate indicators
    df['rsi'] = TechnicalIndicators.rsi(df, period=14)
    df['atr'] = TechnicalIndicators.atr(df)
    
    if 'ema_fast' in params:
        df['ema_fast'] = TechnicalIndicators.ema(df, params['ema_fast'])
        df['ema_slow'] = TechnicalIndicators.ema(df, params['ema_slow'])
    
    if params.get('min_adx', 0) > 0:
        adx, _, _ = TechnicalIndicators.adx(df)
        df['adx'] = adx
    
    if params.get('use_rvol', False):
        df['rvol'] = TechnicalIndicators.relative_volume(df)
    
    if params.get('use_macd', False):
        macd, macd_signal, macd_hist = TechnicalIndicators.macd(df)
        df['macd'] = macd
        df['macd_signal'] = macd_signal
    
    if params.get('use_bb', False):
        bb_upper, bb_middle, bb_lower = TechnicalIndicators.bollinger_bands(df)
        df['bb_upper'] = bb_upper
        df['bb_middle'] = bb_middle
        df['bb_lower'] = bb_lower
    
    signals = []
    
    for i in range(50, len(df)):
        bar = df.iloc[i]
        prev_bar = df.iloc[i-1]
        
        # ADX filter
        if params.get('min_adx', 0) > 0:
            if 'adx' in df.columns and bar['adx'] < params['min_adx']:
                continue
        
        # Volume filter
        if params.get('use_rvol', False):
            if bar['rvol'] < params.get('min_rvol', 1.0):
                continue
        
        # MACD signals
        if params.get('use_macd', False):
            if (bar['macd'] > bar['macd_signal'] and 
                prev_bar['macd'] <= prev_bar['macd_signal']):
                
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
            elif (bar['macd'] < bar['macd_signal'] and 
                  prev_bar['macd'] >= prev_bar['macd_signal']):
                
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
        
        # Bollinger Band signals
        elif params.get('use_bb', False):
            # Long: Price bounces off lower band
            if (prev_bar['close'] <= prev_bar['bb_lower'] and 
                bar['close'] > bar['bb_lower']):
                
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
            
            # Short: Price bounces off upper band
            elif (prev_bar['close'] >= prev_bar['bb_upper'] and 
                  bar['close'] < bar['bb_upper']):
                
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
        
        # EMA crossover signals
        elif 'ema_fast' in params:
            # RSI filter
            rsi_ok = True
            if params.get('use_rsi', False):
                if bar['ema_fast'] > bar['ema_slow']:
                    rsi_ok = bar['rsi'] < params.get('rsi_overbought', 70)
                else:
                    rsi_ok = bar['rsi'] > params.get('rsi_oversold', 30)
            
            if not rsi_ok:
                continue
            
            # Long: Fast EMA crosses above slow
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
            
            # Short: Fast EMA crosses below slow
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

# Test each configuration on each forex pair
all_results = []

for pair in FOREX_PAIRS:
    print('='*80)
    print(f'🔍 Testing {pair.replace("=X", "")}')
    print('='*80)
    print()
    
    # Fetch data
    try:
        handler = DataHandler()
        df = handler.fetch_data(pair, start_date.strftime('%Y-%m-%d'), 
                               end_date.strftime('%Y-%m-%d'), TIMEFRAME)
        print(f'✓ Loaded {len(df)} bars')
        print()
    except Exception as e:
        print(f'✗ Failed to load {pair}: {e}')
        print()
        continue
    
    for idx, config in enumerate(configs):
        print(f'[{idx+1}/{len(configs)}] Testing: {config["name"]}', end='')
        
        try:
            # Generate signals
            signals = generate_signals(df.copy(), config)
            
            if len(signals) > 0:
                # Run backtest
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
                
                print(f' → {metrics["total_trades"]} trades ({trades_per_month:.1f}/mo) | '
                      f'Return: {metrics["total_return_pct"]:.2f}% | '
                      f'Win: {metrics["win_rate_pct"]:.0f}%')
            else:
                print(' → No signals')
        
        except Exception as e:
            print(f' → Error: {e}')
    
    print()

# Analyze results
if all_results:
    results_df = pd.DataFrame(all_results)
    
    print('='*80)
    print('📊 ALL RESULTS')
    print('='*80)
    print()
    
    # Show top performers by trade frequency
    results_df_sorted = results_df.sort_values('trades_per_month', ascending=False)
    
    print(results_df_sorted[['pair', 'strategy', 'trades', 'trades_per_month', 
                              'return', 'win_rate', 'profit_factor']].head(20).to_string(index=False))
    print()
    
    # Find profitable strategies with 10+ trades/month
    profitable_10 = results_df[
        (results_df['return'] > 0) & 
        (results_df['trades_per_month'] >= 10)
    ].sort_values('return', ascending=False)
    
    # Find profitable strategies with 20+ trades/month
    profitable_20 = results_df[
        (results_df['return'] > 0) & 
        (results_df['trades_per_month'] >= 20)
    ].sort_values('return', ascending=False)
    
    print('='*80)
    print('🎯 TARGET: 10+ TRADES PER MONTH')
    print('='*80)
    print()
    
    if len(profitable_10) > 0:
        print(f'✅ FOUND {len(profitable_10)} PROFITABLE STRATEGIES!')
        print()
        
        for idx, row in profitable_10.head(5).iterrows():
            print(f"✅ {row['pair']} - {row['strategy']}")
            print(f"   Trades: {row['trades']} ({row['trades_per_month']:.1f}/month)")
            print(f"   Return: {row['return']:.2f}%")
            print(f"   Win Rate: {row['win_rate']:.1f}%")
            print(f"   Profit Factor: {row['profit_factor']:.2f}")
            print(f"   Sharpe: {row['sharpe']:.2f}")
            print()
    else:
        print('⚠️ No profitable strategies found with 10+ trades/month')
        # Show closest
        close = results_df[results_df['trades_per_month'] >= 10].sort_values('return', ascending=False).head(3)
        if len(close) > 0:
            print('Closest (not profitable):')
            for idx, row in close.iterrows():
                print(f"   {row['pair']} - {row['strategy']}: {row['return']:.2f}% ({row['trades_per_month']:.1f} trades/mo)")
        print()
    
    print('='*80)
    print('🎯 TARGET: 20+ TRADES PER MONTH')
    print('='*80)
    print()
    
    if len(profitable_20) > 0:
        print(f'✅ FOUND {len(profitable_20)} PROFITABLE STRATEGIES!')
        print()
        
        for idx, row in profitable_20.head(5).iterrows():
            print(f"✅ {row['pair']} - {row['strategy']}")
            print(f"   Trades: {row['trades']} ({row['trades_per_month']:.1f}/month)")
            print(f"   Return: {row['return']:.2f}%")
            print(f"   Win Rate: {row['win_rate']:.1f}%")
            print(f"   Profit Factor: {row['profit_factor']:.2f}")
            print(f"   Sharpe: {row['sharpe']:.2f}")
            print()
    else:
        print('⚠️ No profitable strategies found with 20+ trades/month')
        # Show closest
        close = results_df[results_df['trades_per_month'] >= 20].sort_values('return', ascending=False).head(3)
        if len(close) > 0:
            print('Closest (not profitable):')
            for idx, row in close.iterrows():
                print(f"   {row['pair']} - {row['strategy']}: {row['return']:.2f}% ({row['trades_per_month']:.1f} trades/mo)")
        print()
    
    # Save results
    results_df.to_csv('/workspace/forex_optimization_results.csv', index=False)
    print('✓ Results saved to: forex_optimization_results.csv')
    print()

else:
    print('⚠️ No results generated')

print('='*80)
print('✅ FOREX OPTIMIZATION COMPLETE')
print('='*80)
