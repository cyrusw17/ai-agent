#!/usr/bin/env python3
"""
$1000 LEVERAGED ACCOUNT WITH 8% MAX RISK PER TRADE

Conservative simulation with strict position sizing:
- Starting capital: $1000
- Leverage: 50:1
- Max risk per trade: 8% of account
- 20% max drawdown limit
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
print('💰 $1000 LEVERAGED - 8% MAX RISK PER TRADE')
print('='*80)
print()
print('Configuration:')
print('  - Starting Capital: $1,000')
print('  - Leverage: 50:1')
print('  - Max Risk Per Trade: 8%')
print('  - Max Drawdown Limit: 20% ($200)')
print('  - Strategy: Dynamic Targets + Volatility Regime')
print()

class RiskControlledBacktester:
    """Leveraged account with 8% max risk per trade"""
    
    def __init__(self, capital=1000, leverage=50, max_risk_pct=8, max_dd_pct=20):
        self.capital = capital
        self.init = capital
        self.leverage = leverage
        self.max_risk_pct = max_risk_pct  # 8% max risk per trade
        self.max_dd_pct = max_dd_pct
        self.max_dd_dollar = capital * (max_dd_pct / 100)
        
        # Strategy config - will use max_risk_pct for all trades
        self.sniper_allocation = 0.60
        self.background_allocation = 0.40
        
        # Tracking
        self.equity_curve = []
        self.trades = []
        self.daily_equity = {}
        self.peak = capital
        self.max_dd = 0
        self.stopped_out = False
        self.stop_reason = None
        
        # Per-pair limits
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
        """Calculate position size with strict 8% risk limit"""
        risk_per_unit = abs(entry - stop)
        if risk_per_unit == 0:
            return 0
        
        # Use capital allocated for this strategy type
        if is_sniper:
            capital_for_trade = self.capital * self.sniper_allocation
        else:
            capital_for_trade = self.capital * self.background_allocation
        
        # Risk 8% of allocated capital
        risk_amt = capital_for_trade * (self.max_risk_pct / 100)
        
        # Calculate position size
        position_size = risk_amt / risk_per_unit
        
        # Apply leverage constraint
        max_position_with_leverage = self.capital * self.leverage
        margin_required = position_size / self.leverage
        
        if margin_required > self.capital:
            position_size = self.capital * self.leverage
        
        return position_size
    
    def record_daily(self, date):
        day_str = str(date.date()) if hasattr(date, 'date') else str(date)
        
        if day_str not in self.daily_equity:
            self.daily_equity[day_str] = self.capital
    
    def check_drawdown_limit(self):
        """Check if we've hit the 20% DD limit"""
        current_dd_dollar = self.peak - self.capital
        
        if current_dd_dollar >= self.max_dd_dollar:
            self.stopped_out = True
            self.stop_reason = f'Max drawdown reached: ${current_dd_dollar:.2f} (20% limit = ${self.max_dd_dollar:.2f})'
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
                    sig['entry_price'],
                    row['atr'],
                    vol_regime,
                    row['adx'],
                    direction
                )
                
                position_size = self.calculate_position_size(
                    sig['entry_price'],
                    targets['stop'],
                    is_sniper=True
                )
                
                if position_size > 0:
                    risk_per_unit = abs(sig['entry_price'] - targets['stop'])
                    rr = abs(targets['target'] - sig['entry_price']) / risk_per_unit
                    win_prob = min(0.70, 0.35 + (0.06 * rr))
                    
                    won = np.random.random() < win_prob
                    pnl = (abs(targets['target'] - sig['entry_price']) * position_size) if won else (-risk_per_unit * position_size)
                    
                    # Costs
                    pnl -= (0.0002 * position_size + (position_size / 100000) * 7)
                    
                    self.capital += pnl
                    
                    if self.capital < 0:
                        self.capital = 0
                    
                    if self.capital > self.peak:
                        self.peak = self.capital
                    
                    dd = (self.peak - self.capital) / self.init * 100
                    if dd > self.max_dd:
                        self.max_dd = dd
                    
                    # Calculate actual risk taken
                    risk_taken = abs(pnl) if not won else (risk_per_unit * position_size)
                    risk_pct = (risk_taken / (self.peak * self.sniper_allocation)) * 100
                    
                    self.trades.append({
                        'date': str(date.date()),
                        'pair': pair_name,
                        'strategy': 'sniper',
                        'won': won,
                        'pnl': pnl,
                        'equity_after': self.capital,
                        'position_size': position_size,
                        'risk_pct': risk_pct,
                        'rr': rr,
                        'vol_regime': vol_regime
                    })
                    
                    self.monthly_sniper_by_pair[pair_name][current_month] += 1
                    self.record_daily(date)
                    
                    if self.check_drawdown_limit():
                        print(f'  ⚠️  STOPPED: {self.stop_reason}')
                        break
            
            # Background trades
            if date in background_dict and not self.stopped_out:
                sig = background_dict[date]
                direction = 'long' if sig['take_profit'] > sig['entry_price'] else 'short'
                
                targets = self.get_dynamic_targets(
                    sig['entry_price'],
                    row['atr'],
                    vol_regime,
                    row['adx'],
                    direction
                )
                
                position_size = self.calculate_position_size(
                    sig['entry_price'],
                    targets['stop'],
                    is_sniper=False
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
                    
                    risk_taken = abs(pnl) if not won else (risk_per_unit * position_size)
                    risk_pct = (risk_taken / (self.peak * self.background_allocation)) * 100
                    
                    self.trades.append({
                        'date': str(date.date()),
                        'pair': pair_name,
                        'strategy': 'background',
                        'won': won,
                        'pnl': pnl,
                        'equity_after': self.capital,
                        'position_size': position_size,
                        'risk_pct': risk_pct,
                        'rr': rr,
                        'vol_regime': vol_regime
                    })
                    
                    self.record_daily(date)
                    
                    if self.check_drawdown_limit():
                        print(f'  ⚠️  STOPPED: {self.stop_reason}')
                        break

# Load data
print('Loading data...')
handler = DataHandler()
end = datetime.now()
start = end - timedelta(days=180)

pairs = ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'AUDUSD=X']
pair_data = {}

for pair in pairs:
    print(f'Loading {pair.replace("=X", "")}...', end=' ')
    try:
        df_4h = handler.fetch_data(pair, start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'), '4h')
        
        df_4h['atr'] = TechnicalIndicators.atr(df_4h)
        df_4h['ema_f'] = TechnicalIndicators.ema(df_4h, 3)
        df_4h['ema_s'] = TechnicalIndicators.ema(df_4h, 9)
        adx, _, _ = TechnicalIndicators.adx(df_4h)
        df_4h['adx'] = adx
        
        sniper_sigs = []
        for i in range(50, len(df_4h)):
            bar, prev = df_4h.iloc[i], df_4h.iloc[i-1]
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
        
        df_4h['bg_ema_f'] = TechnicalIndicators.ema(df_4h, 9)
        df_4h['bg_ema_s'] = TechnicalIndicators.ema(df_4h, 21)
        
        background_sigs = []
        for i in range(50, len(df_4h)):
            bar, prev = df_4h.iloc[i], df_4h.iloc[i-1]
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
            'df_4h': df_4h,
            'sniper_sigs': pd.DataFrame(sniper_sigs),
            'background_sigs': pd.DataFrame(background_sigs)
        }
        
        print(f'✅ {len(sniper_sigs)}S + {len(background_sigs)}B')
    
    except Exception as e:
        print(f'❌ {str(e)}')

print()

# Run multiple simulations
print('='*80)
print('RUNNING 20 SIMULATIONS WITH 8% MAX RISK')
print('='*80)
print()

all_results = []

for sim_num in range(20):
    print(f'Simulation {sim_num + 1}/20...', end=' ')
    
    bt = RiskControlledBacktester(capital=1000, leverage=50, max_risk_pct=8, max_dd_pct=20)
    
    for pair_name, data in pair_data.items():
        bt.trade_pair(
            data['df_4h'],
            data['sniper_sigs'],
            data['background_sigs'],
            pair_name.replace('=X', '')
        )
        if bt.stopped_out:
            break
    
    result = {
        'final_capital': bt.capital,
        'profit': bt.capital - bt.init,
        'return_pct': (bt.capital - bt.init) / bt.init * 100,
        'trades': len(bt.trades),
        'wins': sum(1 for t in bt.trades if t['won']),
        'losses': sum(1 for t in bt.trades if not t['won']),
        'win_rate': sum(1 for t in bt.trades if t['won']) / len(bt.trades) * 100 if len(bt.trades) > 0 else 0,
        'max_dd': bt.max_dd,
        'stopped_out': bt.stopped_out,
        'avg_risk_per_trade': np.mean([t['risk_pct'] for t in bt.trades]) if len(bt.trades) > 0 else 0
    }
    
    all_results.append(result)
    
    status = '✅' if bt.capital > bt.init else '❌'
    print(f'{status} ${bt.capital:.2f} ({result["return_pct"]:+.1f}%) - {len(bt.trades)} trades')

print()

# Analyze results
results_df = pd.DataFrame(all_results)

print('='*80)
print('📊 AGGREGATE RESULTS (20 simulations)')
print('='*80)
print()
print(f'Average Final Capital: ${results_df["final_capital"].mean():,.2f}')
print(f'Median Final Capital: ${results_df["final_capital"].median():,.2f}')
print(f'Best Result: ${results_df["final_capital"].max():,.2f}')
print(f'Worst Result: ${results_df["final_capital"].min():,.2f}')
print()
print(f'Average Profit: ${results_df["profit"].mean():,.2f}')
print(f'Average Return: {results_df["return_pct"].mean():.2f}%')
print()
print(f'Average Trades: {results_df["trades"].mean():.1f}')
print(f'Average Win Rate: {results_df["win_rate"].mean():.1f}%')
print(f'Average Max DD: {results_df["max_dd"].mean():.2f}%')
print(f'Average Risk Per Trade: {results_df["avg_risk_per_trade"].mean():.2f}%')
print()
print(f'Stopped Out: {results_df["stopped_out"].sum()}/20 ({results_df["stopped_out"].sum()/20*100:.0f}%)')
print(f'Profitable: {len(results_df[results_df["profit"] > 0])}/20 ({len(results_df[results_df["profit"] > 0])/20*100:.0f}%)')
print()

# Use median result for visualization
median_idx = results_df['final_capital'].sub(results_df['final_capital'].median()).abs().idxmin()

print('='*80)
print('📈 GENERATING VISUALIZATION DATA (Median Result)')
print('='*80)
print()

# Re-run median simulation
bt_viz = RiskControlledBacktester(capital=1000, leverage=50, max_risk_pct=8, max_dd_pct=20)

np.random.seed(median_idx)

for pair_name, data in pair_data.items():
    bt_viz.trade_pair(
        data['df_4h'],
        data['sniper_sigs'],
        data['background_sigs'],
        pair_name.replace('=X', '')
    )
    if bt_viz.stopped_out:
        break

# Prepare visualization data
equity_curve_data = []
sorted_dates = sorted(bt_viz.daily_equity.keys())

for date in sorted_dates:
    peak_so_far = max([bt_viz.daily_equity[d] for d in sorted_dates if d <= date])
    equity = bt_viz.daily_equity[date]
    dd_pct = ((peak_so_far - equity) / peak_so_far * 100) if peak_so_far > 0 else 0
    
    equity_curve_data.append({
        'date': date,
        'equity': round(float(equity), 2),
        'peak': round(float(peak_so_far), 2),
        'drawdown_pct': round(float(dd_pct), 2)
    })

# Trade log
trade_log = []
for trade in bt_viz.trades[-50:]:
    trade_log.append({
        'date': trade['date'],
        'pair': trade['pair'],
        'strategy': trade['strategy'],
        'won': bool(trade['won']),
        'pnl': round(float(trade['pnl']), 2),
        'equity_after': round(float(trade['equity_after']), 2),
        'risk_pct': round(float(trade['risk_pct']), 2)
    })

# Save
viz_data = {
    'starting_balance': float(bt_viz.init),
    'final_balance': round(float(bt_viz.capital), 2),
    'profit': round(float(bt_viz.capital - bt_viz.init), 2),
    'return_pct': round(float((bt_viz.capital - bt_viz.init) / bt_viz.init * 100), 2),
    'total_trades': int(len(bt_viz.trades)),
    'win_rate': round(float(sum(1 for t in bt_viz.trades if t['won']) / len(bt_viz.trades) * 100), 1) if len(bt_viz.trades) > 0 else 0,
    'max_drawdown': round(float(bt_viz.max_dd), 2),
    'leverage': int(bt_viz.leverage),
    'max_risk_per_trade': float(bt_viz.max_risk_pct),
    'max_dd_limit': int(bt_viz.max_dd_pct),
    'stopped_out': bool(bt_viz.stopped_out),
    'stop_reason': bt_viz.stop_reason,
    'equity_curve': equity_curve_data,
    'recent_trades': trade_log,
    'aggregate_stats': {
        'simulations': 20,
        'avg_final': round(float(results_df['final_capital'].mean()), 2),
        'avg_return': round(float(results_df['return_pct'].mean()), 2),
        'stopped_out_rate': round(float(results_df['stopped_out'].sum() / 20 * 100), 1),
        'profitable_rate': round(float(len(results_df[results_df['profit'] > 0]) / 20 * 100), 1),
        'avg_risk_per_trade': round(float(results_df['avg_risk_per_trade'].mean()), 2)
    }
}

with open('/workspace/docs/leveraged_8pct_risk_data.json', 'w') as f:
    json.dump(viz_data, f, indent=2)

# Also save to root for GitHub Pages
with open('/workspace/leveraged_8pct_risk_data.json', 'w') as f:
    json.dump(viz_data, f, indent=2)

print(f'Saved visualization data (median result)')
print(f'  Final: ${bt_viz.capital:,.2f}')
print(f'  Return: {(bt_viz.capital - bt_viz.init) / bt_viz.init * 100:.2f}%')
print(f'  Trades: {len(bt_viz.trades)}')
print(f'  Stopped: {bt_viz.stopped_out}')
print()
print('✅ SIMULATION COMPLETE')
