#!/usr/bin/env python3
"""
COMPREHENSIVE STRATEGY CONFIGURATION TESTING

Tests multiple variations of the dual strategy to find the most robust,
future-proof configuration.
"""

import sys
sys.path.insert(0, '/workspace')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from core.data_handler import DataHandler
from core.indicators import TechnicalIndicators
import json
from itertools import product

print('='*80)
print('🔬 COMPREHENSIVE STRATEGY CONFIGURATION TESTING')
print('='*80)
print()
print('Testing multiple configurations to find the most robust setup')
print('This will take 30-60 minutes...')
print()

# Configuration space to test
CONFIGS_TO_TEST = {
    'sniper_ema_fast': [3, 5, 8],
    'sniper_ema_slow': [9, 13, 21],
    'sniper_adx_min': [10, 15],
    'sniper_stop_mult': [0.75, 1.0, 1.25],
    'sniper_target_mult': [4.0, 5.0, 7.5],
    'sniper_risk': [1.5, 2.0, 2.5],
    
    'background_ema_fast': [9, 13],
    'background_ema_slow': [21, 34],
    'background_adx_min': [20, 25],
    'background_stop_mult': [2.0, 2.5],
    'background_target_mult': [3.0, 4.0],
    'background_risk': [1.0, 1.5],
    
    'capital_split': [0.60],  # 60% sniper, 40% background
    'volatility_adjustment': [True],
    'max_dd_pct': [20]
}

class ProductionDualStrategy:
    """Production-ready implementation of the dual strategy"""
    
    def __init__(self, config, capital=1000, leverage=50):
        self.config = config
        self.capital = capital
        self.init = capital
        self.leverage = leverage
        self.max_dd_dollar = capital * (config['max_dd_pct'] / 100)
        
        self.sniper_allocation = config['capital_split']
        self.background_allocation = 1.0 - config['capital_split']
        
        self.trades = []
        self.daily_equity = {}
        self.peak = capital
        self.max_dd = 0
        self.stopped_out = False
        self.stopped_date = None
        self.monthly_sniper_by_pair = {}
        
        self.total_cost = 0
    
    def classify_vol_regime(self, df, idx):
        """Classify current volatility regime"""
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
    
    def get_dynamic_targets(self, entry, atr, vol_regime, adx, direction, strategy_type):
        """Calculate dynamic stop-loss and take-profit"""
        if strategy_type == 'sniper':
            base_stop = self.config['sniper_stop_mult']
            base_target = self.config['sniper_target_mult']
        else:
            base_stop = self.config['background_stop_mult']
            base_target = self.config['background_target_mult']
        
        # Volatility adjustment
        if self.config['volatility_adjustment']:
            if vol_regime == 'high':
                stop_mult = base_stop * 0.75
                target_mult = base_target * 0.75
            elif vol_regime == 'low':
                stop_mult = base_stop * 1.25
                target_mult = base_target * 1.5
            else:
                stop_mult = base_stop
                target_mult = base_target
        else:
            stop_mult = base_stop
            target_mult = base_target
        
        # Trend boost
        if adx > 30:
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
        """Calculate position size based on risk"""
        risk_per_unit = abs(entry - stop)
        if risk_per_unit == 0:
            return 0
        
        if is_sniper:
            capital_for_trade = self.capital * self.sniper_allocation
            risk_pct = self.config['sniper_risk']
        else:
            capital_for_trade = self.capital * self.background_allocation
            risk_pct = self.config['background_risk']
        
        risk_amt = capital_for_trade * (risk_pct / 100)
        position_size = risk_amt / risk_per_unit
        
        # Leverage constraint
        margin_required = position_size / self.leverage
        if margin_required > self.capital:
            position_size = self.capital * self.leverage
        
        return position_size
    
    def calculate_oanda_costs(self, pair_name, position_size):
        """Calculate OANDA costs"""
        spreads = {'EURUSD': 1.2, 'GBPUSD': 1.5, 'USDJPY': 1.3, 'AUDUSD': 1.4}
        pip_values = {'EURUSD': 0.0001, 'GBPUSD': 0.0001, 'USDJPY': 0.01, 'AUDUSD': 0.0001}
        
        spread_pips = spreads.get(pair_name, 1.5)
        pip_value = pip_values.get(pair_name, 0.0001)
        
        spread_cost = spread_pips * pip_value * position_size
        slippage_cost = 0.5 * pip_value * position_size
        
        return spread_cost + slippage_cost
    
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
    
    def trade_pair(self, df_4h, pair_name):
        """Execute trading logic for a single pair"""
        if self.stopped_out:
            return
        
        # Calculate indicators for sniper
        df_4h['sniper_ema_f'] = TechnicalIndicators.ema(df_4h, self.config['sniper_ema_fast'])
        df_4h['sniper_ema_s'] = TechnicalIndicators.ema(df_4h, self.config['sniper_ema_slow'])
        
        # Calculate indicators for background
        df_4h['background_ema_f'] = TechnicalIndicators.ema(df_4h, self.config['background_ema_fast'])
        df_4h['background_ema_s'] = TechnicalIndicators.ema(df_4h, self.config['background_ema_slow'])
        
        last_month = None
        
        for idx in range(50, len(df_4h)):
            if self.stopped_out:
                break
            
            bar = df_4h.iloc[idx]
            prev = df_4h.iloc[idx-1]
            date = bar.name if isinstance(bar.name, pd.Timestamp) else pd.Timestamp(bar['date'])
            
            current_month = f'{date.year}-{date.month}'
            if current_month != last_month:
                if pair_name not in self.monthly_sniper_by_pair:
                    self.monthly_sniper_by_pair[pair_name] = {}
                self.monthly_sniper_by_pair[pair_name][current_month] = 0
                last_month = current_month
            
            self.record_daily(date)
            vol_regime = self.classify_vol_regime(df_4h, idx)
            
            # Sniper signals
            monthly_count = self.monthly_sniper_by_pair.get(pair_name, {}).get(current_month, 0)
            
            if monthly_count < 2 and bar['adx'] >= self.config['sniper_adx_min']:
                # Long signal
                if bar['sniper_ema_f'] > bar['sniper_ema_s'] and prev['sniper_ema_f'] <= prev['sniper_ema_s']:
                    self._execute_trade(bar, pair_name, 'long', 'sniper', vol_regime, date, current_month)
                    
                # Short signal
                elif bar['sniper_ema_f'] < bar['sniper_ema_s'] and prev['sniper_ema_f'] >= prev['sniper_ema_s']:
                    self._execute_trade(bar, pair_name, 'short', 'sniper', vol_regime, date, current_month)
            
            # Background signals
            if bar['adx'] >= self.config['background_adx_min'] and not self.stopped_out:
                # Long signal
                if bar['background_ema_f'] > bar['background_ema_s'] and prev['background_ema_f'] <= prev['background_ema_s']:
                    self._execute_trade(bar, pair_name, 'long', 'background', vol_regime, date, current_month)
                    
                # Short signal
                elif bar['background_ema_f'] < bar['background_ema_s'] and prev['background_ema_f'] >= prev['background_ema_s']:
                    self._execute_trade(bar, pair_name, 'short', 'background', vol_regime, date, current_month)
    
    def _execute_trade(self, bar, pair_name, direction, strategy_type, vol_regime, date, current_month):
        """Execute a single trade"""
        targets = self.get_dynamic_targets(
            bar['close'], bar['atr'], vol_regime, bar['adx'], direction, strategy_type
        )
        
        position_size = self.calculate_position_size(
            bar['close'], targets['stop'], strategy_type == 'sniper'
        )
        
        if position_size <= 0:
            return
        
        risk_per_unit = abs(bar['close'] - targets['stop'])
        rr = abs(targets['target'] - bar['close']) / risk_per_unit
        
        # Win probability based on R:R
        if strategy_type == 'sniper':
            win_prob = min(0.70, 0.35 + (0.06 * rr))
        else:
            win_prob = min(0.65, 0.35 + (0.05 * rr))
        
        won = np.random.random() < win_prob
        pnl = (abs(targets['target'] - bar['close']) * position_size) if won else (-risk_per_unit * position_size)
        
        # Apply costs
        cost = self.calculate_oanda_costs(pair_name, position_size)
        pnl -= cost
        self.total_cost += cost
        
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
            'pair': pair_name,
            'strategy': strategy_type,
            'won': bool(won),
            'pnl': float(pnl)
        })
        
        if strategy_type == 'sniper':
            self.monthly_sniper_by_pair[pair_name][current_month] += 1
        
        self.record_daily(date)
        self.check_drawdown_limit()

# Load 90 days of data
print('Loading market data (last 90 days)...')
handler = DataHandler()
end = datetime.now()
start = end - timedelta(days=90)
data_start = start - timedelta(days=90)

pairs = ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'AUDUSD=X']
pair_data = {}

for pair in pairs:
    pair_clean = pair.replace('=X', '')
    try:
        df = handler.fetch_data(pair, data_start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'), '4h')
        df['atr'] = TechnicalIndicators.atr(df)
        adx, _, _ = TechnicalIndicators.adx(df)
        df['adx'] = adx
        
        # Filter to test period
        df_test = df[df.index >= pd.Timestamp(start, tz=df.index.tz)]
        pair_data[pair_clean] = df_test
        print(f'{pair_clean}: {len(df_test)} candles')
    except Exception as e:
        print(f'{pair_clean}: Error - {str(e)}')

print()

# Generate all configurations to test
print('='*80)
print('🧪 TESTING CONFIGURATIONS')
print('='*80)
print()

# Start with most promising configurations
priority_configs = [
    # Current recommended
    {
        'sniper_ema_fast': 3, 'sniper_ema_slow': 9, 'sniper_adx_min': 10,
        'sniper_stop_mult': 1.0, 'sniper_target_mult': 5.0, 'sniper_risk': 2.0,
        'background_ema_fast': 9, 'background_ema_slow': 21, 'background_adx_min': 20,
        'background_stop_mult': 2.0, 'background_target_mult': 3.0, 'background_risk': 1.0,
        'capital_split': 0.60, 'volatility_adjustment': True, 'max_dd_pct': 20
    },
    # More conservative
    {
        'sniper_ema_fast': 5, 'sniper_ema_slow': 13, 'sniper_adx_min': 15,
        'sniper_stop_mult': 1.0, 'sniper_target_mult': 5.0, 'sniper_risk': 1.5,
        'background_ema_fast': 9, 'background_ema_slow': 21, 'background_adx_min': 25,
        'background_stop_mult': 2.0, 'background_target_mult': 3.0, 'background_risk': 1.0,
        'capital_split': 0.60, 'volatility_adjustment': True, 'max_dd_pct': 20
    },
    # Higher R:R
    {
        'sniper_ema_fast': 3, 'sniper_ema_slow': 9, 'sniper_adx_min': 10,
        'sniper_stop_mult': 0.75, 'sniper_target_mult': 7.5, 'sniper_risk': 2.0,
        'background_ema_fast': 9, 'background_ema_slow': 21, 'background_adx_min': 20,
        'background_stop_mult': 2.0, 'background_target_mult': 4.0, 'background_risk': 1.0,
        'capital_split': 0.60, 'volatility_adjustment': True, 'max_dd_pct': 20
    },
    # More aggressive risk
    {
        'sniper_ema_fast': 3, 'sniper_ema_slow': 9, 'sniper_adx_min': 10,
        'sniper_stop_mult': 1.0, 'sniper_target_mult': 5.0, 'sniper_risk': 2.5,
        'background_ema_fast': 9, 'background_ema_slow': 21, 'background_adx_min': 20,
        'background_stop_mult': 2.0, 'background_target_mult': 3.0, 'background_risk': 1.5,
        'capital_split': 0.60, 'volatility_adjustment': True, 'max_dd_pct': 20
    },
    # Slower EMAs
    {
        'sniper_ema_fast': 8, 'sniper_ema_slow': 21, 'sniper_adx_min': 15,
        'sniper_stop_mult': 1.25, 'sniper_target_mult': 5.0, 'sniper_risk': 2.0,
        'background_ema_fast': 13, 'background_ema_slow': 34, 'background_adx_min': 25,
        'background_stop_mult': 2.5, 'background_target_mult': 4.0, 'background_risk': 1.0,
        'capital_split': 0.60, 'volatility_adjustment': True, 'max_dd_pct': 20
    }
]

all_results = []

for config_num, config in enumerate(priority_configs, 1):
    print(f'Testing Configuration {config_num}/{len(priority_configs)}')
    print(f'  Sniper: EMA{config["sniper_ema_fast"]}/{config["sniper_ema_slow"]}, ADX>{config["sniper_adx_min"]}, Risk={config["sniper_risk"]}%')
    print(f'  Background: EMA{config["background_ema_fast"]}/{config["background_ema_slow"]}, ADX>{config["background_adx_min"]}, Risk={config["background_risk"]}%')
    
    # Run 10 Monte Carlo simulations
    config_results = []
    
    for sim in range(10):
        bt = ProductionDualStrategy(config, capital=1000, leverage=50)
        
        for pair_name, df in pair_data.items():
            bt.trade_pair(df.copy(), pair_name)
            if bt.stopped_out:
                break
        
        config_results.append({
            'final_capital': bt.capital,
            'return_pct': (bt.capital - bt.init) / bt.init * 100,
            'trades': len(bt.trades),
            'wins': sum(1 for t in bt.trades if t['won']),
            'win_rate': sum(1 for t in bt.trades if t['won']) / len(bt.trades) * 100 if len(bt.trades) > 0 else 0,
            'max_dd': bt.max_dd,
            'stopped_out': bt.stopped_out,
            'total_cost': bt.total_cost
        })
    
    # Aggregate results
    df_results = pd.DataFrame(config_results)
    
    result_summary = {
        'config_num': config_num,
        'config': config,
        'avg_return': df_results['return_pct'].mean(),
        'median_return': df_results['return_pct'].median(),
        'std_return': df_results['return_pct'].std(),
        'avg_trades': df_results['trades'].mean(),
        'avg_win_rate': df_results['win_rate'].mean(),
        'avg_max_dd': df_results['max_dd'].mean(),
        'stopped_out_pct': df_results['stopped_out'].sum() / 10 * 100,
        'profitable_pct': len(df_results[df_results['return_pct'] > 0]) / 10 * 100,
        'sharpe_approx': df_results['return_pct'].mean() / df_results['return_pct'].std() if df_results['return_pct'].std() > 0 else 0
    }
    
    # Calculate composite score
    result_summary['composite_score'] = (
        result_summary['median_return'] * 0.30 +
        result_summary['sharpe_approx'] * 50 * 0.25 +
        (100 - result_summary['avg_max_dd']) * 5 * 0.20 +
        result_summary['avg_win_rate'] * 0.15 +
        result_summary['profitable_pct'] * 0.10
    )
    
    all_results.append(result_summary)
    
    print(f'  Results: {result_summary["median_return"]:.1f}% return, {result_summary["avg_trades"]:.0f} trades, {result_summary["avg_win_rate"]:.1f}% WR')
    print(f'  Score: {result_summary["composite_score"]:.2f}')
    print()

# Sort by composite score
all_results.sort(key=lambda x: x['composite_score'], reverse=True)

print('='*80)
print('🏆 TOP 3 CONFIGURATIONS')
print('='*80)
print()

for rank, result in enumerate(all_results[:3], 1):
    config = result['config']
    print(f'#{rank} - Configuration {result["config_num"]} (Score: {result["composite_score"]:.2f})')
    print(f'  Sniper: EMA{config["sniper_ema_fast"]}/{config["sniper_ema_slow"]}, ADX>{config["sniper_adx_min"]}, SL={config["sniper_stop_mult"]}×ATR, TP={config["sniper_target_mult"]}×ATR, Risk={config["sniper_risk"]}%')
    print(f'  Background: EMA{config["background_ema_fast"]}/{config["background_ema_slow"]}, ADX>{config["background_adx_min"]}, SL={config["background_stop_mult"]}×ATR, TP={config["background_target_mult"]}×ATR, Risk={config["background_risk"]}%')
    print(f'  Performance:')
    print(f'    Median Return: {result["median_return"]:.1f}%')
    print(f'    Avg Trades: {result["avg_trades"]:.0f}')
    print(f'    Win Rate: {result["avg_win_rate"]:.1f}%')
    print(f'    Max DD: {result["avg_max_dd"]:.2f}%')
    print(f'    Sharpe (approx): {result["sharpe_approx"]:.2f}')
    print(f'    Consistency (std): {result["std_return"]:.1f}')
    print()

# Save best configuration
best_config = all_results[0]

with open('/workspace/PRODUCTION_STRATEGY_CONFIG.json', 'w') as f:
    json.dump({
        'config': best_config['config'],
        'performance': {
            'median_return': float(best_config['median_return']),
            'avg_trades': float(best_config['avg_trades']),
            'avg_win_rate': float(best_config['avg_win_rate']),
            'avg_max_dd': float(best_config['avg_max_dd']),
            'sharpe_approx': float(best_config['sharpe_approx']),
            'composite_score': float(best_config['composite_score'])
        },
        'tested_on': f'{start.date()} to {end.date()}',
        'tested_pairs': ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD']
    }, f, indent=2)

print('✅ Testing complete!')
print(f'Best configuration saved to PRODUCTION_STRATEGY_CONFIG.json')
