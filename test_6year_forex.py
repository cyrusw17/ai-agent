#!/usr/bin/env python3
"""
6-Year Historical Backtest (2018-2024) - Production Strategy on Forex
Tests the production dual strategy across major market events:
- Pre-COVID (2018-2019)
- COVID crash and recovery (2020-2021)
- Post-COVID rate hikes (2022-2023)
- Recent market (2024)
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import warnings
warnings.filterwarnings('ignore')

# Load production config
with open('PRODUCTION_STRATEGY_CONFIG.json', 'r') as f:
    prod_data = json.load(f)
    CONFIG = prod_data['config']

# Forex pairs (using forex=X format for yfinance)
FOREX_PAIRS = {
    'EURUSD': 'EURUSD=X',
    'GBPUSD': 'GBPUSD=X',
    'USDJPY': 'USDJPY=X',
    'AUDUSD': 'AUDUSD=X'
}

print("=" * 80)
print("6-YEAR FOREX BACKTEST (2018-2024)")
print("=" * 80)
print(f"Production Config:")
print(f"  Sniper: EMA{CONFIG['sniper_ema_fast']}/{CONFIG['sniper_ema_slow']}, "
      f"ADX>{CONFIG['sniper_adx_min']}, Risk={CONFIG['sniper_risk']}%")
print(f"  Background: EMA{CONFIG['background_ema_fast']}/{CONFIG['background_ema_slow']}, "
      f"ADX>{CONFIG['background_adx_min']}, Risk={CONFIG['background_risk']}%")
print(f"  Capital Split: {CONFIG['capital_split']*100:.0f}% Sniper / {(1-CONFIG['capital_split'])*100:.0f}% Background")
print(f"  Max Drawdown Limit: {CONFIG['max_dd_pct']}%")
print()


class SixYearBacktester:
    """Backtester for 6-year historical period"""
    
    def __init__(self, config, capital=1000, leverage=50):
        self.config = config
        self.init = capital
        self.capital = capital
        self.leverage = leverage
        self.max_dd_pct = config['max_dd_pct']
        self.high_water = capital
        
        self.sniper_capital = capital * config['capital_split']
        self.bg_capital = capital * (1 - config['capital_split'])
        
        self.trades = []
        self.daily_equity = []
        self.active_sniper = None
        self.active_bg = None
        
        self.yearly_stats = {}
        
    def calculate_indicators(self, df):
        """Calculate all technical indicators"""
        # EMAs for sniper
        df['ema_fast_s'] = df['close'].ewm(span=self.config['sniper_ema_fast']).mean()
        df['ema_slow_s'] = df['close'].ewm(span=self.config['sniper_ema_slow']).mean()
        
        # EMAs for background
        df['ema_fast_b'] = df['close'].ewm(span=self.config['background_ema_fast']).mean()
        df['ema_slow_b'] = df['close'].ewm(span=self.config['background_ema_slow']).mean()
        
        # ATR
        df['high_low'] = df['high'] - df['low']
        df['high_close'] = abs(df['high'] - df['close'].shift())
        df['low_close'] = abs(df['low'] - df['close'].shift())
        df['tr'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
        df['atr'] = df['tr'].rolling(14).mean()
        
        # ADX
        df['up_move'] = df['high'] - df['high'].shift()
        df['down_move'] = df['low'].shift() - df['low']
        df['plus_dm'] = np.where((df['up_move'] > df['down_move']) & (df['up_move'] > 0), df['up_move'], 0)
        df['minus_dm'] = np.where((df['down_move'] > df['up_move']) & (df['down_move'] > 0), df['down_move'], 0)
        df['plus_di'] = 100 * (df['plus_dm'].rolling(14).mean() / df['atr'])
        df['minus_di'] = 100 * (df['minus_dm'].rolling(14).mean() / df['atr'])
        df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
        df['adx'] = df['dx'].rolling(14).mean()
        
        # Volatility regime
        df['volatility'] = df['close'].pct_change().rolling(20).std() * 100
        df['vol_ma'] = df['volatility'].rolling(50).mean()
        
        return df
    
    def classify_regime(self, row):
        """Classify market regime"""
        if pd.isna(row['vol_ma']) or pd.isna(row['volatility']):
            return 'normal'
        
        if row['volatility'] > row['vol_ma'] * 1.5:
            return 'high_vol'
        elif row['volatility'] < row['vol_ma'] * 0.7:
            return 'low_vol'
        return 'normal'
    
    def calculate_costs(self, position_size):
        """Estimate trading costs (OANDA-style)"""
        # Using average spread of 1.3 pips and 0.5 pips slippage
        spread_cost = position_size * 0.00013
        slippage = position_size * 0.00005
        return spread_cost + slippage
    
    def calculate_position_size(self, entry, stop, risk_pct, allocated_capital):
        """Calculate position size with leverage"""
        risk_amt = allocated_capital * (risk_pct / 100)
        stop_distance = abs(entry - stop)
        
        if stop_distance == 0:
            return 0
        
        base_size = risk_amt / stop_distance
        leveraged_size = base_size * self.leverage
        
        # Cap at 80% of allocated capital
        max_size = allocated_capital * 0.8
        return min(leveraged_size, max_size)
    
    def check_drawdown(self):
        """Check if max drawdown exceeded"""
        self.high_water = max(self.high_water, self.capital)
        dd_pct = ((self.high_water - self.capital) / self.high_water) * 100
        return dd_pct >= self.max_dd_pct
    
    def generate_signal(self, row, is_sniper=True):
        """Generate trading signal"""
        if is_sniper:
            ema_fast = row['ema_fast_s']
            ema_slow = row['ema_slow_s']
            adx_min = self.config['sniper_adx_min']
            stop_mult = self.config['sniper_stop_mult']
            target_mult = self.config['sniper_target_mult']
            risk = self.config['sniper_risk']
        else:
            ema_fast = row['ema_fast_b']
            ema_slow = row['ema_slow_b']
            adx_min = self.config['background_adx_min']
            stop_mult = self.config['background_stop_mult']
            target_mult = self.config['background_target_mult']
            risk = self.config['background_risk']
        
        if pd.isna(ema_fast) or pd.isna(ema_slow) or pd.isna(row['adx']) or pd.isna(row['atr']):
            return None
        
        if row['adx'] < adx_min:
            return None
        
        # Dynamic target adjustment
        regime = self.classify_regime(row)
        if self.config['volatility_adjustment']:
            if regime == 'high_vol':
                target_mult *= 1.2
            elif regime == 'low_vol':
                target_mult *= 0.8
        
        # Long signal
        if ema_fast > ema_slow and row['close'] > ema_fast:
            stop = row['close'] - (row['atr'] * stop_mult)
            target = row['close'] + (row['atr'] * target_mult)
            
            return {
                'direction': 'long',
                'entry': row['close'],
                'stop': stop,
                'target': target,
                'risk': risk,
                'is_sniper': is_sniper
            }
        
        # Short signal
        elif ema_fast < ema_slow and row['close'] < ema_fast:
            stop = row['close'] + (row['atr'] * stop_mult)
            target = row['close'] - (row['atr'] * target_mult)
            
            return {
                'direction': 'short',
                'entry': row['close'],
                'stop': stop,
                'target': target,
                'risk': risk,
                'is_sniper': is_sniper
            }
        
        return None
    
    def check_exit(self, trade, row):
        """Check if trade should exit"""
        if trade['direction'] == 'long':
            if row['low'] <= trade['stop']:
                return 'stop', trade['stop']
            elif row['high'] >= trade['target']:
                return 'target', trade['target']
        else:  # short
            if row['high'] >= trade['stop']:
                return 'stop', trade['stop']
            elif row['low'] <= trade['target']:
                return 'target', trade['target']
        
        return None, None
    
    def record_daily_equity(self, date):
        """Record daily equity snapshot"""
        self.daily_equity.append({
            'date': date.strftime('%Y-%m-%d'),
            'capital': float(self.capital),
            'sniper': float(self.sniper_capital),
            'background': float(self.bg_capital),
            'high_water': float(self.high_water)
        })
    
    def run(self, df, pair_name):
        """Run backtest on data"""
        df = self.calculate_indicators(df)
        
        current_year = None
        
        for idx, row in df.iterrows():
            # Track yearly stats
            year = idx.year
            if year != current_year:
                if current_year is not None:
                    self.yearly_stats[current_year]['end_capital'] = self.capital
                current_year = year
                if year not in self.yearly_stats:
                    self.yearly_stats[year] = {
                        'start_capital': self.capital,
                        'trades': 0,
                        'wins': 0,
                        'losses': 0
                    }
            
            if self.check_drawdown():
                break
            
            # Check active trades
            if self.active_sniper:
                exit_type, exit_price = self.check_exit(self.active_sniper, row)
                if exit_type:
                    pnl = (exit_price - self.active_sniper['entry']) * self.active_sniper['size']
                    if self.active_sniper['direction'] == 'short':
                        pnl = -pnl
                    
                    costs = self.calculate_costs(self.active_sniper['size'])
                    net_pnl = pnl - costs
                    
                    self.sniper_capital += net_pnl
                    self.capital += net_pnl
                    
                    won = exit_type == 'target'
                    self.trades.append({
                        'date': idx.strftime('%Y-%m-%d'),
                        'year': year,
                        'pair': pair_name,
                        'type': 'sniper',
                        'direction': self.active_sniper['direction'],
                        'entry': float(self.active_sniper['entry']),
                        'exit': float(exit_price),
                        'exit_type': exit_type,
                        'pnl': float(net_pnl),
                        'won': bool(won)
                    })
                    
                    self.yearly_stats[year]['trades'] += 1
                    if won:
                        self.yearly_stats[year]['wins'] += 1
                    else:
                        self.yearly_stats[year]['losses'] += 1
                    
                    self.active_sniper = None
            
            if self.active_bg:
                exit_type, exit_price = self.check_exit(self.active_bg, row)
                if exit_type:
                    pnl = (exit_price - self.active_bg['entry']) * self.active_bg['size']
                    if self.active_bg['direction'] == 'short':
                        pnl = -pnl
                    
                    costs = self.calculate_costs(self.active_bg['size'])
                    net_pnl = pnl - costs
                    
                    self.bg_capital += net_pnl
                    self.capital += net_pnl
                    
                    won = exit_type == 'target'
                    self.trades.append({
                        'date': idx.strftime('%Y-%m-%d'),
                        'year': year,
                        'pair': pair_name,
                        'type': 'background',
                        'direction': self.active_bg['direction'],
                        'entry': float(self.active_bg['entry']),
                        'exit': float(exit_price),
                        'exit_type': exit_type,
                        'pnl': float(net_pnl),
                        'won': bool(won)
                    })
                    
                    self.yearly_stats[year]['trades'] += 1
                    if won:
                        self.yearly_stats[year]['wins'] += 1
                    else:
                        self.yearly_stats[year]['losses'] += 1
                    
                    self.active_bg = None
            
            # Generate new signals
            if not self.active_sniper and self.sniper_capital > 0:
                signal = self.generate_signal(row, is_sniper=True)
                if signal:
                    size = self.calculate_position_size(
                        signal['entry'], signal['stop'], signal['risk'], self.sniper_capital
                    )
                    if size > 0:
                        signal['size'] = size
                        self.active_sniper = signal
            
            if not self.active_bg and self.bg_capital > 0:
                signal = self.generate_signal(row, is_sniper=False)
                if signal:
                    size = self.calculate_position_size(
                        signal['entry'], signal['stop'], signal['risk'], self.bg_capital
                    )
                    if size > 0:
                        signal['size'] = size
                        self.active_bg = signal
            
            # Record daily equity
            self.record_daily_equity(idx)
        
        # Finalize last year stats
        if current_year:
            self.yearly_stats[current_year]['end_capital'] = self.capital
        
        return self.get_metrics()
    
    def get_metrics(self):
        """Calculate performance metrics"""
        if not self.trades:
            return {
                'return': 0,
                'trades': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0,
                'final_capital': float(self.init)
            }
        
        wins = [t for t in self.trades if t['won']]
        losses = [t for t in self.trades if not t['won']]
        
        total_win = sum(t['pnl'] for t in wins) if wins else 0
        total_loss = abs(sum(t['pnl'] for t in losses)) if losses else 0
        
        # Calculate max drawdown from equity curve
        max_dd = 0
        peak = self.init
        for point in self.daily_equity:
            if point['capital'] > peak:
                peak = point['capital']
            dd = ((peak - point['capital']) / peak) * 100
            max_dd = max(max_dd, dd)
        
        return {
            'return': float(((self.capital - self.init) / self.init) * 100),
            'trades': len(self.trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': float((len(wins) / len(self.trades)) * 100),
            'avg_win': float(total_win / len(wins)) if wins else 0,
            'avg_loss': float(total_loss / len(losses)) if losses else 0,
            'profit_factor': float(total_win / total_loss) if total_loss > 0 else float('inf'),
            'max_dd': float(max_dd),
            'final_capital': float(self.capital)
        }


def load_forex_data(pair_name, symbol, start, end):
    """Load forex data"""
    try:
        print(f"  Loading {pair_name}...")
        df = yf.download(symbol, start=start, end=end, interval='1d', progress=False)
        
        if df.empty:
            print(f"    ❌ No data available")
            return None
        
        # Handle MultiIndex columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df.columns = df.columns.str.lower()
        print(f"    ✓ Loaded {len(df)} days")
        return df
        
    except Exception as e:
        print(f"    ❌ Error: {e}")
        return None


# Run backtest
print("Loading data (2018-01-01 to 2024-12-31)...")
print()

start_date = datetime(2018, 1, 1)
end_date = datetime(2024, 12, 31)

all_data = {}
for pair_name, symbol in FOREX_PAIRS.items():
    df = load_forex_data(pair_name, symbol, start_date, end_date)
    if df is not None and len(df) > 100:
        all_data[pair_name] = df

if not all_data:
    print("\n❌ No data loaded. Exiting.")
    exit(1)

print(f"\n✓ Loaded {len(all_data)} pairs")
print()
print("=" * 80)
print("RUNNING BACKTEST...")
print("=" * 80)

# Run backtest
bt = SixYearBacktester(CONFIG, capital=1000, leverage=50)

for pair_name, df in all_data.items():
    print(f"\nProcessing {pair_name}...")
    bt.run(df.copy(), pair_name)

metrics = bt.get_metrics()

print("\n" + "=" * 80)
print("OVERALL RESULTS (2018-2024)")
print("=" * 80)
print(f"Starting Capital: ${bt.init:,.0f}")
print(f"Final Capital: ${metrics['final_capital']:,.0f}")
print(f"Total Return: {metrics['return']:,.1f}%")
print(f"Total Trades: {metrics['trades']}")
print(f"Win Rate: {metrics['win_rate']:.1f}%")
print(f"Profit Factor: {metrics['profit_factor']:.2f}")
print(f"Max Drawdown: {metrics['max_dd']:.1f}%")
print(f"Avg Win: ${metrics['avg_win']:,.2f}")
print(f"Avg Loss: ${metrics['avg_loss']:,.2f}")

# Yearly breakdown
print("\n" + "=" * 80)
print("YEARLY BREAKDOWN")
print("=" * 80)

yearly_summary = []
for year in sorted(bt.yearly_stats.keys()):
    stats = bt.yearly_stats[year]
    start_cap = stats['start_capital']
    end_cap = stats.get('end_capital', bt.capital if year == max(bt.yearly_stats.keys()) else start_cap)
    year_return = ((end_cap - start_cap) / start_cap) * 100
    win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
    
    yearly_summary.append({
        'year': int(year),
        'trades': int(stats['trades']),
        'wins': int(stats['wins']),
        'losses': int(stats['losses']),
        'win_rate': float(win_rate),
        'start_capital': float(start_cap),
        'end_capital': float(end_cap),
        'return': float(year_return)
    })
    
    print(f"\n{year}:")
    print(f"  Trades: {stats['trades']} ({stats['wins']}W / {stats['losses']}L)")
    print(f"  Win Rate: {win_rate:.1f}%")
    print(f"  Start: ${start_cap:,.0f} → End: ${end_cap:,.0f}")
    print(f"  Return: {year_return:,.1f}%")

# Calculate annualized metrics
years = (end_date - start_date).days / 365.25
total_return = metrics['return'] / 100
annualized_return = ((1 + total_return) ** (1 / years) - 1) * 100

print("\n" + "=" * 80)
print("ANNUALIZED METRICS")
print("=" * 80)
print(f"Time Period: {years:.2f} years")
print(f"Annualized Return: {annualized_return:.1f}%")
print(f"Trades per Year: {metrics['trades'] / years:.0f}")

# Save results
output = {
    'config': CONFIG,
    'period': {
        'start': start_date.strftime('%Y-%m-%d'),
        'end': end_date.strftime('%Y-%m-%d'),
        'years': float(years)
    },
    'overall_metrics': metrics,
    'annualized': {
        'return': float(annualized_return),
        'trades_per_year': float(metrics['trades'] / years)
    },
    'yearly_breakdown': yearly_summary,
    'daily_equity': bt.daily_equity,
    'trades': bt.trades[:100]  # First 100 trades for reference
}

with open('docs/6year_forex_data.json', 'w') as f:
    json.dump(output, f, indent=2)

print("\n" + "=" * 80)
print("✅ Backtest complete!")
print("Results saved to docs/6year_forex_data.json")
print("=" * 80)
