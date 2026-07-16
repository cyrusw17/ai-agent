#!/usr/bin/env python3
"""
Cross-Market Validation: Test production strategy on crypto, commodities, and stocks
This validates the strategy's robustness on markets it wasn't developed for.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import random

# Market definitions
CRYPTO_PAIRS = ['BTC-USD', 'ETH-USD', 'BNB-USD', 'SOL-USD', 'ADA-USD']
COMMODITIES = ['GC=F', 'SI=F', 'CL=F', 'NG=F']  # Gold, Silver, Oil, Natural Gas
STOCKS = ['SPY', 'QQQ', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA']

# Load production config
with open('PRODUCTION_STRATEGY_CONFIG.json', 'r') as f:
    prod_data = json.load(f)
    CONFIG = prod_data['config']

print("=" * 80)
print("CROSS-MARKET VALIDATION")
print("=" * 80)
print(f"Testing production config on unseen markets...")
print(f"Sniper: EMA{CONFIG['sniper_ema_fast']}/{CONFIG['sniper_ema_slow']}, "
      f"ADX>{CONFIG['sniper_adx_min']}, Risk={CONFIG['sniper_risk']}%")
print(f"Background: EMA{CONFIG['background_ema_fast']}/{CONFIG['background_ema_slow']}, "
      f"ADX>{CONFIG['background_adx_min']}, Risk={CONFIG['background_risk']}%")
print()


class CrossMarketBacktester:
    """Dual strategy backtester adapted for different markets"""
    
    def __init__(self, config, capital=1000, leverage=50, max_dd_pct=20):
        self.config = config
        self.init = capital
        self.capital = capital
        self.leverage = leverage
        self.max_dd_pct = max_dd_pct
        self.high_water = capital
        
        self.sniper_capital = capital * config['capital_split']
        self.bg_capital = capital * (1 - config['capital_split'])
        
        self.trades = []
        self.equity_curve = []
        self.active_sniper = None
        self.active_bg = None
        
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
        
        # Volatility regime (for dynamic targets)
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
    
    def calculate_costs(self, pair_name, position_size):
        """Estimate trading costs based on market type"""
        if '-USD' in pair_name:  # Crypto
            # Higher spreads for crypto
            spread_cost = position_size * 0.001  # ~0.1% spread
            slippage = position_size * 0.0005  # 0.05% slippage
        elif '=F' in pair_name:  # Commodities
            # Commodity futures costs
            spread_cost = position_size * 0.0008
            slippage = position_size * 0.0003
        else:  # Stocks
            # Stock trading costs
            spread_cost = position_size * 0.0002  # Tight spreads
            slippage = position_size * 0.0001  # Minimal slippage
        
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
    
    def update_equity(self):
        """Track equity curve"""
        self.equity_curve.append({
            'capital': float(self.capital),
            'sniper': float(self.sniper_capital),
            'background': float(self.bg_capital)
        })
    
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
    
    def run(self, df, pair_name):
        """Run backtest on data"""
        df = self.calculate_indicators(df)
        
        for idx, row in df.iterrows():
            if self.check_drawdown():
                break
            
            # Check active trades
            if self.active_sniper:
                exit_type, exit_price = self.check_exit(self.active_sniper, row)
                if exit_type:
                    pnl = (exit_price - self.active_sniper['entry']) * self.active_sniper['size']
                    if self.active_sniper['direction'] == 'short':
                        pnl = -pnl
                    
                    costs = self.calculate_costs(pair_name, self.active_sniper['size'])
                    net_pnl = pnl - costs
                    
                    self.sniper_capital += net_pnl
                    self.capital += net_pnl
                    
                    self.trades.append({
                        'pair': pair_name,
                        'type': 'sniper',
                        'direction': self.active_sniper['direction'],
                        'entry': float(self.active_sniper['entry']),
                        'exit': float(exit_price),
                        'exit_type': exit_type,
                        'pnl': float(net_pnl),
                        'won': bool(exit_type == 'target')
                    })
                    
                    self.active_sniper = None
            
            if self.active_bg:
                exit_type, exit_price = self.check_exit(self.active_bg, row)
                if exit_type:
                    pnl = (exit_price - self.active_bg['entry']) * self.active_bg['size']
                    if self.active_bg['direction'] == 'short':
                        pnl = -pnl
                    
                    costs = self.calculate_costs(pair_name, self.active_bg['size'])
                    net_pnl = pnl - costs
                    
                    self.bg_capital += net_pnl
                    self.capital += net_pnl
                    
                    self.trades.append({
                        'pair': pair_name,
                        'type': 'background',
                        'direction': self.active_bg['direction'],
                        'entry': float(self.active_bg['entry']),
                        'exit': float(exit_price),
                        'exit_type': exit_type,
                        'pnl': float(net_pnl),
                        'won': bool(exit_type == 'target')
                    })
                    
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
            
            self.update_equity()
        
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
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'max_dd': 0,
                'final_capital': float(self.init)
            }
        
        wins = [t for t in self.trades if t['won']]
        losses = [t for t in self.trades if not t['won']]
        
        total_win = sum(t['pnl'] for t in wins) if wins else 0
        total_loss = abs(sum(t['pnl'] for t in losses)) if losses else 0
        
        # Calculate max drawdown from equity curve
        max_dd = 0
        peak = self.init
        for point in self.equity_curve:
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


def load_data(symbol, start, end):
    """Load market data"""
    try:
        df = yf.download(symbol, start=start, end=end, interval='4h', progress=False)
        if df.empty:
            return None
        
        # Handle MultiIndex columns from yfinance
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df.columns = df.columns.str.lower()
        return df
    except Exception as e:
        print(f"  ❌ Failed to load {symbol}: {e}")
        return None


def test_market(symbols, market_name, config, num_simulations=10):
    """Test strategy on a market category"""
    print(f"\n{'='*80}")
    print(f"Testing {market_name.upper()}")
    print(f"{'='*80}")
    
    end = datetime.now()
    start = end - timedelta(days=90)
    
    results = []
    
    for symbol in symbols:
        print(f"\n{symbol}:")
        df = load_data(symbol, start, end)
        
        if df is None or len(df) < 100:
            print(f"  ⚠️  Insufficient data")
            continue
        
        # Run multiple simulations
        sim_results = []
        for sim in range(num_simulations):
            bt = CrossMarketBacktester(config, capital=1000, leverage=50, max_dd_pct=20)
            metrics = bt.run(df.copy(), symbol)
            sim_results.append(metrics)
        
        # Calculate statistics
        returns = [r['return'] for r in sim_results]
        trades = [r['trades'] for r in sim_results]
        win_rates = [r['win_rate'] for r in sim_results]
        max_dds = [r['max_dd'] for r in sim_results]
        
        result = {
            'symbol': symbol,
            'market': market_name,
            'median_return': float(np.median(returns)),
            'avg_return': float(np.mean(returns)),
            'std_return': float(np.std(returns)),
            'median_trades': float(np.median(trades)),
            'median_win_rate': float(np.median(win_rates)),
            'median_max_dd': float(np.median(max_dds)),
            'min_return': float(np.min(returns)),
            'max_return': float(np.max(returns))
        }
        
        results.append(result)
        
        print(f"  ✓ Median Return: {result['median_return']:.1f}%")
        print(f"    Trades: {result['median_trades']:.0f}")
        print(f"    Win Rate: {result['median_win_rate']:.1f}%")
        print(f"    Max DD: {result['median_max_dd']:.1f}%")
    
    return results


# Run tests
all_results = []

print("\n" + "="*80)
print("STARTING CROSS-MARKET VALIDATION")
print(f"Testing period: Last 90 days")
print(f"Simulations per instrument: 10")
print("="*80)

# Test crypto
crypto_results = test_market(CRYPTO_PAIRS, 'Crypto', CONFIG, num_simulations=10)
all_results.extend(crypto_results)

# Test commodities
commodity_results = test_market(COMMODITIES, 'Commodities', CONFIG, num_simulations=10)
all_results.extend(commodity_results)

# Test stocks
stock_results = test_market(STOCKS, 'Stocks', CONFIG, num_simulations=10)
all_results.extend(stock_results)

# Calculate market summaries
print("\n" + "="*80)
print("MARKET SUMMARIES")
print("="*80)

for market_name in ['Crypto', 'Commodities', 'Stocks']:
    market_data = [r for r in all_results if r['market'] == market_name]
    if market_data:
        avg_return = np.mean([r['median_return'] for r in market_data])
        avg_trades = np.mean([r['median_trades'] for r in market_data])
        avg_win_rate = np.mean([r['median_win_rate'] for r in market_data])
        profitable_pct = (sum(1 for r in market_data if r['median_return'] > 0) / len(market_data)) * 100
        
        print(f"\n{market_name}:")
        print(f"  Instruments tested: {len(market_data)}")
        print(f"  Avg Return: {avg_return:.1f}%")
        print(f"  Avg Trades: {avg_trades:.0f}")
        print(f"  Avg Win Rate: {avg_win_rate:.1f}%")
        print(f"  Profitable: {profitable_pct:.0f}%")

# Save results
output = {
    'config': CONFIG,
    'test_period': {
        'days': 90,
        'end_date': datetime.now().strftime('%Y-%m-%d')
    },
    'results': all_results,
    'market_summaries': {
        'crypto': {
            'instruments': [r['symbol'] for r in all_results if r['market'] == 'Crypto'],
            'avg_return': float(np.mean([r['median_return'] for r in all_results if r['market'] == 'Crypto'])) if [r for r in all_results if r['market'] == 'Crypto'] else 0,
            'profitable_pct': float((sum(1 for r in all_results if r['market'] == 'Crypto' and r['median_return'] > 0) / len([r for r in all_results if r['market'] == 'Crypto'])) * 100) if [r for r in all_results if r['market'] == 'Crypto'] else 0
        },
        'commodities': {
            'instruments': [r['symbol'] for r in all_results if r['market'] == 'Commodities'],
            'avg_return': float(np.mean([r['median_return'] for r in all_results if r['market'] == 'Commodities'])) if [r for r in all_results if r['market'] == 'Commodities'] else 0,
            'profitable_pct': float((sum(1 for r in all_results if r['market'] == 'Commodities' and r['median_return'] > 0) / len([r for r in all_results if r['market'] == 'Commodities'])) * 100) if [r for r in all_results if r['market'] == 'Commodities'] else 0
        },
        'stocks': {
            'instruments': [r['symbol'] for r in all_results if r['market'] == 'Stocks'],
            'avg_return': float(np.mean([r['median_return'] for r in all_results if r['market'] == 'Stocks'])) if [r for r in all_results if r['market'] == 'Stocks'] else 0,
            'profitable_pct': float((sum(1 for r in all_results if r['market'] == 'Stocks' and r['median_return'] > 0) / len([r for r in all_results if r['market'] == 'Stocks'])) * 100) if [r for r in all_results if r['market'] == 'Stocks'] else 0
        }
    }
}

with open('docs/cross_market_data.json', 'w') as f:
    json.dump(output, f, indent=2)

print("\n" + "="*80)
print("✅ Cross-market validation complete!")
print("Results saved to docs/cross_market_data.json")
print("="*80)
