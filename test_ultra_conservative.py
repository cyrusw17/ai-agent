#!/usr/bin/env python3
"""
ULTRA-CONSERVATIVE LEVERAGED TRADING
Max loss per trade: 1.5% ($150 on $10k)
Max total drawdown: 1.5% (from peak)

This is MUCH more conservative than previous tests
"""

import sys
sys.path.insert(0, '/workspace')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from core.data_handler import DataHandler
from core.indicators import TechnicalIndicators

print('='*80)
print('🛡️ ULTRA-CONSERVATIVE LEVERAGED TRADING')
print('='*80)
print()

class UltraConservativeBacktester:
    """Backtest with strict 1.5% limits"""
    
    def __init__(self, capital=10000, leverage=50, max_loss_per_trade_pct=0.015, 
                 max_dd_pct=0.015, withdrawal_threshold=10000):
        self.capital = capital
        self.init_capital = capital
        self.leverage = leverage
        self.max_loss_per_trade = capital * max_loss_per_trade_pct  # $150 on $10k
        self.max_dd_pct = max_dd_pct  # 1.5%
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
        self.trades_rejected = 0
    
    def get_current_dd(self):
        """Get current drawdown percentage"""
        if self.capital > self.peak:
            self.peak = self.capital
        return (self.peak - self.capital) / self.peak * 100 if self.peak > 0 else 0
    
    def can_take_trade(self, potential_loss):
        """Check if trade would violate limits"""
        # Check if loss exceeds per-trade limit
        if potential_loss > self.max_loss_per_trade:
            return False, "Exceeds max loss per trade"
        
        # Check if loss would exceed drawdown limit
        current_dd_pct = self.get_current_dd()
        capital_after_loss = self.capital - potential_loss
        dd_after_loss = (self.peak - capital_after_loss) / self.peak * 100
        
        if dd_after_loss > self.max_dd_pct * 100:
            return False, f"Would cause {dd_after_loss:.2f}% DD (limit {self.max_dd_pct*100}%)"
        
        return True, "OK"
    
    def get_max_position_size(self, entry_price, stop_loss):
        """Calculate maximum position size within limits"""
        risk_per_unit = abs(entry_price - stop_loss)
        
        if risk_per_unit == 0:
            return 0
        
        # Max size based on per-trade loss limit
        max_size_by_loss = self.max_loss_per_trade / risk_per_unit
        
        # Max size based on drawdown limit
        current_dd_pct = self.get_current_dd()
        remaining_dd = (self.max_dd_pct * 100) - current_dd_pct
        max_loss_allowed = (remaining_dd / 100) * self.peak
        max_size_by_dd = max_loss_allowed / risk_per_unit if max_loss_allowed > 0 else 0
        
        # Take the minimum
        max_size = min(max_size_by_loss, max_size_by_dd)
        
        # Also respect leverage limit
        max_position_value = self.capital * self.leverage
        max_size_by_leverage = max_position_value / entry_price
        
        return min(max_size, max_size_by_leverage)
    
    def check_withdrawal(self, date):
        """Check if we should withdraw profits (Fridays)"""
        if date.weekday() == 4 and self.capital > self.withdrawal_threshold:
            withdrawal = self.capital - self.withdrawal_threshold
            self.capital = self.withdrawal_threshold
            self.peak = self.capital  # Reset peak
            self.withdrawals.append({
                'date': date,
                'amount': withdrawal,
                'balance_after': self.capital
            })
            self.total_withdrawn += withdrawal
            return withdrawal
        return 0
    
    def run(self, df, sigs):
        """Run ultra-conservative backtest"""
        
        sig_dict = {}
        for _, sig in sigs.iterrows():
            sig_dict[sig['date']] = sig
        
        for idx, row in df.iterrows():
            current_date = row.name if isinstance(row.name, pd.Timestamp) else pd.Timestamp(row['date'])
            
            # Check for withdrawal
            withdrawal = self.check_withdrawal(current_date)
            
            # Check for signal
            if current_date in sig_dict:
                sig = sig_dict[current_date]
                
                risk_per_unit = abs(sig['entry_price'] - sig['stop_loss'])
                
                if risk_per_unit == 0 or risk_per_unit > sig['entry_price'] * 0.3:
                    continue
                
                # Calculate max position size within strict limits
                max_size = self.get_max_position_size(sig['entry_price'], sig['stop_loss'])
                
                if max_size <= 0:
                    self.trades_rejected += 1
                    continue
                
                size = max_size
                position_value = size * sig['entry_price']
                potential_loss = risk_per_unit * size
                
                # Double-check we can take this trade
                can_trade, reason = self.can_take_trade(potential_loss)
                
                if not can_trade:
                    self.trades_rejected += 1
                    continue
                
                # Simulate outcome
                rr = abs(sig['take_profit'] - sig['entry_price']) / risk_per_unit
                win_prob = min(0.60, 0.35 + (0.06 * rr))
                
                if np.random.random() < win_prob:
                    # Winner
                    pnl = abs(sig['take_profit'] - sig['entry_price']) * size
                    result = 'W'
                else:
                    # Loser - use actual stop loss
                    pnl = -risk_per_unit * size
                    result = 'L'
                
                prev_capital = self.capital
                self.capital += pnl
                
                if self.capital <= 0:
                    self.capital = 0
                    self.stopped_out = True
                    self.stop_reason = 'Account blown'
                    break
                
                # Check DD
                current_dd = self.get_current_dd()
                if current_dd > self.max_dd:
                    self.max_dd = current_dd
                
                if current_dd >= self.max_dd_pct * 100:
                    self.stopped_out = True
                    self.stop_reason = f'Max DD {current_dd:.2f}% >= {self.max_dd_pct*100}%'
                    break
                
                ret = (self.capital - prev_capital) / prev_capital if prev_capital > 0 else 0
                self.daily_returns.append(ret)
                
                self.trades.append({
                    'date': current_date,
                    'pnl': pnl,
                    'result': result,
                    'capital': self.capital,
                    'position_value': position_value,
                    'size': size,
                    'loss_if_stopped': potential_loss
                })
        
        # Metrics
        wins = [t for t in self.trades if t['result'] == 'W']
        losses = [t for t in self.trades if t['result'] == 'L']
        
        total_value = self.capital + self.total_withdrawn
        total_return = (total_value - self.init_capital) / self.init_capital * 100
        
        sharpe = 0
        if len(self.daily_returns) > 1:
            ret_std = np.std(self.daily_returns)
            avg_ret = np.mean(self.daily_returns)
            sharpe = (avg_ret / ret_std * np.sqrt(252)) if ret_std > 0 else 0
        
        # Check actual max loss
        max_actual_loss = max([abs(t['pnl']) for t in losses]) if losses else 0
        max_loss_pct = (max_actual_loss / self.init_capital * 100) if max_actual_loss > 0 else 0
        
        return {
            'return': total_return,
            'dd': self.max_dd,
            'trades': len(self.trades),
            'trades_rejected': self.trades_rejected,
            'wr': len(wins) / len(self.trades) * 100 if self.trades else 0,
            'final_capital': self.capital,
            'total_withdrawn': self.total_withdrawn,
            'total_value': total_value,
            'sharpe': sharpe,
            'max_actual_loss': max_actual_loss,
            'max_loss_pct': max_loss_pct,
            'num_withdrawals': len(self.withdrawals),
            'stopped_out': self.stopped_out,
            'stop_reason': self.stop_reason
        }

STRATEGY = {
    'name': 'EMA 5/13 ADX15 Ultra-Conservative',
    'ema_fast': 5,
    'ema_slow': 13,
    'adx': 15,
    'stop': 1.5,
    'target': 4.0
}

PAIRS = ['AUDUSD=X', 'EURUSD=X', 'GBPUSD=X', 'USDJPY=X']

end_date = datetime.now()
TEST_PERIODS = [
    (end_date - timedelta(days=365), end_date, '1 year'),
    (end_date - timedelta(days=730), end_date, '2 years'),
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

print('Constraints:')
print('  - Starting Capital: $10,000')
print('  - Max Loss Per Trade: 1.5% ($150)')
print('  - Max Total Drawdown: 1.5% ($150)')
print('  - Leverage: 1:50 (if needed)')
print('  - Weekly Withdrawals: Profits > $10k on Fridays')
print()

results = []

for start, end, period_name in TEST_PERIODS:
    print(f'\n{"="*80}')
    print(f'Period: {period_name}')
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
                # 10 simulations
                sim_results = []
                
                for sim in range(10):
                    bt = UltraConservativeBacktester(
                        capital=10000,
                        leverage=50,
                        max_loss_per_trade_pct=0.015,
                        max_dd_pct=0.015,
                        withdrawal_threshold=10000
                    )
                    m = bt.run(df, sigs)
                    sim_results.append(m)
                
                # Averages
                avg_return = np.mean([r['return'] for r in sim_results])
                avg_withdrawn = np.mean([r['total_withdrawn'] for r in sim_results])
                avg_total_value = np.mean([r['total_value'] for r in sim_results])
                avg_dd = np.mean([r['dd'] for r in sim_results])
                avg_trades = np.mean([r['trades'] for r in sim_results])
                avg_rejected = np.mean([r['trades_rejected'] for r in sim_results])
                avg_wr = np.mean([r['wr'] for r in sim_results])
                avg_sharpe = np.mean([r['sharpe'] for r in sim_results])
                avg_max_loss = np.mean([r['max_actual_loss'] for r in sim_results])
                avg_max_loss_pct = np.mean([r['max_loss_pct'] for r in sim_results])
                avg_withdrawals = np.mean([r['num_withdrawals'] for r in sim_results])
                stopped_count = sum([1 for r in sim_results if r['stopped_out']])
                
                # Annual profit
                years = len(df) / 252
                profit_per_year = (avg_total_value - 10000) / years if years > 0 else 0
                
                print(f'{pair_name}: {len(sigs)} signals')
                print(f'  💰 Total Value: ${avg_total_value:,.2f}')
                print(f'  📈 Return: {avg_return:+.2f}%')
                print(f'  💵 Withdrawn: ${avg_withdrawn:,.2f}')
                print(f'  📊 Annual Profit: ${profit_per_year:,.2f}')
                print(f'  📉 Max DD: {avg_dd:.2f}% | Max Loss/Trade: ${avg_max_loss:.2f} ({avg_max_loss_pct:.2f}%)')
                print(f'  🎯 Trades: {avg_trades:.0f} (Rejected: {avg_rejected:.0f}) | WR: {avg_wr:.1f}%')
                print(f'  💸 Withdrawals: {avg_withdrawals:.0f}x | Stopped: {stopped_count}/10')
                
                # Check if constraints met
                if avg_max_loss_pct <= 1.5 and avg_dd <= 1.5:
                    print(f'  ✅ WITHIN LIMITS')
                else:
                    print(f'  ⚠️ EXCEEDED LIMITS')
                
                if avg_return > 10:
                    print(f'  🏆 Excellent return')
                elif avg_return > 5:
                    print(f'  💚 Good return')
                print()
                
                result = {
                    'period': period_name,
                    'pair': pair_name,
                    'return': avg_return,
                    'total_value': avg_total_value,
                    'withdrawn': avg_withdrawn,
                    'profit_per_year': profit_per_year,
                    'dd': avg_dd,
                    'max_loss': avg_max_loss,
                    'max_loss_pct': avg_max_loss_pct,
                    'trades': avg_trades,
                    'rejected': avg_rejected,
                    'wr': avg_wr,
                    'sharpe': avg_sharpe,
                    'withdrawals': avg_withdrawals,
                    'stopped_count': stopped_count
                }
                
                results.append(result)
        
        except Exception as e:
            print(f'{pair.replace("=X", "")}: Failed - {e}')

# Summary
print()
print('='*80)
print('🛡️ ULTRA-CONSERVATIVE RESULTS - FINAL SUMMARY')
print('='*80)
print()

if results:
    results_df = pd.DataFrame(results)
    
    print(f'Total Tests: {len(results)}')
    print()
    
    print('📊 ALL RESULTS (sorted by return):')
    print()
    
    for idx, r in results_df.nlargest(len(results), 'return').iterrows():
        within_limits = "✅" if r['max_loss_pct'] <= 1.5 and r['dd'] <= 1.5 else "⚠️"
        print(f"{within_limits} {r['period']:10s} | {r['pair']:6s} | Return: {r['return']:+.2f}%")
        print(f"   Value: ${r['total_value']:,.2f} | Withdrawn: ${r['withdrawn']:,.2f}")
        print(f"   DD: {r['dd']:.2f}% | Max Loss: ${r['max_loss']:.2f} ({r['max_loss_pct']:.2f}%)")
        print(f"   Trades: {r['trades']:.0f} (Rejected: {r['rejected']:.0f})")
        print()
    
    print('='*80)
    print('📈 STATISTICAL SUMMARY')
    print('='*80)
    print()
    
    print(f"💎 Average Return: {results_df['return'].mean():.2f}%")
    print(f"🏆 Best Return: {results_df['return'].max():.2f}%")
    print(f"💵 Average Withdrawn: ${results_df['withdrawn'].mean():,.2f}")
    print(f"📊 Average Annual Profit: ${results_df['profit_per_year'].mean():,.2f}")
    print()
    print(f"📉 Average Max DD: {results_df['dd'].mean():.2f}%")
    print(f"🛡️ Average Max Loss/Trade: ${results_df['max_loss'].mean():.2f} ({results_df['max_loss_pct'].mean():.2f}%)")
    print(f"🎯 Average Trades: {results_df['trades'].mean():.0f}")
    print(f"❌ Average Rejected: {results_df['rejected'].mean():.0f}")
    print(f"🎲 Average Stopped Out: {results_df['stopped_count'].mean():.1f}/10")
    print()
    
    # Check compliance
    compliant = results_df[(results_df['max_loss_pct'] <= 1.5) & (results_df['dd'] <= 1.5)]
    print(f"✅ Within Limits: {len(compliant)}/{len(results)} ({len(compliant)/len(results)*100:.1f}%)")
    
    results_df.to_csv('/workspace/ultra_conservative_results.csv', index=False)
    print()
    print('✓ Saved to: ultra_conservative_results.csv')

print()
print('✅ Ultra-conservative backtest complete')
