"""
Forex Multi-Timeframe Testing Suite
Comprehensive testing across forex pairs, timeframes, and confluence combinations
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
import sys
sys.path.append('..')

from core.data_handler import DataHandler
from core.backtest import Backtester
from strategies.htf_itf_confluence import HTFITFStrategy, ConfluenceTester


class ForexTestingSuite:
    """Comprehensive forex strategy testing"""
    
    # Major forex pairs
    FOREX_PAIRS = [
        'EURUSD=X',  # Euro / US Dollar
        'GBPUSD=X',  # British Pound / US Dollar
        'USDJPY=X',  # US Dollar / Japanese Yen
        'AUDUSD=X',  # Australian Dollar / US Dollar
        'USDCAD=X',  # US Dollar / Canadian Dollar
        'NZDUSD=X',  # New Zealand Dollar / US Dollar
        'USDCHF=X',  # US Dollar / Swiss Franc
        'EURGBP=X',  # Euro / British Pound
        'EURJPY=X',  # Euro / Japanese Yen
        'GBPJPY=X',  # British Pound / Japanese Yen
    ]
    
    # Timeframe combinations to test
    TIMEFRAME_COMBOS = [
        {'htf': '4H', 'itf': '1H', 'ltf': '15M', 'name': '4H-1H-15M'},
        {'htf': '4H', 'itf': '1H', 'ltf': '5M', 'name': '4H-1H-5M'},
        {'htf': '1D', 'itf': '4H', 'ltf': '1H', 'name': '1D-4H-1H'},
        {'htf': '1D', 'itf': '4H', 'ltf': '15M', 'name': '1D-4H-15M'},
    ]
    
    # Confluence combinations to test
    CONFLUENCE_COMBOS = [
        ['fvg', 'ob', 'eq'],
        ['fvg', 'ob', 'bb'],
        ['ob', 'fvg', 'eq'],
        ['ob', 'bb', 'fvg'],
        ['eq', 'ob', 'fvg'],
        ['eq', 'bb', 'ob'],
        ['bb', 'fvg', 'eq'],
        ['bb', 'ob', 'eq'],
        ['fvg', 'eq', 'ob'],
        ['ob', 'eq', 'bb'],
    ]
    
    def __init__(self):
        self.data_handler = DataHandler()
        self.results = []
        
    def test_single_pair(self, 
                        pair: str,
                        start_date: str,
                        end_date: str,
                        tf_combo: Dict,
                        confluence_combo: List[str],
                        entry_type: str = 'bos') -> Dict:
        """
        Test a single configuration on one forex pair
        
        Args:
            pair: Forex pair symbol
            start_date: Start date
            end_date: End date
            tf_combo: Timeframe combination dict
            confluence_combo: List of confluence types
            entry_type: 'bos' or 'candle'
            
        Returns:
            Dictionary with test results
        """
        try:
            # Fetch data
            htf_interval = tf_combo['htf'].lower()
            itf_interval = tf_combo['itf'].lower()
            ltf_interval = tf_combo['ltf'].lower()
            
            # Start with base data
            if '1h' in [htf_interval, itf_interval, ltf_interval]:
                base_df = self.data_handler.fetch_data(pair, start_date, end_date, '1h')
            else:
                base_df = self.data_handler.fetch_data(pair, start_date, end_date, '1h')
            
            # Prepare timeframes
            if tf_combo['htf'] == '4H':
                htf_df = self.data_handler.resample_data(base_df, '4H')
            elif tf_combo['htf'] == '1D':
                htf_df = self.data_handler.resample_data(base_df, '1D')
            else:
                htf_df = base_df.copy()
            
            itf_df = base_df.copy()
            
            if tf_combo['ltf'] in ['15M', '5M']:
                try:
                    ltf_df = self.data_handler.fetch_data(
                        pair, start_date, end_date, 
                        '15m' if tf_combo['ltf'] == '15M' else '5m'
                    )
                except:
                    ltf_df = base_df.copy()
            else:
                ltf_df = base_df.copy()
            
            # Run strategy
            strategy = HTFITFStrategy(
                tf_combo['htf'], 
                tf_combo['itf'], 
                tf_combo['ltf']
            )
            
            signals = strategy.generate_signals(
                htf_df, itf_df, ltf_df,
                confluence_combo=confluence_combo,
                require_ltf_bos=(entry_type == 'bos')
            )
            
            if len(signals) == 0:
                return {
                    'pair': pair,
                    'tf_combo': tf_combo['name'],
                    'confluence': ' → '.join(confluence_combo),
                    'entry': entry_type,
                    'signals': 0,
                    'error': None
                }
            
            # Backtest
            backtester = Backtester(initial_capital=10000)
            metrics = backtester.run_backtest(ltf_df, signals)
            
            return {
                'pair': pair,
                'tf_combo': tf_combo['name'],
                'confluence': ' → '.join(confluence_combo),
                'entry': entry_type,
                'signals': len(signals),
                'return': metrics['total_return_pct'],
                'win_rate': metrics['win_rate_pct'],
                'profit_factor': metrics['profit_factor'],
                'sharpe': metrics['sharpe_ratio'],
                'max_dd': metrics['max_drawdown_pct'],
                'trades': metrics['total_trades'],
                'avg_win': metrics['avg_win'],
                'avg_loss': metrics['avg_loss'],
                'expectancy': metrics['expectancy'],
                'error': None
            }
            
        except Exception as e:
            return {
                'pair': pair,
                'tf_combo': tf_combo['name'],
                'confluence': ' → '.join(confluence_combo),
                'entry': entry_type,
                'signals': 0,
                'error': str(e)
            }
    
    def run_comprehensive_test(self,
                              pairs: List[str] = None,
                              start_date: str = None,
                              end_date: str = None,
                              max_tests_per_pair: int = 10) -> pd.DataFrame:
        """
        Run comprehensive testing across pairs, timeframes, and confluences
        
        Args:
            pairs: List of forex pairs (default: major pairs)
            start_date: Start date (default: 180 days ago)
            end_date: End date (default: today)
            max_tests_per_pair: Maximum confluence combos to test per pair/TF
            
        Returns:
            DataFrame with all results
        """
        if pairs is None:
            pairs = self.FOREX_PAIRS
        
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
        
        print(f"\n{'='*80}")
        print("COMPREHENSIVE FOREX MULTI-TIMEFRAME TESTING")
        print(f"{'='*80}")
        print(f"Pairs: {len(pairs)}")
        print(f"Timeframe Combos: {len(self.TIMEFRAME_COMBOS)}")
        print(f"Confluence Combos per TF: {max_tests_per_pair}")
        print(f"Entry Types: 2 (BOS + Candle)")
        print(f"Period: {start_date} to {end_date}")
        print(f"Total Tests: ~{len(pairs) * len(self.TIMEFRAME_COMBOS) * max_tests_per_pair * 2}")
        print(f"{'='*80}\n")
        
        results = []
        test_count = 0
        
        for pair_idx, pair in enumerate(pairs):
            print(f"\n[{pair_idx + 1}/{len(pairs)}] Testing {pair}")
            print("-" * 60)
            
            for tf_idx, tf_combo in enumerate(self.TIMEFRAME_COMBOS):
                print(f"  Timeframes: {tf_combo['name']}")
                
                # Test subset of confluence combinations
                for conf_idx, conf_combo in enumerate(self.CONFLUENCE_COMBOS[:max_tests_per_pair]):
                    test_count += 1
                    
                    if conf_idx % 5 == 0:
                        print(f"    Testing confluence {conf_idx + 1}/{max_tests_per_pair}...", end='')
                    
                    # Test with BOS entry
                    result_bos = self.test_single_pair(
                        pair, start_date, end_date,
                        tf_combo, conf_combo, 'bos'
                    )
                    results.append(result_bos)
                    
                    # Test with candle entry
                    result_candle = self.test_single_pair(
                        pair, start_date, end_date,
                        tf_combo, conf_combo, 'candle'
                    )
                    results.append(result_candle)
                    
                    if conf_idx % 5 == 0:
                        print(f" Done ({test_count * 2} tests completed)")
        
        # Convert to DataFrame
        results_df = pd.DataFrame(results)
        
        # Filter out errors and zero signals
        valid_results = results_df[
            (results_df['signals'] > 0) & 
            (results_df['error'].isnull())
        ]
        
        if len(valid_results) > 0:
            # Sort by return
            valid_results = valid_results.sort_values('return', ascending=False)
            
            print(f"\n{'='*80}")
            print("TOP 20 CONFIGURATIONS")
            print(f"{'='*80}\n")
            
            display_cols = ['pair', 'tf_combo', 'confluence', 'entry', 
                          'signals', 'return', 'win_rate', 'profit_factor', 
                          'sharpe', 'max_dd']
            
            print(valid_results[display_cols].head(20).to_string(index=False))
            
            # Summary statistics
            print(f"\n{'='*80}")
            print("SUMMARY STATISTICS")
            print(f"{'='*80}\n")
            
            print(f"Total Tests: {len(results_df)}")
            print(f"Valid Results: {len(valid_results)}")
            print(f"Configurations with Signals: {len(valid_results)}")
            print(f"Errors: {results_df['error'].notna().sum()}\n")
            
            print("Performance Distribution:")
            print(f"  Positive Return: {(valid_results['return'] > 0).sum()} ({(valid_results['return'] > 0).sum() / len(valid_results) * 100:.1f}%)")
            print(f"  Win Rate > 50%: {(valid_results['win_rate'] > 50).sum()}")
            print(f"  Win Rate > 60%: {(valid_results['win_rate'] > 60).sum()}")
            print(f"  Profit Factor > 1.5: {(valid_results['profit_factor'] > 1.5).sum()}")
            print(f"  Sharpe > 1.0: {(valid_results['sharpe'] > 1.0).sum()}\n")
            
            print("Average Metrics (All Valid):")
            print(f"  Avg Return: {valid_results['return'].mean():.2f}%")
            print(f"  Avg Win Rate: {valid_results['win_rate'].mean():.1f}%")
            print(f"  Avg Profit Factor: {valid_results['profit_factor'].mean():.2f}")
            print(f"  Avg Sharpe: {valid_results['sharpe'].mean():.2f}")
            print(f"  Avg Max DD: {valid_results['max_dd'].mean():.2f}%\n")
            
            # Best by category
            print("Best by Category:")
            best_return = valid_results.nlargest(1, 'return').iloc[0]
            print(f"  Highest Return: {best_return['pair']} | {best_return['tf_combo']} | {best_return['return']:.2f}%")
            
            best_wr = valid_results.nlargest(1, 'win_rate').iloc[0]
            print(f"  Highest Win Rate: {best_wr['pair']} | {best_wr['tf_combo']} | {best_wr['win_rate']:.1f}%")
            
            best_pf = valid_results.nlargest(1, 'profit_factor').iloc[0]
            print(f"  Highest PF: {best_pf['pair']} | {best_pf['tf_combo']} | {best_pf['profit_factor']:.2f}")
            
            best_sharpe = valid_results.nlargest(1, 'sharpe').iloc[0]
            print(f"  Highest Sharpe: {best_sharpe['pair']} | {best_sharpe['tf_combo']} | {best_sharpe['sharpe']:.2f}")
            
            print(f"\n{'='*80}\n")
        
        return results_df
    
    def analyze_by_pair(self, results_df: pd.DataFrame) -> pd.DataFrame:
        """Analyze results grouped by forex pair"""
        valid = results_df[
            (results_df['signals'] > 0) & 
            (results_df['error'].isnull())
        ]
        
        if len(valid) == 0:
            return pd.DataFrame()
        
        pair_stats = valid.groupby('pair').agg({
            'return': ['mean', 'max', 'min', 'std'],
            'win_rate': 'mean',
            'profit_factor': 'mean',
            'signals': 'sum',
            'trades': 'sum'
        }).round(2)
        
        pair_stats.columns = ['avg_return', 'max_return', 'min_return', 'std_return',
                             'avg_win_rate', 'avg_pf', 'total_signals', 'total_trades']
        
        return pair_stats.sort_values('avg_return', ascending=False)
    
    def analyze_by_timeframe(self, results_df: pd.DataFrame) -> pd.DataFrame:
        """Analyze results grouped by timeframe combination"""
        valid = results_df[
            (results_df['signals'] > 0) & 
            (results_df['error'].isnull())
        ]
        
        if len(valid) == 0:
            return pd.DataFrame()
        
        tf_stats = valid.groupby('tf_combo').agg({
            'return': ['mean', 'max', 'std'],
            'win_rate': 'mean',
            'profit_factor': 'mean',
            'sharpe': 'mean',
            'signals': 'mean'
        }).round(2)
        
        tf_stats.columns = ['avg_return', 'max_return', 'std_return',
                           'avg_win_rate', 'avg_pf', 'avg_sharpe', 'avg_signals']
        
        return tf_stats.sort_values('avg_return', ascending=False)
    
    def analyze_by_confluence(self, results_df: pd.DataFrame) -> pd.DataFrame:
        """Analyze results grouped by confluence combination"""
        valid = results_df[
            (results_df['signals'] > 0) & 
            (results_df['error'].isnull())
        ]
        
        if len(valid) == 0:
            return pd.DataFrame()
        
        conf_stats = valid.groupby('confluence').agg({
            'return': ['mean', 'max', 'count'],
            'win_rate': 'mean',
            'profit_factor': 'mean',
            'signals': 'mean'
        }).round(2)
        
        conf_stats.columns = ['avg_return', 'max_return', 'occurrences',
                             'avg_win_rate', 'avg_pf', 'avg_signals']
        
        return conf_stats.sort_values('avg_return', ascending=False)
    
    def analyze_by_entry_type(self, results_df: pd.DataFrame) -> pd.DataFrame:
        """Compare BOS vs Candle entry types"""
        valid = results_df[
            (results_df['signals'] > 0) & 
            (results_df['error'].isnull())
        ]
        
        if len(valid) == 0:
            return pd.DataFrame()
        
        entry_stats = valid.groupby('entry').agg({
            'return': ['mean', 'max', 'count'],
            'win_rate': 'mean',
            'profit_factor': 'mean',
            'sharpe': 'mean',
            'signals': 'mean'
        }).round(2)
        
        entry_stats.columns = ['avg_return', 'max_return', 'tests',
                              'avg_win_rate', 'avg_pf', 'avg_sharpe', 'avg_signals']
        
        return entry_stats


def main():
    """Run comprehensive forex testing"""
    
    suite = ForexTestingSuite()
    
    # Run tests on selected pairs
    test_pairs = [
        'EURUSD=X',
        'GBPUSD=X',
        'USDJPY=X',
        'AUDUSD=X',
    ]
    
    results = suite.run_comprehensive_test(
        pairs=test_pairs,
        max_tests_per_pair=5  # Test 5 confluence combos per TF
    )
    
    # Save results
    results.to_csv('forex_comprehensive_results.csv', index=False)
    print("Full results saved to: forex_comprehensive_results.csv\n")
    
    # Analyze by different dimensions
    print("="*80)
    print("ANALYSIS BY FOREX PAIR")
    print("="*80)
    pair_analysis = suite.analyze_by_pair(results)
    print(pair_analysis)
    print()
    
    print("="*80)
    print("ANALYSIS BY TIMEFRAME COMBINATION")
    print("="*80)
    tf_analysis = suite.analyze_by_timeframe(results)
    print(tf_analysis)
    print()
    
    print("="*80)
    print("ANALYSIS BY CONFLUENCE TYPE")
    print("="*80)
    conf_analysis = suite.analyze_by_confluence(results)
    print(conf_analysis)
    print()
    
    print("="*80)
    print("ANALYSIS BY ENTRY TYPE (BOS vs CANDLE)")
    print("="*80)
    entry_analysis = suite.analyze_by_entry_type(results)
    print(entry_analysis)
    print()
    
    # Save analyses
    pair_analysis.to_csv('forex_pair_analysis.csv')
    tf_analysis.to_csv('forex_timeframe_analysis.csv')
    conf_analysis.to_csv('forex_confluence_analysis.csv')
    entry_analysis.to_csv('forex_entry_analysis.csv')
    
    print("Analysis files saved:")
    print("  - forex_pair_analysis.csv")
    print("  - forex_timeframe_analysis.csv")
    print("  - forex_confluence_analysis.csv")
    print("  - forex_entry_analysis.csv")


if __name__ == "__main__":
    main()
