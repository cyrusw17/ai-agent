#!/usr/bin/env python3
"""
Strategy Performance Demo - Original Strategies
"""

import sys
sys.path.insert(0, '/workspace')

from core.data_handler import DataHandler
from strategies.example_strategies import (
    TJRStrategy, 
    MomentumBreakoutStrategy,
    ReversalStrategy,
    StructureStrategy
)
from core.backtest import Backtester
from datetime import datetime, timedelta

print('='*80)
print('QUANTITATIVE TRADING STRATEGIES - PERFORMANCE RESULTS')
print('='*80)
print()

handler = DataHandler()

try:
    # Fetch SPY data (more liquid than forex for demo)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    print(f'📊 Testing Symbol: SPY (S&P 500 ETF)')
    print(f'📅 Period: {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")} (180 days)')
    print(f'⏰ Timeframe: 1 Hour')
    print()
    
    print('Fetching market data...')
    df = handler.fetch_data('SPY', start_date.strftime('%Y-%m-%d'), 
                           end_date.strftime('%Y-%m-%d'), '1h')
    print(f'✓ Loaded {len(df)} bars')
    print()
    
    # Test strategies
    strategies = [
        ('TJR Enhanced', TJRStrategy()),
        ('Momentum Breakout', MomentumBreakoutStrategy()),
        ('Reversal', ReversalStrategy()),
        ('Market Structure', StructureStrategy())
    ]
    
    print('='*80)
    print('TESTING STRATEGIES')
    print('='*80)
    print()
    
    results = []
    
    for idx, (name, strategy) in enumerate(strategies):
        print(f'[{idx+1}/{len(strategies)}] {name} Strategy')
        print('-'*80)
        
        try:
            signals = strategy.generate_signals(df)
            
            if len(signals) > 0:
                backtester = Backtester(initial_capital=10000)
                metrics = backtester.run_backtest(df, signals)
                
                print(f'✓ Signals: {len(signals)}')
                print(f'✓ Trades: {metrics["total_trades"]}')
                print(f'✓ Return: {metrics["total_return_pct"]:.2f}%')
                print(f'✓ Win Rate: {metrics["win_rate_pct"]:.1f}%')
                print(f'✓ Profit Factor: {metrics["profit_factor"]:.2f}')
                print(f'✓ Sharpe Ratio: {metrics["sharpe_ratio"]:.2f}')
                print(f'✓ Max Drawdown: {metrics["max_drawdown_pct"]:.2f}%')
                print(f'✓ Avg Win: ${metrics["avg_win"]:.2f}')
                print(f'✓ Avg Loss: ${metrics["avg_loss"]:.2f}')
                print(f'✓ Expectancy: ${metrics["expectancy"]:.2f}')
                
                results.append({
                    'name': name,
                    'signals': len(signals),
                    'trades': metrics["total_trades"],
                    'return': metrics["total_return_pct"],
                    'win_rate': metrics["win_rate_pct"],
                    'pf': metrics["profit_factor"],
                    'sharpe': metrics["sharpe_ratio"],
                    'max_dd': metrics["max_drawdown_pct"],
                    'expectancy': metrics["expectancy"]
                })
            else:
                print('✗ No signals generated')
                
        except Exception as e:
            print(f'✗ Error: {str(e)}')
        
        print()
    
    # Summary
    if results:
        print('='*80)
        print('📈 PERFORMANCE COMPARISON')
        print('='*80)
        print()
        
        # Sort by return
        results_sorted = sorted(results, key=lambda x: x['return'], reverse=True)
        
        print(f"{'Rank':<6} {'Strategy':<25} {'Return':<10} {'Win Rate':<10} {'PF':<8} {'Sharpe':<8}")
        print('-'*80)
        
        for idx, r in enumerate(results_sorted):
            print(f"{idx+1:<6} {r['name']:<25} {r['return']:>6.2f}%   {r['win_rate']:>6.1f}%   {r['pf']:>6.2f}  {r['sharpe']:>6.2f}")
        
        print()
        print('='*80)
        print('📊 KEY INSIGHTS')
        print('='*80)
        print()
        
        best = results_sorted[0]
        print(f"🏆 Best Performing Strategy: {best['name']}")
        print(f"   ├─ Return: {best['return']:.2f}%")
        print(f"   ├─ Win Rate: {best['win_rate']:.1f}%")
        print(f"   ├─ Profit Factor: {best['pf']:.2f}")
        print(f"   ├─ Sharpe Ratio: {best['sharpe']:.2f}")
        print(f"   ├─ Max Drawdown: {best['max_dd']:.2f}%")
        print(f"   ├─ Trades: {best['trades']}")
        print(f"   └─ Expectancy: ${best['expectancy']:.2f} per trade")
        print()
        
        avg_return = sum(r['return'] for r in results) / len(results)
        avg_wr = sum(r['win_rate'] for r in results) / len(results)
        avg_pf = sum(r['pf'] for r in results) / len(results)
        
        print(f"📊 Average Across All Strategies:")
        print(f"   ├─ Return: {avg_return:.2f}%")
        print(f"   ├─ Win Rate: {avg_wr:.1f}%")
        print(f"   └─ Profit Factor: {avg_pf:.2f}")
        print()
        
        profitable = sum(1 for r in results if r['return'] > 0)
        print(f"💰 Profitable Strategies: {profitable}/{len(results)} ({profitable/len(results)*100:.0f}%)")
        
        high_wr = sum(1 for r in results if r['win_rate'] > 55)
        print(f"🎯 Win Rate > 55%: {high_wr}/{len(results)}")
        
        good_pf = sum(1 for r in results if r['pf'] > 1.5)
        print(f"📈 Profit Factor > 1.5: {good_pf}/{len(results)}")

except Exception as e:
    print(f'❌ Error: {str(e)}')
    import traceback
    traceback.print_exc()

print()
print('='*80)
print('✅ Performance Demo Complete!')
print('='*80)
print()
print('💡 These are the 7 pre-built strategies included in the framework.')
print('💡 The multi-timeframe confluence strategies are in development.')
print('💡 All strategies are fully documented in docs/RESEARCH.md')
