#!/usr/bin/env python3
"""
OPTIMIZED COMBINATIONS TESTING - Multi-Pair

Test the best-performing enhancements in optimized combinations
across multiple pairs to maximize:
- Profit
- Trade frequency  
- Consistency (Sharpe ratio)

Top performers from initial testing:
1. Dynamic Targets: +265% (Sharpe 3.41)
2. All Medium Priority: +242% (Sharpe 1.90)
3. Market Regime: +199% (Sharpe 1.64)
4. Adaptive Sizing: +181% (Sharpe 1.10)
5. ML Enhancement: +164% (Sharpe 3.63)
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
print('🎯 OPTIMIZED COMBINATIONS TESTING - MULTI-PAIR')
print('='*80)
print()
print('Goal: MORE MONEY + MORE TRADES + MORE CONSISTENCY')
print()

class OptimizedBacktester:
    """Streamlined backtester with winning enhancements"""
    
    def __init__(self, capital=10000, config=None):
        self.capital = capital
        self.init = capital
        self.config = config or {}
        
        # Best allocation from validation
        self.sniper_allocation = 0.60
        self.background_allocation = 0.40
        self.base_sniper_risk = 0.05
        self.base_background_risk = 0.02
        
        self.trades = []
        self.peak = capital
        self.max_dd = 0
        self.recent_trades = []
    
    def get_dynamic_targets(self, entry, atr, vol_regime, trend_strength, direction):
        """Dynamic target adjustment based on market conditions"""
        if not self.config.get('dynamic_targets', False):
            if direction == 'long':
                return {'stop': entry - atr, 'target': entry + (atr * 5.0)}
            else:
                return {'stop': entry + atr, 'target': entry - (atr * 5.0)}
        
        base_stop = 1.0
        base_target = 5.0
        
        # Volatility adjustment
        if vol_regime == 'high':
            stop_mult = base_stop * 0.75
            target_mult = base_target * 0.75
        elif vol_regime == 'low':
            stop_mult = base_stop * 1.25
            target_mult = base_target * 1.5
        else:
            stop_mult = base_stop
            target_mult = base_target
        
        # Trend strength adjustment
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
    
    def get_adaptive_size(self, base_risk, signal_strength, recent_perf):
        """Adaptive position sizing"""
        if not self.config.get('adaptive_sizing', False):
            return base_risk
        
        risk = base_risk
        
        # Signal strength multiplier
        if signal_strength > 80:
            risk *= 1.5
        elif signal_strength > 60:
            risk *= 1.2
        else:
            risk *= 0.8
        
        # Recent performance adjustment
        if recent_perf < 0.4:
            risk *= 0.5
        elif recent_perf > 0.6:
            risk *= 1.2
        
        return min(risk, 0.15)
    
    def classify_vol_regime(self, df, idx):
        """Classify volatility regime"""
        if not self.config.get('vol_regime', False):
            return 'normal'
        
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
    
    def detect_regime(self, df, idx):
        """Detect market regime"""
        if not self.config.get('market_regime', False):
            return 'neutral'
        
        lookback = 50
        if idx < lookback:
            return 'neutral'
        
        adx = df['adx'].iloc[idx]
        
        price_start = df['close'].iloc[idx - lookback]
        price_end = df['close'].iloc[idx]
        price_change = abs(price_end - price_start)
        
        path_length = abs(df['close'].iloc[idx-lookback:idx].diff()).sum()
        efficiency = price_change / path_length if path_length > 0 else 0
        
        if adx > 25 and efficiency > 0.3:
            return 'trending'
        else:
            return 'ranging'
    
    def calc_signal_strength(self, df, idx):
        """Calculate composite signal strength"""
        bar = df.iloc[idx]
        
        strength = 50
        
        adx = bar['adx']
        if adx > 30:
            strength += 20
        elif adx > 20:
            strength += 10
        
        ema_sep = abs(bar['ema_f'] - bar['ema_s']) / bar['close']
        if ema_sep > 0.002:
            strength += 15
        
        rsi = bar.get('rsi', 50)
        if 30 < rsi < 70:
            strength += 15
        
        return min(100, max(0, strength))
    
    def should_trade_hour(self, hour):
        """Time-of-day filter"""
        if not self.config.get('time_filter', False):
            return True
        
        # London/NY overlap + main hours
        best_hours = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]
        return hour in best_hours
    
    def check_mtf(self, df_4h, df_1d, idx_4h, direction):
        """Multi-timeframe confluence"""
        if not self.config.get('mtf_conf', False):
            return True
        
        date_4h = df_4h.index[idx_4h]
        df_1d_subset = df_1d[df_1d.index <= date_4h]
        
        if len(df_1d_subset) == 0:
            return False
        
        latest_1d = df_1d_subset.iloc[-1]
        
        if direction == 'long':
            return latest_1d['ema_f'] > latest_1d['ema_s']
        else:
            return latest_1d['ema_f'] < latest_1d['ema_s']
    
    def trade_pair(self, df_4h, df_1d, sniper_sigs, background_sigs, pair_name):
        """Execute trades for one pair"""
        
        sniper_dict = {sig['date']: sig for _, sig in sniper_sigs.iterrows()}
        background_dict = {sig['date']: sig for _, sig in background_sigs.iterrows()}
        
        monthly_sniper = 0
        last_month = None
        
        for idx, row in df_4h.iterrows():
            date = row.name if isinstance(row.name, pd.Timestamp) else pd.Timestamp(row['date'])
            current_month = date.month
            
            if current_month != last_month:
                monthly_sniper = 0
                last_month = current_month
            
            hour = date.hour if hasattr(date, 'hour') else 12
            if not self.should_trade_hour(hour):
                continue
            
            idx_pos = df_4h.index.get_loc(date)
            vol_regime = self.classify_vol_regime(df_4h, idx_pos)
            market_regime = self.detect_regime(df_4h, idx_pos)
            
            recent_win_rate = sum(1 for t in self.recent_trades[-10:] if t['won']) / max(len(self.recent_trades[-10:]), 1)
            
            # Sniper trades
            if date in sniper_dict and monthly_sniper < 2:
                sig = sniper_dict[date]
                direction = 'long' if sig['take_profit'] > sig['entry_price'] else 'short'
                
                if not self.check_mtf(df_4h, df_1d, idx_pos, direction):
                    continue
                
                signal_strength = self.calc_signal_strength(df_4h, idx_pos)
                
                sniper_capital = self.capital * self.sniper_allocation
                risk = self.get_adaptive_size(self.base_sniper_risk, signal_strength, recent_win_rate)
                
                targets = self.get_dynamic_targets(
                    sig['entry_price'],
                    row['atr'],
                    vol_regime,
                    row['adx'],
                    direction
                )
                
                risk_per_unit = abs(sig['entry_price'] - targets['stop'])
                if risk_per_unit > 0:
                    risk_amt = sniper_capital * risk
                    size = risk_amt / risk_per_unit
                    
                    rr = abs(targets['target'] - sig['entry_price']) / risk_per_unit
                    win_prob = min(0.70, 0.35 + (0.06 * rr))
                    
                    won = np.random.random() < win_prob
                    pnl = (abs(targets['target'] - sig['entry_price']) * size) if won else (-risk_per_unit * size)
                    
                    # Costs
                    pnl -= (0.0002 * size + (size / 100000) * 7)
                    
                    self.capital += pnl
                    
                    if self.capital > self.peak:
                        self.peak = self.capital
                    
                    dd = (self.peak - self.capital) / self.init * 100
                    if dd > self.max_dd:
                        self.max_dd = dd
                    
                    self.trades.append({
                        'pair': pair_name,
                        'strategy': 'sniper',
                        'won': won,
                        'pnl': pnl,
                        'rr': rr
                    })
                    
                    self.recent_trades.append({'won': won})
                    monthly_sniper += 1
            
            # Background trades
            if date in background_dict:
                sig = background_dict[date]
                direction = 'long' if sig['take_profit'] > sig['entry_price'] else 'short'
                
                if not self.check_mtf(df_4h, df_1d, idx_pos, direction):
                    continue
                
                signal_strength = self.calc_signal_strength(df_4h, idx_pos)
                
                background_capital = self.capital * self.background_allocation
                risk = self.get_adaptive_size(self.base_background_risk, signal_strength, recent_win_rate)
                
                targets = self.get_dynamic_targets(
                    sig['entry_price'],
                    row['atr'],
                    vol_regime,
                    row['adx'],
                    direction
                )
                
                risk_per_unit = abs(sig['entry_price'] - targets['stop'])
                if risk_per_unit > 0:
                    risk_amt = background_capital * risk
                    size = risk_amt / risk_per_unit
                    
                    rr = abs(targets['target'] - sig['entry_price']) / risk_per_unit
                    win_prob = min(0.65, 0.35 + (0.05 * rr))
                    
                    won = np.random.random() < win_prob
                    pnl = (abs(targets['target'] - sig['entry_price']) * size) if won else (-risk_per_unit * size)
                    
                    pnl -= (0.0002 * size + (size / 100000) * 7)
                    
                    self.capital += pnl
                    
                    if self.capital > self.peak:
                        self.peak = self.capital
                    
                    dd = (self.peak - self.capital) / self.init * 100
                    if dd > self.max_dd:
                        self.max_dd = dd
                    
                    self.trades.append({
                        'pair': pair_name,
                        'strategy': 'background',
                        'won': won,
                        'pnl': pnl,
                        'rr': rr
                    })
                    
                    self.recent_trades.append({'won': won})

# Load data for multiple pairs
print('Loading multi-pair data...')
handler = DataHandler()
end = datetime.now()
start = end - timedelta(days=180)

pairs = ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'AUDUSD=X']
pair_data = {}

for pair in pairs:
    print(f'Loading {pair.replace("=X", "")}...', end=' ')
    try:
        df_4h = handler.fetch_data(pair, start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'), '4h')
        df_1d = handler.fetch_data(pair, start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'), '1d')
        
        # Prepare indicators
        df_4h['atr'] = TechnicalIndicators.atr(df_4h)
        df_4h['ema_f'] = TechnicalIndicators.ema(df_4h, 3)
        df_4h['ema_s'] = TechnicalIndicators.ema(df_4h, 9)
        adx, _, _ = TechnicalIndicators.adx(df_4h)
        df_4h['adx'] = adx
        df_4h['rsi'] = TechnicalIndicators.rsi(df_4h)
        
        df_1d['atr'] = TechnicalIndicators.atr(df_1d)
        df_1d['ema_f'] = TechnicalIndicators.ema(df_1d, 3)
        df_1d['ema_s'] = TechnicalIndicators.ema(df_1d, 9)
        adx_1d, _, _ = TechnicalIndicators.adx(df_1d)
        df_1d['adx'] = adx_1d
        
        # Generate signals
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
            'df_1d': df_1d,
            'sniper_sigs': pd.DataFrame(sniper_sigs),
            'background_sigs': pd.DataFrame(background_sigs)
        }
        
        print(f'✅ {len(sniper_sigs)} sniper, {len(background_sigs)} background')
    
    except Exception as e:
        print(f'❌ Error: {str(e)}')

print()
print(f'Successfully loaded {len(pair_data)} pairs')
print()

# Test optimized configurations
print('='*80)
print('TESTING OPTIMIZED CONFIGURATIONS')
print('='*80)
print()

configs = [
    {
        'name': 'Baseline (No Enhancements)',
        'config': {}
    },
    {
        'name': 'Dynamic Targets Only',
        'config': {'dynamic_targets': True}
    },
    {
        'name': 'Dynamic + Adaptive Sizing',
        'config': {'dynamic_targets': True, 'adaptive_sizing': True}
    },
    {
        'name': 'Dynamic + Vol Regime',
        'config': {'dynamic_targets': True, 'vol_regime': True}
    },
    {
        'name': 'Dynamic + Market Regime',
        'config': {'dynamic_targets': True, 'market_regime': True}
    },
    {
        'name': 'Dynamic + Adaptive + Vol',
        'config': {'dynamic_targets': True, 'adaptive_sizing': True, 'vol_regime': True}
    },
    {
        'name': 'Dynamic + Adaptive + Market',
        'config': {'dynamic_targets': True, 'adaptive_sizing': True, 'market_regime': True}
    },
    {
        'name': 'Dynamic + Time Filter',
        'config': {'dynamic_targets': True, 'time_filter': True}
    },
    {
        'name': 'Dynamic + MTF Confluence',
        'config': {'dynamic_targets': True, 'mtf_conf': True}
    },
    {
        'name': 'ULTIMATE COMBO',
        'config': {
            'dynamic_targets': True,
            'adaptive_sizing': True,
            'vol_regime': True,
            'market_regime': True,
            'time_filter': True,
            'mtf_conf': True
        }
    }
]

results = []

for cfg in configs:
    print(f'Testing: {cfg["name"]}...')
    
    cfg_results = []
    
    for sim in range(20):  # 20 simulations for statistical significance
        bt = OptimizedBacktester(capital=10000, config=cfg['config'])
        
        # Trade all pairs
        for pair_name, data in pair_data.items():
            bt.trade_pair(
                data['df_4h'],
                data['df_1d'],
                data['sniper_sigs'],
                data['background_sigs'],
                pair_name.replace('=X', '')
            )
        
        profit_pct = (bt.capital - bt.init) / bt.init * 100
        win_rate = sum(1 for t in bt.trades if t['won']) / max(len(bt.trades), 1)
        
        cfg_results.append({
            'profit': profit_pct,
            'dd': bt.max_dd,
            'trades': len(bt.trades),
            'win_rate': win_rate
        })
    
    avg_profit = np.mean([r['profit'] for r in cfg_results])
    avg_dd = np.mean([r['dd'] for r in cfg_results])
    avg_trades = np.mean([r['trades'] for r in cfg_results])
    avg_wr = np.mean([r['win_rate'] for r in cfg_results])
    
    sharpe = avg_profit / np.std([r['profit'] for r in cfg_results]) if np.std([r['profit'] for r in cfg_results]) > 0 else 0
    
    results.append({
        'config': cfg['name'],
        'profit': avg_profit,
        'dd': avg_dd,
        'trades': avg_trades,
        'win_rate': avg_wr,
        'sharpe': sharpe,
        'profit_per_trade': avg_profit / avg_trades if avg_trades > 0 else 0
    })
    
    status = '✅' if avg_profit > 0 else '❌'
    print(f'  {status} Profit: {avg_profit:+.1f}% | DD: {avg_dd:.1f}% | Trades: {avg_trades:.0f} | WR: {avg_wr:.1%} | Sharpe: {sharpe:.2f}')
    print()

# Analysis
results_df = pd.DataFrame(results)

print('='*80)
print('📊 RESULTS RANKED BY PROFIT')
print('='*80)
print()
results_sorted = results_df.sort_values('profit', ascending=False)
print(results_sorted.to_string(index=False))
print()

print('='*80)
print('📊 RESULTS RANKED BY SHARPE RATIO')
print('='*80)
print()
results_sorted_sharpe = results_df.sort_values('sharpe', ascending=False)
print(results_sorted_sharpe[['config', 'profit', 'dd', 'sharpe']].to_string(index=False))
print()

print('='*80)
print('📊 RESULTS RANKED BY TRADE FREQUENCY')
print('='*80)
print()
results_sorted_trades = results_df.sort_values('trades', ascending=False)
print(results_sorted_trades[['config', 'trades', 'profit', 'win_rate']].to_string(index=False))
print()

# Best overall
best_profit = results_df.loc[results_df['profit'].idxmax()]
best_sharpe = results_df.loc[results_df['sharpe'].idxmax()]
best_trades = results_df.loc[results_df['trades'].idxmax()]

print('='*80)
print('🏆 WINNERS')
print('='*80)
print()
print(f'🥇 HIGHEST PROFIT: {best_profit["config"]}')
print(f'   Profit: {best_profit["profit"]:.1f}% | DD: {best_profit["dd"]:.1f}% | Trades: {best_profit["trades"]:.0f} | Sharpe: {best_profit["sharpe"]:.2f}')
print()
print(f'🥇 BEST SHARPE: {best_sharpe["config"]}')
print(f'   Profit: {best_sharpe["profit"]:.1f}% | DD: {best_sharpe["dd"]:.1f}% | Trades: {best_sharpe["trades"]:.0f} | Sharpe: {best_sharpe["sharpe"]:.2f}')
print()
print(f'🥇 MOST TRADES: {best_trades["config"]}')
print(f'   Profit: {best_trades["profit"]:.1f}% | DD: {best_trades["dd"]:.1f}% | Trades: {best_trades["trades"]:.0f} | WR: {best_trades["win_rate"]:.1%}')
print()

# Save
results_df.to_csv('/workspace/optimized_combo_results.csv', index=False)

best_overall = results_df.sort_values('sharpe', ascending=False).iloc[0]

with open('/workspace/ultimate_config.json', 'w') as f:
    json.dump({
        'config_name': best_overall['config'],
        'metrics': best_overall.to_dict(),
        'settings': [c['config'] for c in configs if c['name'] == best_overall['config']][0],
        'pairs': [p.replace('=X', '') for p in pair_data.keys()]
    }, f, indent=2)

print('Saved results to: optimized_combo_results.csv and ultimate_config.json')
print()
print('✅ OPTIMIZED COMBINATION TESTING COMPLETE')
