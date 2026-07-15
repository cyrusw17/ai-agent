#!/usr/bin/env python3
"""
Funded Account Strategy - Aggressive Configuration
Designed specifically to meet funded account standards:
- 8-10% profit target in 3 months
- <10% max drawdown
- Aggressive position sizing (up to 50% of capital per trade)
- High risk/reward ratios
"""

import sys
sys.path.insert(0, '/workspace')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from core.data_handler import DataHandler
from core.indicators import TechnicalIndicators

print('='*80)
print('💰 AGGRESSIVE FUNDED ACCOUNT STRATEGY')
print('='*80)
print()

class AggressiveFundedBacktester:
    """
    Aggressive backtester for funded accounts
    - Higher position sizing (30-50% of capital)
    - Compound profits
    - Risk management for funded standards
    """
    
    def __init__(self, initial_capital=10000, max_risk_per_trade=0.05, max_capital_per_trade=0.4):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.max_risk_per_trade = max_risk_per_trade  # 5% risk per trade
        self.max_capital_per_trade = max_capital_per_trade  # 40% capital per trade
        self.trades = []
        self.equity_curve = [{'timestamp': None, 'equity': initial_capital}]
        self.peak_equity = initial_capital
        self.max_drawdown = 0
        
    def run_backtest(self, df, signals):
        """Run backtest with aggressive sizing"""
        
        open_position = None
        
        for idx, signal in signals.iterrows():
            signal_idx = signal['index']
            
            # Close existing position if any
            if open_position:
                for i in range(signal_idx, len(df)):
                    bar = df.iloc[i]
                    
                    # Check stop loss
                    if open_position['type'] == 'LONG':
                        if bar['low'] <= open_position['stop_loss']:
                            pnl = (open_position['stop_loss'] - open_position['entry_price']) * open_position['size']
                            self.capital += pnl
                            self.trades.append({
                                'entry': open_position['entry_price'],
                                'exit': open_position['stop_loss'],
                                'pnl': pnl,
                                'type': 'LONG',
                                'result': 'LOSS'
                            })
                            open_position = None
                            break
                        # Check take profit
                        elif bar['high'] >= open_position['take_profit']:
                            pnl = (open_position['take_profit'] - open_position['entry_price']) * open_position['size']
                            self.capital += pnl
                            self.trades.append({
                                'entry': open_position['entry_price'],
                                'exit': open_position['take_profit'],
                                'pnl': pnl,
                                'type': 'LONG',
                                'result': 'WIN'
                            })
                            open_position = None
                            break
                    else:  # SHORT
                        if bar['high'] >= open_position['stop_loss']:
                            pnl = (open_position['entry_price'] - open_position['stop_loss']) * open_position['size']
                            self.capital += pnl
                            self.trades.append({
                                'entry': open_position['entry_price'],
                                'exit': open_position['stop_loss'],
                                'pnl': pnl,
                                'type': 'SHORT',
                                'result': 'LOSS'
                            })
                            open_position = None
                            break
                        elif bar['low'] <= open_position['take_profit']:
                            pnl = (open_position['entry_price'] - open_position['take_profit']) * open_position['size']
                            self.capital += pnl
                            self.trades.append({
                                'entry': open_position['entry_price'],
                                'exit': open_position['take_profit'],
                                'pnl': pnl,
                                'type': 'SHORT',
                                'result': 'WIN'
                            })
                            open_position = None
                            break
            
            # Open new position if no position open
            if not open_position:
                risk_amount = self.capital * self.max_risk_per_trade
                risk_per_unit = abs(signal['entry_price'] - signal['stop_loss'])
                
                if risk_per_unit > 0:
                    position_size = risk_amount / risk_per_unit
                    position_value = position_size * signal['entry_price']
                    
                    # Limit to max capital percentage
                    max_position_value = self.capital * self.max_capital_per_trade
                    if position_value > max_position_value:
                        position_size = max_position_value / signal['entry_price']
                    
                    open_position = {
                        'type': signal['type'],
                        'entry_price': signal['entry_price'],
                        'stop_loss': signal['stop_loss'],
                        'take_profit': signal['take_profit_1'],  # Use TP1
                        'size': position_size,
                        'entry_idx': signal_idx
                    }
            
            # Update equity curve and drawdown
            self.equity_curve.append({
                'timestamp': signal['timestamp'],
                'equity': self.capital
            })
            
            if self.capital > self.peak_equity:
                self.peak_equity = self.capital
            
            dd = (self.peak_equity - self.capital) / self.peak_equity * 100
            if dd > self.max_drawdown:
                self.max_drawdown = dd
        
        # Calculate metrics
        winning_trades = [t for t in self.trades if t['result'] == 'WIN']
        losing_trades = [t for t in self.trades if t['result'] == 'LOSS']
        
        total_return_pct = (self.capital - self.initial_capital) / self.initial_capital * 100
        
        metrics = {
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate_pct': len(winning_trades) / len(self.trades) * 100 if self.trades else 0,
            'total_return_pct': total_return_pct,
            'final_equity': self.capital,
            'max_drawdown_pct': self.max_drawdown,
            'profit_factor': sum([t['pnl'] for t in winning_trades]) / abs(sum([t['pnl'] for t in losing_trades])) if losing_trades else 999,
        }
        
        return metrics

# Test configuration
FOREX_PAIRS = ['USDJPY=X', 'EURUSD=X', 'GBPUSD=X']
test_periods = [
    {'start': datetime(2025, 7, 1), 'end': datetime(2025, 10, 1), 'name': 'Q3 2025'},
    {'start': datetime(2025, 10, 1), 'end': datetime(2026, 1, 1), 'name': 'Q4 2025'},
    {'start': datetime(2026, 1, 1), 'end': datetime(2026, 4, 1), 'name': 'Q1 2026'},
    {'start': datetime(2026, 4, 1), 'end': datetime(2026, 7, 1), 'name': 'Q2 2026'},
]

# Aggressive configs
configs = [
    {
        'name': 'Aggressive Trend EMA3/21',
        'ema_fast': 3,
        'ema_slow': 21,
        'min_adx': 25,
        'stop_mult': 1.5,
        'target_mult': 4.0,  # 1:2.67 R:R
    },
    {
        'name': 'Aggressive Trend EMA5/13',
        'ema_fast': 5,
        'ema_slow': 13,
        'min_adx': 20,
        'stop_mult': 1.2,
        'target_mult': 3.5,  # 1:2.9 R:R
    },
    {
        'name': 'Very Aggressive EMA7/21',
        'ema_fast': 7,
        'ema_slow': 21,
        'min_adx': 15,
        'stop_mult': 1.0,
        'target_mult': 3.0,  # 1:3 R:R
    },
]

def generate_signals(df, params):
    """Generate trend signals"""
    
    df['ema_fast'] = TechnicalIndicators.ema(df, params['ema_fast'])
    df['ema_slow'] = TechnicalIndicators.ema(df, params['ema_slow'])
    df['atr'] = TechnicalIndicators.atr(df)
    adx, _, _ = TechnicalIndicators.adx(df)
    df['adx'] = adx
    
    signals = []
    
    for i in range(50, len(df)):
        bar = df.iloc[i]
        prev_bar = df.iloc[i-1]
        
        if bar['adx'] < params['min_adx']:
            continue
        
        if bar['ema_fast'] > bar['ema_slow'] and prev_bar['ema_fast'] <= prev_bar['ema_slow']:
            signals.append({
                'type': 'LONG',
                'index': i,
                'timestamp': df.index[i],
                'entry_price': bar['close'],
                'stop_loss': bar['close'] - (bar['atr'] * params['stop_mult']),
                'take_profit_1': bar['close'] + (bar['atr'] * params['target_mult']),
                'take_profit_2': bar['close'] + (bar['atr'] * params['target_mult'] * 1.5),
                'take_profit_3': bar['close'] + (bar['atr'] * params['target_mult'] * 2.0)
            })
        elif bar['ema_fast'] < bar['ema_slow'] and prev_bar['ema_fast'] >= prev_bar['ema_slow']:
            signals.append({
                'type': 'SHORT',
                'index': i,
                'timestamp': df.index[i],
                'entry_price': bar['close'],
                'stop_loss': bar['close'] + (bar['atr'] * params['stop_mult']),
                'take_profit_1': bar['close'] - (bar['atr'] * params['target_mult']),
                'take_profit_2': bar['close'] - (bar['atr'] * params['target_mult'] * 1.5),
                'take_profit_3': bar['close'] - (bar['atr'] * params['target_mult'] * 2.0)
            })
    
    return pd.DataFrame(signals)

# Test all combinations
all_results = []
funded_passers = []

print('Testing with AGGRESSIVE position sizing (40% capital per trade, 5% risk)...')
print()

for period in test_periods:
    print(f'Period: {period["name"]}')
    
    for pair in FOREX_PAIRS:
        try:
            handler = DataHandler()
            df = handler.fetch_data(pair, period['start'].strftime('%Y-%m-%d'),
                                   period['end'].strftime('%Y-%m-%d'), '4h')
            
            if len(df) < 50:
                continue
            
            pair_name = pair.replace('=X', '')
            
            for config in configs:
                try:
                    signals = generate_signals(df.copy(), config)
                    
                    if len(signals) >= 5:
                        backtester = AggressiveFundedBacktester(
                            initial_capital=10000,
                            max_risk_per_trade=0.05,  # 5% risk
                            max_capital_per_trade=0.40  # 40% capital
                        )
                        metrics = backtester.run_backtest(df, signals)
                        
                        result = {
                            'period': period['name'],
                            'pair': pair_name,
                            'strategy': config['name'],
                            'return': metrics['total_return_pct'],
                            'max_dd': metrics['max_drawdown_pct'],
                            'trades': metrics['total_trades'],
                            'win_rate': metrics['win_rate_pct'],
                            'profit_factor': metrics['profit_factor'],
                            'final_capital': metrics['final_equity'],
                            'config': config
                        }
                        
                        all_results.append(result)
                        
                        # Check funded standards
                        if (metrics['total_return_pct'] >= 8.0 and 
                            metrics['max_drawdown_pct'] < 10.0):
                            funded_passers.append(result)
                            print(f'  ✅ {pair_name:6s} | {config["name"]:30s} | {metrics["total_return_pct"]:7.2f}% (DD: {metrics["max_drawdown_pct"]:.1f}%)')
                        elif metrics['total_return_pct'] >= 5.0:
                            print(f'  💚 {pair_name:6s} | {config["name"]:30s} | {metrics["total_return_pct"]:7.2f}% (DD: {metrics["max_drawdown_pct"]:.1f}%)')
                
                except Exception as e:
                    continue
        
        except Exception as e:
            continue

# Results
print()
print('='*80)
print('📊 AGGRESSIVE STRATEGY RESULTS')
print('='*80)
print()

if all_results:
    results_df = pd.DataFrame(all_results)
    profitable = results_df[results_df['return'] > 0]
    
    print(f'Total tests: {len(results_df)}')
    print(f'Profitable: {len(profitable)}')
    print(f'Funded passers (8%+, <10% DD): {len(funded_passers)}')
    print()
    
    if len(funded_passers) > 0:
        print('🎉 FOUND FUNDED ACCOUNT STRATEGIES!')
        print()
        
        for result in sorted(funded_passers, key=lambda x: x['return'], reverse=True):
            print(f"✅ {result['period']} | {result['pair']} | {result['strategy']}")
            print(f"   Return: {result['return']:.2f}% | Max DD: {result['max_dd']:.2f}%")
            print(f"   Trades: {result['trades']} | Win Rate: {result['win_rate']:.1f}%")
            print(f"   Final Capital: ${result['final_capital']:,.2f}")
            print()
        
        # Save best
        best = max(funded_passers, key=lambda x: x['return'])
        
        import json
        with open('/workspace/funded_strategy_winner.json', 'w') as f:
            json.dump(best, f, indent=2, default=str)
        
        print('✓ Best funded strategy saved!')
    
    elif len(profitable) > 0:
        print('💚 Profitable but not meeting 8% target')
        print()
        print('Top 5:')
        for idx, row in profitable.nlargest(5, 'return').iterrows():
            print(f"  {row['period']} | {row['pair']} | {row['strategy']}")
            print(f"    Return: {row['return']:.2f}% | DD: {row['max_dd']:.2f}%")
    
    else:
        print('⚠️ No profitable with aggressive sizing')
        print('Best 5:')
        for idx, row in results_df.nlargest(5, 'return').iterrows():
            print(f"  {row['period']} | {row['pair']}: {row['return']:.2f}%")
    
    results_df.to_csv('/workspace/aggressive_funded_results.csv', index=False)

print()
print('✅ Complete')
