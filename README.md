# Quantitative Trading Framework

A comprehensive Python framework for algorithmic trading that combines advanced quantitative analysis, market structure analysis, liquidity detection, and institutional order flow analysis.

## 🎯 Overview

This framework implements cutting-edge trading methodologies used by professional traders and institutions in 2026, including:

- **Market Structure Analysis**: Break of Structure (BOS), Change of Character (CHoCH)
- **Liquidity Analysis**: Sweep detection, liquidity pools, institutional order flow
- **Momentum Indicators**: RSI, MACD, Volume analysis, CVD (Cumulative Volume Delta)
- **Trend Analysis**: EMAs, SuperTrend, VWAP, ADX
- **Reversal Detection**: Divergence patterns, double tops/bottoms, exhaustion candles
- **Session Analysis**: London/NY session timing and overlap detection
- **Composite Scoring**: Multi-factor signal evaluation system
- **Backtesting Engine**: Comprehensive performance analysis

## 🚀 Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Basic Usage

```python
from core.data_handler import DataHandler
from core.signals import SignalGenerator
from core.backtest import Backtester

# 1. Load data
data_handler = DataHandler()
df = data_handler.fetch_data('SPY', '2025-01-01', '2026-07-15', '1h')

# 2. Generate signals
signal_gen = SignalGenerator()
df_analyzed = signal_gen.analyze_complete(df)
signals = signal_gen.generate_signals(df_analyzed, strategy_type='comprehensive')

# 3. Backtest
backtester = Backtester(initial_capital=100000)
metrics = backtester.run_backtest(df_analyzed, signals)
backtester.print_summary(metrics)
```

## 📁 Project Structure

```
quantitative-trading-framework/
├── config.py                    # Configuration settings
├── requirements.txt             # Dependencies
├── core/                        # Core modules
│   ├── data_handler.py         # Data fetching and preparation
│   ├── indicators.py           # Technical indicators
│   ├── liquidity.py            # Liquidity analysis
│   ├── market_structure.py     # BOS/CHoCH detection
│   ├── sessions.py             # Session analysis
│   ├── reversals.py            # Reversal pattern detection
│   ├── signals.py              # Signal generation
│   └── backtest.py             # Backtesting engine
├── strategies/                  # Example strategies
│   └── example_strategies.py   # Pre-built strategies
└── examples/                    # Usage examples
    └── quickstart.py           # Quick start guide
```

## 🔬 Key Features

### 1. Liquidity Analysis

The framework detects institutional liquidity patterns:

- **Liquidity Pools**: Identifies significant support/resistance levels where stops accumulate
- **Liquidity Sweeps**: Detects stop hunts and institutional accumulation
- **Order Blocks**: Identifies zones where institutions positioned
- **CVD Analysis**: Cumulative Volume Delta for order flow tracking

**5-Factor Liquidity Sweep Scoring:**
- F1: Wick Rejection Purity (28%)
- F2: Volume Participation (20%)
- F3: CVD Net Absorption (25%)
- F4: Structural Recovery (17%)
- F5: Session Window (10%)

### 2. Market Structure Analysis

Implements Smart Money Concepts (SMC):

- **Break of Structure (BOS)**: Confirms trend continuation
  - Bullish BOS: Price breaks above previous swing high
  - Bearish BOS: Price breaks below previous swing low
  - Requires momentum confirmation and volume validation

- **Change of Character (CHoCH)**: Signals potential reversals
  - Opposite direction break indicates trend shift
  - Early warning for trend changes

- **Swing Point Detection**: Identifies higher highs/lows, lower highs/lows

### 3. Momentum & Trend Indicators

Professional-grade indicators with optimal settings:

```python
# Momentum
RSI (14): Overbought/oversold, divergence
MACD (12/26/9): Trend momentum, crossovers
Volume Z-Score: Abnormal volume detection

# Trend
EMA (9/21/50/200): Multi-timeframe trend
SuperTrend (10,3): Clear trend direction
VWAP: Institutional reference price
ADX (14): Trend strength measurement
```

### 4. Session-Based Analysis

Optimizes timing based on global trading sessions:

- **London Session** (7-10 UTC): 100% weight, highest institutional activity
- **New York Session** (13-16 UTC): 85% weight, second-highest volume
- **London/NY Overlap** (13-16 UTC): Maximum liquidity window
- **Off-Peak**: 45% weight, reduced activity

### 5. Reversal Detection

Multiple reversal confirmation methods:

- **RSI/MACD Divergence**: Price vs indicator disagreement
- **Double Tops/Bottoms**: Classic reversal patterns
- **Exhaustion Candles**: High volume, large wicks, reversal closes
- **Overbought/Oversold**: Extreme RSI/RSI conditions

### 6. Composite Scoring System

Every signal receives a 0-100 composite score based on:

```python
Composite Score = (
    Trend Score × 0.25 +
    Momentum Score × 0.20 +
    Volume Score × 0.20 +
    Structure Score × 0.20 +
    Session Score × 0.10 +
    Liquidity Score × 0.05
)
```

Only signals above configurable thresholds generate trades.

## 📊 Pre-Built Strategies

### 1. TJR Enhanced Strategy
Upgraded version combining market structure, liquidity sweeps, and session timing.
- **Best For**: Day trading, swing trading
- **Timeframes**: 15m, 1h, 4h

### 2. Momentum Breakout Strategy
Trades breakouts with strong momentum confirmation.
- **Best For**: Trending markets
- **Timeframes**: 5m, 15m, 1h

### 3. Reversal Strategy
Identifies high-probability reversal points.
- **Best For**: Range-bound markets
- **Timeframes**: 1h, 4h, 1d

### 4. Market Structure Strategy
Pure structure trading (BOS/CHoCH).
- **Best For**: Clean trending/reversal moves
- **Timeframes**: 15m, 1h, 4h

### 5. Session-Based Strategy
Only trades during London and NY sessions.
- **Best For**: Forex, indices
- **Timeframes**: 15m, 1h

### 6. Scalping Strategy
Fast entries/exits for short-term traders.
- **Best For**: Active day trading
- **Timeframes**: 1m, 5m

### 7. Swing Strategy
Multi-day holds for larger moves.
- **Best For**: Position trading
- **Timeframes**: 4h, 1d

## ⚙️ Configuration

Edit `config.py` to customize:

```python
# Indicator settings
INDICATORS['RSI']['period'] = 14
INDICATORS['MACD']['fast'] = 12

# Risk management
RISK['max_risk_per_trade'] = 0.02  # 2% per trade
RISK['risk_reward_ratio'] = 2.0

# Signal filters
FILTERS['min_composite_score'] = 60
FILTERS['require_session_alignment'] = True
```

## 📈 Backtesting

The backtesting engine provides comprehensive metrics:

```python
backtester = Backtester(initial_capital=100000)
metrics = backtester.run_backtest(df, signals)

# Available metrics:
# - Total return, P&L
# - Win rate, profit factor
# - Sharpe ratio, expectancy
# - Max drawdown
# - Average win/loss
# - Long vs short performance
```

## 🎓 Usage Examples

### Example 1: Quick Analysis

```python
from strategies.example_strategies import TJRStrategy

strategy = TJRStrategy()
signals = strategy.generate_signals(df)
print(f"Generated {len(signals)} signals")
```

### Example 2: Custom Strategy

```python
from core.signals import SignalGenerator

signal_gen = SignalGenerator()
df = signal_gen.analyze_complete(df)

# Custom logic
custom_signals = []
for i in range(50, len(df)):
    if (df['rsi'].iloc[i] > 50 and 
        df['close'].iloc[i] > df['vwap'].iloc[i] and
        df['rvol'].iloc[i] > 1.5):
        # Add signal logic...
        pass
```

### Example 3: Strategy Comparison

```python
from strategies.example_strategies import run_strategy_comparison

results = run_strategy_comparison(
    symbol='SPY',
    start_date='2025-01-01',
    end_date='2026-07-15',
    interval='1h'
)
```

## 📚 Research & Methodology

This framework is based on 2026 institutional trading research:

### Key Research Findings:

1. **Liquidity is Dynamic**: Modern markets have mobile liquidity, not static levels
2. **Session Timing Matters**: 35-43% of forex volume occurs during London session
3. **Volume Confirms Moves**: High-probability setups require elevated volume
4. **Structure Before Entry**: Wait for structural confirmation (BOS/CHoCH)
5. **Multi-Factor Validation**: Single indicators fail; composite scoring succeeds

### Sources:
- BIS (Bank for International Settlements) liquidity data
- LuxAlgo market structure research (2026)
- PickMyTrade institutional sweep analysis
- Bookmap order flow studies

## 🔧 Advanced Features

### Custom Indicators

Add your own indicators to `core/indicators.py`:

```python
@staticmethod
def custom_indicator(df: pd.DataFrame, period: int) -> pd.Series:
    # Your indicator logic
    return result
```

### Custom Scoring

Modify scoring weights in `config.py`:

```python
SCORING_WEIGHTS = {
    'wick_rejection': 0.28,
    'volume_participation': 0.20,
    # ...
}
```

### Multi-Timeframe Analysis

```python
from core.data_handler import DataHandler

data_handler = DataHandler()
df_1h = data_handler.fetch_data('SPY', start, end, '1h')
df_4h = data_handler.resample_data(df_1h, '4H')
```

## 📊 Performance Metrics

The framework tracks:

- **Return Metrics**: Total return, CAGR, monthly returns
- **Risk Metrics**: Max drawdown, Sharpe ratio, Sortino ratio
- **Trade Metrics**: Win rate, profit factor, expectancy
- **Execution Metrics**: Avg trade duration, long/short performance

## 🚨 Risk Management

Built-in risk controls:

```python
# Per-trade risk
max_risk_per_trade = 0.02  # 2%

# Position sizing
size = (capital × max_risk) / (entry - stop_loss)

# Max positions
max_positions = 3

# Daily loss limit
max_daily_loss = 0.06  # 6%
```

## 🤝 Contributing

This is a research and educational framework. Contributions welcome:

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

## ⚠️ Disclaimer

**This framework is for educational and research purposes only.**

- Past performance does not guarantee future results
- Trading involves substantial risk of loss
- Always paper trade before risking real capital
- Consult a financial advisor before trading
- The authors are not responsible for trading losses

## 📝 License

MIT License - See LICENSE file for details

## 📧 Support

For questions, issues, or feature requests:
- Open an issue on GitHub
- Check the examples/ directory
- Review the research documentation

---

**Built with quantitative analysis expertise for the modern trader.**

*Last Updated: July 2026*
