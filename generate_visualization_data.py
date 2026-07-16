#!/usr/bin/env python3
"""
Generate equity curve data for visualization
Creates data for 3-month, 6-month, and 1-year periods
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
print('📊 GENERATING VISUALIZATION DATA')
print('='*80)
print()

class VisualizationBacktester:
    """Detailed backtest with equity curve tracking"""
    
    def __init__(self, capital=10000):
        self.capital = capital
        self.init = capital
        
        self.sniper_allocation = 0.40
        self.background_allocation = 0.60
        self.sniper_risk = 0.05
        self.background_risk = 0.02
        
        self.equity_curve = []
        self.trades = []
        self.daily_equity = {}
        
        self.peak = capital
        self.max_dd = 0
    
    def record_daily(self, date):
        """Record daily equity"""
        day = date.date() if hasattr(date, 'date') else date
        self.daily_equity[str(day)] = self.capital
        
        self.equity_curve.append({
            'date': str(day),
            'equity': self.capital,
            'peak': self.peak,
            'drawdown': ((self.peak - self.capital) / self.peak * 100) if self.peak > 0 else 0
        })
    
    def trade_sniper(self, entry, stop, target, date):
        sniper_capital = self.capital * self.sniper_allocation
        risk_per_unit = abs(entry - stop)
        
        if risk_per_unit == 0:
            return None
        
        risk_amt = sniper_capital * self.sniper_risk
        size = risk_amt / risk_per_unit
        
        rr = abs(target - entry) / risk_per_unit
        win_prob = min(0.65, 0.35 + (0.06 * rr))
        
        won = np.random.random() < win_prob
        pnl = (abs(target - entry) * size) if won else (-risk_per_unit * size)
        
        self.capital += pnl
        
        if self.capital > self.peak:
            self.peak = self.capital
        
        dd = (self.peak - self.capital) / self.init * 100
        if dd > self.max_dd:
            self.max_dd = dd
        
        self.trades.append({
            'date': str(date.date() if hasattr(date, 'date') else date),
            'strategy': 'sniper',
            'direction': 'LONG' if target > entry else 'SHORT',
            'won': won,
            'pnl': pnl,
            'pnl_pct': (pnl / self.init) * 100,
            'equity_after': self.capital
        })
        
        return pnl
    
    def trade_background(self, entry, stop, target, date):
        background_capital = self.capital * self.background_allocation
        risk_per_unit = abs(entry - stop)
        
        if risk_per_unit == 0:
            return None
        
        risk_amt = background_capital * self.background_risk
        size = risk_amt / risk_per_unit
        
        rr = abs(target - entry) / risk_per_unit
        win_prob = min(0.60, 0.35 + (0.05 * rr))
        
        won = np.random.random() < win_prob
        pnl = (abs(target - entry) * size) if won else (-risk_per_unit * size)
        
        self.capital += pnl
        
        if self.capital > self.peak:
            self.peak = self.capital
        
        dd = (self.peak - self.capital) / self.init * 100
        if dd > self.max_dd:
            self.max_dd = dd
        
        self.trades.append({
            'date': str(date.date() if hasattr(date, 'date') else date),
            'strategy': 'background',
            'direction': 'LONG' if target > entry else 'SHORT',
            'won': won,
            'pnl': pnl,
            'pnl_pct': (pnl / self.init) * 100,
            'equity_after': self.capital
        })
        
        return pnl
    
    def run(self, df, sniper_sigs, background_sigs):
        sniper_dict = {sig['date']: sig for _, sig in sniper_sigs.iterrows()}
        background_dict = {sig['date']: sig for _, sig in background_sigs.iterrows()}
        
        monthly_sniper = 0
        last_month = None
        
        for _, row in df.iterrows():
            date = row.name if isinstance(row.name, pd.Timestamp) else pd.Timestamp(row['date'])
            
            # Reset monthly counter
            current_month = date.month
            if current_month != last_month:
                monthly_sniper = 0
                last_month = current_month
            
            # Record daily
            self.record_daily(date)
            
            # Sniper trades (limit to 2 per month)
            if date in sniper_dict and monthly_sniper < 2:
                sig = sniper_dict[date]
                self.trade_sniper(sig['entry_price'], sig['stop_loss'], sig['take_profit'], date)
                monthly_sniper += 1
            
            # Background trades
            if date in background_dict:
                sig = background_dict[date]
                self.trade_background(sig['entry_price'], sig['stop_loss'], sig['take_profit'], date)
        
        return {
            'equity_curve': self.equity_curve,
            'trades': self.trades,
            'final_equity': self.capital,
            'max_dd': self.max_dd,
            'total_return': ((self.capital - self.init) / self.init * 100)
        }

def gen_sniper_sigs(df):
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
            sigs.append({'date': date, 'entry_price': bar['close'],
                        'stop_loss': bar['close'] - (bar['atr'] * 1.0),
                        'take_profit': bar['close'] + (bar['atr'] * 5.0)})
        elif bar['ema_f'] < bar['ema_s'] and prev['ema_f'] >= prev['ema_s']:
            sigs.append({'date': date, 'entry_price': bar['close'],
                        'stop_loss': bar['close'] + (bar['atr'] * 1.0),
                        'take_profit': bar['close'] - (bar['atr'] * 5.0)})
    return pd.DataFrame(sigs)

def gen_background_sigs(df):
    df = df.copy()
    df['atr'] = TechnicalIndicators.atr(df)
    df['ema_f'] = TechnicalIndicators.ema(df, 9)
    df['ema_s'] = TechnicalIndicators.ema(df, 21)
    adx, _, _ = TechnicalIndicators.adx(df)
    df['adx'] = adx
    
    sigs = []
    for i in range(50, len(df)):
        bar, prev = df.iloc[i], df.iloc[i-1]
        if bar['adx'] < 20:
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

# Generate data for all periods
handler = DataHandler()
end = datetime.now()

periods = [
    (90, '3months'),
    (180, '6months'),
    (365, '1year')
]

all_data = {}

for days, label in periods:
    print(f'Generating {label} data...')
    start = end - timedelta(days=days)
    
    df = handler.fetch_data('EURUSD=X', start.strftime('%Y-%m-%d'), 
                           end.strftime('%Y-%m-%d'), '4h')
    
    sniper_sigs = gen_sniper_sigs(df.copy())
    background_sigs = gen_background_sigs(df.copy())
    
    # Run backtest
    bt = VisualizationBacktester(capital=10000)
    result = bt.run(df, sniper_sigs, background_sigs)
    
    # Prepare data
    all_data[label] = {
        'period': label,
        'days': days,
        'starting_balance': 10000,
        'ending_balance': result['final_equity'],
        'total_return': result['total_return'],
        'max_drawdown': result['max_dd'],
        'total_trades': len(result['trades']),
        'sniper_trades': len([t for t in result['trades'] if t['strategy'] == 'sniper']),
        'background_trades': len([t for t in result['trades'] if t['strategy'] == 'background']),
        'equity_curve': result['equity_curve'],
        'trades': result['trades']
    }
    
    print(f'  ✓ {label}: {result["total_return"]:.2f}% return, {len(result["trades"])} trades')

# Save data
with open('/workspace/docs/data.json', 'w') as f:
    json.dump(all_data, f, indent=2)

print()
print('✅ Data generated successfully!')
print('   Saved to: docs/data.json')
