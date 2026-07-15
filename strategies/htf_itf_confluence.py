"""
HTF → ITF → LTF Confluence Strategy
Implements multi-timeframe scaling with confluence validation
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from core.data_handler import DataHandler
from core.multi_timeframe import MultiTimeframeAnalysis
from core.indicators import TechnicalIndicators


class HTFITFStrategy:
    """
    Higher Timeframe → Intermediate Timeframe → Lower Timeframe Strategy
    
    Entry Logic:
    1. Check 4H bias/trend
    2. Check 1H bias/trend
    3. Determine scaling timeframe based on alignment
    4. Wait for HTF confluence hit
    5. Wait for ITF BOS
    6. Wait for 3rd confluence (FVG, OB, BB, EQ)
    7. Enter on smaller timeframe BOS or directional candle
    """
    
    def __init__(self, htf: str = '4H', itf: str = '1H', ltf: str = '15M'):
        """
        Initialize strategy
        
        Args:
            htf: Higher timeframe (e.g., '4H')
            itf: Intermediate timeframe (e.g., '1H')
            ltf: Lower timeframe (e.g., '15M')
        """
        self.htf = htf
        self.itf = itf
        self.ltf = ltf
        
        self.mtf_analyzer = MultiTimeframeAnalysis()
        
        self.name = f"HTF({htf}) → ITF({itf}) → LTF({ltf}) Confluence Strategy"
        
    def generate_signals(self, 
                        htf_df: pd.DataFrame,
                        itf_df: pd.DataFrame,
                        ltf_df: pd.DataFrame,
                        confluence_combo: List[str] = ['fvg', 'ob', 'eq'],
                        require_ltf_bos: bool = True) -> pd.DataFrame:
        """
        Generate trading signals using multi-timeframe analysis
        
        Args:
            htf_df: Higher timeframe data
            itf_df: Intermediate timeframe data
            ltf_df: Lower timeframe data
            confluence_combo: List of confluences to check ['fvg', 'ob', 'bb', 'eq']
            require_ltf_bos: If True, require LTF BOS; if False, use directional candle
            
        Returns:
            DataFrame with signals
        """
        # Analyze all timeframes
        print(f"Analyzing {self.htf} timeframe...")
        htf_analysis = self.mtf_analyzer.analyze_timeframe(htf_df, self.htf)
        
        print(f"Analyzing {self.itf} timeframe...")
        itf_analysis = self.mtf_analyzer.analyze_timeframe(itf_df, self.itf)
        
        print(f"Analyzing {self.ltf} timeframe...")
        ltf_analysis = self.mtf_analyzer.analyze_timeframe(ltf_df, self.ltf)
        
        signals = []
        
        # Iterate through LTF bars (execution timeframe)
        for i in range(200, len(ltf_df)):
            current_timestamp = ltf_df.index[i]
            
            # Get corresponding HTF and ITF indices
            htf_idx = self._get_corresponding_index(htf_df, current_timestamp)
            itf_idx = self._get_corresponding_index(itf_df, current_timestamp)
            
            if htf_idx is None or itf_idx is None:
                continue
            
            # Step 1: Check HTF bias/trend
            htf_trend = htf_analysis['trend'].iloc[htf_idx]
            
            if htf_trend == 'ranging':
                continue
            
            # Step 2: Check ITF bias/trend
            itf_trend = itf_analysis['trend'].iloc[itf_idx]
            
            if itf_trend == 'ranging':
                continue
            
            # Step 3: Determine if trends are aligned
            trends_aligned = self.mtf_analyzer.check_trend_alignment(
                htf_trend, itf_trend
            )
            
            # Determine scaling timeframe
            if trends_aligned:
                scale_tf = self.itf
                scale_analysis = itf_analysis
                scale_idx = itf_idx
            else:
                scale_tf = self.htf
                scale_analysis = htf_analysis
                scale_idx = htf_idx
            
            # Determine direction
            direction = 'bullish' if htf_trend == 'uptrend' else 'bearish'
            
            # Step 4: Check if HTF confluence was hit (in recent past)
            htf_confluence_hit = False
            htf_confluence_data = {}
            
            # Check recent bars for HTF confluence
            for lookback in range(1, min(20, htf_idx)):
                hit, data = self.mtf_analyzer.detect_confluence_hit(
                    htf_df, htf_idx - lookback,
                    confluence_combo[0] if len(confluence_combo) > 0 else 'ob',
                    htf_analysis, direction
                )
                if hit:
                    htf_confluence_hit = True
                    htf_confluence_data = data
                    break
            
            if not htf_confluence_hit:
                continue
            
            # Step 5: Check for ITF BOS (recent)
            itf_bos_occurred = False
            recent_bos = itf_analysis['bos_events'][
                (itf_analysis['bos_events']['index'] >= itf_idx - 10) &
                (itf_analysis['bos_events']['index'] <= itf_idx)
            ]
            
            for _, bos in recent_bos.iterrows():
                if direction == 'bullish' and bos['type'] == 'bullish_bos':
                    itf_bos_occurred = True
                    break
                elif direction == 'bearish' and bos['type'] == 'bearish_bos':
                    itf_bos_occurred = True
                    break
            
            if not itf_bos_occurred:
                continue
            
            # Step 6: Check for 3rd confluence on ITF
            third_confluence_hit = False
            third_confluence_data = {}
            
            if len(confluence_combo) >= 3:
                hit, data = self.mtf_analyzer.detect_confluence_hit(
                    itf_df, itf_idx,
                    confluence_combo[2],
                    itf_analysis, direction
                )
                
                if hit:
                    third_confluence_hit = True
                    third_confluence_data = data
            else:
                # If no 3rd confluence specified, proceed
                third_confluence_hit = True
            
            if not third_confluence_hit:
                continue
            
            # Step 7: Check for LTF entry trigger
            entry_triggered = False
            
            if require_ltf_bos:
                # Wait for LTF BOS
                recent_ltf_bos = ltf_analysis['bos_events'][
                    (ltf_analysis['bos_events']['index'] >= i - 5) &
                    (ltf_analysis['bos_events']['index'] <= i)
                ]
                
                for _, bos in recent_ltf_bos.iterrows():
                    if direction == 'bullish' and bos['type'] == 'bullish_bos':
                        entry_triggered = True
                        break
                    elif direction == 'bearish' and bos['type'] == 'bearish_bos':
                        entry_triggered = True
                        break
            else:
                # Check for directional candle
                entry_triggered = self.mtf_analyzer.check_directional_candle(
                    ltf_df, i, direction
                )
            
            if not entry_triggered:
                continue
            
            # Generate signal
            bar = ltf_df.iloc[i]
            atr = TechnicalIndicators.atr(ltf_df, period=14).iloc[i]
            
            if direction == 'bullish':
                entry_price = bar['close']
                stop_loss = entry_price - (atr * 1.5)
                take_profit_1 = entry_price + (atr * 2.0)
                take_profit_2 = entry_price + (atr * 3.0)
                take_profit_3 = entry_price + (atr * 4.0)
            else:
                entry_price = bar['close']
                stop_loss = entry_price + (atr * 1.5)
                take_profit_1 = entry_price - (atr * 2.0)
                take_profit_2 = entry_price - (atr * 3.0)
                take_profit_3 = entry_price - (atr * 4.0)
            
            signals.append({
                'type': 'LONG' if direction == 'bullish' else 'SHORT',
                'index': i,
                'timestamp': current_timestamp,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit_1': take_profit_1,
                'take_profit_2': take_profit_2,
                'take_profit_3': take_profit_3,
                'htf_trend': htf_trend,
                'itf_trend': itf_trend,
                'trends_aligned': trends_aligned,
                'scale_tf': scale_tf,
                'htf_confluence': htf_confluence_data.get('type', 'unknown'),
                'third_confluence': third_confluence_data.get('type', 'unknown'),
                'confluence_combo': ','.join(confluence_combo),
                'ltf_entry': 'bos' if require_ltf_bos else 'candle'
            })
        
        return pd.DataFrame(signals)
    
    def _get_corresponding_index(self, df: pd.DataFrame, 
                                timestamp: pd.Timestamp) -> Optional[int]:
        """
        Get the index in df that corresponds to or precedes the timestamp
        
        Args:
            df: Dataframe to search
            timestamp: Target timestamp
            
        Returns:
            Index or None
        """
        # Find the last bar that is <= timestamp
        mask = df.index <= timestamp
        
        if mask.sum() == 0:
            return None
        
        valid_indices = df.index[mask]
        last_valid = valid_indices[-1]
        
        return df.index.get_loc(last_valid)


class ConfluenceTester:
    """Tests multiple confluence combinations and parameters"""
    
    def __init__(self):
        self.data_handler = DataHandler()
        
    def test_confluence_combinations(self,
                                    symbol: str,
                                    start_date: str,
                                    end_date: str,
                                    htf: str = '4H',
                                    itf: str = '1H',
                                    ltf: str = '15M',
                                    test_ltf_entry: bool = True) -> pd.DataFrame:
        """
        Test all possible confluence combinations
        
        Args:
            symbol: Trading symbol (e.g., 'EURUSD=X')
            start_date: Start date
            end_date: End date
            htf: Higher timeframe
            itf: Intermediate timeframe
            ltf: Lower timeframe
            test_ltf_entry: If True, test both BOS and candle entries
            
        Returns:
            DataFrame with results for each combination
        """
        from core.backtest import Backtester
        
        print(f"\n{'='*80}")
        print(f"CONFLUENCE COMBINATION TESTING: {symbol}")
        print(f"HTF: {htf} | ITF: {itf} | LTF: {ltf}")
        print(f"Period: {start_date} to {end_date}")
        print(f"{'='*80}\n")
        
        # Fetch data for all timeframes
        print("Fetching market data...")
        
        # Start with 1H data and resample
        base_df = self.data_handler.fetch_data(symbol, start_date, end_date, '1h')
        
        # Prepare timeframes
        if htf == '4H':
            htf_df = self.data_handler.resample_data(base_df, '4H')
        elif htf == '1D':
            htf_df = self.data_handler.resample_data(base_df, '1D')
        else:
            htf_df = base_df.copy()
        
        itf_df = base_df.copy()
        
        if ltf == '15M':
            ltf_df = self.data_handler.fetch_data(symbol, start_date, end_date, '15m')
        elif ltf == '5M':
            ltf_df = self.data_handler.fetch_data(symbol, start_date, end_date, '5m')
        else:
            ltf_df = base_df.copy()
        
        print(f"HTF bars: {len(htf_df)}, ITF bars: {len(itf_df)}, LTF bars: {len(ltf_df)}\n")
        
        # Define confluence combinations to test
        confluence_types = ['fvg', 'ob', 'bb', 'eq']
        
        combinations = []
        
        # 3-confluence combinations
        for i, c1 in enumerate(confluence_types):
            for j, c2 in enumerate(confluence_types):
                if i != j:
                    for k, c3 in enumerate(confluence_types):
                        if k != i and k != j:
                            combinations.append([c1, c2, c3])
        
        results = []
        
        strategy = HTFITFStrategy(htf, itf, ltf)
        
        for idx, combo in enumerate(combinations[:20]):  # Test first 20 combinations
            print(f"\n[{idx+1}/{min(20, len(combinations))}] Testing: {' → '.join(combo)}")
            
            # Test with LTF BOS entry
            if test_ltf_entry:
                print("  Entry: LTF BOS")
                try:
                    signals = strategy.generate_signals(
                        htf_df, itf_df, ltf_df,
                        confluence_combo=combo,
                        require_ltf_bos=True
                    )
                    
                    if len(signals) > 0:
                        backtester = Backtester(initial_capital=10000)
                        metrics = backtester.run_backtest(ltf_df, signals)
                        
                        results.append({
                            'combo': ' → '.join(combo),
                            'entry_type': 'LTF_BOS',
                            'signals': len(signals),
                            'return': metrics['total_return_pct'],
                            'win_rate': metrics['win_rate_pct'],
                            'profit_factor': metrics['profit_factor'],
                            'sharpe': metrics['sharpe_ratio'],
                            'max_dd': metrics['max_drawdown_pct'],
                            'trades': metrics['total_trades']
                        })
                        
                        print(f"    Signals: {len(signals)} | Return: {metrics['total_return_pct']:.2f}% | Win Rate: {metrics['win_rate_pct']:.1f}%")
                    else:
                        print("    No signals generated")
                        
                except Exception as e:
                    print(f"    Error: {str(e)}")
            
            # Test with directional candle entry
            print("  Entry: Directional Candle")
            try:
                signals = strategy.generate_signals(
                    htf_df, itf_df, ltf_df,
                    confluence_combo=combo,
                    require_ltf_bos=False
                )
                
                if len(signals) > 0:
                    backtester = Backtester(initial_capital=10000)
                    metrics = backtester.run_backtest(ltf_df, signals)
                    
                    results.append({
                        'combo': ' → '.join(combo),
                        'entry_type': 'CANDLE',
                        'signals': len(signals),
                        'return': metrics['total_return_pct'],
                        'win_rate': metrics['win_rate_pct'],
                        'profit_factor': metrics['profit_factor'],
                        'sharpe': metrics['sharpe_ratio'],
                        'max_dd': metrics['max_drawdown_pct'],
                        'trades': metrics['total_trades']
                    })
                    
                    print(f"    Signals: {len(signals)} | Return: {metrics['total_return_pct']:.2f}% | Win Rate: {metrics['win_rate_pct']:.1f}%")
                else:
                    print("    No signals generated")
                    
            except Exception as e:
                print(f"    Error: {str(e)}")
        
        if results:
            results_df = pd.DataFrame(results)
            results_df = results_df.sort_values('return', ascending=False)
            
            print(f"\n{'='*80}")
            print("TOP 10 CONFLUENCE COMBINATIONS")
            print(f"{'='*80}\n")
            print(results_df.head(10).to_string(index=False))
            print()
            
            return results_df
        
        return pd.DataFrame()


if __name__ == "__main__":
    # Example usage
    tester = ConfluenceTester()
    
    results = tester.test_confluence_combinations(
        symbol='EURUSD=X',
        start_date='2025-01-01',
        end_date='2026-07-15',
        htf='4H',
        itf='1H',
        ltf='15M'
    )
    
    if not results.empty:
        results.to_csv('confluence_test_results.csv', index=False)
        print("Results saved to confluence_test_results.csv")
