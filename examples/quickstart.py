"""
Quick Start Example
Demonstrates basic usage of the framework
"""

import sys
sys.path.append('..')

from core.data_handler import DataHandler
from core.signals import SignalGenerator
from core.backtest import Backtester
from datetime import datetime, timedelta


def main():
    """Quick start example"""
    
    print("\n" + "="*80)
    print("QUANTITATIVE TRADING FRAMEWORK - QUICK START")
    print("="*80 + "\n")
    
    symbol = 'SPY'
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    print(f"1. Fetching data for {symbol}...")
    data_handler = DataHandler()
    df = data_handler.fetch_data(
        symbol=symbol,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d'),
        interval='1h'
    )
    print(f"   Loaded {len(df)} bars\n")
    
    print("2. Analyzing market and generating signals...")
    signal_gen = SignalGenerator()
    
    df_analyzed = signal_gen.analyze_complete(df)
    print(f"   Added {len(df_analyzed.columns) - len(df.columns)} analysis columns\n")
    
    signals = signal_gen.generate_signals(df_analyzed, strategy_type='comprehensive')
    print(f"   Generated {len(signals)} raw signals\n")
    
    print("3. Filtering high-quality signals...")
    filtered_signals = signal_gen.filter_signals(signals, min_score=65, min_risk_reward=2.0)
    print(f"   {len(filtered_signals)} signals passed filters\n")
    
    if len(filtered_signals) > 0:
        print("4. Running backtest...")
        backtester = Backtester(initial_capital=100000)
        
        metrics = backtester.run_backtest(df_analyzed, filtered_signals)
        
        backtester.print_summary(metrics)
        
        trades_df = backtester.get_trades_dataframe()
        equity_curve = backtester.get_equity_curve()
        
        print("5. Saving results...")
        trades_df.to_csv('backtest_trades.csv', index=False)
        equity_curve.to_csv('equity_curve.csv', index=False)
        filtered_signals.to_csv('signals.csv', index=False)
        
        print("   Saved trades, equity curve, and signals to CSV files\n")
        
        print("Example signals:")
        print(filtered_signals[['type', 'timestamp', 'entry_price', 'stop_loss', 
                               'take_profit_1', 'composite_score', 'risk_reward']].head(5))
        print()
    else:
        print("   No signals passed the quality filters.\n")
        print("   Try:\n")
        print("   - Adjusting config.py filter settings")
        print("   - Using a different time period")
        print("   - Testing a different symbol")
        print("   - Using a different strategy type\n")
    
    print("="*80)
    print("QUICK START COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
