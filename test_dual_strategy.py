#!/usr/bin/env python3
"""
DUAL STRATEGY SYSTEM
Strategy A: Aggressive Sniper (for prop firm pass)
Strategy B: Conservative Background (for steady income)

Run both simultaneously on same account
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
print('🎯 DUAL STRATEGY SYSTEM')
print('='*80)
print()

class DualStrategyBacktester:
    """Run two strategies simultaneously"""
    
    def __init__(self, capital=10000):
        self.capital = capital
        self.init = capital
        
        # Strategy A: Aggressive Sniper (for prop firm)
        self.sniper_risk = 0.08  # 8% risk
        self.sniper_leverage = 40  # High leverage
        
        # Strategy B: Conservative Background
        self.background_risk = 0.02  # 2% risk per trade
        self.background_leverage = 2  # Low leverage (conservative)
        
        self.trades = []
        self.sniper_trades = []
        self.background_trades = []
        
        self.peak = capital
        self.max_dd = 0
        
        self.passed = False
        self.failed = False
        self.reason = None
    
    def can_take_sniper(self):
        """Check if we can take sniper trade"""
        # Don't take sniper if we already passed
        if self.passed:
            return False
        
        # Check if we have any open background trades
        # In real trading, you'd check actual positions
        # For simulation, we assume trades don't overlap much
        return True
    
    def trade_sniper(self, entry, stop, target, date):
        """Execute sniper trade (aggressive, prop firm)"""
        
        risk_per_unit = abs(entry - stop)
        if risk_per_unit == 0 or risk_per_unit > entry * 0.3:
            return None
        
        # Aggressive sizing
        risk_amt = self.capital * self.sniper_risk
        size = risk_amt / risk_per_unit
        
        # High leverage
        position_value = size * entry
        
        # Outcome (68% win rate)
        rr = abs(target - entry) / risk_per_unit
        win_prob = min(0.68, 0.40 + (0.05 * rr))
        
        won = np.random.random() < win_prob
        pnl = (abs(target - entry) * size) if won else (-risk_per_unit * size)
        
        self.capital += pnl
        
        trade_info = {
            'date': date,
            'strategy': 'SNIPER',
            'won': won,
            'pnl': pnl,
            'pnl_pct': (pnl / self.init) * 100,
            'capital': self.capital,
            'position_value': position_value,
            'leverage': position_value / self.capital
        }
        
        self.trades.append(trade_info)
        self.sniper_trades.append(trade_info)
        
        # Check if passed (5% target for Instant Funding)
        profit_pct = (self.capital - self.init) / self.init * 100
        if profit_pct >= 5:
            self.passed = True
            self.reason = f'Passed with {profit_pct:.1f}%'
        
        # Check if failed (daily DD)
        if pnl < 0 and abs(pnl) >= self.init * 0.04:  # 4% daily DD
            self.failed = True
            self.reason = f'Daily DD from sniper'
        
        return trade_info
    
    def trade_background(self, entry, stop, target, date):
        """Execute background trade (conservative)"""
        
        risk_per_unit = abs(entry - stop)
        if risk_per_unit == 0 or risk_per_unit > entry * 0.3:
            return None
        
        # Conservative sizing
        risk_amt = self.capital * self.background_risk
        size = risk_amt / risk_per_unit
        
        # Low leverage
        position_value = size * entry
        max_position = self.capital * self.background_leverage
        
        if position_value > max_position:
            size = max_position / entry
            position_value = max_position
        
        # Outcome (55% win rate, more conservative)
        rr = abs(target - entry) / risk_per_unit
        win_prob = min(0.60, 0.35 + (0.05 * rr))
        
        won = np.random.random() < win_prob
        pnl = (abs(target - entry) * size) if won else (-risk_per_unit * size)
        
        self.capital += pnl
        
        trade_info = {
            'date': date,
            'strategy': 'BACKGROUND',
            'won': won,
            'pnl': pnl,
            'pnl_pct': (pnl / self.init) * 100,
            'capital': self.capital,
            'position_value': position_value,
            'leverage': position_value / self.init if self.init > 0 else 0
        }
        
        self.trades.append(trade_info)
        self.background_trades.append(trade_info)
        
        # Update DD
        if self.capital > self.peak:
            self.peak = self.capital
        
        dd = (self.peak - self.capital) / self.init * 100
        if dd > self.max_dd:
            self.max_dd = dd
        
        return trade_info
    
    def run(self, df, sniper_sigs, background_sigs):
        """Run both strategies"""
        
        sniper_dict = {sig['date']: sig for _, sig in sniper_sigs.iterrows()}
        background_dict = {sig['date']: sig for _, sig in background_sigs.iterrows()}
        
        for _, row in df.iterrows():
            if self.passed or self.failed:
                break
            
            date = row.name if isinstance(row.name, pd.Timestamp) else pd.Timestamp(row['date'])
            
            # Check for sniper trade first (priority)
            if date in sniper_dict and self.can_take_sniper():
                sig = sniper_dict[date]
                self.trade_sniper(sig['entry_price'], sig['stop_loss'], sig['take_profit'], date)
            
            # Check for background trade
            elif date in background_dict and not self.passed:
                sig = background_dict[date]
                self.trade_background(sig['entry_price'], sig['stop_loss'], sig['take_profit'], date)
        
        profit_pct = (self.capital - self.init) / self.init * 100
        
        return {
            'passed': self.passed,
            'failed': self.failed,
            'reason': self.reason,
            'profit': profit_pct,
            'dd': self.max_dd,
            'total_trades': len(self.trades),
            'sniper_trades': len(self.sniper_trades),
            'background_trades': len(self.background_trades),
            'final_capital': self.capital
        }

# Generate signals for both strategies
def gen_sniper_sigs(df):
    """Sniper: EMA 5/13, ADX 10, tight"""
    df = df.copy()
    df['atr'] = TechnicalIndicators.atr(df)
    df['ema_f'] = TechnicalIndicators.ema(df, 5)
    df['ema_s'] = TechnicalIndicators.ema(df, 13)
    adx, _, _ = TechnicalIndicators.adx(df)
    df['adx'] = adx
    
    sigs = []
    for i in range(50, len(df)):
        bar, prev = df.iloc[i], df.iloc[i-1]
        
        if bar['adx'] < 10:
            continue
        
        date = bar.name if isinstance(bar.name, pd.Timestamp) else pd.Timestamp(bar['date'])
        
        if bar['ema_f'] > bar['ema_s'] and prev['ema_f'] <= prev['ema_s']:
            sigs.append({
                'date': date,
                'entry_price': bar['close'],
                'stop_loss': bar['close'] - (bar['atr'] * 1.0),
                'take_profit': bar['close'] + (bar['atr'] * 5.0)
            })
        elif bar['ema_f'] < bar['ema_s'] and prev['ema_f'] >= prev['ema_s']:
            sigs.append({
                'date': date,
                'entry_price': bar['close'],
                'stop_loss': bar['close'] + (bar['atr'] * 1.0),
                'take_profit': bar['close'] - (bar['atr'] * 5.0)
            })
    
    return pd.DataFrame(sigs)

def gen_background_sigs(df):
    """Background: EMA 9/21, ADX 20, wider stops (conservative)"""
    df = df.copy()
    df['atr'] = TechnicalIndicators.atr(df)
    df['ema_f'] = TechnicalIndicators.ema(df, 9)
    df['ema_s'] = TechnicalIndicators.ema(df, 21)
    adx, _, _ = TechnicalIndicators.adx(df)
    df['adx'] = adx
    
    sigs = []
    for i in range(50, len(df)):
        bar, prev = df.iloc[i], df.iloc[i-1]
        
        if bar['adx'] < 20:  # Higher ADX = fewer but better trades
            continue
        
        date = bar.name if isinstance(bar.name, pd.Timestamp) else pd.Timestamp(bar['date'])
        
        if bar['ema_f'] > bar['ema_s'] and prev['ema_f'] <= prev['ema_s']:
            sigs.append({
                'date': date,
                'entry_price': bar['close'],
                'stop_loss': bar['close'] - (bar['atr'] * 2.0),  # Wider
                'take_profit': bar['close'] + (bar['atr'] * 3.0)  # Conservative R:R
            })
        elif bar['ema_f'] < bar['ema_s'] and prev['ema_f'] >= prev['ema_s']:
            sigs.append({
                'date': date,
                'entry_price': bar['close'],
                'stop_loss': bar['close'] + (bar['atr'] * 2.0),
                'take_profit': bar['close'] - (bar['atr'] * 3.0)
            })
    
    return pd.DataFrame(sigs)

# Load data
print('Loading EURUSD data (90 days)...')
end = datetime.now()
start = end - timedelta(days=90)

handler = DataHandler()
df = handler.fetch_data('EURUSD=X', start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'), '4h')
print(f'✓ Loaded {len(df)} bars')
print()

# Generate signals for both
sniper_sigs = gen_sniper_sigs(df.copy())
background_sigs = gen_background_sigs(df.copy())

print(f'Sniper Signals: {len(sniper_sigs)} (aggressive, 5:1 R:R)')
print(f'Background Signals: {len(background_sigs)} (conservative, 1.5:1 R:R)')
print()

# Check overlap
sniper_dates = set(sniper_sigs['date'])
background_dates = set(background_sigs['date'])
overlap = sniper_dates.intersection(background_dates)
print(f'Signal Overlap: {len(overlap)} (these will prioritize sniper)')
print()

# Run simulations
print('='*80)
print('Running 100 simulations...')
print('='*80)
print()

results = []

for sim in range(100):
    bt = DualStrategyBacktester(capital=10000)
    result = bt.run(df.copy(), sniper_sigs, background_sigs)
    results.append(result)
    
    if (sim + 1) % 20 == 0:
        print(f'  Completed {sim + 1}/100...')

results_df = pd.DataFrame(results)

print()
print('='*80)
print('📊 DUAL STRATEGY RESULTS')
print('='*80)
print()

passed = results_df[results_df['passed'] == True]
failed = results_df[results_df['failed'] == True]

print('🎯 EVALUATION OUTCOMES:')
print(f"  Total Simulations: 100")
print(f"  Passed: {len(passed)} ({len(passed)}%)")
print(f"  Failed: {len(failed)} ({len(failed)}%)")
print()

if len(passed) > 0:
    print('✅ PASSED SIMULATIONS:')
    print(f"  Avg Profit: {passed['profit'].mean():.2f}%")
    print(f"  Median Profit: {passed['profit'].median():.2f}%")
    print(f"  Min/Max: {passed['profit'].min():.2f}% to {passed['profit'].max():.2f}%")
    print(f"  Avg Drawdown: {passed['dd'].mean():.2f}%")
    print()
    
    print('  Trade Breakdown:')
    print(f"    Total Trades: {passed['total_trades'].mean():.1f}")
    print(f"    Sniper Trades: {passed['sniper_trades'].mean():.1f}")
    print(f"    Background Trades: {passed['background_trades'].mean():.1f}")
    print()

if len(failed) > 0:
    print('❌ FAILED SIMULATIONS:')
    print(f"  Avg Loss: {failed['profit'].mean():.2f}%")
    print(f"  Background trades before failure: {failed['background_trades'].mean():.1f}")
    print()

# Compare with sniper-only
print('='*80)
print('📊 COMPARISON: DUAL vs SNIPER-ONLY')
print('='*80)
print()

print('DUAL STRATEGY (Sniper + Background):')
print(f"  Pass Rate: {len(passed)}%")
if len(passed) > 0:
    print(f"  Avg Profit: {passed['profit'].mean():.2f}%")
    print(f"  Avg Total Trades: {passed['total_trades'].mean():.1f}")
    print(f"    - Sniper: {passed['sniper_trades'].mean():.1f}")
    print(f"    - Background: {passed['background_trades'].mean():.1f}")
print()

print('SNIPER-ONLY (from previous test):')
print(f"  Pass Rate: 68%")
print(f"  Avg Profit: 40.00%")
print(f"  Avg Trades: 1.0")
print()

# Calculate improvement
if len(passed) > 0:
    pass_improvement = len(passed) - 68
    profit_improvement = passed['profit'].mean() - 40.0
    
    print('IMPROVEMENT:')
    print(f"  Pass Rate: {pass_improvement:+d} percentage points")
    print(f"  Avg Profit: {profit_improvement:+.2f} percentage points")
    print()
    
    if len(passed) > 68:
        print('✅ Dual strategy IMPROVES pass rate!')
    elif len(passed) == 68:
        print('➡️  Pass rate unchanged (but background adds income)')
    else:
        print('⚠️  Pass rate slightly lower (background adds complexity)')

# Expected value analysis
print()
print('='*80)
print('💰 EXPECTED VALUE ANALYSIS')
print('='*80)
print()

account_cost = 750
profit_split = 0.80

if len(passed) > 0:
    pass_rate = len(passed) / 100
    avg_profit_usd = passed['profit'].mean() / 100 * 10000
    
    print('DUAL STRATEGY:')
    print(f"  Pass Rate: {len(passed)}%")
    print(f"  Avg Profit (if pass): ${avg_profit_usd:.0f}")
    print(f"  Your Share: ${avg_profit_usd * profit_split:.0f}")
    print(f"  Net Profit: ${avg_profit_usd * profit_split - account_cost:.0f}")
    
    expected = (pass_rate * avg_profit_usd * profit_split) - account_cost
    print(f"  Expected Value: ${expected:.0f}")
    print(f"  Expected ROI: {(expected / account_cost * 100):.0f}%")

print()
print('SNIPER-ONLY (from previous):')
print(f"  Pass Rate: 68%")
print(f"  Avg Profit: $4,000")
print(f"  Your Share: $3,200")
print(f"  Net: $2,450")
print(f"  Expected Value: $1,426")
print(f"  Expected ROI: 190%")

print()
print('='*80)
print('💡 KEY INSIGHTS')
print('='*80)
print()

if len(passed) > 0:
    print('1. PASS RATE:')
    if len(passed) >= 68:
        print(f"   ✅ Maintained or improved ({len(passed)}%)")
    else:
        print(f"   ⚠️  Slightly lower ({len(passed)}% vs 68%)")
    print()
    
    print('2. PROFITABILITY:')
    if passed['profit'].mean() > 40:
        print(f"   ✅ Higher profits ({passed["profit"].mean():.1f}% vs 40%)")
    else:
        print(f"   ➡️  Similar profits ({passed["profit"].mean():.1f}% vs 40%)")
    print()
    
    print('3. BACKGROUND CONTRIBUTION:')
    bg_trades = passed['background_trades'].mean()
    if bg_trades > 0:
        print(f"   ✅ Background added {bg_trades:.1f} trades on average")
        print(f"   💰 Generates income while waiting for sniper setup")
    else:
        print(f"   ➡️  Most passes came from sniper only")
    print()

print('4. RECOMMENDATION:')
if len(passed) >= 68 and passed['background_trades'].mean() > 0:
    print('   ✅ USE DUAL STRATEGY')
    print('   Background trades add value without hurting pass rate')
elif len(passed) >= 65:
    print('   ✅ DUAL STRATEGY VIABLE')
    print('   Minimal impact on pass rate, background adds income')
else:
    print('   ⚠️  STICK WITH SNIPER-ONLY')
    print('   Background may interfere with prop firm evaluation')

print()
print('='*80)
print('✅ DUAL STRATEGY ANALYSIS COMPLETE')
print('='*80)

# Save results
results_df.to_csv('/workspace/dual_strategy_results.csv', index=False)
print()
print('Saved to: dual_strategy_results.csv')
