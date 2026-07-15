#!/usr/bin/env python3
"""
Comprehensive Strategy Backtesting - Full Implementation
Tests all strategies with real data and shows actual results
"""

import sys
sys.path.insert(0, '/workspace')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from core.data_handler import DataHandler
from core.backtest import Backtester

print('='*80)
print('COMPREHENSIVE STRATEGY BACKTESTING - LIVE RESULTS')
print('='*80)
print()

# Initialize
handler = DataHandler()
end_date = datetime.now()
start_date = end_date - timedelta(days=180)

print(f'📊 Symbol: SPY (S&P 500 ETF)')
print(f'📅 Period: {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}')
print(f'⏰ Timeframe: 1 Hour')
print(f'💰 Starting Capital: $100,000')
print()

# Fetch data
print('Fetching market data...')
try:
    df = handler.fetch_data('SPY', start_date.strftime('%Y-%m-%d'), 
                           end_date.strftime('%Y-%m-%d'), '1h')
    print(f'✓ Loaded {len(df)} bars')
    print(f'✓ Date range: {df.index[0]} to {df.index[-1]}')
    print()
except Exception as e:
    print(f'✗ Error fetching data: {e}')
    sys.exit(1)

# Add all indicators needed
print('Calculating indicators...')
from core.indicators import TechnicalIndicators

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

df['supertrend'], df['supertrend_direction'] = TechnicalIndicators.supertrend(df)
df['atr'] = TechnicalIndicators.atr(df)
df['vwap'] = TechnicalIndicators.vwap(df)

adx, plus_di, minus_di = TechnicalIndicators.adx(df)
df['adx'] = adx
df['plus_di'] = plus_di
df['minus_di'] = minus_di

df['rvol'] = TechnicalIndicators.relative_volume(df)
df['volume_zscore'] = TechnicalIndicators.volume_zscore(df)

bb_upper, bb_middle, bb_lower = TechnicalIndicators.bollinger_bands(df)
df['bb_upper'] = bb_upper
df['bb_middle'] = bb_middle
df['bb_lower'] = bb_lower

print('✓ All indicators calculated')
print()

# Strategy 1: Simple Trend Following
print('='*80)
print('STRATEGY 1: TREND FOLLOWING (EMA Crossover)')
print('='*80)
print()

signals_1 = []
for i in range(200, len(df)):
    bar = df.iloc[i]
    
    # Long signal: Fast EMA crosses above slow EMA, ADX > 20
    if (df['ema_9'].iloc[i] > df['ema_21'].iloc[i] and 
        df['ema_9'].iloc[i-1] <= df['ema_21'].iloc[i-1] and
        bar['adx'] > 20):
        
        signals_1.append({
            'type': 'LONG',
            'index': i,
            'timestamp': df.index[i],
            'entry_price': bar['close'],
            'stop_loss': bar['close'] - (bar['atr'] * 1.5),
            'take_profit_1': bar['close'] + (bar['atr'] * 2.0),
            'take_profit_2': bar['close'] + (bar['atr'] * 3.0),
            'take_profit_3': bar['close'] + (bar['atr'] * 4.0)
        })
    
    # Short signal: Fast EMA crosses below slow EMA, ADX > 20
    elif (df['ema_9'].iloc[i] < df['ema_21'].iloc[i] and 
          df['ema_9'].iloc[i-1] >= df['ema_21'].iloc[i-1] and
          bar['adx'] > 20):
        
        signals_1.append({
            'type': 'SHORT',
            'index': i,
            'timestamp': df.index[i],
            'entry_price': bar['close'],
            'stop_loss': bar['close'] + (bar['atr'] * 1.5),
            'take_profit_1': bar['close'] - (bar['atr'] * 2.0),
            'take_profit_2': bar['close'] - (bar['atr'] * 3.0),
            'take_profit_3': bar['close'] - (bar['atr'] * 4.0)
        })

signals_df_1 = pd.DataFrame(signals_1)
print(f'Generated {len(signals_df_1)} signals')

if len(signals_df_1) > 0:
    backtester = Backtester(initial_capital=100000)
    metrics_1 = backtester.run_backtest(df, signals_df_1)
    backtester.print_summary(metrics_1)
else:
    print('No signals generated')
    metrics_1 = None

print()

# Strategy 2: RSI Mean Reversion
print('='*80)
print('STRATEGY 2: RSI MEAN REVERSION')
print('='*80)
print()

signals_2 = []
for i in range(50, len(df)):
    bar = df.iloc[i]
    
    # Long signal: RSI oversold, price above 200 EMA
    if (bar['rsi'] < 35 and 
        bar['rsi'] > df['rsi'].iloc[i-1] and
        bar['close'] > df['ema_200'].iloc[i]):
        
        signals_2.append({
            'type': 'LONG',
            'index': i,
            'timestamp': df.index[i],
            'entry_price': bar['close'],
            'stop_loss': bar['close'] - (bar['atr'] * 2.0),
            'take_profit_1': bar['close'] + (bar['atr'] * 2.0),
            'take_profit_2': bar['close'] + (bar['atr'] * 3.0),
            'take_profit_3': bar['close'] + (bar['atr'] * 4.0)
        })
    
    # Short signal: RSI overbought, price below 200 EMA
    elif (bar['rsi'] > 65 and 
          bar['rsi'] < df['rsi'].iloc[i-1] and
          bar['close'] < df['ema_200'].iloc[i]):
        
        signals_2.append({
            'type': 'SHORT',
            'index': i,
            'timestamp': df.index[i],
            'entry_price': bar['close'],
            'stop_loss': bar['close'] + (bar['atr'] * 2.0),
            'take_profit_1': bar['close'] - (bar['atr'] * 2.0),
            'take_profit_2': bar['close'] - (bar['atr'] * 3.0),
            'take_profit_3': bar['close'] - (bar['atr'] * 4.0)
        })

signals_df_2 = pd.DataFrame(signals_2)
print(f'Generated {len(signals_df_2)} signals')

if len(signals_df_2) > 0:
    backtester = Backtester(initial_capital=100000)
    metrics_2 = backtester.run_backtest(df, signals_df_2)
    backtester.print_summary(metrics_2)
else:
    print('No signals generated')
    metrics_2 = None

print()

# Strategy 3: MACD + Volume Confirmation
print('='*80)
print('STRATEGY 3: MACD + VOLUME CONFIRMATION')
print('='*80)
print()

signals_3 = []
for i in range(50, len(df)):
    bar = df.iloc[i]
    
    # Long signal: MACD crosses above signal, high volume
    if (bar['macd'] > bar['macd_signal'] and
        df['macd'].iloc[i-1] <= df['macd_signal'].iloc[i-1] and
        bar['rvol'] > 1.2):
        
        signals_3.append({
            'type': 'LONG',
            'index': i,
            'timestamp': df.index[i],
            'entry_price': bar['close'],
            'stop_loss': bar['close'] - (bar['atr'] * 1.5),
            'take_profit_1': bar['close'] + (bar['atr'] * 2.5),
            'take_profit_2': bar['close'] + (bar['atr'] * 3.5),
            'take_profit_3': bar['close'] + (bar['atr'] * 5.0)
        })
    
    # Short signal: MACD crosses below signal, high volume
    elif (bar['macd'] < bar['macd_signal'] and
          df['macd'].iloc[i-1] >= df['macd_signal'].iloc[i-1] and
          bar['rvol'] > 1.2):
        
        signals_3.append({
            'type': 'SHORT',
            'index': i,
            'timestamp': df.index[i],
            'entry_price': bar['close'],
            'stop_loss': bar['close'] + (bar['atr'] * 1.5),
            'take_profit_1': bar['close'] - (bar['atr'] * 2.5),
            'take_profit_2': bar['close'] - (bar['atr'] * 3.5),
            'take_profit_3': bar['close'] - (bar['atr'] * 5.0)
        })

signals_df_3 = pd.DataFrame(signals_3)
print(f'Generated {len(signals_df_3)} signals')

if len(signals_df_3) > 0:
    backtester = Backtester(initial_capital=100000)
    metrics_3 = backtester.run_backtest(df, signals_df_3)
    backtester.print_summary(metrics_3)
else:
    print('No signals generated')
    metrics_3 = None

print()

# Strategy 4: Bollinger Band Bounce
print('='*80)
print('STRATEGY 4: BOLLINGER BAND BOUNCE')
print('='*80)
print()

signals_4 = []
for i in range(50, len(df)):
    bar = df.iloc[i]
    
    # Long signal: Price touches lower BB, RSI not oversold
    if (bar['low'] <= df['bb_lower'].iloc[i] and
        bar['close'] > df['bb_lower'].iloc[i] and
        bar['rsi'] < 40):
        
        signals_4.append({
            'type': 'LONG',
            'index': i,
            'timestamp': df.index[i],
            'entry_price': bar['close'],
            'stop_loss': bar['close'] - (bar['atr'] * 1.5),
            'take_profit_1': df['bb_middle'].iloc[i],
            'take_profit_2': df['bb_upper'].iloc[i],
            'take_profit_3': df['bb_upper'].iloc[i] + (bar['atr'] * 1.0)
        })
    
    # Short signal: Price touches upper BB, RSI not overbought
    elif (bar['high'] >= df['bb_upper'].iloc[i] and
          bar['close'] < df['bb_upper'].iloc[i] and
          bar['rsi'] > 60):
        
        signals_4.append({
            'type': 'SHORT',
            'index': i,
            'timestamp': df.index[i],
            'entry_price': bar['close'],
            'stop_loss': bar['close'] + (bar['atr'] * 1.5),
            'take_profit_1': df['bb_middle'].iloc[i],
            'take_profit_2': df['bb_lower'].iloc[i],
            'take_profit_3': df['bb_lower'].iloc[i] - (bar['atr'] * 1.0)
        })

signals_df_4 = pd.DataFrame(signals_4)
print(f'Generated {len(signals_df_4)} signals')

if len(signals_df_4) > 0:
    backtester = Backtester(initial_capital=100000)
    metrics_4 = backtester.run_backtest(df, signals_df_4)
    backtester.print_summary(metrics_4)
else:
    print('No signals generated')
    metrics_4 = None

print()

# Strategy 5: VWAP + Trend
print('='*80)
print('STRATEGY 5: VWAP + TREND FOLLOWING')
print('='*80)
print()

signals_5 = []
for i in range(50, len(df)):
    bar = df.iloc[i]
    
    # Long signal: Price above VWAP, uptrend, pullback complete
    if (bar['close'] > bar['vwap'] and
        df['ema_9'].iloc[i] > df['ema_21'].iloc[i] and
        df['close'].iloc[i-1] < df['ema_9'].iloc[i-1] and
        bar['close'] > df['ema_9'].iloc[i] and
        bar['rvol'] > 1.0):
        
        signals_5.append({
            'type': 'LONG',
            'index': i,
            'timestamp': df.index[i],
            'entry_price': bar['close'],
            'stop_loss': bar['vwap'] - (bar['atr'] * 1.0),
            'take_profit_1': bar['close'] + (bar['atr'] * 2.0),
            'take_profit_2': bar['close'] + (bar['atr'] * 3.0),
            'take_profit_3': bar['close'] + (bar['atr'] * 4.0)
        })
    
    # Short signal: Price below VWAP, downtrend, pullback complete
    elif (bar['close'] < bar['vwap'] and
          df['ema_9'].iloc[i] < df['ema_21'].iloc[i] and
          df['close'].iloc[i-1] > df['ema_9'].iloc[i-1] and
          bar['close'] < df['ema_9'].iloc[i] and
          bar['rvol'] > 1.0):
        
        signals_5.append({
            'type': 'SHORT',
            'index': i,
            'timestamp': df.index[i],
            'entry_price': bar['close'],
            'stop_loss': bar['vwap'] + (bar['atr'] * 1.0),
            'take_profit_1': bar['close'] - (bar['atr'] * 2.0),
            'take_profit_2': bar['close'] - (bar['atr'] * 3.0),
            'take_profit_3': bar['close'] - (bar['atr'] * 4.0)
        })

signals_df_5 = pd.DataFrame(signals_5)
print(f'Generated {len(signals_df_5)} signals')

if len(signals_df_5) > 0:
    backtester = Backtester(initial_capital=100000)
    metrics_5 = backtester.run_backtest(df, signals_df_5)
    backtester.print_summary(metrics_5)
else:
    print('No signals generated')
    metrics_5 = None

print()

# Final Comparison
print('='*80)
print('📊 STRATEGY COMPARISON SUMMARY')
print('='*80)
print()

results = []
for idx, (name, metrics, signals_df) in enumerate([
    ('Trend Following (EMA)', metrics_1, signals_df_1),
    ('RSI Mean Reversion', metrics_2, signals_df_2),
    ('MACD + Volume', metrics_3, signals_df_3),
    ('Bollinger Bounce', metrics_4, signals_df_4),
    ('VWAP + Trend', metrics_5, signals_df_5)
]):
    if metrics:
        results.append({
            'Strategy': name,
            'Signals': len(signals_df),
            'Trades': metrics['total_trades'],
            'Return %': metrics['total_return_pct'],
            'Win Rate %': metrics['win_rate_pct'],
            'Profit Factor': metrics['profit_factor'],
            'Sharpe': metrics['sharpe_ratio'],
            'Max DD %': metrics['max_drawdown_pct']
        })

if results:
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('Return %', ascending=False)
    
    print(results_df.to_string(index=False))
    print()
    
    print('='*80)
    print('🏆 BEST PERFORMING STRATEGY')
    print('='*80)
    print()
    
    best = results_df.iloc[0]
    print(f"Strategy: {best['Strategy']}")
    print(f"Return: {best['Return %']:.2f}%")
    print(f"Win Rate: {best['Win Rate %']:.1f}%")
    print(f"Profit Factor: {best['Profit Factor']:.2f}")
    print(f"Sharpe Ratio: {best['Sharpe']:.2f}")
    print(f"Max Drawdown: {best['Max DD %']:.2f}%")
    print(f"Total Trades: {int(best['Trades'])}")
    
    print()
    print('💡 Key Insights:')
    avg_return = results_df['Return %'].mean()
    avg_wr = results_df['Win Rate %'].mean()
    profitable = len(results_df[results_df['Return %'] > 0])
    
    print(f"  • Average Return: {avg_return:.2f}%")
    print(f"  • Average Win Rate: {avg_wr:.1f}%")
    print(f"  • Profitable Strategies: {profitable}/{len(results_df)}")
    
    # Save results
    results_df.to_csv('/workspace/backtest_results.csv', index=False)
    print()
    print('✓ Results saved to: /workspace/backtest_results.csv')
else:
    print('No successful backtests to compare')

print()
print('='*80)
print('✅ COMPREHENSIVE BACKTESTING COMPLETE')
print('='*80)
