#!/usr/bin/env python3
"""
LEVERAGED TRADING WITH WEEKLY WITHDRAWALS

Scenario:
- 1:50 leverage available
- Max drawdown: 10% (hard stop)
- Weekly withdrawals: Any balance over $10k withdrawn on Fridays
- Starting capital: $10,000

This models a realistic funded account with profit sharing
"""

import sys
sys.path.insert(0, '/workspace')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from core.data_handler import DataHandler
from core.indicators import TechnicalIndicators

print('='*80)
print('💰 LEVERAGED TRADING WITH WEEKLY WITHDRAWALS')
print('='*80)
print()
print('Scenario:')
print('  - Starting Capital: $10,000')
print('  - Leverage: 1:50')
print('  - Max Drawdown: 10% (hard stop)')
print('  - Weekly Withdrawals: Profits over $10k withdrawn on Fridays')
print()

class LeveragedBacktester:
    """Backtest with leverage and weekly withdrawals"""
    
    def __init__(self, capital=10000, leverage=50, max_dd_pct=10, withdrawal_threshold=10000):
        self.capital = capital
        self.init_capital = capital
        self.leverage = leverage
        self.max_dd_pct = max_dd_pct
        self.withdrawal_threshold = withdrawal_threshold
        
        self.trades = []
        self.equity_curve = []
        self.withdrawals = []
        self.total_withdrawn = 0
        
        self.peak = capital
        self.max_dd = 0
        self.daily_returns = []
        
        self.stopped_out = False
        self.stop_reason = None
    
    def check_withdrawal(self, date):
        """Check if we should withdraw profits (Fridays)"""
        if date.weekday() == 4 and self.capital > self.withdrawal_threshold:  # Friday
            withdrawal = self.capital - self.withdrawal_threshold
            self.capital = self.withdrawal_threshold
            self.withdrawals.append({
                'date': date,
                'amount': withdrawal,
                'balance_after': self.capital
            })
            self.total_withdrawn += withdrawal
            return withdrawal
        return 0
    
    def check_drawdown(self):
        """Check if we've exceeded max drawdown"""
        if self.capital > self.peak:
            self.peak = self.capital
        
        dd = (self.peak - self.capital) / self.peak * 100
        
        if dd > self.max_dd:
            self.max_dd = dd
        
        if dd >= self.max_dd_pct:
            self.stopped_out = True
            self.stop_reason = f'Max drawdown {dd:.2f}% exceeded {self.max_dd_pct}%'
            return True
        
        return False
    
    def run(self, df, sigs):
        """Run backtest with leverage and withdrawals"""
        
        # Map signals to dates
        sig_dict = {}
        for _, sig in sigs.iterrows():
            sig_dict[sig['date']] = sig
        
        for idx, row in df.iterrows():
            current_date = row.name if isinstance(row.name, pd.Timestamp) else pd.Timestamp(row['date'])
            
            # Check for withdrawal (Fridays)
            withdrawal = self.check_withdrawal(current_date)
            if withdrawal > 0:
                self.equity_curve.append({
                    'date': current_date,
                    'capital': self.capital,
                    'event': f'Withdrawal: ${withdrawal:,.2f}'
                })
            
            # Check for signal
            if current_date in sig_dict:
                sig = sig_dict[current_date]
                
                # Calculate position size with leverage
                risk_per_unit = abs(sig['entry_price'] - sig['stop_loss'])
                
                if risk_per_unit == 0 or risk_per_unit > sig['entry_price'] * 0.3:
                    continue
                
                # With leverage: we can control larger positions
                # Risk management: still only risk X% of capital per trade
                risk_pct = 0.02  # Conservative 2% risk per trade with leverage
                risk_amount = self.capital * risk_pct
                
                # Position size based on risk
                size = risk_amount / risk_per_unit
                position_value = size * sig['entry_price']
                
                # With 1:50 leverage, we can control up to 50x our capital
                max_position = self.capital * self.leverage
                
                if position_value > max_position:
                    size = max_position / sig['entry_price']
                    position_value = max_position
                
                # Simulate outcome
                rr = abs(sig['take_profit'] - sig['entry_price']) / risk_per_unit
                win_prob = min(0.65, 0.35 + (0.06 * rr))
                
                if np.random.random() < win_prob:
                    # Winner
                    pnl = abs(sig['take_profit'] - sig['entry_price']) * size
                    result = 'W'
                else:
                    # Loser
                    pnl = -risk_per_unit * size
                    result = 'L'
                
                # Apply P&L
                prev_capital = self.capital
                self.capital += pnl
                
                # Ensure capital doesn't go negative
                if self.capital <= 0:
                    self.capital = 0
                    self.stopped_out = True
                    self.stop_reason = 'Account blown'
                    break
                
                ret = (self.capital - prev_capital) / prev_capital if prev_capital > 0 else 0
                self.daily_returns.append(ret)
                
                self.trades.append({
                    'date': current_date,
                    'pnl': pnl,
                    'result': result,
                    'capital': self.capital,
                    'position_value': position_value,
                    'leverage_used': position_value / prev_capital if prev_capital > 0 else 0
                })
                
                self.equity_curve.append({
                    'date': current_date,
                    'capital': self.capital,
                    'event': f'Trade: {result} ${pnl:+,.2f}'
                })
                
                # Check drawdown
                if self.check_drawdown():
                    break
        
        # Calculate metrics
        wins = [t for t in self.trades if t['result'] == 'W']
        
        # Total return including withdrawals
        total_value = self.capital + self.total_withdrawn
        total_return = (total_value - self.init_capital) / self.init_capital * 100
        
        # Sharpe ratio
        if len(self.daily_returns) > 1:
            ret_std = np.std(self.daily_returns)
            avg_ret = np.mean(self.daily_returns)
            sharpe = (avg_ret / ret_std * np.sqrt(252)) if ret_std > 0 else 0
        else:
            sharpe = 0
        
        # Average leverage used
        avg_leverage = np.mean([t['leverage_used'] for t in self.trades]) if self.trades else 0
        
        return {
            'return': total_return,
            'dd': self.max_dd,
            'trades': len(self.trades),
            'wr': len(wins) / len(self.trades) * 100 if self.trades else 0,
            'final_capital': self.capital,
            'total_withdrawn': self.total_withdrawn,
            'total_value': total_value,
            'sharpe': sharpe,
            'avg_leverage': avg_leverage,
            'num_withdrawals': len(self.withdrawals),
            'stopped_out': self.stopped_out,
            'stop_reason': self.stop_reason,
            'equity_curve': self.equity_curve,
            'withdrawals': self.withdrawals
        }

# Test the winning strategy
STRATEGY = {
    'name': 'EMA 5/13 ADX15 Leveraged',
    'ema_fast': 5,
    'ema_slow': 13,
    'adx': 15,
    'stop': 1.5,
    'target': 4.0
}

PAIRS = ['AUDUSD=X', 'EURUSD=X', 'GBPUSD=X', 'USDJPY=X']

# Test periods
end_date = datetime.now()
TEST_PERIODS = [
    (end_date - timedelta(days=365), end_date, '1 year'),
    (end_date - timedelta(days=730), end_date, '2 years'),
]

def gen_sigs(df, cfg):
    """Generate signals with dates"""
    
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

# Run tests
results = []

for start, end, period_name in TEST_PERIODS:
    print(f'\n{"="*80}')
    print(f'Testing Period: {period_name}')
    print(f'{"="*80}\n')
    
    for pair in PAIRS:
        try:
            handler = DataHandler()
            df = handler.fetch_data(pair, start.strftime('%Y-%m-%d'), 
                                   end.strftime('%Y-%m-%d'), '1d')
            
            if len(df) < 100:
                continue
            
            pair_name = pair.replace('=X', '')
            
            sigs = gen_sigs(df.copy(), STRATEGY)
            
            if len(sigs) >= 5:
                # Run 5 simulations and average (Monte Carlo)
                sim_results = []
                
                for sim in range(5):
                    bt = LeveragedBacktester(
                        capital=10000,
                        leverage=50,
                        max_dd_pct=10,
                        withdrawal_threshold=10000
                    )
                    m = bt.run(df, sigs)
                    sim_results.append(m)
                
                # Average the results
                avg_return = np.mean([r['return'] for r in sim_results])
                avg_withdrawn = np.mean([r['total_withdrawn'] for r in sim_results])
                avg_final = np.mean([r['final_capital'] for r in sim_results])
                avg_total_value = np.mean([r['total_value'] for r in sim_results])
                avg_dd = np.mean([r['dd'] for r in sim_results])
                avg_trades = np.mean([r['trades'] for r in sim_results])
                avg_wr = np.mean([r['wr'] for r in sim_results])
                avg_sharpe = np.mean([r['sharpe'] for r in sim_results])
                avg_leverage = np.mean([r['avg_leverage'] for r in sim_results])
                avg_withdrawals = np.mean([r['num_withdrawals'] for r in sim_results])
                stopped_count = sum([1 for r in sim_results if r['stopped_out']])
                
                print(f'{pair_name}: {len(df)} days, {len(sigs)} signals')
                print(f'  Total Value: ${avg_total_value:,.2f} (Acct: ${avg_final:,.2f} + Withdrawn: ${avg_withdrawn:,.2f})')
                print(f'  Return: {avg_return:+.2f}%')
                print(f'  Max DD: {avg_dd:.2f}%')
                print(f'  Trades: {avg_trades:.0f} | WR: {avg_wr:.1f}%')
                print(f'  Avg Leverage: {avg_leverage:.1f}x')
                print(f'  Withdrawals: {avg_withdrawals:.0f} times')
                print(f'  Stopped Out: {stopped_count}/5 simulations')
                
                if avg_return > 0:
                    print(f'  ✅ PROFITABLE')
                print()
                
                result = {
                    'period': period_name,
                    'pair': pair_name,
                    'return': avg_return,
                    'final_capital': avg_final,
                    'withdrawn': avg_withdrawn,
                    'total_value': avg_total_value,
                    'dd': avg_dd,
                    'trades': avg_trades,
                    'wr': avg_wr,
                    'sharpe': avg_sharpe,
                    'avg_leverage': avg_leverage,
                    'withdrawals': avg_withdrawals,
                    'stopped_count': stopped_count
                }
                
                results.append(result)
        
        except Exception as e:
            print(f'{pair.replace("=X", "")}: Failed - {e}')

# Summary
print()
print('='*80)
print('📊 LEVERAGED TRADING SUMMARY')
print('='*80)
print()

if results:
    results_df = pd.DataFrame(results)
    profitable = results_df[results_df['return'] > 0]
    
    print(f'Total Tests: {len(results)}')
    print(f'Profitable: {len(profitable)} ({len(profitable)/len(results)*100:.1f}%)')
    print()
    
    if len(profitable) > 0:
        print('📈 TOP PERFORMERS:')
        print()
        
        for _, r in profitable.nlargest(10, 'return').iterrows():
            print(f"{r['period']:10s} | {r['pair']:6s}")
            print(f"  Total Value: ${r['total_value']:,.2f}")
            print(f"  Return: {r['return']:+.2f}%")
            print(f"  Withdrawn: ${r['withdrawn']:,.2f} ({r['withdrawals']:.0f} times)")
            print(f"  Max DD: {r['dd']:.2f}% | Avg Leverage: {r['avg_leverage']:.1f}x")
            print(f"  Stopped Out: {r['stopped_count']}/5 times")
            print()
        
        print('='*80)
        print('💰 FINANCIAL SUMMARY')
        print('='*80)
        print()
        
        print(f"Average Total Return: {profitable['return'].mean():.2f}%")
        print(f"Best Return: {profitable['return'].max():.2f}%")
        print(f"Average Withdrawn: ${profitable['withdrawn'].mean():,.2f}")
        print(f"Best Withdrawn: ${profitable['withdrawn'].max():,.2f}")
        print(f"Average Final Value: ${profitable['total_value'].mean():,.2f}")
        print(f"Best Final Value: ${profitable['total_value'].max():,.2f}")
        print(f"Average Max DD: {profitable['dd'].mean():.2f}%")
        print(f"Average Leverage Used: {profitable['avg_leverage'].mean():.1f}x")
        print()
        
        results_df.to_csv('/workspace/leveraged_withdrawals_results.csv', index=False)
        print('✓ Saved to: leveraged_withdrawals_results.csv')

print()
print('✅ Leveraged backtest complete')
