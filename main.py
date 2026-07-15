"""
Main script to run quantitative trading strategies

Demonstrates multiple strategies:
1. Liquidity-Adjusted Momentum
2. Pairs Trading (Statistical Arbitrage)
3. Hybrid Momentum-Reversion
4. XGBoost ML Strategy

Usage:
    python main.py --strategy all --symbols SPY,QQQ,IWM
    python main.py --strategy momentum --symbols AAPL,MSFT,GOOGL
"""

import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

from utils.data_loader import DataLoader, SyntheticDataGenerator
from strategies.momentum.liquidity_adjusted_momentum import LiquidityAdjustedMomentum
from strategies.mean_reversion.pairs_trading import PairsTradingStrategy
from strategies.hybrid.momentum_reversion_hybrid import HybridMomentumReversionStrategy
from strategies.ml.xgboost_strategy import XGBoostTradingStrategy


class StrategyRunner:
    """Run and compare multiple trading strategies"""
    
    def __init__(self, symbols, start_date, end_date, initial_capital=100000):
        """
        Initialize strategy runner
        
        Args:
            symbols: List of symbols
            start_date: Start date string
            end_date: End date string
            initial_capital: Starting capital
        """
        self.symbols = symbols
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.data = {}
        self.results = {}
        
    def load_data(self):
        """Load market data"""
        print(f"\n{'='*80}")
        print(f"Loading data for {len(self.symbols)} symbols...")
        print(f"{'='*80}\n")
        
        loader = DataLoader(self.symbols, self.start_date, self.end_date)
        self.data = loader.load_data()
        
        if not self.data:
            print("No data loaded. Using synthetic data for demonstration...")
            self.data = {
                'STOCK_A': SyntheticDataGenerator.generate_trending_market(1000, drift=0.0005),
                'STOCK_B': SyntheticDataGenerator.generate_trending_market(1000, drift=0.0003),
                'STOCK_C': SyntheticDataGenerator.generate_ranging_market(1000)
            }
        
        print(f"\nLoaded {len(self.data)} symbols successfully\n")
        
    def run_momentum_strategy(self):
        """Run liquidity-adjusted momentum strategy"""
        print("\n" + "="*80)
        print("RUNNING: Liquidity-Adjusted Momentum Strategy")
        print("="*80 + "\n")
        
        try:
            strategy = LiquidityAdjustedMomentum(
                momentum_lookback=252,
                momentum_skip=21,
                volume_ratio_threshold=1.5,
                illiquidity_percentile=80
            )
            
            equity_curve = strategy.backtest(self.data, self.initial_capital)
            
            if not equity_curve.empty:
                stats = strategy.get_performance_stats(equity_curve)
                self.results['Momentum'] = {
                    'equity_curve': equity_curve,
                    'stats': stats
                }
                self._print_stats('Liquidity-Adjusted Momentum', stats)
            else:
                print("Insufficient data for momentum strategy\n")
                
        except Exception as e:
            print(f"Error running momentum strategy: {e}\n")
    
    def run_pairs_strategy(self):
        """Run pairs trading strategy"""
        print("\n" + "="*80)
        print("RUNNING: Pairs Trading (Statistical Arbitrage)")
        print("="*80 + "\n")
        
        try:
            if len(self.data) < 2:
                print("Need at least 2 symbols for pairs trading\n")
                return
            
            strategy = PairsTradingStrategy(
                lookback_period=252,
                entry_z=2.0,
                exit_z=0.5,
                use_kalman=True
            )
            
            equity_curve = strategy.backtest_portfolio(
                self.data,
                self.initial_capital,
                max_pairs=min(5, len(self.data) // 2)
            )
            
            if not equity_curve.empty:
                stats = strategy.get_performance_stats(equity_curve)
                self.results['Pairs'] = {
                    'equity_curve': equity_curve,
                    'stats': stats
                }
                self._print_stats('Pairs Trading', stats)
            else:
                print("No cointegrated pairs found\n")
                
        except Exception as e:
            print(f"Error running pairs strategy: {e}\n")
    
    def run_hybrid_strategy(self):
        """Run hybrid momentum-reversion strategy"""
        print("\n" + "="*80)
        print("RUNNING: Hybrid Momentum-Reversion Strategy")
        print("="*80 + "\n")
        
        try:
            strategy = HybridMomentumReversionStrategy(
                ema_fast=20,
                ema_slow=50,
                rsi_oversold=30,
                rsi_overbought=70
            )
            
            for symbol, df in list(self.data.items())[:3]:
                print(f"\nTesting {symbol}...")
                
                equity_curve = strategy.backtest(
                    df,
                    self.initial_capital,
                    regime_mode='adaptive'
                )
                
                if not equity_curve.empty:
                    stats = strategy.get_performance_stats(equity_curve)
                    self.results[f'Hybrid_{symbol}'] = {
                        'equity_curve': equity_curve,
                        'stats': stats
                    }
                    self._print_stats(f'Hybrid ({symbol})', stats)
                    
        except Exception as e:
            print(f"Error running hybrid strategy: {e}\n")
    
    def run_ml_strategy(self):
        """Run XGBoost ML strategy"""
        print("\n" + "="*80)
        print("RUNNING: XGBoost Machine Learning Strategy")
        print("="*80 + "\n")
        
        try:
            strategy = XGBoostTradingStrategy(
                feature_lookbacks=[5, 10, 20],
                prob_threshold=0.55,
                train_size=252,
                retrain_frequency=21
            )
            
            for symbol, df in list(self.data.items())[:3]:
                if len(df) < 500:
                    continue
                    
                print(f"\nTraining on {symbol}...")
                
                equity_curve = strategy.backtest(df, self.initial_capital)
                
                if not equity_curve.empty:
                    stats = strategy.get_performance_stats(equity_curve)
                    self.results[f'ML_{symbol}'] = {
                        'equity_curve': equity_curve,
                        'stats': stats
                    }
                    self._print_stats(f'XGBoost ({symbol})', stats)
                    
                    print("\nTop Feature Importances:")
                    importance = strategy.get_feature_importance(df, top_n=5)
                    print(importance.to_string(index=False))
                    
        except Exception as e:
            print(f"Error running ML strategy: {e}\n")
    
    def _print_stats(self, strategy_name, stats):
        """Print performance statistics"""
        print(f"\n{strategy_name} Performance:")
        print("-" * 60)
        print(f"Total Return:        {stats.get('total_return', 0):.2%}")
        print(f"Annual Return:       {stats.get('annual_return', 0):.2%}")
        print(f"Annual Volatility:   {stats.get('annual_volatility', 0):.2%}")
        print(f"Sharpe Ratio:        {stats.get('sharpe_ratio', 0):.2f}")
        print(f"Max Drawdown:        {stats.get('max_drawdown', 0):.2%}")
        print(f"Win Rate:            {stats.get('win_rate', 0):.2%}")
        
        if 'avg_confidence' in stats:
            print(f"Avg Confidence:      {stats.get('avg_confidence', 0):.2%}")
        if 'trend_regime_pct' in stats:
            print(f"Trend Regime %:      {stats.get('trend_regime_pct', 0):.2%}")
            
        print(f"Number of Trades:    {stats.get('num_trades', 0)}")
        print()
    
    def compare_strategies(self):
        """Compare all strategy results"""
        if not self.results:
            print("\nNo strategy results to compare\n")
            return
        
        print("\n" + "="*80)
        print("STRATEGY COMPARISON")
        print("="*80 + "\n")
        
        comparison = []
        for name, result in self.results.items():
            stats = result['stats']
            comparison.append({
                'Strategy': name,
                'Total Return': f"{stats.get('total_return', 0):.2%}",
                'Sharpe': f"{stats.get('sharpe_ratio', 0):.2f}",
                'Max DD': f"{stats.get('max_drawdown', 0):.2%}",
                'Win Rate': f"{stats.get('win_rate', 0):.2%}"
            })
        
        comparison_df = pd.DataFrame(comparison)
        print(comparison_df.to_string(index=False))
        print()
    
    def plot_results(self):
        """Plot equity curves"""
        if not self.results:
            return
        
        plt.figure(figsize=(14, 8))
        
        for name, result in self.results.items():
            equity = result['equity_curve']['equity']
            plt.plot(equity.index, equity.values, label=name, linewidth=2)
        
        plt.title('Strategy Performance Comparison', fontsize=16, fontweight='bold')
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Equity ($)', fontsize=12)
        plt.legend(loc='best', fontsize=10)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        output_path = '/workspace/strategy_comparison.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"\nChart saved to: {output_path}\n")
        plt.close()


def main():
    parser = argparse.ArgumentParser(description='Run quantitative trading strategies')
    parser.add_argument('--strategy', type=str, default='all',
                       choices=['all', 'momentum', 'pairs', 'hybrid', 'ml'],
                       help='Strategy to run')
    parser.add_argument('--symbols', type=str, default='SPY,QQQ,IWM',
                       help='Comma-separated list of symbols')
    parser.add_argument('--start-date', type=str, default='2020-01-01',
                       help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default='2024-01-01',
                       help='End date (YYYY-MM-DD)')
    parser.add_argument('--capital', type=float, default=100000,
                       help='Initial capital')
    
    args = parser.parse_args()
    
    symbols = [s.strip() for s in args.symbols.split(',')]
    
    print("\n" + "="*80)
    print(" QUANTITATIVE TRADING STRATEGY FRAMEWORK")
    print("="*80)
    print(f"\nSymbols: {', '.join(symbols)}")
    print(f"Period: {args.start_date} to {args.end_date}")
    print(f"Initial Capital: ${args.capital:,.0f}")
    
    runner = StrategyRunner(symbols, args.start_date, args.end_date, args.capital)
    
    runner.load_data()
    
    if args.strategy in ['all', 'momentum']:
        runner.run_momentum_strategy()
    
    if args.strategy in ['all', 'pairs']:
        runner.run_pairs_strategy()
    
    if args.strategy in ['all', 'hybrid']:
        runner.run_hybrid_strategy()
    
    if args.strategy in ['all', 'ml']:
        runner.run_ml_strategy()
    
    runner.compare_strategies()
    
    runner.plot_results()
    
    print("\n" + "="*80)
    print(" EXECUTION COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
