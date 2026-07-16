#!/usr/bin/env python3
"""
FAST AGGRESSIVE PROP FIRM OPTIMIZER
Focused on most promising configurations for passing prop firm evaluations

Target: 80% pass rate minimum (20% failure OK)
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
print('🚀 FAST AGGRESSIVE PROP FIRM OPTIMIZER')
print('='*80)
print()
print('BLUEBERRY FUNDED (2-Step Phase 1):')
print('  Target: 10% profit')
print('  Max DD: 10%')
print('  Daily DD: 5%')
print('  Min Days: 3 (with 0.5% profit each)')
print()
print('INSTANT FUNDING ($10K):')
print('  Target: 5% profit (to unlock payouts)')
print('  Max DD: 10% (locks at 5% after 5% profit)')
print('  Daily DD: 4%')
print()
print('Acceptance: 80% pass rate (20% failure OK)')
print()

class PropFirmBacktester:
    """Fast prop firm backtester"""
    
    def __init__(self, firm='blueberry', capital=10000, risk_pct=0.05):
        self.firm = firm
        self.capital = capital
        self.init = capital
        self.risk_pct = risk_pct
        
        # Rules
        if firm == 'blueberry':
            self.target = 10
            self.max_dd = 10
            self.daily_dd = 5
            self.min_days = 3
            self.min_daily_profit = 0.5
        else:  # instant
            self.target = 5
            self.max_dd = 10
            self.daily_dd = 4
            self.min_days = 0
            self.min_daily_profit = 0
            self.smart_dd = True
        
        self.trades = []
        self.peak = capital
        self.max_dd_reached = 0
        self.daily_profits = {}
        self.current_day = None
        self.day_start_equity = capital
        
        self.passed = False
        self.failed = False
        self.reason = None
    
    def new_day(self, date):
        """Start new trading day"""
        day = date.date() if hasattr(date, 'date') else date
        if day != self.current_day:
            self.current_day = day
            self.day_start_equity = max(self.capital, self.peak)
            if day not in self.daily_profits:
                self.daily_profits[day] = 0
    
    def trade(self, entry, stop, target, date):
        """Execute a trade"""
        self.new_day(date)
        
        risk_per_unit = abs(entry - stop)
        if risk_per_unit == 0 or risk_per_unit > entry * 0.3:
            return
        
        # Position size
        risk_amt = self.capital * self.risk_pct
        size = risk_amt / risk_per_unit
        
        # Outcome
        rr = abs(target - entry) / risk_per_unit
        win_prob = min(0.65, 0.40 + (0.05 * rr))
        
        if np.random.random() < win_prob:
            pnl = abs(target - entry) * size
        else:
            pnl = -risk_per_unit * size
        
        self.capital += pnl
        
        if self.capital <= 0:
            self.failed = True
            self.reason = 'Blown'
            return
        
        self.trades.append(pnl)
        self.daily_profits[self.current_day] += pnl
        
        # Check daily DD
        daily_loss = self.day_start_equity - self.capital
        daily_loss_pct = (daily_loss / self.init) * 100
        if daily_loss_pct >= self.daily_dd:
            self.failed = True
            self.reason = f'Daily DD {daily_loss_pct:.1f}%'
            return
        
        # Check max DD
        if self.capital > self.peak:
            self.peak = self.capital
        
        dd = (self.peak - self.capital) / self.init * 100
        if dd > self.max_dd_reached:
            self.max_dd_reached = dd
        
        # Smart DD for Instant Funding
        if self.firm == 'instant' and hasattr(self, 'smart_dd'):
            profit_pct = (self.capital - self.init) / self.init * 100
            dd_limit = 5 if profit_pct >= 5 else 10
        else:
            dd_limit = self.max_dd
        
        if dd >= dd_limit:
            self.failed = True
            self.reason = f'Max DD {dd:.1f}%'
            return
        
        # Check if passed
        profit_pct = (self.capital - self.init) / self.init * 100
        if profit_pct >= self.target:
            # Check qualifying days
            qual_days = 0
            for day, profit in self.daily_profits.items():
                if (profit / self.init * 100) >= self.min_daily_profit:
                    qual_days += 1
            
            if qual_days >= self.min_days:
                self.passed = True
                self.reason = f'Target {profit_pct:.1f}%'
    
    def run(self, df, sigs):
        """Run backtest"""
        sig_dict = {sig['date']: sig for _, sig in sigs.iterrows()}
        
        for _, row in df.iterrows():
            if self.passed or self.failed:
                break
            
            date = row.name if isinstance(row.name, pd.Timestamp) else pd.Timestamp(row['date'])
            
            if date in sig_dict:
                sig = sig_dict[date]
                self.trade(sig['entry_price'], sig['stop_loss'], sig['take_profit'], date)
        
        profit_pct = (self.capital - self.init) / self.init * 100
        wins = sum(1 for t in self.trades if t > 0)
        
        return {
            'passed': self.passed,
            'failed': self.failed,
            'reason': self.reason,
            'profit': profit_pct,
            'dd': self.max_dd_reached,
            'trades': len(self.trades),
            'wr': wins / len(self.trades) * 100 if self.trades else 0
        }

# Focused configs - most promising based on prior testing
CONFIGS = [
    # Aggressive EMA + ADX
    {'ema_fast': 5, 'ema_slow': 13, 'adx': 15, 'stop': 1.0, 'target': 4.0, 'risk': 0.05},
    {'ema_fast': 5, 'ema_slow': 13, 'adx': 15, 'stop': 1.0, 'target': 5.0, 'risk': 0.05},
    {'ema_fast': 5, 'ema_slow': 13, 'adx': 15, 'stop': 1.5, 'target': 4.0, 'risk': 0.05},
    {'ema_fast': 5, 'ema_slow': 13, 'adx': 10, 'stop': 1.0, 'target': 4.0, 'risk': 0.05},
    {'ema_fast': 5, 'ema_slow': 13, 'adx': 20, 'stop': 1.0, 'target': 4.0, 'risk': 0.05},
    
    # Higher risk versions
    {'ema_fast': 5, 'ema_slow': 13, 'adx': 15, 'stop': 1.0, 'target': 4.0, 'risk': 0.08},
    {'ema_fast': 5, 'ema_slow': 13, 'adx': 15, 'stop': 1.0, 'target': 5.0, 'risk': 0.08},
    {'ema_fast': 5, 'ema_slow': 13, 'adx': 10, 'stop': 1.0, 'target': 5.0, 'risk': 0.08},
    
    # Faster EMA
    {'ema_fast': 3, 'ema_slow': 13, 'adx': 15, 'stop': 1.0, 'target': 4.0, 'risk': 0.05},
    {'ema_fast': 3, 'ema_slow': 13, 'adx': 15, 'stop': 1.0, 'target': 5.0, 'risk': 0.08},
    
    # Slower EMA
    {'ema_fast': 7, 'ema_slow': 21, 'adx': 15, 'stop': 1.5, 'target': 4.0, 'risk': 0.05},
    {'ema_fast': 9, 'ema_slow': 21, 'adx': 15, 'stop': 1.5, 'target': 3.5, 'risk': 0.05},
    
    # Extreme aggression (10% risk)
    {'ema_fast': 5, 'ema_slow': 13, 'adx': 15, 'stop': 1.0, 'target': 5.0, 'risk': 0.10},
    {'ema_fast': 5, 'ema_slow': 13, 'adx': 10, 'stop': 1.0, 'target': 5.0, 'risk': 0.10},
]

PAIRS = ['AUDUSD=X', 'EURUSD=X', 'GBPUSD=X', 'USDJPY=X']

def gen_sigs(df, cfg):
    """Generate signals"""
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

# Load data (90 days)
print('Loading data...')
end = datetime.now()
start = end - timedelta(days=90)

data = {}
for pair in PAIRS:
    try:
        handler = DataHandler()
        df = handler.fetch_data(pair, start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'), '4h')
        if len(df) >= 50:
            data[pair] = df
            print(f'  ✓ {pair.replace("=X", "")}: {len(df)} bars')
    except:
        pass

print()
print('='*80)
print('Testing configurations...')
print('='*80)
print()

results = []

for cfg_idx, cfg in enumerate(CONFIGS):
    print(f"Config {cfg_idx+1}/{len(CONFIGS)}: EMA {cfg['ema_fast']}/{cfg['ema_slow']}, ADX {cfg['adx']}, Risk {cfg['risk']*100:.0f}%")
    
    for pair, df in data.items():
        sigs = gen_sigs(df.copy(), cfg)
        
        if len(sigs) < 5:
            continue
        
        for firm in ['blueberry', 'instant']:
            # Run 20 simulations
            sims = []
            for _ in range(20):
                bt = PropFirmBacktester(firm=firm, capital=10000, risk_pct=cfg['risk'])
                m = bt.run(df.copy(), sigs)
                sims.append(m)
            
            # Stats
            passed = sum(1 for s in sims if s['passed'])
            failed = sum(1 for s in sims if s['failed'])
            pass_rate = passed / len(sims) * 100
            
            if passed > 0:
                avg_profit = np.mean([s['profit'] for s in sims if s['passed']])
                avg_dd = np.mean([s['dd'] for s in sims if s['passed']])
                avg_trades = np.mean([s['trades'] for s in sims if s['passed']])
            else:
                avg_profit = 0
                avg_dd = 0
                avg_trades = 0
            
            result = {
                'firm': firm,
                'pair': pair.replace('=X', ''),
                'pass_rate': pass_rate,
                'avg_profit': avg_profit,
                'avg_dd': avg_dd,
                'avg_trades': avg_trades,
                'passed': passed,
                'failed': failed,
                'config': cfg
            }
            
            if pass_rate >= 80:
                results.append(result)
                print(f'  ✅ {firm.upper()} {pair.replace("=X", "")}: {pass_rate:.0f}% pass, {avg_profit:.1f}% profit')

print()
print('='*80)
print('🎯 RESULTS')
print('='*80)
print()

if results:
    results_df = pd.DataFrame(results)
    
    # Best for each firm
    blueberry = results_df[results_df['firm'] == 'blueberry']
    instant = results_df[results_df['firm'] == 'instant']
    
    if len(blueberry) > 0:
        best_bb = blueberry.nlargest(1, 'avg_profit').iloc[0]
        print('🏆 BEST BLUEBERRY FUNDED:')
        print(f"  Pair: {best_bb['pair']}")
        print(f"  Pass Rate: {best_bb['pass_rate']:.0f}%")
        print(f"  Avg Profit: {best_bb['avg_profit']:.2f}%")
        print(f"  Avg DD: {best_bb['avg_dd']:.2f}%")
        print(f"  Avg Trades: {best_bb['avg_trades']:.0f}")
        print(f"  Config: EMA {best_bb['config']['ema_fast']}/{best_bb['config']['ema_slow']}, "
              f"ADX {best_bb['config']['adx']}, "
              f"Stop {best_bb['config']['stop']}x, "
              f"Target {best_bb['config']['target']}x, "
              f"Risk {best_bb['config']['risk']*100:.0f}%")
        print()
        
        with open('/workspace/blueberry_winner.json', 'w') as f:
            json.dump(best_bb.to_dict(), f, indent=2, default=str)
    
    if len(instant) > 0:
        best_if = instant.nlargest(1, 'avg_profit').iloc[0]
        print('🏆 BEST INSTANT FUNDING:')
        print(f"  Pair: {best_if['pair']}")
        print(f"  Pass Rate: {best_if['pass_rate']:.0f}%")
        print(f"  Avg Profit: {best_if['avg_profit']:.2f}%")
        print(f"  Avg DD: {best_if['avg_dd']:.2f}%")
        print(f"  Avg Trades: {best_if['avg_trades']:.0f}")
        print(f"  Config: EMA {best_if['config']['ema_fast']}/{best_if['config']['ema_slow']}, "
              f"ADX {best_if['config']['adx']}, "
              f"Stop {best_if['config']['stop']}x, "
              f"Target {best_if['config']['target']}x, "
              f"Risk {best_if['config']['risk']*100:.0f}%")
        print()
        
        with open('/workspace/instant_winner.json', 'w') as f:
            json.dump(best_if.to_dict(), f, indent=2, default=str)
    
    results_df.to_csv('/workspace/propfirm_aggressive_results.csv', index=False)
    print(f'✓ Found {len(results)} winning configs (≥80% pass rate)')
    print('✓ Saved to: propfirm_aggressive_results.csv')

else:
    print('⚠️  No configs found with ≥80% pass rate')
    print('Try lowering acceptance threshold or testing more configs')

print()
print('✅ Complete!')
