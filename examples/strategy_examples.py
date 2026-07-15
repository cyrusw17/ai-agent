"""
Strategy Examples - Individual Strategy Usage

This file demonstrates how to use each strategy independently
"""

import sys
sys.path.append('/workspace')

import pandas as pd
import numpy as np
from datetime import datetime

from utils.data_loader import DataLoader, SyntheticDataGenerator
from strategies.momentum.liquidity_adjusted_momentum import LiquidityAdjustedMomentum
from strategies.mean_reversion.pairs_trading import PairsTradingStrategy
from strategies.hybrid.momentum_reversion_hybrid import HybridMomentumReversionStrategy
from strategies.ml.xgboost_strategy import XGBoostTradingStrategy
from risk_management.position_sizing import PositionSizer


def example_momentum_strategy():
    """
    Example: Liquidity-Adjusted Momentum Strategy
    
    Best for: Trending markets, swing trading, portfolio of 20+ stocks
    """
    print("\n" + "="*80)
    print("EXAMPLE 1: Liquidity-Adjusted Momentum Strategy")
    print("="*80 + "\n")
    
    print("Generating synthetic trending market data...")
    data = {
        'STOCK_A': SyntheticDataGenerator.generate_trending_market(500, drift=0.001, volatility=0.02),
        'STOCK_B': SyntheticDataGenerator.generate_trending_market(500, drift=0.0008, volatility=0.025),
        'STOCK_C': SyntheticDataGenerator.generate_trending_market(500, drift=0.0005, volatility=0.018),
        'STOCK_D': SyntheticDataGenerator.generate_trending_market(500, drift=0.0012, volatility=0.03),
    }
    
    print("Initializing momentum strategy...")
    strategy = LiquidityAdjustedMomentum(
        momentum_lookback=126,  # 6 months for demo
        momentum_skip=21,
        volume_ratio_threshold=1.5,
        illiquidity_percentile=80,
        rebalance_frequency=21
    )
    
    print("Running backtest...")
    equity_curve = strategy.backtest(data, initial_capital=100000)
    
    if not equity_curve.empty:
        stats = strategy.get_performance_stats(equity_curve)
        
        print("\nPerformance Metrics:")
        print(f"  Total Return: {stats['total_return']:.2%}")
        print(f"  Sharpe Ratio: {stats['sharpe_ratio']:.2f}")
        print(f"  Max Drawdown: {stats['max_drawdown']:.2%}")
        print(f"  Win Rate: {stats['win_rate']:.2%}")
        
        print(f"\nFinal Equity: ${equity_curve['equity'].iloc[-1]:,.2f}")
        print(f"Number of Rebalances: {len(equity_curve) // 21}")


def example_pairs_trading():
    """
    Example: Pairs Trading Strategy
    
    Best for: Market-neutral strategies, mean-reversion, sector pairs
    """
    print("\n" + "="*80)
    print("EXAMPLE 2: Pairs Trading (Statistical Arbitrage)")
    print("="*80 + "\n")
    
    print("Generating cointegrated pair...")
    stock1, stock2 = SyntheticDataGenerator.generate_mean_reverting_pair(500, correlation=0.85)
    
    data = {
        'STOCK_X': stock1,
        'STOCK_Y': stock2
    }
    
    print("Initializing pairs trading strategy...")
    strategy = PairsTradingStrategy(
        lookback_period=126,
        entry_z=2.0,
        exit_z=0.5,
        stop_loss_z=3.5,
        use_kalman=True
    )
    
    print("Finding cointegrated pairs...")
    pairs = strategy.find_cointegrated_pairs(data)
    
    if pairs:
        print(f"Found {len(pairs)} cointegrated pair(s)")
        print(f"  Hedge Ratio: {pairs[0]['hedge_ratio']:.4f}")
        print(f"  P-value: {pairs[0]['p_value']:.4f}")
        print(f"  Half-life: {pairs[0]['half_life']:.2f} days")
        
        print("\nBacktesting pair...")
        equity_curve = strategy.backtest_pair(pairs[0], data, capital_per_pair=50000)
        
        if not equity_curve.empty:
            stats = strategy.get_performance_stats(equity_curve)
            
            print("\nPerformance Metrics:")
            print(f"  Total Return: {stats['total_return']:.2%}")
            print(f"  Sharpe Ratio: {stats['sharpe_ratio']:.2f}")
            print(f"  Max Drawdown: {stats['max_drawdown']:.2%}")
            
            print(f"\nFinal Equity: ${equity_curve['equity'].iloc[-1]:,.2f}")
            print(f"Number of Trades: {(equity_curve['position'].diff() != 0).sum()}")


def example_hybrid_strategy():
    """
    Example: Hybrid Momentum-Reversion Strategy
    
    Best for: Single-asset trading, adaptive to market conditions
    """
    print("\n" + "="*80)
    print("EXAMPLE 3: Hybrid Momentum-Reversion Strategy")
    print("="*80 + "\n")
    
    print("Generating mixed market data (trending + ranging)...")
    df = SyntheticDataGenerator.generate_ranging_market(500, volatility=0.025)
    
    print("Initializing hybrid strategy...")
    strategy = HybridMomentumReversionStrategy(
        ema_fast=20,
        ema_slow=50,
        rsi_oversold=30,
        rsi_overbought=70,
        vol_threshold=1.5
    )
    
    print("Testing in adaptive mode...")
    equity_curve = strategy.backtest(df, initial_capital=100000, regime_mode='adaptive')
    
    if not equity_curve.empty:
        stats = strategy.get_performance_stats(equity_curve)
        
        print("\nPerformance Metrics:")
        print(f"  Total Return: {stats['total_return']:.2%}")
        print(f"  Sharpe Ratio: {stats['sharpe_ratio']:.2f}")
        print(f"  Max Drawdown: {stats['max_drawdown']:.2%}")
        print(f"  Win Rate: {stats['win_rate']:.2%}")
        print(f"  Time in Trend Mode: {stats['trend_regime_pct']:.2%}")
        
        print(f"\nFinal Equity: ${equity_curve['equity'].iloc[-1]:,.2f}")
        
        trend_trades = (equity_curve['regime'] == 1).sum()
        mr_trades = (equity_curve['regime'] == 0).sum()
        print(f"Trend trades: {trend_trades}, Mean-reversion trades: {mr_trades}")


def example_ml_strategy():
    """
    Example: XGBoost Machine Learning Strategy
    
    Best for: Feature-rich environments, non-linear patterns
    """
    print("\n" + "="*80)
    print("EXAMPLE 4: XGBoost Machine Learning Strategy")
    print("="*80 + "\n")
    
    print("Generating complex market data...")
    df = SyntheticDataGenerator.generate_trending_market(800, drift=0.0005, volatility=0.02)
    
    print("Initializing ML strategy...")
    strategy = XGBoostTradingStrategy(
        feature_lookbacks=[5, 10, 20],
        prob_threshold=0.55,
        train_size=252,
        retrain_frequency=21
    )
    
    print("Training and backtesting (this may take a moment)...")
    equity_curve = strategy.backtest(df, initial_capital=100000)
    
    if not equity_curve.empty:
        stats = strategy.get_performance_stats(equity_curve)
        
        print("\nPerformance Metrics:")
        print(f"  Total Return: {stats['total_return']:.2%}")
        print(f"  Sharpe Ratio: {stats['sharpe_ratio']:.2f}")
        print(f"  Max Drawdown: {stats['max_drawdown']:.2%}")
        print(f"  Win Rate: {stats['win_rate']:.2%}")
        print(f"  Avg Confidence: {stats['avg_confidence']:.2%}")
        
        print(f"\nFinal Equity: ${equity_curve['equity'].iloc[-1]:,.2f}")
        
        print("\nTop 5 Feature Importances:")
        importance = strategy.get_feature_importance(df, top_n=5)
        for _, row in importance.iterrows():
            print(f"  {row['feature']}: {row['importance']:.4f}")


def example_position_sizing():
    """
    Example: Position Sizing and Risk Management
    
    Demonstrates Kelly Criterion and risk-adjusted sizing
    """
    print("\n" + "="*80)
    print("EXAMPLE 5: Position Sizing and Risk Management")
    print("="*80 + "\n")
    
    account_size = 100000
    sizer = PositionSizer(
        account_size=account_size,
        max_risk_per_trade=0.02,
        max_portfolio_risk=0.10
    )
    
    print("1. Fixed Fraction Position Sizing")
    result = sizer.fixed_fraction(risk_per_trade=0.02)
    print(f"   Position Size: {result.position_size:.2%}")
    print(f"   Risk Amount: ${result.risk_amount:,.2f}")
    
    print("\n2. Kelly Criterion Position Sizing")
    print("   Assuming: 55% win rate, 1.5:1 win/loss ratio")
    result = sizer.kelly_criterion(
        win_rate=0.55,
        win_loss_ratio=1.5,
        fraction=0.25  # Quarter Kelly
    )
    print(f"   Full Kelly: {result.kelly_fraction:.2%}")
    print(f"   Quarter Kelly Position: {result.position_size:.2%}")
    print(f"   Risk Amount: ${result.risk_amount:,.2f}")
    
    print("\n3. Volatility-Adjusted Position Sizing")
    asset_vol = 0.30  # 30% annualized volatility
    result = sizer.volatility_adjusted(
        volatility=asset_vol,
        target_volatility=0.15  # Target 15% portfolio vol
    )
    print(f"   Asset Volatility: {asset_vol:.2%}")
    print(f"   Adjusted Position: {result.position_size:.2%}")
    print(f"   Risk Amount: ${result.risk_amount:,.2f}")
    
    print("\n4. ATR-Based Position Sizing")
    entry_price = 150.0
    atr = 5.0
    shares, stop_loss = sizer.atr_based(
        entry_price=entry_price,
        atr=atr,
        atr_multiplier=2.0
    )
    print(f"   Entry Price: ${entry_price:.2f}")
    print(f"   ATR: ${atr:.2f}")
    print(f"   Position Size: {shares:.2f} shares")
    print(f"   Stop Loss: ${stop_loss:.2f}")
    print(f"   Capital at Risk: ${shares * (entry_price - stop_loss):,.2f}")


def main():
    """Run all examples"""
    print("\n" + "="*80)
    print(" QUANTITATIVE TRADING STRATEGY EXAMPLES")
    print("="*80)
    
    example_momentum_strategy()
    
    example_pairs_trading()
    
    example_hybrid_strategy()
    
    example_ml_strategy()
    
    example_position_sizing()
    
    print("\n" + "="*80)
    print(" ALL EXAMPLES COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
