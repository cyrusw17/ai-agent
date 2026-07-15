#!/usr/bin/env python3
"""
STRESS TESTING & ALTERNATIVE CONFIGURATIONS

This script tests:
1. Monte Carlo stress testing with varying win rates
2. Alternative strategy configurations
3. Risk management variations
4. Market condition filters

Goal: Find the most robust configuration for live trading
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
print('🔥 STRESS TESTING & ALTERNATIVE CONFIGURATIONS')
print('='*80)
print()

class StressBacktester:
    def __init__(self, capital=10000, config=None):
        self.capital = capital
        self.init = capital
        self.config = config or {}
        self.sniper_allocation = self.config.get('sniper_allocation', 0.40)
        self.background_allocation = self.config.get('background_allocation', 0.60)
        self.sniper_risk = self.config.get('sniper_risk', 0.05)
        self.background_risk = self.config.get('background_risk', 0.02)
        self.max_dd_stop = self.config.get('max_dd_stop', None)  # Kill switch
        self.trades = []
        self.peak = capital
        self.max_dd = 0
        self.stopped_out = False
    
    def trade_sniper(self, entry, stop, target, win_rate_modifier=1.0):
        if self.stopped_out:
            return None
        
        sniper_capital = self.capital * self.sniper_allocation
        risk_per_unit = abs(entry - stop)
        if risk_per_unit == 0:
            return None
        
        risk_amt = sniper_capital * self.sniper_risk
        size = risk_amt / risk_per_unit
        rr = abs(target - entry) / risk_per_unit
        
        # Apply stress modifier
        base_win_prob = min(0.65, 0.35 + (0.06 * rr))
        win_prob = base_win_prob * win_rate_modifier
        win_prob = max(0.20, min(0.85, win_prob))  # Clamp
        
        won = np.random.random() < win_prob
        pnl = (abs(target - entry) * size) if won else (-risk_per_unit * size)
        
        # Costs
        slippage = 0.0002 * size
        commission = (size / 100000) * 7
        pnl -= (slippage + commission)
        
        self.capital += pnl
        
        if self.capital > self.peak:
            self.peak = self.capital
        
        dd = (self.peak - self.capital) / self.init * 100
        if dd > self.max_dd:
            self.max_dd = dd
        
        # Check kill switch
        if self.max_dd_stop and dd >= self.max_dd_stop:
            self.stopped_out = True
        
        self.trades.append({'won': won, 'pnl': pnl, 'strategy': 'sniper'})
        return pnl
    
    def trade_background(self, entry, stop, target, win_rate_modifier=1.0):
        if self.stopped_out:
            return None
        
        background_capital = self.capital * self.background_allocation
        risk_per_unit = abs(entry - stop)
        if risk_per_unit == 0:
            return None
        
        risk_amt = background_capital * self.background_risk
        size = risk_amt / risk_per_unit
        rr = abs(target - entry) / risk_per_unit
        
        # Apply stress modifier
        base_win_prob = min(0.60, 0.35 + (0.05 * rr))
        win_prob = base_win_prob * win_rate_modifier
        win_prob = max(0.20, min(0.85, win_prob))  # Clamp
        
        won = np.random.random() < win_prob
        pnl = (abs(target - entry) * size) if won else (-risk_per_unit * size)
        
        # Costs
        slippage = 0.0002 * size
        commission = (size / 100000) * 7
        pnl -= (slippage + commission)
        
        self.capital += pnl
        
        if self.capital > self.peak:
            self.peak = self.capital
        
        dd = (self.peak - self.capital) / self.init * 100
        if dd > self.max_dd:
            self.max_dd = dd
        
        # Check kill switch
        if self.max_dd_stop and dd >= self.max_dd_stop:
            self.stopped_out = True
        
        self.trades.append({'won': won, 'pnl': pnl, 'strategy': 'background'})
        return pnl
    
    def run(self, df, sniper_sigs, background_sigs, win_rate_modifier=1.0):
        sniper_dict = {sig['date']: sig for _, sig in sniper_sigs.iterrows()}
        background_dict = {sig['date']: sig for _, sig in background_sigs.iterrows()}
        
        monthly_sniper = 0
        last_month = None
        
        for _, row in df.iterrows():
            if self.stopped_out:
                break
            
            date = row.name if isinstance(row.name, pd.Timestamp) else pd.Timestamp(row['date'])
            
            current_month = date.month
            if current_month != last_month:
                monthly_sniper = 0
                last_month = current_month
            
            if date in sniper_dict and monthly_sniper < 2:
                sig = sniper_dict[date]
                self.trade_sniper(sig['entry_price'], sig['stop_loss'], sig['take_profit'], win_rate_modifier)
                monthly_sniper += 1
            
            if date in background_dict:
                sig = background_dict[date]
                self.trade_background(sig['entry_price'], sig['stop_loss'], sig['take_profit'], win_rate_modifier)
        
        profit_pct = (self.capital - self.init) / self.init * 100
        return {
            'profit': profit_pct,
            'final': self.capital,
            'dd': self.max_dd,
            'trades': len(self.trades),
            'stopped_out': self.stopped_out
        }

def gen_sniper_sigs(df, ema_fast=5, ema_slow=13, adx_threshold=10):
    df = df.copy()
    df['atr'] = TechnicalIndicators.atr(df)
    df['ema_f'] = TechnicalIndicators.ema(df, ema_fast)
    df['ema_s'] = TechnicalIndicators.ema(df, ema_slow)
    adx, _, _ = TechnicalIndicators.adx(df)
    df['adx'] = adx
    
    sigs = []
    for i in range(50, len(df)):
        bar, prev = df.iloc[i], df.iloc[i-1]
        if bar['adx'] < adx_threshold:
            continue
        date = bar.name if isinstance(bar.name, pd.Timestamp) else pd.Timestamp(bar['date'])
        if bar['ema_f'] > bar['ema_s'] and prev['ema_f'] <= prev['ema_s']:
            sigs.append({'date': date, 'entry_price': bar['close'],
                        'stop_loss': bar['close'] - (bar['atr'] * 1.0),
                        'take_profit': bar['close'] + (bar['atr'] * 5.0)})
        elif bar['ema_f'] < bar['ema_s'] and prev['ema_f'] >= prev['ema_s']:
            sigs.append({'date': date, 'entry_price': bar['close'],
                        'stop_loss': bar['close'] + (bar['atr'] * 1.0),
                        'take_profit': bar['close'] - (bar['atr'] * 5.0)})
    return pd.DataFrame(sigs)

def gen_background_sigs(df, ema_fast=9, ema_slow=21, adx_threshold=20):
    df = df.copy()
    df['atr'] = TechnicalIndicators.atr(df)
    df['ema_f'] = TechnicalIndicators.ema(df, ema_fast)
    df['ema_s'] = TechnicalIndicators.ema(df, ema_slow)
    adx, _, _ = TechnicalIndicators.adx(df)
    df['adx'] = adx
    
    sigs = []
    for i in range(50, len(df)):
        bar, prev = df.iloc[i], df.iloc[i-1]
        if bar['adx'] < adx_threshold:
            continue
        date = bar.name if isinstance(bar.name, pd.Timestamp) else pd.Timestamp(bar['date'])
        if bar['ema_f'] > bar['ema_s'] and prev['ema_f'] <= prev['ema_s']:
            sigs.append({'date': date, 'entry_price': bar['close'],
                        'stop_loss': bar['close'] - (bar['atr'] * 2.0),
                        'take_profit': bar['close'] + (bar['atr'] * 3.0)})
        elif bar['ema_f'] < bar['ema_s'] and prev['ema_f'] >= prev['ema_s']:
            sigs.append({'date': date, 'entry_price': bar['close'],
                        'stop_loss': bar['close'] + (bar['atr'] * 2.0),
                        'take_profit': bar['close'] - (bar['atr'] * 3.0)})
    return pd.DataFrame(sigs)

# Load data
handler = DataHandler()
end = datetime.now()
start = end - timedelta(days=90)

print('Loading EURUSD data for stress testing...')
df = handler.fetch_data('EURUSD=X', start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'), '4h')
print(f'Loaded {len(df)} bars')
print()

# ============================================================================
# TEST 1: MONTE CARLO STRESS TESTING (varying win rates)
# ============================================================================

print('='*80)
print('TEST 1: MONTE CARLO STRESS TESTING')
print('='*80)
print()
print('Testing strategy under different win rate scenarios...')
print()

# Generate base signals
sniper_sigs = gen_sniper_sigs(df.copy())
background_sigs = gen_background_sigs(df.copy())

stress_scenarios = [
    {'name': 'Optimal', 'modifier': 1.0},
    {'name': 'Good', 'modifier': 0.95},
    {'name': 'Normal', 'modifier': 0.90},
    {'name': 'Poor', 'modifier': 0.85},
    {'name': 'Bad', 'modifier': 0.80},
]

stress_results = []

for scenario in stress_scenarios:
    scenario_results = []
    
    for _ in range(50):  # 50 simulations per scenario
        bt = StressBacktester(capital=10000)
        result = bt.run(df, sniper_sigs, background_sigs, scenario['modifier'])
        scenario_results.append(result['profit'])
    
    avg_profit = np.mean(scenario_results)
    profitable_pct = sum(1 for r in scenario_results if r > 0) / len(scenario_results) * 100
    
    stress_results.append({
        'scenario': scenario['name'],
        'modifier': scenario['modifier'],
        'avg_profit': avg_profit,
        'profitable_pct': profitable_pct
    })
    
    status = '✅' if avg_profit > 0 else '⚠️'
    print(f'{status} {scenario["name"]:10s} (WR x{scenario["modifier"]:.2f}): {avg_profit:+6.2f}% avg, {profitable_pct:.0f}% profitable')

print()
stress_df = pd.DataFrame(stress_results)

# Find break-even point
profitable_scenarios = stress_df[stress_df['avg_profit'] > 0]
if len(profitable_scenarios) > 0:
    worst_profitable = profitable_scenarios.iloc[-1]
    print(f'Strategy remains profitable down to {worst_profitable["modifier"]:.0%} of expected win rate')
else:
    print('Strategy not profitable under any stress scenario')

print()

# ============================================================================
# TEST 2: ALTERNATIVE CONFIGURATIONS
# ============================================================================

print('='*80)
print('TEST 2: ALTERNATIVE STRATEGY CONFIGURATIONS')
print('='*80)
print()
print('Testing variations of the strategy setup...')
print()

alt_configs = [
    {
        'name': 'Original (40/60 split)',
        'sniper_allocation': 0.40,
        'background_allocation': 0.60,
        'sniper_risk': 0.05,
        'background_risk': 0.02
    },
    {
        'name': 'Balanced (50/50 split)',
        'sniper_allocation': 0.50,
        'background_allocation': 0.50,
        'sniper_risk': 0.05,
        'background_risk': 0.02
    },
    {
        'name': 'Sniper Focus (60/40 split)',
        'sniper_allocation': 0.60,
        'background_allocation': 0.40,
        'sniper_risk': 0.05,
        'background_risk': 0.02
    },
    {
        'name': 'Conservative Risk',
        'sniper_allocation': 0.40,
        'background_allocation': 0.60,
        'sniper_risk': 0.03,
        'background_risk': 0.01
    },
    {
        'name': 'Aggressive Risk',
        'sniper_allocation': 0.40,
        'background_allocation': 0.60,
        'sniper_risk': 0.07,
        'background_risk': 0.03
    },
    {
        'name': 'With 15% DD Kill Switch',
        'sniper_allocation': 0.40,
        'background_allocation': 0.60,
        'sniper_risk': 0.05,
        'background_risk': 0.02,
        'max_dd_stop': 15.0
    }
]

config_results = []

for config in alt_configs:
    config_sims = []
    
    for _ in range(30):
        bt = StressBacktester(capital=10000, config=config)
        result = bt.run(df, sniper_sigs, background_sigs)
        config_sims.append(result)
    
    avg_profit = np.mean([r['profit'] for r in config_sims])
    avg_dd = np.mean([r['dd'] for r in config_sims])
    stopped_out_pct = sum(1 for r in config_sims if r['stopped_out']) / len(config_sims) * 100
    
    config_results.append({
        'name': config['name'],
        'avg_profit': avg_profit,
        'avg_dd': avg_dd,
        'stopped_out_pct': stopped_out_pct
    })
    
    status = '✅' if avg_profit > 0 else '⚠️'
    extra = f' ({stopped_out_pct:.0f}% stopped)' if 'Kill Switch' in config['name'] else ''
    print(f'{status} {config["name"]:30s}: {avg_profit:+6.2f}% return, {avg_dd:.2f}% DD{extra}')

print()

config_df = pd.DataFrame(config_results)
best_config = config_df.loc[config_df['avg_profit'].idxmax()]

print(f'BEST CONFIGURATION: {best_config["name"]}')
print(f'  Return: {best_config["avg_profit"]:.2f}%')
print(f'  Drawdown: {best_config["avg_dd"]:.2f}%')
print()

# ============================================================================
# TEST 3: PARAMETER VARIATIONS
# ============================================================================

print('='*80)
print('TEST 3: ALTERNATIVE INDICATOR PARAMETERS')
print('='*80)
print()
print('Testing different EMA and ADX combinations...')
print()

param_variations = [
    {'name': 'Original', 'sniper_ema': (5, 13), 'sniper_adx': 10, 'bg_ema': (9, 21), 'bg_adx': 20},
    {'name': 'Fast Sniper', 'sniper_ema': (3, 9), 'sniper_adx': 10, 'bg_ema': (9, 21), 'bg_adx': 20},
    {'name': 'Slow Sniper', 'sniper_ema': (8, 21), 'sniper_adx': 10, 'bg_ema': (9, 21), 'bg_adx': 20},
    {'name': 'Strict ADX', 'sniper_ema': (5, 13), 'sniper_adx': 15, 'bg_ema': (9, 21), 'bg_adx': 25},
    {'name': 'Relaxed ADX', 'sniper_ema': (5, 13), 'sniper_adx': 5, 'bg_ema': (9, 21), 'bg_adx': 15},
]

param_results = []

for params in param_variations:
    # Generate signals with these parameters
    sniper_sigs_test = gen_sniper_sigs(df.copy(), 
                                       ema_fast=params['sniper_ema'][0],
                                       ema_slow=params['sniper_ema'][1],
                                       adx_threshold=params['sniper_adx'])
    
    background_sigs_test = gen_background_sigs(df.copy(),
                                               ema_fast=params['bg_ema'][0],
                                               ema_slow=params['bg_ema'][1],
                                               adx_threshold=params['bg_adx'])
    
    param_sims = []
    for _ in range(30):
        bt = StressBacktester(capital=10000)
        result = bt.run(df, sniper_sigs_test, background_sigs_test)
        param_sims.append(result['profit'])
    
    avg_profit = np.mean(param_sims)
    
    param_results.append({
        'name': params['name'],
        'avg_profit': avg_profit,
        'signal_count': len(sniper_sigs_test) + len(background_sigs_test)
    })
    
    status = '✅' if avg_profit > 0 else '⚠️'
    print(f'{status} {params["name"]:20s}: {avg_profit:+6.2f}% avg, {len(sniper_sigs_test) + len(background_sigs_test)} signals')

print()

param_df = pd.DataFrame(param_results)
best_params = param_df.loc[param_df['avg_profit'].idxmax()]

print(f'BEST PARAMETERS: {best_params["name"]}')
print(f'  Return: {best_params["avg_profit"]:.2f}%')
print(f'  Signals: {best_params["signal_count"]}')
print()

# Save all results
comprehensive_results = {
    'stress_testing': stress_df.to_dict('records'),
    'config_testing': config_df.to_dict('records'),
    'param_testing': param_df.to_dict('records'),
    'recommendations': {
        'best_config': best_config.to_dict(),
        'best_params': best_params.to_dict(),
        'stress_tolerance': float(stress_df[stress_df['avg_profit'] > 0].iloc[-1]['modifier']) if len(stress_df[stress_df['avg_profit'] > 0]) > 0 else 0.0
    }
}

with open('/workspace/stress_test_results.json', 'w') as f:
    json.dump(comprehensive_results, f, indent=2)

print('='*80)
print('📊 COMPREHENSIVE TESTING SUMMARY')
print('='*80)
print()
print(f'Stress Testing: Strategy profitable down to {stress_df[stress_df["avg_profit"] > 0].iloc[-1]["modifier"]:.0%} win rate')
print(f'Best Config: {best_config["name"]} ({best_config["avg_profit"]:+.2f}%)')
print(f'Best Params: {best_params["name"]} ({best_params["avg_profit"]:+.2f}%)')
print()
print('Saved comprehensive results to: stress_test_results.json')
print()
print('✅ STRESS TESTING COMPLETE')
