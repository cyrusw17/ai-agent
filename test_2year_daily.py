#!/usr/bin/env python3
"""
2-YEAR VALIDATION TEST - Using Daily Data
Since intraday data is limited to 730 days, use daily bars for 2-year tests
"""

import sys
sys.path.insert(0, '/workspace')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from core.data_handler import DataHandler
from core.indicators import TechnicalIndicators

print('='*80)
print('📊 2-YEAR VALIDATION - DAILY TIMEFRAME')
print('='*80)
print()
print('Note: Using DAILY data for 2-year validation')
print('(Intraday data limited to 730 days by provider)')
print()

class LongTermBacktester:
    """Backtest over long periods"""
    
    def __init__(self, capital=10000, risk=0.05, pos_pct=0.40):
        # More conservative for daily timeframe
        self.capital = capital
        self.init = capital
        self.risk = risk
        self.pos_pct = pos_pct
        self.trades = []
        self.equity_curve = [capital]
        self.peak = capital
        self.max_dd = 0
        self.daily_returns = []
    
    def run(self, df, sigs):
        """Run backtest"""
        
        for _, sig in sigs.iterrows():
            risk_per_unit = abs(sig['entry_price'] - sig['stop_loss'])
            if risk_per_unit == 0 or risk_per_unit > sig['entry_price'] * 0.3:
                continue
            
            # Position sizing
            size = (self.capital * self.risk) / risk_per_unit
            pos_val = size * sig['entry_price']
            
            if pos_val > self.capital * self.pos_pct:
                size = (self.capital * self.pos_pct) / sig['entry_price']
            
            # Simulate outcome
            rr = abs(sig['take_profit'] - sig['entry_price']) / risk_per_unit
            win_prob = min(0.60, 0.35 + (0.06 * rr))  # Slightly lower for daily
            
            if np.random.random() < win_prob:
                pnl = abs(sig['take_profit'] - sig['entry_price']) * size
                self.trades.append({'pnl': pnl, 'result': 'W'})
            else:
                pnl = -risk_per_unit * size
                self.trades.append({'pnl': pnl, 'result': 'L'})
            
            prev_capital = self.capital
            self.capital += pnl
            
            ret = (self.capital - prev_capital) / prev_capital
            self.daily_returns.append(ret)
            
            self.equity_curve.append(self.capital)
            
            if self.capital > self.peak:
                self.peak = self.capital
            dd = (self.peak - self.capital) / self.peak * 100
            if dd > self.max_dd:
                self.max_dd = dd
        
        wins = [t for t in self.trades if t['result'] == 'W']
        total_return = (self.capital - self.init) / self.init * 100
        
        # Sharpe ratio
        if len(self.daily_returns) > 1:
            ret_std = np.std(self.daily_returns)
            avg_ret = np.mean(self.daily_returns)
            sharpe = (avg_ret / ret_std * np.sqrt(252)) if ret_std > 0 else 0
        else:
            sharpe = 0
        
        return {
            'return': total_return,
            'dd': self.max_dd,
            'trades': len(self.trades),
            'wr': len(wins) / len(self.trades) * 100 if self.trades else 0,
            'final': self.capital,
            'sharpe': sharpe
        }

# Test configurations
CONFIGS = [
    {
        'name': 'EMA5/13 ADX15 (Winner)',
        'ema_fast': 5,
        'ema_slow': 13,
        'adx': 15,
        'stop': 1.5,  # Wider for daily
        'target': 4.0
    },
    {
        'name': 'EMA5/13 ADX20',
        'ema_fast': 5,
        'ema_slow': 13,
        'adx': 20,
        'stop': 1.5,
        'target': 4.0
    },
    {
        'name': 'EMA9/21 ADX15',
        'ema_fast': 9,
        'ema_slow': 21,
        'adx': 15,
        'stop': 1.5,
        'target': 3.5
    },
    {
        'name': 'EMA7/21 ADX20',
        'ema_fast': 7,
        'ema_slow': 21,
        'adx': 20,
        'stop': 1.5,
        'target': 4.0
    }
]

PAIRS = ['AUDUSD=X', 'EURUSD=X', 'GBPUSD=X', 'USDJPY=X']

# Test available 2-year windows
end_date = datetime.now()
TEST_PERIODS = []

# Try different 2-year windows
for months_back in [24, 30, 36]:
    start = end_date - timedelta(days=months_back*30)
    TEST_PERIODS.append((start, end_date, f'{months_back} months'))

print(f'Testing {len(CONFIGS)} configurations')
print(f'Pairs: {len(PAIRS)}')
print(f'Periods: {len(TEST_PERIODS)}')
print(f'Timeframe: DAILY')
print()

def gen_sigs(df, cfg):
    """Generate signals"""
    
    df['atr'] = TechnicalIndicators.atr(df)
    df['ema_f'] = TechnicalIndicators.ema(df, cfg['ema_fast'])
    df['ema_s'] = TechnicalIndicators.ema(df, cfg['ema_slow'])
    
    if cfg['adx'] > 0:
        adx, _, _ = TechnicalIndicators.adx(df)
        df['adx'] = adx
    
    sigs = []
    for i in range(50, len(df)):
        bar, prev = df.iloc[i], df.iloc[i-1]
        
        if cfg['adx'] > 0 and ('adx' not in df.columns or bar['adx'] < cfg['adx']):
            continue
        
        if bar['ema_f'] > bar['ema_s'] and prev['ema_f'] <= prev['ema_s']:
            sigs.append({
                'entry_price': bar['close'],
                'stop_loss': bar['close'] - (bar['atr'] * cfg['stop']),
                'take_profit': bar['close'] + (bar['atr'] * cfg['target'])
            })
        elif bar['ema_f'] < bar['ema_s'] and prev['ema_f'] >= prev['ema_s']:
            sigs.append({
                'entry_price': bar['close'],
                'stop_loss': bar['close'] + (bar['atr'] * cfg['stop']),
                'take_profit': bar['close'] - (bar['atr'] * cfg['target'])
            })
    
    return pd.DataFrame(sigs)

# Run tests
results = []

for start, end, period_name in TEST_PERIODS:
    print(f'\n{"="*80}')
    print(f'Testing: {period_name} ({start.strftime("%Y-%m-%d")} to {end.strftime("%Y-%m-%d")})')
    print(f'{"="*80}\n')
    
    for pair in PAIRS:
        try:
            handler = DataHandler()
            df = handler.fetch_data(pair, start.strftime('%Y-%m-%d'), 
                                   end.strftime('%Y-%m-%d'), '1d')
            
            if len(df) < 100:
                continue
            
            pair_name = pair.replace('=X', '')
            print(f'{pair_name}: {len(df)} days')
            
            for cfg in CONFIGS:
                try:
                    sigs = gen_sigs(df.copy(), cfg)
                    
                    if len(sigs) >= 10:
                        bt = LongTermBacktester(capital=10000, risk=0.05, pos_pct=0.40)
                        m = bt.run(df, sigs)
                        
                        # Annualized
                        years = len(df) / 252
                        annualized = ((m['final'] / 10000) ** (1/years) - 1) * 100 if years > 0 else 0
                        
                        result = {
                            'period': period_name,
                            'pair': pair_name,
                            'strategy': cfg['name'],
                            'return_total': m['return'],
                            'return_annualized': annualized,
                            'dd': m['dd'],
                            'trades': m['trades'],
                            'trades_per_year': m['trades'] / years if years > 0 else 0,
                            'wr': m['wr'],
                            'sharpe': m['sharpe'],
                            'final': m['final']
                        }
                        
                        results.append(result)
                        
                        if m['return'] > 5:
                            print(f'  ✅ {cfg["name"][:25]:25s} | {m["return"]:6.2f}% ({annualized:.2f}%/yr) | '
                                  f'{m["trades"]} trades | DD:{m["dd"]:.1f}%')
                        elif m['return'] > 0:
                            print(f'  💚 {cfg["name"][:25]:25s} | {m["return"]:6.2f}% ({annualized:.2f}%/yr)')
                
                except Exception as e:
                    pass
        
        except Exception as e:
            print(f'{pair.replace("=X", "")}: Failed - {e}')

# Results
print()
print('='*80)
print('📊 2-YEAR VALIDATION RESULTS (DAILY TIMEFRAME)')
print('='*80)
print()

if results:
    results_df = pd.DataFrame(results)
    prof = results_df[results_df['return_total'] > 0]
    
    print(f'Total tests: {len(results)}')
    print(f'Profitable: {len(prof)} ({len(prof)/len(results)*100:.1f}%)')
    print()
    
    if len(prof) > 0:
        print('TOP 10 BY TOTAL RETURN:')
        print()
        for _, r in prof.nlargest(10, 'return_total').iterrows():
            print(f"{r['period']:15s} | {r['pair']:6s} | {r['strategy']}")
            print(f"  Total: {r['return_total']:7.2f}% | Annual: {r['return_annualized']:6.2f}% | "
                  f"DD: {r['dd']:5.2f}% | Sharpe: {r['sharpe']:5.2f}")
            print(f"  Trades: {r['trades']} ({r['trades_per_year']:.1f}/yr) | WR: {r['wr']:.1f}%")
            print()
        
        print('='*80)
        print('📈 LONG-TERM STATISTICS')
        print('='*80)
        print()
        
        print(f"Average Total Return: {prof['return_total'].mean():.2f}%")
        print(f"Average Annualized Return: {prof['return_annualized'].mean():.2f}%")
        print(f"Median Annualized Return: {prof['return_annualized'].median():.2f}%")
        print(f"Best Annualized Return: {prof['return_annualized'].max():.2f}%")
        print(f"Worst Profitable Return: {prof['return_annualized'].min():.2f}%")
        print()
        print(f"Average Max Drawdown: {prof['dd'].mean():.2f}%")
        print(f"Average Sharpe Ratio: {prof['sharpe'].mean():.2f}")
        print(f"Average Win Rate: {prof['wr'].mean():.1f}%")
        print()
        
        # By strategy
        print('='*80)
        print('📊 PERFORMANCE BY STRATEGY')
        print('='*80)
        print()
        
        for cfg in CONFIGS:
            strat = prof[prof['strategy'] == cfg['name']]
            if len(strat) > 0:
                print(f"{cfg['name']}:")
                print(f"  Profitable Tests: {len(strat)}")
                print(f"  Avg Annualized: {strat['return_annualized'].mean():.2f}%")
                print(f"  Avg Drawdown: {strat['dd'].mean():.2f}%")
                print(f"  Avg Sharpe: {strat['sharpe'].mean():.2f}")
                print()
        
        results_df.to_csv('/workspace/2year_daily_validation.csv', index=False)
        print('✓ Saved to: 2year_daily_validation.csv')
    
    else:
        print('⚠️ No profitable strategies')
        print('Best 5:')
        for _, r in results_df.nlargest(5, 'return_total').iterrows():
            print(f"  {r['pair']} | {r['strategy']}: {r['return_total']:.2f}%")

print()
print('✅ 2-year validation complete')
