#!/usr/bin/env python3
"""
AGGRESSIVE PROP FIRM OPTIMIZER
Targeting Blueberry Funded and Instant Funding rules
Accepting 20% failure rate for maximum profit potential

BLUEBERRY FUNDED 2-Step:
- Phase 1: 10% profit, 5% daily DD, 10% max DD, 3 min days
- Phase 2: 5% profit, 5% daily DD, 10% max DD, 3 min days
- Funded: 1.5% risk per trade, 5% daily DD, 10% max DD

INSTANT FUNDING $10K:
- No target (but 5% to unlock payouts)
- 10% max DD (EOD trailing) → 5% after 5% profit
- 4% daily loss limit
- No consistency rule
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
print('🚀 AGGRESSIVE PROP FIRM OPTIMIZER')
print('='*80)
print()
print('Target Firms:')
print('  1. Blueberry Funded (2-Step Challenge)')
print('  2. Instant Funding ($10K Account)')
print()
print('Acceptance Criteria:')
print('  - 20% failure rate OK')
print('  - Maximize profit potential')
print('  - Must pass evaluation requirements')
print()

class AggressivePropFirmBacktester:
    """Aggressive backtester for prop firm evaluations"""
    
    def __init__(self, firm_type='blueberry', phase='phase1', capital=10000, 
                 max_risk_per_trade=0.05):
        self.firm_type = firm_type
        self.phase = phase
        self.capital = capital
        self.init_capital = capital
        self.max_risk_per_trade = max_risk_per_trade
        
        # Firm-specific rules
        if firm_type == 'blueberry':
            if phase == 'phase1':
                self.profit_target_pct = 10
                self.max_dd_pct = 10
                self.daily_dd_pct = 5
                self.min_days = 3
                self.min_daily_profit_pct = 0.5
            elif phase == 'phase2':
                self.profit_target_pct = 5
                self.max_dd_pct = 10
                self.daily_dd_pct = 5
                self.min_days = 3
                self.min_daily_profit_pct = 0.5
            else:  # funded
                self.profit_target_pct = None
                self.max_dd_pct = 10
                self.daily_dd_pct = 5
                self.min_days = 0
                self.min_daily_profit_pct = 0
                self.max_risk_per_trade = 0.015  # 1.5% rule
        
        elif firm_type == 'instant':
            self.profit_target_pct = 5  # To unlock payouts
            self.max_dd_pct = 10
            self.daily_dd_pct = 4
            self.min_days = 0
            self.min_daily_profit_pct = 0
            self.smart_drawdown = True  # Locks at 5% after 5% profit
        
        self.trades = []
        self.daily_results = {}
        self.peak = capital
        self.max_dd = 0
        self.current_daily_start = None
        self.daily_start_equity = capital
        
        self.failed = False
        self.fail_reason = None
        self.passed = False
        self.pass_reason = None
    
    def start_new_day(self, date):
        """Start a new trading day"""
        self.current_daily_start = date.date() if hasattr(date, 'date') else date
        self.daily_start_equity = max(self.capital, self.peak)
        
        if self.current_daily_start not in self.daily_results:
            self.daily_results[self.current_daily_start] = {
                'start_equity': self.daily_start_equity,
                'trades': 0,
                'profit': 0,
                'end_equity': self.capital
            }
    
    def check_daily_dd(self):
        """Check daily drawdown"""
        if self.current_daily_start is None:
            return False
        
        daily_loss = self.daily_start_equity - self.capital
        daily_loss_pct = (daily_loss / self.init_capital) * 100
        
        if daily_loss_pct >= self.daily_dd_pct:
            self.failed = True
            self.fail_reason = f'Daily DD {daily_loss_pct:.2f}% >= {self.daily_dd_pct}%'
            return True
        
        return False
    
    def check_max_dd(self):
        """Check max drawdown"""
        if self.capital > self.peak:
            self.peak = self.capital
        
        dd = (self.peak - self.capital) / self.init_capital * 100
        if dd > self.max_dd:
            self.max_dd = dd
        
        # For instant funding, check smart drawdown
        if self.firm_type == 'instant' and hasattr(self, 'smart_drawdown'):
            profit_pct = ((self.capital - self.init_capital) / self.init_capital) * 100
            
            if profit_pct >= 5:
                # Locked at 5%
                if dd >= 5:
                    self.failed = True
                    self.fail_reason = f'Max DD {dd:.2f}% >= 5% (locked)'
                    return True
            else:
                # Still at 10%
                if dd >= 10:
                    self.failed = True
                    self.fail_reason = f'Max DD {dd:.2f}% >= 10%'
                    return True
        else:
            if dd >= self.max_dd_pct:
                self.failed = True
                self.fail_reason = f'Max DD {dd:.2f}% >= {self.max_dd_pct}%'
                return True
        
        return False
    
    def check_passed(self):
        """Check if evaluation passed"""
        if self.profit_target_pct is None:
            return False
        
        profit_pct = ((self.capital - self.init_capital) / self.init_capital) * 100
        
        if profit_pct >= self.profit_target_pct:
            # Check minimum trading days
            qualifying_days = 0
            for day, result in self.daily_results.items():
                daily_profit_pct = (result['profit'] / self.init_capital) * 100
                if daily_profit_pct >= self.min_daily_profit_pct:
                    qualifying_days += 1
            
            if qualifying_days >= self.min_days:
                self.passed = True
                self.pass_reason = f'Target {profit_pct:.2f}% >= {self.profit_target_pct}% with {qualifying_days} qualifying days'
                return True
        
        return False
    
    def run(self, df, sigs):
        """Run aggressive backtest"""
        
        sig_dict = {}
        for _, sig in sigs.iterrows():
            sig_dict[sig['date']] = sig
        
        for idx, row in df.iterrows():
            current_date = row.name if isinstance(row.name, pd.Timestamp) else pd.Timestamp(row['date'])
            
            # Start new day
            self.start_new_day(current_date)
            
            # Check for signal
            if current_date in sig_dict:
                sig = sig_dict[current_date]
                
                risk_per_unit = abs(sig['entry_price'] - sig['stop_loss'])
                
                if risk_per_unit == 0 or risk_per_unit > sig['entry_price'] * 0.3:
                    continue
                
                # Aggressive position sizing
                risk_amt = self.capital * self.max_risk_per_trade
                size = risk_amt / risk_per_unit
                position_value = size * sig['entry_price']
                
                # Simulate outcome
                rr = abs(sig['take_profit'] - sig['entry_price']) / risk_per_unit
                win_prob = min(0.65, 0.40 + (0.06 * rr))
                
                if np.random.random() < win_prob:
                    pnl = abs(sig['take_profit'] - sig['entry_price']) * size
                    result = 'W'
                else:
                    pnl = -risk_per_unit * size
                    result = 'L'
                
                self.capital += pnl
                
                if self.capital <= 0:
                    self.failed = True
                    self.fail_reason = 'Account blown'
                    break
                
                # Update daily results
                day_key = self.current_daily_start
                self.daily_results[day_key]['trades'] += 1
                self.daily_results[day_key]['profit'] += pnl
                self.daily_results[day_key]['end_equity'] = self.capital
                
                self.trades.append({
                    'date': current_date,
                    'pnl': pnl,
                    'result': result,
                    'capital': self.capital
                })
                
                # Check violations
                if self.check_daily_dd():
                    break
                
                if self.check_max_dd():
                    break
                
                # Check if passed
                if self.check_passed():
                    break
        
        # Final metrics
        profit_pct = ((self.capital - self.init_capital) / self.init_capital) * 100
        wins = [t for t in self.trades if t['result'] == 'W']
        
        qualifying_days = 0
        for day, result in self.daily_results.items():
            daily_profit_pct = (result['profit'] / self.init_capital) * 100
            if daily_profit_pct >= self.min_daily_profit_pct:
                qualifying_days += 1
        
        return {
            'passed': self.passed,
            'failed': self.failed,
            'pass_reason': self.pass_reason,
            'fail_reason': self.fail_reason,
            'profit_pct': profit_pct,
            'final_capital': self.capital,
            'max_dd': self.max_dd,
            'trades': len(self.trades),
            'wr': len(wins) / len(self.trades) * 100 if self.trades else 0,
            'trading_days': len(self.daily_results),
            'qualifying_days': qualifying_days
        }

# Aggressive configurations to test
AGGRESSIVE_CONFIGS = []

# EMA strategies with varying aggressiveness
for fast in [3, 5, 7, 9]:
    for slow in [13, 21, 34]:
        for adx in [10, 15, 20]:
            for stop in [1.0, 1.5, 2.0]:
                for target in [3.0, 4.0, 5.0]:
                    for risk in [0.03, 0.05, 0.08, 0.10]:  # 3-10% risk per trade
                        AGGRESSIVE_CONFIGS.append({
                            'type': 'ema',
                            'ema_fast': fast,
                            'ema_slow': slow,
                            'adx': adx,
                            'stop': stop,
                            'target': target,
                            'risk': risk
                        })

print(f'Testing {len(AGGRESSIVE_CONFIGS)} aggressive configurations')
print()

PAIRS = ['AUDUSD=X', 'EURUSD=X', 'GBPUSD=X', 'USDJPY=X']
FIRMS = [
    ('blueberry', 'phase1'),
    ('instant', 'phase1')
]

def gen_sigs(df, cfg):
    """Generate signals"""
    df = df.copy()
    df['atr'] = TechnicalIndicators.atr(df)
    df['ema_f'] = TechnicalIndicators.ema(df, cfg['ema_fast'])
    df['ema_s'] = TechnicalIndicators.ema(df, cfg['ema_slow'])
    
    if cfg['adx'] > 0:
        adx, _, _ = TechnicalIndicators.adx(df)
        df['adx'] = adx
    
    sigs = []
    for i in range(50, len(df)):
        bar, prev = df.iloc[i], df.iloc[i-1]
        
        if cfg['adx'] > 0 and bar['adx'] < cfg['adx']:
            continue
        
        date = bar.name if isinstance(bar.name, pd.Timestamp) else pd.Timestamp(bar['date'])
        
        if bar['ema_f'] > bar['ema_s'] and prev['ema_f'] <= prev['ema_s']:
            sigs.append({
                'date': date,
                'entry_price': bar['close'],
                'stop_loss': bar['close'] - (bar['atr'] * cfg['stop']),
                'take_profit': bar['close'] + (bar['atr'] * cfg['target'])
            })
        elif bar['ema_f'] < bar['ema_s'] and prev['ema_f'] >= prev['ema_s']:
            sigs.append({
                'date': date,
                'entry_price': bar['close'],
                'stop_loss': bar['close'] + (bar['atr'] * cfg['stop']),
                'take_profit': bar['close'] - (bar['atr'] * cfg['target'])
            })
    
    return pd.DataFrame(sigs)

# Get data (use recent 90 days for speed)
end_date = datetime.now()
start_date = end_date - timedelta(days=90)

print('Loading data...')
data = {}
for pair in PAIRS:
    try:
        handler = DataHandler()
        df = handler.fetch_data(pair, start_date.strftime('%Y-%m-%d'), 
                               end_date.strftime('%Y-%m-%d'), '4h')
        if len(df) >= 50:
            data[pair] = df
            print(f'  ✓ {pair.replace("=X", "")}: {len(df)} bars')
    except Exception as e:
        print(f'  ✗ {pair.replace("=X", "")}: {e}')

print()
print('='*80)
print('Running aggressive optimization...')
print('='*80)
print()

results = []
best_blueberry = None
best_instant = None

total_tests = len(AGGRESSIVE_CONFIGS) * len(data) * len(FIRMS) * 5  # 5 simulations each
print(f'Total tests to run: {total_tests:,}')
print('This will take a while...')
print()

tested = 0
for cfg in AGGRESSIVE_CONFIGS:
    for pair, df in data.items():
        sigs = gen_sigs(df.copy(), cfg)
        
        if len(sigs) < 5:
            continue
        
        for firm_type, phase in FIRMS:
            # Run 5 simulations per config
            sim_results = []
            
            for sim in range(5):
                bt = AggressivePropFirmBacktester(
                    firm_type=firm_type,
                    phase=phase,
                    capital=10000,
                    max_risk_per_trade=cfg['risk']
                )
                
                m = bt.run(df.copy(), sigs)
                sim_results.append(m)
                
                tested += 1
                if tested % 1000 == 0:
                    print(f'  Progress: {tested:,}/{total_tests:,} ({tested/total_tests*100:.1f}%)')
            
            # Calculate stats
            passed_count = sum([1 for r in sim_results if r['passed']])
            failed_count = sum([1 for r in sim_results if r['failed']])
            pass_rate = passed_count / len(sim_results) * 100
            fail_rate = failed_count / len(sim_results) * 100
            
            avg_profit = np.mean([r['profit_pct'] for r in sim_results if r['passed']])
            avg_dd = np.mean([r['max_dd'] for r in sim_results])
            avg_trades = np.mean([r['trades'] for r in sim_results])
            
            result = {
                'firm': firm_type,
                'phase': phase,
                'pair': pair.replace('=X', ''),
                'config': cfg,
                'pass_rate': pass_rate,
                'fail_rate': fail_rate,
                'avg_profit': avg_profit if passed_count > 0 else 0,
                'avg_dd': avg_dd,
                'avg_trades': avg_trades,
                'passed': passed_count,
                'failed': failed_count
            }
            
            # Check if this is a winner (80% pass rate minimum)
            if pass_rate >= 80:
                results.append(result)
                
                if firm_type == 'blueberry':
                    if best_blueberry is None or result['avg_profit'] > best_blueberry['avg_profit']:
                        best_blueberry = result
                elif firm_type == 'instant':
                    if best_instant is None or result['avg_profit'] > best_instant['avg_profit']:
                        best_instant = result

print()
print('='*80)
print('🎯 AGGRESSIVE OPTIMIZATION COMPLETE')
print('='*80)
print()

print(f'Tested: {tested:,} simulations')
print(f'Winners (≥80% pass rate): {len(results)}')
print()

if best_blueberry:
    print('🏆 BEST BLUEBERRY FUNDED STRATEGY:')
    print(f"  Pair: {best_blueberry['pair']}")
    print(f"  Pass Rate: {best_blueberry['pass_rate']:.1f}%")
    print(f"  Avg Profit: {best_blueberry['avg_profit']:.2f}%")
    print(f"  Avg DD: {best_blueberry['avg_dd']:.2f}%")
    print(f"  Avg Trades: {best_blueberry['avg_trades']:.0f}")
    print(f"  Config: EMA {best_blueberry['config']['ema_fast']}/{best_blueberry['config']['ema_slow']}, "
          f"ADX {best_blueberry['config']['adx']}, "
          f"Stop {best_blueberry['config']['stop']}x, "
          f"Target {best_blueberry['config']['target']}x, "
          f"Risk {best_blueberry['config']['risk']*100}%")
    print()
    
    # Save
    with open('/workspace/best_blueberry_config.json', 'w') as f:
        json.dump(best_blueberry, f, indent=2, default=str)
else:
    print('⚠️  No Blueberry strategies found with ≥80% pass rate')
    print()

if best_instant:
    print('🏆 BEST INSTANT FUNDING STRATEGY:')
    print(f"  Pair: {best_instant['pair']}")
    print(f"  Pass Rate: {best_instant['pass_rate']:.1f}%")
    print(f"  Avg Profit: {best_instant['avg_profit']:.2f}%")
    print(f"  Avg DD: {best_instant['avg_dd']:.2f}%")
    print(f"  Avg Trades: {best_instant['avg_trades']:.0f}")
    print(f"  Config: EMA {best_instant['config']['ema_fast']}/{best_instant['config']['ema_slow']}, "
          f"ADX {best_instant['config']['adx']}, "
          f"Stop {best_instant['config']['stop']}x, "
          f"Target {best_instant['config']['target']}x, "
          f"Risk {best_instant['config']['risk']*100}%")
    print()
    
    # Save
    with open('/workspace/best_instant_config.json', 'w') as f:
        json.dump(best_instant, f, indent=2, default=str)
else:
    print('⚠️  No Instant Funding strategies found with ≥80% pass rate')
    print()

# Save all results
if results:
    results_df = pd.DataFrame(results)
    results_df.to_csv('/workspace/aggressive_propfirm_results.csv', index=False)
    print(f'✓ Saved {len(results)} winning strategies to: aggressive_propfirm_results.csv')

print()
print('✅ Optimization complete')
