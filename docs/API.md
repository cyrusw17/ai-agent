"""
API Reference Documentation
"""

# Complete API Reference

## Data Handler

```python
from core.data_handler import DataHandler

handler = DataHandler()

# Fetch data
df = handler.fetch_data(
    symbol='SPY',
    start_date='2025-01-01',
    end_date='2026-07-15',
    interval='1h'  # 1m, 5m, 15m, 1h, 1d
)

# Resample data
df_4h = handler.resample_data(df, '4H')

# Get session data
london_data = handler.get_session_data(df, session_start=7, session_end=10)

# Split train/test
train, test = handler.split_train_test(df, train_ratio=0.8)
```

## Technical Indicators

```python
from core.indicators import TechnicalIndicators

# RSI
rsi = TechnicalIndicators.rsi(df, period=14)

# MACD
macd_line, signal_line, histogram = TechnicalIndicators.macd(df)

# EMAs
ema_9 = TechnicalIndicators.ema(df, period=9)
ema_21 = TechnicalIndicators.ema(df, period=21)

# SuperTrend
supertrend, direction = TechnicalIndicators.supertrend(df, period=10, multiplier=3.0)

# VWAP
vwap = TechnicalIndicators.vwap(df)

# ADX
adx, plus_di, minus_di = TechnicalIndicators.adx(df)

# ATR
atr = TechnicalIndicators.atr(df, period=14)

# Bollinger Bands
upper, middle, lower = TechnicalIndicators.bollinger_bands(df)

# OBV
obv = TechnicalIndicators.obv(df)

# Relative Volume
rvol = TechnicalIndicators.relative_volume(df)

# Volume Z-Score
vol_zscore = TechnicalIndicators.volume_zscore(df, period=20)
```

## Liquidity Analysis

```python
from core.liquidity import LiquidityAnalysis

liquidity = LiquidityAnalysis()

# Identify liquidity pools
pools = liquidity.identify_liquidity_pools(df, lookback=50, min_touches=2)

# Detect sweeps
sweeps = liquidity.detect_liquidity_sweep(df, pools)

# Calculate CVD
cvd_zscore = liquidity.calculate_cvd(df, window=20)

# Score sweep
sweep_score = liquidity.score_liquidity_sweep(
    df, 
    sweep_idx=100, 
    session_weight=1.0
)

# Identify order blocks
order_blocks = liquidity.identify_order_blocks(df, lookback=3)
```

## Market Structure

```python
from core.market_structure import MarketStructure

structure = MarketStructure()

# Identify swing points
swing_highs, swing_lows = structure.identify_swing_points(df, lookback=5)

# Detect BOS
bos_events = structure.detect_break_of_structure(
    df, 
    swing_highs, 
    swing_lows,
    min_momentum=2.0
)

# Detect CHoCH
choch_events = structure.detect_change_of_character(df, swing_highs, swing_lows)

# Identify trend
trend = structure.identify_trend(df)

# Score BOS
bos_score = structure.score_bos(df, bos_idx=100, order_blocks=order_blocks)

# Get HH/HL/LH/LL patterns
patterns = structure.identify_higher_highs_lows(df, swing_highs, swing_lows)

# Structure strength
strength = structure.calculate_structure_strength(df)
```

## Session Analysis

```python
from core.sessions import SessionAnalysis

sessions = SessionAnalysis()

# Add session info
df = sessions.add_session_info(df)

# Get statistics
stats = sessions.calculate_session_statistics(df)

# High impact times
high_impact = sessions.identify_high_impact_times(df, volume_threshold=1.5)

# Overlap analysis
overlap_stats = sessions.session_overlap_analysis(df)

# Session trend
london_trend = sessions.get_session_trend(df, 'LONDON')

# Mark key times
df = sessions.mark_key_times(df)
```

## Reversal Detection

```python
from core.reversals import ReversalDetection

reversals = ReversalDetection()

# RSI divergence
rsi_divs = reversals.detect_rsi_divergence(df, lookback=14)

# MACD divergence
macd_divs = reversals.detect_macd_divergence(df, lookback=14)

# Double tops/bottoms
patterns = reversals.detect_double_top_bottom(
    df, 
    tolerance=0.02, 
    min_distance=10
)

# Exhaustion candles
exhaustion = reversals.detect_exhaustion_candles(df, volume_threshold=2.0)

# Score reversal probability
reversal_prob = reversals.score_reversal_probability(
    df, 
    idx=100,
    divergences=rsi_divs,
    patterns=patterns
)
```

## Signal Generation

```python
from core.signals import SignalGenerator

signal_gen = SignalGenerator()

# Complete analysis
df_analyzed = signal_gen.analyze_complete(df)

# Generate signals
signals = signal_gen.generate_signals(
    df_analyzed,
    strategy_type='comprehensive'  # 'momentum', 'reversal', 'structure'
)

# Filter signals
filtered = signal_gen.filter_signals(
    signals,
    min_score=65,
    min_risk_reward=2.0
)
```

## Backtesting

```python
from core.backtest import Backtester

backtester = Backtester(
    initial_capital=100000,
    commission=0.001,
    slippage=0.0005
)

# Run backtest
metrics = backtester.run_backtest(
    df, 
    signals,
    max_risk_per_trade=0.02
)

# Print summary
backtester.print_summary(metrics)

# Get results
equity_curve = backtester.get_equity_curve()
trades_df = backtester.get_trades_dataframe()
```

## Pre-Built Strategies

```python
from strategies.example_strategies import (
    TJRStrategy,
    MomentumBreakoutStrategy,
    ReversalStrategy,
    StructureStrategy,
    SessionBasedStrategy,
    ScalpingStrategy,
    SwingStrategy
)

# Use a strategy
strategy = TJRStrategy()
signals = strategy.generate_signals(df)

# Compare strategies
from strategies.example_strategies import run_strategy_comparison

results = run_strategy_comparison(
    symbol='SPY',
    start_date='2025-01-01',
    end_date='2026-07-15',
    interval='1h'
)
```

## Configuration

```python
import config

# Modify settings
config.INDICATORS['RSI']['period'] = 9
config.RISK['max_risk_per_trade'] = 0.015
config.FILTERS['min_composite_score'] = 70

# Access settings
session_info = config.SESSIONS['LONDON']
weights = config.SCORING_WEIGHTS
```

## Common Workflows

### Workflow 1: Quick Backtest

```python
from core.data_handler import DataHandler
from core.signals import SignalGenerator
from core.backtest import Backtester

# 1. Get data
df = DataHandler().fetch_data('SPY', '2025-01-01', '2026-07-15', '1h')

# 2. Generate signals
signal_gen = SignalGenerator()
df = signal_gen.analyze_complete(df)
signals = signal_gen.generate_signals(df, 'comprehensive')

# 3. Backtest
backtester = Backtester()
metrics = backtester.run_backtest(df, signals)
backtester.print_summary(metrics)
```

### Workflow 2: Custom Strategy

```python
from core.data_handler import DataHandler
from core.indicators import TechnicalIndicators
from core.market_structure import MarketStructure

# Get data
df = DataHandler().fetch_data('SPY', '2025-01-01', '2026-07-15', '1h')

# Add indicators
df['rsi'] = TechnicalIndicators.rsi(df)
df['ema_9'] = TechnicalIndicators.ema(df, 9)
df['ema_21'] = TechnicalIndicators.ema(df, 21)

# Custom logic
signals = []
for i in range(50, len(df)):
    if (df['rsi'].iloc[i] > 50 and 
        df['ema_9'].iloc[i] > df['ema_21'].iloc[i]):
        signals.append({
            'type': 'LONG',
            'index': i,
            'timestamp': df.index[i],
            'entry_price': df['close'].iloc[i],
            # Add stop/TP levels...
        })
```

### Workflow 3: Multi-Timeframe Analysis

```python
from core.data_handler import DataHandler
from core.signals import SignalGenerator

handler = DataHandler()

# Get multiple timeframes
df_1h = handler.fetch_data('SPY', '2025-01-01', '2026-07-15', '1h')
df_4h = handler.resample_data(df_1h, '4H')
df_daily = handler.resample_data(df_1h, '1D')

# Analyze each
signal_gen = SignalGenerator()

df_1h = signal_gen.analyze_complete(df_1h)
df_4h = signal_gen.analyze_complete(df_4h)
df_daily = signal_gen.analyze_complete(df_daily)

# Check alignment
# Entry on 1h if 4h and daily trends align
```

## Error Handling

```python
try:
    df = DataHandler().fetch_data('INVALID', '2025-01-01', '2026-07-15')
except ValueError as e:
    print(f"Data error: {e}")

try:
    signals = signal_gen.generate_signals(df, 'invalid_type')
except ValueError as e:
    print(f"Strategy error: {e}")
```

## Performance Tips

1. **Vectorize operations** - Use pandas operations instead of loops
2. **Cache results** - Store analyzed dataframes
3. **Limit lookback** - Don't analyze entire history repeatedly
4. **Use appropriate intervals** - Don't fetch 1m data for swing trading
5. **Filter early** - Apply filters before backtesting

## Debugging

```python
# Enable verbose logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check data quality
print(f"Missing values: {df.isnull().sum()}")
print(f"Date range: {df.index[0]} to {df.index[-1]}")
print(f"Total bars: {len(df)}")

# Inspect signals
print(f"Total signals: {len(signals)}")
print(f"Long/Short: {len(signals[signals['type']=='LONG'])} / {len(signals[signals['type']=='SHORT'])}")
print(f"Avg score: {signals['composite_score'].mean():.2f}")
```
