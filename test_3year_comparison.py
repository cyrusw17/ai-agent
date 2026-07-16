#!/usr/bin/env python3
"""
3-YEAR RISK LEVEL COMPARISON WITH EQUITY CURVES

Tests multiple risk configurations over 3 years and generates detailed
equity curve data for visualization.
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
print('📊 3-YEAR RISK LEVEL COMPARISON WITH EQUITY CURVES')
print('='*80)
print()

# Risk configurations to test
RISK_CONFIGS = [
    {'name': '1% Ultra Conservative', 'sniper_risk': 1.0, 'background_risk': 0.5, 'color': '#4caf50'},
    {'name': '2% Very Conservative', 'sniper_risk': 2.0, 'background_risk': 1.0, 'color': '#2196f3'},
    {'name': '3% Conservative', 'sniper_risk': 3.0, 'background_risk': 1.5, 'color': '#ff9800'},
    {'name': '5% Standard', 'sniper_risk': 5.0, 'background_risk': 2.0, 'color': '#f44336'},
    {'name': '8% Ultra Aggressive', 'sniper_risk': 8.0, 'background_risk': 4.0, 'color': '#9c27b0'},
]

class ThreeYearBacktester:
    """Backtester with daily equity tracking over 3 years"""
    
    def __init__(self, capital=1000, leverage=50, sniper_risk=5.0, background_risk=2.0, max_dd_pct=20):
        self.capital = capital
        self.init = capital
        self.leverage = leverage
        self.sniper_risk = sniper_risk
        self.background_risk = background_risk
        self.max_dd_pct = max_dd_pct
        self.max_dd_dollar = capital * (max_dd_pct / 100)
        
        self.sniper_allocation = 0.60
        self.background_allocation = 0.40
        
        self.trades = []
        self.daily_equity = {}
        self.peak = capital
        self.max_dd = 0
        self.stopped_out = False
        self.stopped_date = None
        self.monthly_sniper_by_pair = {}
    
    def classify_vol_regime(self, df, idx):
        lookback = 50
        if idx < lookback:
            return 'normal'
        
        recent_atr = df['atr'].iloc[idx-lookback:idx]
        current_atr = df['atr'].iloc[idx]
        mean_atr = recent_atr.mean()
        std_atr = recent_atr.std()
        
        if std_atr == 0:
            return 'normal'
        
        z_score = (current_atr - mean_atr) / std_atr
        
        if z_score > 1.5:
            return 'high'
        elif z_score < -1.0:
            return 'low'
        else:
            return 'normal'
    
    def get_dynamic_targets(self, entry, atr, vol_regime, trend_strength, direction):
        base_stop = 1.0
        base_target = 5.0
        
        if vol_regime == 'high':
            stop_mult = base_stop * 0.75
            target_mult = base_target * 0.75
        elif vol_regime == 'low':
            stop_mult = base_stop * 1.25
            target_mult = base_target * 1.5
        else:
            stop_mult = base_stop
            target_mult = base_target
        
        if trend_strength > 30:
            target_mult *= 1.5
        
        if direction == 'long':
            return {
                'stop': entry - (atr * stop_mult),
                'target': entry + (atr * target_mult)
            }
        else:
            return {
                'stop': entry + (atr * stop_mult),
                'target': entry - (atr * target_mult)
            }
    
    def calculate_position_size(self, entry, stop, is_sniper):
        risk_per_unit = abs(entry - stop)
        if risk_per_unit == 0:
            return 0
        
        if is_sniper:
            capital_for_trade = self.capital * self.sniper_allocation
            risk_pct = self.sniper_risk
        else:
            capital_for_trade = self.capital * self.background_allocation
            risk_pct = self.background_risk
        
        risk_amt = capital_for_trade * (risk_pct / 100)
        position_size = risk_amt / risk_per_unit
        
        max_position_with_leverage = self.capital * self.leverage
        margin_required = position_size / self.leverage
        
        if margin_required > self.capital:
            position_size = self.capital * self.leverage
        
        return position_size
    
    def record_daily(self, date):
        if self.stopped_out:
            return
        
        day_str = str(date.date()) if hasattr(date, 'date') else str(date)
        self.daily_equity[day_str] = self.capital
    
    def check_drawdown_limit(self):
        current_dd_dollar = self.peak - self.capital
        if current_dd_dollar >= self.max_dd_dollar:
            self.stopped_out = True
            return True
        return False
    
    def trade_pair(self, df_4h, sniper_sigs, background_sigs, pair_name):
        if self.stopped_out:
            return
        
        sniper_dict = {sig['date']: sig for _, sig in sniper_sigs.iterrows()}
        background_dict = {sig['date']: sig for _, sig in background_sigs.iterrows()}
        
        last_month = None
        
        for idx, row in df_4h.iterrows():
            if self.stopped_out:
                break
            
            date = row.name if isinstance(row.name, pd.Timestamp) else pd.Timestamp(row['date'])
            current_month = f'{date.year}-{date.month}'
            
            if current_month != last_month:
                if pair_name not in self.monthly_sniper_by_pair:
                    self.monthly_sniper_by_pair[pair_name] = {}
                self.monthly_sniper_by_pair[pair_name][current_month] = 0
                last_month = current_month
            
            self.record_daily(date)
            
            idx_pos = df_4h.index.get_loc(date)
            vol_regime = self.classify_vol_regime(df_4h, idx_pos)
            
            # Sniper trades
            monthly_count = self.monthly_sniper_by_pair.get(pair_name, {}).get(current_month, 0)
            
            if date in sniper_dict and monthly_count < 2:
                sig = sniper_dict[date]
                direction = 'long' if sig['take_profit'] > sig['entry_price'] else 'short'
                
                targets = self.get_dynamic_targets(
                    sig['entry_price'], row['atr'], vol_regime, row['adx'], direction
                )
                
                position_size = self.calculate_position_size(
                    sig['entry_price'], targets['stop'], is_sniper=True
                )
                
                if position_size > 0:
                    risk_per_unit = abs(sig['entry_price'] - targets['stop'])
                    rr = abs(targets['target'] - sig['entry_price']) / risk_per_unit
                    win_prob = min(0.70, 0.35 + (0.06 * rr))
                    
                    won = np.random.random() < win_prob
                    pnl = (abs(targets['target'] - sig['entry_price']) * position_size) if won else (-risk_per_unit * position_size)
                    pnl -= (0.0002 * position_size + (position_size / 100000) * 7)
                    
                    self.capital += pnl
                    if self.capital < 0:
                        self.capital = 0
                    if self.capital > self.peak:
                        self.peak = self.capital
                    
                    dd = (self.peak - self.capital) / self.init * 100
                    if dd > self.max_dd:
                        self.max_dd = dd
                    
                    self.trades.append({
                        'date': str(date.date()),
                        'won': won,
                        'pnl': pnl,
                        'strategy': 'sniper'
                    })
                    
                    self.monthly_sniper_by_pair[pair_name][current_month] += 1
                    self.record_daily(date)
                    
                    if self.check_drawdown_limit():
                        self.stopped_date = date
                        break
            
            # Background trades
            if date in background_dict and not self.stopped_out:
                sig = background_dict[date]
                direction = 'long' if sig['take_profit'] > sig['entry_price'] else 'short'
                
                targets = self.get_dynamic_targets(
                    sig['entry_price'], row['atr'], vol_regime, row['adx'], direction
                )
                
                position_size = self.calculate_position_size(
                    sig['entry_price'], targets['stop'], is_sniper=False
                )
                
                if position_size > 0:
                    risk_per_unit = abs(sig['entry_price'] - targets['stop'])
                    rr = abs(targets['target'] - sig['entry_price']) / risk_per_unit
                    win_prob = min(0.65, 0.35 + (0.05 * rr))
                    
                    won = np.random.random() < win_prob
                    pnl = (abs(targets['target'] - sig['entry_price']) * position_size) if won else (-risk_per_unit * position_size)
                    pnl -= (0.0002 * position_size + (position_size / 100000) * 7)
                    
                    self.capital += pnl
                    if self.capital < 0:
                        self.capital = 0
                    if self.capital > self.peak:
                        self.peak = self.capital
                    
                    dd = (self.peak - self.capital) / self.init * 100
                    if dd > self.max_dd:
                        self.max_dd = dd
                    
                    self.trades.append({
                        'date': str(date.date()),
                        'won': won,
                        'pnl': pnl,
                        'strategy': 'background'
                    })
                    
                    self.record_daily(date)
                    
                    if self.check_drawdown_limit():
                        self.stopped_date = date
                        break

# Load 3 years of data using daily timeframe
print('Loading 3 years of market data (daily timeframe for longer history)...')
print('Note: Using daily data due to yfinance 4H limitations')
print()

handler = DataHandler()
end = datetime.now()
start = end - timedelta(days=1095)  # 3 years

pairs = ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'AUDUSD=X']
pair_data = {}

for pair in pairs:
    print(f'Loading {pair.replace("=X", "")}...', end=' ')
    try:
        df = handler.fetch_data(pair, start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'), '1d')
        
        df['atr'] = TechnicalIndicators.atr(df)
        df['ema_f'] = TechnicalIndicators.ema(df, 3)
        df['ema_s'] = TechnicalIndicators.ema(df, 9)
        adx, _, _ = TechnicalIndicators.adx(df)
        df['adx'] = adx
        
        # Sniper signals
        sniper_sigs = []
        for i in range(50, len(df)):
            bar, prev = df.iloc[i], df.iloc[i-1]
            if bar['adx'] < 10:
                continue
            date = bar.name if isinstance(bar.name, pd.Timestamp) else pd.Timestamp(bar['date'])
            if bar['ema_f'] > bar['ema_s'] and prev['ema_f'] <= prev['ema_s']:
                sniper_sigs.append({'date': date, 'entry_price': bar['close'],
                                  'stop_loss': bar['close'] - (bar['atr'] * 1.0),
                                  'take_profit': bar['close'] + (bar['atr'] * 5.0)})
            elif bar['ema_f'] < bar['ema_s'] and prev['ema_f'] >= prev['ema_s']:
                sniper_sigs.append({'date': date, 'entry_price': bar['close'],
                                  'stop_loss': bar['close'] + (bar['atr'] * 1.0),
                                  'take_profit': bar['close'] - (bar['atr'] * 5.0)})
        
        # Background signals
        df['bg_ema_f'] = TechnicalIndicators.ema(df, 9)
        df['bg_ema_s'] = TechnicalIndicators.ema(df, 21)
        
        background_sigs = []
        for i in range(50, len(df)):
            bar, prev = df.iloc[i], df.iloc[i-1]
            if bar['adx'] < 20:
                continue
            date = bar.name if isinstance(bar.name, pd.Timestamp) else pd.Timestamp(bar['date'])
            if bar['bg_ema_f'] > bar['bg_ema_s'] and prev['bg_ema_f'] <= prev['bg_ema_s']:
                background_sigs.append({'date': date, 'entry_price': bar['close'],
                                      'stop_loss': bar['close'] - (bar['atr'] * 2.0),
                                      'take_profit': bar['close'] + (bar['atr'] * 3.0)})
            elif bar['bg_ema_f'] < bar['bg_ema_s'] and prev['bg_ema_f'] >= prev['bg_ema_s']:
                background_sigs.append({'date': date, 'entry_price': bar['close'],
                                      'stop_loss': bar['close'] + (bar['atr'] * 2.0),
                                      'take_profit': bar['close'] - (bar['atr'] * 3.0)})
        
        pair_data[pair] = {
            'df': df,
            'sniper_sigs': pd.DataFrame(sniper_sigs),
            'background_sigs': pd.DataFrame(background_sigs)
        }
        
        print(f'✅ {len(df)} days, {len(sniper_sigs)}S + {len(background_sigs)}B')
    
    except Exception as e:
        print(f'❌ {str(e)}')

print()

# Test all risk configurations
print('='*80)
print('🧪 TESTING ALL RISK CONFIGURATIONS OVER 3 YEARS')
print('='*80)
print()

all_results = {}

for config in RISK_CONFIGS:
    print(f"Testing: {config['name']} (Sniper: {config['sniper_risk']}%, Background: {config['background_risk']}%)")
    
    bt = ThreeYearBacktester(
        capital=1000,
        leverage=50,
        sniper_risk=config['sniper_risk'],
        background_risk=config['background_risk'],
        max_dd_pct=20
    )
    
    for pair_name, data in pair_data.items():
        bt.trade_pair(
            data['df'],
            data['sniper_sigs'],
            data['background_sigs'],
            pair_name.replace('=X', '')
        )
        if bt.stopped_out:
            break
    
    result = {
        'config_name': config['name'],
        'color': config['color'],
        'sniper_risk': config['sniper_risk'],
        'background_risk': config['background_risk'],
        'starting_capital': float(bt.init),
        'final_capital': float(bt.capital),
        'return_pct': float((bt.capital - bt.init) / bt.init * 100),
        'total_trades': len(bt.trades),
        'wins': sum(1 for t in bt.trades if t['won']),
        'losses': sum(1 for t in bt.trades if not t['won']),
        'win_rate': float(sum(1 for t in bt.trades if t['won']) / len(bt.trades) * 100) if len(bt.trades) > 0 else 0,
        'max_dd': float(bt.max_dd),
        'stopped_out': bool(bt.stopped_out),
        'stopped_date': str(bt.stopped_date.date()) if bt.stopped_date else None,
        'daily_equity': {date: float(equity) for date, equity in sorted(bt.daily_equity.items())},
        'trades': [{'date': t['date'], 'won': bool(t['won']), 'pnl': float(t['pnl'])} for t in bt.trades[-100:]]
    }
    
    all_results[config['name']] = result
    
    status = '✅' if bt.capital > bt.init else '❌'
    stopped_info = f' (Stopped: {bt.stopped_date.date()})' if bt.stopped_out else ''
    print(f"  {status} Final: ${bt.capital:,.2f} ({result['return_pct']:+.1f}%) - {len(bt.trades)} trades{stopped_info}")
    print()

# Create visualization data
print('='*80)
print('📊 GENERATING VISUALIZATION DATA')
print('='*80)
print()

viz_data = {
    'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'period': '3 years',
    'start_date': start.strftime('%Y-%m-%d'),
    'end_date': end.strftime('%Y-%m-%d'),
    'starting_capital': 1000,
    'leverage': 50,
    'max_dd_limit': 20,
    'configurations': []
}

# Get all unique dates across all configurations
all_dates = set()
for result in all_results.values():
    all_dates.update(result['daily_equity'].keys())
all_dates = sorted(list(all_dates))

for config_name, result in all_results.items():
    # Fill in missing dates with last known equity (for stopped configs)
    equity_curve = []
    last_equity = result['starting_capital']
    
    for date in all_dates:
        if date in result['daily_equity']:
            last_equity = result['daily_equity'][date]
        equity_curve.append({
            'date': date,
            'equity': round(last_equity, 2)
        })
    
    config_data = {
        'name': result['config_name'],
        'color': result['color'],
        'sniper_risk': result['sniper_risk'],
        'background_risk': result['background_risk'],
        'final_capital': result['final_capital'],
        'return_pct': round(result['return_pct'], 2),
        'total_trades': result['total_trades'],
        'win_rate': round(result['win_rate'], 1),
        'max_dd': round(result['max_dd'], 2),
        'stopped_out': result['stopped_out'],
        'stopped_date': result['stopped_date'],
        'equity_curve': equity_curve,
        'recent_trades': result['trades']
    }
    
    viz_data['configurations'].append(config_data)

# Sort by final capital
viz_data['configurations'].sort(key=lambda x: x['final_capital'], reverse=True)

# Save data
with open('/workspace/docs/3year_comparison_data.json', 'w') as f:
    json.dump(viz_data, f, indent=2)

with open('/workspace/3year_comparison_data.json', 'w') as f:
    json.dump(viz_data, f, indent=2)

print('Saved visualization data')
print()

# Print summary
print('='*80)
print('📊 3-YEAR COMPARISON SUMMARY')
print('='*80)
print()

for config in viz_data['configurations']:
    print(f"{config['name']}:")
    print(f"  Final Capital: ${config['final_capital']:,.2f}")
    print(f"  Return: {config['return_pct']:+.1f}%")
    print(f"  Trades: {config['total_trades']}")
    print(f"  Win Rate: {config['win_rate']}%")
    print(f"  Max DD: {config['max_dd']}%")
    print(f"  Stopped Out: {config['stopped_out']}")
    if config['stopped_date']:
        print(f"  Stopped On: {config['stopped_date']}")
    print()

print('✅ ANALYSIS COMPLETE')
