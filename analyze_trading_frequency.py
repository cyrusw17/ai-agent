#!/usr/bin/env python3
"""
TRADING FREQUENCY AND POSITION SIZING ANALYSIS
How often does this strategy trade? How big are positions?
"""

import sys
sys.path.insert(0, '/workspace')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from core.data_handler import DataHandler
from core.indicators import TechnicalIndicators
import json

print('='*80)
print('📊 TRADING FREQUENCY & POSITION ANALYSIS')
print('='*80)
print()

# Load winner config
with open('/workspace/instant_winner.json', 'r') as f:
    winner = json.load(f)

print('Strategy: EMA 5/13, ADX 10, 8% risk, 5:1 R:R')
print()

def gen_sigs(df, cfg):
    """Generate signals with dates"""
    df = df.copy()
    df['atr'] = TechnicalIndicators.atr(df)
    df['ema_f'] = TechnicalIndicators.ema(df, cfg['ema_fast'])
    df['ema_s'] = TechnicalIndicators.ema(df, cfg['ema_slow'])
    
    adx, _, _ = TechnicalIndicators.adx(df)
    df['adx'] = adx
    
    sigs = []
    for i in range(50, len(df)):
        bar, prev = df.iloc[i], df.iloc[i-1]
        
        if bar['adx'] < cfg['adx']:
            continue
        
        date = bar.name if isinstance(bar.name, pd.Timestamp) else pd.Timestamp(bar['date'])
        
        direction = None
        if bar['ema_f'] > bar['ema_s'] and prev['ema_f'] <= prev['ema_s']:
            direction = 'LONG'
        elif bar['ema_f'] < bar['ema_s'] and prev['ema_f'] >= prev['ema_s']:
            direction = 'SHORT'
        
        if direction:
            sigs.append({
                'date': date,
                'direction': direction,
                'entry_price': bar['close'],
                'stop_loss': bar['close'] - (bar['atr'] * cfg['stop']) if direction == 'LONG' else bar['close'] + (bar['atr'] * cfg['stop']),
                'take_profit': bar['close'] + (bar['atr'] * cfg['target']) if direction == 'LONG' else bar['close'] - (bar['atr'] * cfg['target']),
                'atr': bar['atr'],
                'ema_fast': bar['ema_f'],
                'ema_slow': bar['ema_s'],
                'adx': bar['adx']
            })
    
    return pd.DataFrame(sigs)

# Load different time periods
print('='*80)
print('ANALYZING MULTIPLE TIME PERIODS')
print('='*80)
print()

end = datetime.now()
periods = [
    (90, '90 days (3 months)'),
    (180, '180 days (6 months)'),
    (365, '365 days (1 year)')
]

all_stats = []

for days, period_name in periods:
    start = end - timedelta(days=days)
    
    print(f'\n📅 {period_name.upper()}:')
    print(f'   Period: {start.strftime("%Y-%m-%d")} to {end.strftime("%Y-%m-%d")}')
    
    try:
        handler = DataHandler()
        df = handler.fetch_data('EURUSD=X', start.strftime('%Y-%m-%d'), 
                               end.strftime('%Y-%m-%d'), '4h')
        
        sigs = gen_sigs(df.copy(), winner['config'])
        
        if len(sigs) > 0:
            # Calculate time between signals
            sigs['date'] = pd.to_datetime(sigs['date'])
            sigs = sigs.sort_values('date')
            sigs['days_since_last'] = sigs['date'].diff().dt.total_seconds() / (24 * 3600)
            
            # Trading days
            trading_days = (sigs['date'].max() - sigs['date'].min()).days
            
            # Weeks and months
            weeks = days / 7
            months = days / 30
            
            stats = {
                'period': period_name,
                'days': days,
                'bars': len(df),
                'signals': len(sigs),
                'signals_per_week': len(sigs) / weeks,
                'signals_per_month': len(sigs) / months,
                'avg_days_between': sigs['days_since_last'].mean(),
                'min_days_between': sigs['days_since_last'].min(),
                'max_days_between': sigs['days_since_last'].max(),
                'long_signals': len(sigs[sigs['direction'] == 'LONG']),
                'short_signals': len(sigs[sigs['direction'] == 'SHORT'])
            }
            
            all_stats.append(stats)
            
            print(f'   Bars: {len(df)} (4H)')
            print(f'   Signals Generated: {len(sigs)}')
            print(f'   Signals per Week: {stats["signals_per_week"]:.1f}')
            print(f'   Signals per Month: {stats["signals_per_month"]:.1f}')
            print(f'   Avg Days Between Signals: {stats["avg_days_between"]:.1f}')
            print(f'   Min Days Between: {stats["min_days_between"]:.1f}')
            print(f'   Max Days Between: {stats["max_days_between"]:.1f}')
            print(f'   Direction: {stats["long_signals"]} LONG, {stats["short_signals"]} SHORT')
    
    except Exception as e:
        print(f'   ✗ Error: {e}')

# Position sizing analysis
print()
print('='*80)
print('💰 POSITION SIZING ANALYSIS')
print('='*80)
print()

capital = 10000
risk_pct = winner['config']['risk']
risk_amt = capital * risk_pct

print(f'Account Size: ${capital:,}')
print(f'Risk per Trade: {risk_pct*100:.0f}% (${risk_amt:,.0f})')
print()

# Example calculation
print('EXAMPLE POSITION CALCULATION:')
print()
print("Assume EURUSD at 1.0800, ATR = 0.0020 (20 pips)")
print()

entry = 1.0800
atr = 0.0020
stop_mult = winner['config']['stop']
target_mult = winner['config']['target']

stop_distance = atr * stop_mult
stop_price = entry - stop_distance

print(f"Entry: {entry:.4f}")
print(f"Stop: {stop_price:.4f} ({stop_mult}x ATR = {stop_distance:.4f})")
print(f"Risk per Unit: ${stop_distance:.4f}")
print()

# Position size
risk_per_pip = stop_distance
position_size = risk_amt / risk_per_pip
position_value_usd = position_size * entry

print(f"Position Size: {position_size:,.0f} units")
print(f"Position Value: ${position_value_usd:,.0f}")
print(f"Leverage Used: {position_value_usd / capital:.1f}x")
print()

# With 1:50 leverage available
max_leverage = 50
max_position = capital * max_leverage

print(f"Max Available (1:50): ${max_position:,.0f}")
print(f"Actually Using: ${position_value_usd:,.0f}")
print(f"Leverage Utilization: {(position_value_usd / max_position * 100):.1f}%")
print()

# Target calculation
target_distance = atr * target_mult
target_price = entry + target_distance
potential_profit = position_size * target_distance

print(f"Target: {target_price:.4f} ({target_mult}x ATR = {target_distance:.4f})")
print(f"Potential Profit: ${potential_profit:,.0f}")
print(f"Potential Profit %: {(potential_profit / capital * 100):.1f}%")
print()

# Risk/Reward
print(f"Risk: ${risk_amt:,.0f} ({risk_pct*100:.0f}%)")
print(f"Reward: ${potential_profit:,.0f} ({(potential_profit/capital*100):.0f}%)")
print(f"R:R Ratio: {(potential_profit / risk_amt):.1f}:1")
print()

# Is it "full porting"?
print('='*80)
print('❓ IS THIS "ALL-IN" TRADING?')
print('='*80)
print()

print('🎯 POSITION SIZE:')
print(f"   NOT using full capital directly")
print(f"   Using LEVERAGE to control larger position")
print()
print(f"   Account: ${capital:,}")
print(f"   Position: ${position_value_usd:,.0f} (~40x capital)")
print(f"   But RISK: Only ${risk_amt:,} (8% of capital)")
print()

print('💡 HOW IT WORKS:')
print(f"   1. You have ${capital:,} in account")
print(f"   2. Broker gives 1:50 leverage")
print(f"   3. You control ${position_value_usd:,.0f} position (40x)")
print(f"   4. But only risk 8% = ${risk_amt:,}")
print(f"   5. If stopped out: Lose ${risk_amt:,} only")
print(f"   6. If target hit: Gain ~${potential_profit:,.0f}")
print()

print('🚨 ONE TRADE AT A TIME:')
print(f"   Strategy: Take ONE high-quality setup")
print(f"   Wait for perfect entry (EMA cross + ADX)")
print(f"   Enter with 8% risk (leveraged position)")
print(f"   Either win 40% or lose 8%")
print(f"   Then DONE (passed or failed)")
print()

print('='*80)
print('📊 TRADING FREQUENCY SUMMARY')
print('='*80)
print()

if all_stats:
    avg_per_week = np.mean([s['signals_per_week'] for s in all_stats])
    avg_per_month = np.mean([s['signals_per_month'] for s in all_stats])
    
    print(f"Average Across All Periods:")
    print(f"  Signals per Week: {avg_per_week:.1f}")
    print(f"  Signals per Month: {avg_per_month:.1f}")
    print()
    
    print(f"For Prop Firm Evaluation:")
    print(f"  Take: 1-2 trades maximum")
    print(f"  Wait: Days to weeks for perfect setup")
    print(f"  Result: Pass (68%) or Fail (32%)")
    print()
    
    print(f"For Live Trading (if funded):")
    print(f"  Available setups: {avg_per_week:.1f} per week")
    print(f"  Recommended: Trade 1-2 per month (best setups)")
    print(f"  NOT: Trade every signal (too aggressive)")

print()
print('='*80)
print('✅ ANALYSIS COMPLETE')
print('='*80)
