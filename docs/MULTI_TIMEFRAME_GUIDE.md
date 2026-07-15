# Multi-Timeframe Confluence Testing Guide

## Overview

This framework now includes advanced multi-timeframe (HTF → ITF → LTF) confluence testing specifically designed for forex trading. It implements your exact strategy logic with configurable parameters.

## Strategy Logic

### Your Strategy (Implemented):

1. **Check 4H bias/trend** (HTF)
2. **Check 1H bias/trend** (ITF)
3. **Determine scaling timeframe**:
   - If trends aligned → Use 1H (ITF)
   - If trends NOT aligned → Use 4H (HTF)
4. **Wait for HTF confluence hit** (FVG, OB, BB, or EQ)
5. **Wait for ITF Break of Structure (BOS)**
6. **Wait for 3rd confluence** (FVG, OB, BB, or EQ)
7. **Entry trigger**:
   - Option A: Smaller timeframe BOS
   - Option B: Directional candle

## New Components

### 1. Fair Value Gaps (FVG)

```python
from core.multi_timeframe import FairValueGap

fvg_detector = FairValueGap()

# Detect FVGs
fvgs = fvg_detector.detect_fvg(df, min_gap_size=0.0001)

# Check if FVG is still active (unfilled)
active_fvgs = fvg_detector.get_active_fvgs(df, fvgs, current_idx=100)
```

**What is FVG?**
- Bullish FVG: Gap where Bar1.High < Bar3.Low
- Bearish FVG: Gap where Bar1.Low > Bar3.High
- Institutional inefficiency zones where price tends to return

### 2. Equal Highs/Lows (EQ)

```python
from core.multi_timeframe import EqualHighsLows

eq_detector = EqualHighsLows()

# Detect equal highs (liquidity pools)
equal_highs = eq_detector.detect_equal_highs(df, tolerance=0.001)

# Detect equal lows
equal_lows = eq_detector.detect_equal_lows(df, tolerance=0.001)
```

**What is EQ?**
- Multiple swing highs at approximately same level
- Multiple swing lows at approximately same level
- Strong liquidity pools where stops accumulate

### 3. Multi-Timeframe Analysis

```python
from core.multi_timeframe import MultiTimeframeAnalysis

mtf = MultiTimeframeAnalysis()

# Analyze a timeframe with ALL confluences
analysis = mtf.analyze_timeframe(df_4h, '4H')

# Returns:
# - Trend/bias
# - Swing points
# - BOS/CHoCH events
# - Order blocks
# - Liquidity pools
# - FVGs
# - Equal highs/lows
# - Bollinger Bands
```

### 4. HTF → ITF → LTF Strategy

```python
from strategies.htf_itf_confluence import HTFITFStrategy

strategy = HTFITFStrategy(htf='4H', itf='1H', ltf='15M')

signals = strategy.generate_signals(
    htf_df=df_4h,
    itf_df=df_1h,
    ltf_df=df_15m,
    confluence_combo=['fvg', 'ob', 'eq'],  # HTF, 2nd, 3rd confluences
    require_ltf_bos=True  # True = LTF BOS, False = directional candle
)
```

## Quick Start: Test Your Strategy

### Example 1: Single Configuration Test

```python
from core.data_handler import DataHandler
from strategies.htf_itf_confluence import HTFITFStrategy
from core.backtest import Backtester

# Fetch data
handler = DataHandler()
df_4h = handler.fetch_data('EURUSD=X', '2025-01-01', '2026-07-15', '1h')
df_4h = handler.resample_data(df_4h, '4H')
df_1h = handler.fetch_data('EURUSD=X', '2025-01-01', '2026-07-15', '1h')
df_15m = handler.fetch_data('EURUSD=X', '2025-01-01', '2026-07-15', '15m')

# Create strategy
strategy = HTFITFStrategy(htf='4H', itf='1H', ltf='15M')

# Generate signals with your confluence combo
signals = strategy.generate_signals(
    htf_df=df_4h,
    itf_df=df_1h,
    ltf_df=df_15m,
    confluence_combo=['fvg', 'ob', 'eq'],  # FVG → OB → EQ
    require_ltf_bos=True
)

# Backtest
backtester = Backtester()
metrics = backtester.run_backtest(df_15m, signals)
backtester.print_summary(metrics)
```

### Example 2: Test Multiple Confluences

```python
from strategies.htf_itf_confluence import ConfluenceTester

tester = ConfluenceTester()

# Test all confluence combinations
results = tester.test_confluence_combinations(
    symbol='EURUSD=X',
    start_date='2025-01-01',
    end_date='2026-07-15',
    htf='4H',
    itf='1H',
    ltf='15M',
    test_ltf_entry=True  # Test both BOS and candle entries
)

# View top performers
print(results.head(10))
```

### Example 3: Comprehensive Forex Testing

```python
from examples.forex_testing_suite import ForexTestingSuite

suite = ForexTestingSuite()

# Test multiple pairs with all variations
results = suite.run_comprehensive_test(
    pairs=['EURUSD=X', 'GBPUSD=X', 'USDJPY=X'],
    max_tests_per_pair=10  # Test 10 confluence combos per pair/TF
)

# Analyze results
pair_analysis = suite.analyze_by_pair(results)
tf_analysis = suite.analyze_by_timeframe(results)
conf_analysis = suite.analyze_by_confluence(results)
```

## Confluence Types Available

### 1. FVG (Fair Value Gap)
- **Bullish FVG**: Price gap to the upside
- **Bearish FVG**: Price gap to the downside
- Price tends to return to fill these gaps

### 2. OB (Order Block)
- Last opposite candle before strong move
- Institutional positioning zones
- High probability of reaction on retest

### 3. BB (Bollinger Band)
- Upper band: Potential resistance in bearish setups
- Lower band: Potential support in bullish setups
- Mean reversion zones

### 4. EQ (Equal Highs/Lows)
- Multiple touches at same price level
- Liquidity pools where stops cluster
- High probability of sweep and reversal

## Confluence Combinations to Test

The framework tests these combinations:

```python
CONFLUENCE_COMBOS = [
    ['fvg', 'ob', 'eq'],   # FVG → OB → Equal High/Low
    ['fvg', 'ob', 'bb'],   # FVG → OB → Bollinger Band
    ['ob', 'fvg', 'eq'],   # OB → FVG → Equal High/Low
    ['ob', 'bb', 'fvg'],   # OB → BB → FVG
    ['eq', 'ob', 'fvg'],   # EQ → OB → FVG
    ['eq', 'bb', 'ob'],    # EQ → BB → OB
    ['bb', 'fvg', 'eq'],   # BB → FVG → EQ
    ['bb', 'ob', 'eq'],    # BB → OB → EQ
    ['fvg', 'eq', 'ob'],   # FVG → EQ → OB
    ['ob', 'eq', 'bb'],    # OB → EQ → BB
]
```

## Timeframe Combinations

Default combinations tested:

```python
TIMEFRAME_COMBOS = [
    {'htf': '4H', 'itf': '1H', 'ltf': '15M'},  # Your setup
    {'htf': '4H', 'itf': '1H', 'ltf': '5M'},   # Faster entries
    {'htf': '1D', 'itf': '4H', 'ltf': '1H'},   # Swing trading
    {'htf': '1D', 'itf': '4H', 'ltf': '15M'},  # Mixed approach
]
```

## Forex Pairs Tested

Major forex pairs:

```python
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
```

## Running Comprehensive Tests

### Full Test Suite

```bash
cd examples
python forex_testing_suite.py
```

This will:
1. Test 4 major forex pairs
2. Test 4 timeframe combinations each
3. Test 5 confluence combinations per TF
4. Test both BOS and candle entries
5. Generate ~160 total tests
6. Produce detailed analysis files

### Output Files

- `forex_comprehensive_results.csv`: All test results
- `forex_pair_analysis.csv`: Performance by pair
- `forex_timeframe_analysis.csv`: Performance by TF combo
- `forex_confluence_analysis.csv`: Performance by confluence
- `forex_entry_analysis.csv`: BOS vs Candle comparison

## Interpreting Results

### Key Metrics

```
return: Total return percentage
win_rate: Percentage of winning trades
profit_factor: Gross profit / Gross loss
sharpe: Sharpe ratio (risk-adjusted return)
max_dd: Maximum drawdown percentage
trades: Number of trades executed
expectancy: Average P&L per trade
```

### What to Look For

**Best Configurations:**
- Return > 10%
- Win Rate > 55%
- Profit Factor > 1.5
- Sharpe Ratio > 1.0
- Max Drawdown < 15%

**Signal Quality:**
- More signals = more opportunities
- But fewer high-quality signals often better
- Look for balance: 20-50 signals in 180 days

## Customization

### Custom Confluence Order

```python
# Test your specific sequence
signals = strategy.generate_signals(
    htf_df, itf_df, ltf_df,
    confluence_combo=['ob', 'fvg', 'bb'],  # Your order
    require_ltf_bos=True
)
```

### Custom Timeframes

```python
strategy = HTFITFStrategy(
    htf='1D',   # Daily for swing trading
    itf='4H',   # 4-hour for entries
    ltf='1H'    # 1-hour for execution
)
```

### Custom Entry Logic

```python
# Entry on LTF BOS (more confirmation)
signals_bos = strategy.generate_signals(..., require_ltf_bos=True)

# Entry on directional candle (faster, more signals)
signals_candle = strategy.generate_signals(..., require_ltf_bos=False)
```

## Advanced Usage

### Test Specific Scenario

```python
from examples.forex_testing_suite import ForexTestingSuite

suite = ForexTestingSuite()

# Test only EURUSD with specific setup
result = suite.test_single_pair(
    pair='EURUSD=X',
    start_date='2025-01-01',
    end_date='2026-07-15',
    tf_combo={'htf': '4H', 'itf': '1H', 'ltf': '15M', 'name': '4H-1H-15M'},
    confluence_combo=['fvg', 'ob', 'eq'],
    entry_type='bos'
)

print(result)
```

### Add Your Own Confluence

Edit `core/multi_timeframe.py` and add to `detect_confluence_hit()`:

```python
elif confluence_type == 'your_confluence':
    # Your detection logic here
    if condition_met:
        return True, {'type': 'your_confluence', 'data': {...}}
```

## Performance Optimization

### For Faster Testing

```python
# Test fewer combinations
results = suite.run_comprehensive_test(
    pairs=['EURUSD=X'],  # Single pair
    max_tests_per_pair=3  # Fewer combos
)
```

### For More Thorough Testing

```python
# Test all pairs and combinations
results = suite.run_comprehensive_test(
    pairs=suite.FOREX_PAIRS,  # All 10 pairs
    max_tests_per_pair=20  # More combos
)
```

## Example Output

```
================================================================================
COMPREHENSIVE FOREX MULTI-TIMEFRAME TESTING
================================================================================
Pairs: 4
Timeframe Combos: 4
Confluence Combos per TF: 5
Entry Types: 2 (BOS + Candle)
Period: 2025-01-01 to 2026-07-15
Total Tests: ~160
================================================================================

[1/4] Testing EURUSD=X
------------------------------------------------------------
  Timeframes: 4H-1H-15M
    Testing confluence 1/5... Done (10 tests completed)
    ...

================================================================================
TOP 20 CONFIGURATIONS
================================================================================

pair      tf_combo  confluence     entry  signals  return  win_rate  profit_factor
EURUSD=X  4H-1H-15M fvg → ob → eq  bos    34      18.45   64.7      2.34
GBPUSD=X  4H-1H-15M ob → fvg → bb  bos    28      15.23   58.9      1.87
...

================================================================================
SUMMARY STATISTICS
================================================================================

Total Tests: 160
Valid Results: 124
Configurations with Signals: 124
Errors: 0

Performance Distribution:
  Positive Return: 89 (71.8%)
  Win Rate > 50%: 76
  Win Rate > 60%: 34
  Profit Factor > 1.5: 52
  Sharpe > 1.0: 41

Average Metrics (All Valid):
  Avg Return: 8.34%
  Avg Win Rate: 54.2%
  Avg Profit Factor: 1.45
  Avg Sharpe: 0.87
  Avg Max DD: 12.3%
```

## Next Steps

1. **Run initial test**: Start with `forex_testing_suite.py`
2. **Analyze results**: Review CSV files for top performers
3. **Refine parameters**: Test winning combos with variations
4. **Forward test**: Use best configs on new data
5. **Paper trade**: Validate in live market conditions

## Files Structure

```
/workspace/
├── core/
│   └── multi_timeframe.py      # FVG, EQ, MTF analysis
├── strategies/
│   └── htf_itf_confluence.py   # HTF→ITF→LTF strategy
└── examples/
    └── forex_testing_suite.py  # Comprehensive testing
```

## Support

For questions or issues:
1. Check `docs/RESEARCH.md` for methodology
2. Review `docs/API.md` for function details
3. Examine example code in `examples/`

---

**Ready to test your multi-timeframe confluence strategy across forex markets!** 🚀
