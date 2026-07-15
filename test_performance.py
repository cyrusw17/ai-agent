#!/usr/bin/env python3
"""
Quick Demo: HTF → ITF → LTF Confluence Strategy Performance
"""

import sys
sys.path.insert(0, '/workspace')

from core.data_handler import DataHandler
from strategies.htf_itf_confluence import HTFITFStrategy
from core.backtest import Backtester
from datetime import datetime, timedelta

print('='*80)
print('HTF → ITF → LTF CONFLUENCE STRATEGY - PERFORMANCE DEMO')
print('='*80)
print()

# Test EURUSD with your exact setup
print('📊 Testing EURUSD/USD: 4H → 1H → 1H (LTF simplified for speed)')
print('-'*80)
print()

handler = DataHandler()

try:
    # Fetch data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    print(f'📅 Period: {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")} (180 days)')
    print(f'💱 Pair: EURUSD=X')
    print()
    
    print('Fetching market data...')
    df_1h = handler.fetch_data('EURUSD=X', start_date.strftime('%Y-%m-%d'), 
                                end_date.strftime('%Y-%m-%d'), '1h')
    print(f'✓ Loaded {len(df_1h)} hourly bars')
    
    df_4h = handler.resample_data(df_1h, '4h')
    print(f'✓ Resampled to {len(df_4h)} 4-hour bars')
    
    # Use 1H as LTF for faster demo
    df_ltf = df_1h.copy()
    print(f'✓ Using {len(df_ltf)} bars for execution')
    print()
    
    # Test 3 different confluence combinations
    print('='*80)
    print('TESTING DIFFERENT CONFLUENCE COMBINATIONS')
    print('='*80)
    print()
    
    confluence_combos = [
        (['fvg', 'ob', 'eq'], 'FVG → OB → EQ'),
        (['ob', 'fvg', 'bb'], 'OB → FVG → BB'),
        (['eq', 'ob', 'fvg'], 'EQ → OB → FVG')
    ]
    
    results = []
    
    for idx, (combo, name) in enumerate(confluence_combos):
        print(f'🔍 [{idx+1}/3] Testing Confluence: {name}')
        print('-'*80)
        
        strategy = HTFITFStrategy(htf='4H', itf='1H', ltf='1H')
        
        # Test with BOS entry
        print(f'   Entry Type: LTF BOS (More Confirmation)')
        signals_bos = strategy.generate_signals(
            df_4h, df_1h, df_ltf,
            confluence_combo=combo,
            require_ltf_bos=True
        )
        
        if len(signals_bos) > 0:
            backtester = Backtester(initial_capital=10000)
            metrics = backtester.run_backtest(df_ltf, signals_bos)
            
            print(f'   ├─ Signals Generated: {len(signals_bos)}')
            print(f'   ├─ Trades Executed: {metrics["total_trades"]}')
            print(f'   ├─ Total Return: {metrics["total_return_pct"]:.2f}%')
            print(f'   ├─ Win Rate: {metrics["win_rate_pct"]:.1f}%')
            print(f'   ├─ Profit Factor: {metrics["profit_factor"]:.2f}')
            print(f'   ├─ Sharpe Ratio: {metrics["sharpe_ratio"]:.2f}')
            print(f'   └─ Max Drawdown: {metrics["max_drawdown_pct"]:.2f}%')
            
            results.append({
                'combo': name,
                'entry': 'BOS',
                'signals': len(signals_bos),
                'return': metrics["total_return_pct"],
                'win_rate': metrics["win_rate_pct"],
                'pf': metrics["profit_factor"],
                'sharpe': metrics["sharpe_ratio"]
            })
        else:
            print(f'   └─ No signals generated')
        
        print()
        
        # Test with Candle entry
        print(f'   Entry Type: Directional Candle (Faster Entry)')
        signals_candle = strategy.generate_signals(
            df_4h, df_1h, df_ltf,
            confluence_combo=combo,
            require_ltf_bos=False
        )
        
        if len(signals_candle) > 0:
            backtester = Backtester(initial_capital=10000)
            metrics = backtester.run_backtest(df_ltf, signals_candle)
            
            print(f'   ├─ Signals Generated: {len(signals_candle)}')
            print(f'   ├─ Trades Executed: {metrics["total_trades"]}')
            print(f'   ├─ Total Return: {metrics["total_return_pct"]:.2f}%')
            print(f'   ├─ Win Rate: {metrics["win_rate_pct"]:.1f}%')
            print(f'   ├─ Profit Factor: {metrics["profit_factor"]:.2f}')
            print(f'   ├─ Sharpe Ratio: {metrics["sharpe_ratio"]:.2f}')
            print(f'   └─ Max Drawdown: {metrics["max_drawdown_pct"]:.2f}%')
            
            results.append({
                'combo': name,
                'entry': 'Candle',
                'signals': len(signals_candle),
                'return': metrics["total_return_pct"],
                'win_rate': metrics["win_rate_pct"],
                'pf': metrics["profit_factor"],
                'sharpe': metrics["sharpe_ratio"]
            })
        else:
            print(f'   └─ No signals generated')
        
        print()
    
    # Summary
    if results:
        print('='*80)
        print('📈 PERFORMANCE SUMMARY')
        print('='*80)
        print()
        
        # Sort by return
        results.sort(key=lambda x: x['return'], reverse=True)
        
        print('Top Performing Configurations:')
        print()
        print(f"{'Rank':<6} {'Confluence':<20} {'Entry':<8} {'Signals':<9} {'Return':<10} {'Win Rate':<10} {'PF':<8}")
        print('-'*80)
        
        for idx, r in enumerate(results[:5]):
            print(f"{idx+1:<6} {r['combo']:<20} {r['entry']:<8} {r['signals']:<9} {r['return']:>6.2f}%   {r['win_rate']:>6.1f}%   {r['pf']:>6.2f}")
        
        print()
        print('Key Insights:')
        best = results[0]
        print(f"✓ Best Setup: {best['combo']} with {best['entry']} entry")
        print(f"✓ Achieved {best['return']:.2f}% return with {best['win_rate']:.1f}% win rate")
        print(f"✓ Profit Factor: {best['pf']:.2f} (${best['pf']:.2f} made per $1 risked)")
        
        avg_return = sum(r['return'] for r in results) / len(results)
        avg_wr = sum(r['win_rate'] for r in results) / len(results)
        print(f"✓ Average Return: {avg_return:.2f}%")
        print(f"✓ Average Win Rate: {avg_wr:.1f}%")
        
        positive = sum(1 for r in results if r['return'] > 0)
        print(f"✓ Profitable Configs: {positive}/{len(results)} ({positive/len(results)*100:.0f}%)")

except Exception as e:
    print(f'❌ Error: {str(e)}')
    import traceback
    traceback.print_exc()

print()
print('='*80)
print('✅ Demo Complete!')
print('='*80)
print()
print('💡 To run full testing on all forex pairs:')
print('   cd examples && python3 forex_testing_suite.py')
