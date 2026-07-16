# 🤖 Agent Task: Recreate Forex Trading Strategy (2020-2025 Data)

## 📋 Mission Overview

You are tasked with **recreating and optimizing a forex trading strategy** using **ONLY data from 2020-2025**. The goal is to develop a strategy that can then be **forward-tested on 2026 data** to validate its real-world performance without look-ahead bias.

---

## 🎯 Objectives

### Primary Goal
Develop a **profitable, robust forex trading strategy** that:
- Works on major forex pairs (EURUSD, GBPUSD, USDJPY, AUDUSD)
- Uses 50:1 leverage (legal for US citizens)
- Achieves consistent returns with manageable risk
- Can pass funded account evaluations (optional target)

### Success Metrics
1. **Profitability**: Positive returns over 2020-2025 period
2. **Consistency**: Works across different market conditions
3. **Risk Management**: Max drawdown < 20%
4. **Trade Frequency**: 5-20 trades per month
5. **Sharpe Ratio**: > 1.5 (ideally > 2.0)
6. **Win Rate**: > 55%

---

## ⚠️ CRITICAL CONSTRAINT: NO 2026 DATA

**DO NOT USE ANY DATA FROM 2026.**

- Training data: **2020-01-01 to 2025-12-31**
- Validation data: Use walk-forward analysis within 2020-2025
- Forward testing: Will be done separately on 2026 data

This ensures **no look-ahead bias** and validates true predictive power.

---

## 📚 Reference Strategy (What Was Built Before)

A previous agent developed a successful strategy on 2023-2026 data. Here's what worked:

### Core Components

#### 1. **Dual Strategy System**
- **Sniper Strategy**: High R:R, lower frequency
  - EMA 3/9 crossover
  - ADX > 10 filter
  - 1.0 ATR stop-loss, 5.0 ATR take-profit
  - Max 2 trades per pair per month
  - Risk: 2% per trade
  
- **Background Strategy**: Moderate R:R, higher frequency
  - EMA 9/21 crossover
  - ADX > 20 filter
  - 2.0 ATR stop-loss, 3.0 ATR take-profit
  - No monthly limits
  - Risk: 1% per trade

#### 2. **Key Enhancements**
- **Dynamic Targets**: Adjust SL/TP based on volatility regime
  - High volatility: Tighter targets (0.75x multiplier)
  - Low volatility: Wider targets (1.5x multiplier)
  - Normal: Standard targets
  
- **Volatility Regime Detection**:
  - ATR z-score calculation (50-period lookback)
  - Classify as high/normal/low volatility
  
- **Multi-Pair Portfolio**: Trade 4 major pairs simultaneously
- **Capital Allocation**: 60% sniper / 40% background

#### 3. **Risk Management**
- Fixed 20% max drawdown limit
- Position sizing based on capital allocation
- Dynamic stop-loss using ATR
- Leverage: 50:1 (legal US maximum)

#### 4. **Performance (2023-2026)**
- 90-day return: **~1,070%**
- 3-year return: **~1,800%**
- Win rate: **~70%**
- Max drawdown: **~12%**

---

## 🛠️ Tools & Resources Available

### Python Libraries
```python
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
```

### Custom Modules (Check `/workspace/core/`)
```python
from core.data_handler import DataHandler
from core.indicators import TechnicalIndicators
from core.backtest import Backtester
```

### Available Indicators
- EMA (Exponential Moving Average)
- SMA (Simple Moving Average)
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- ADX (Average Directional Index)
- ATR (Average True Range)
- Bollinger Bands
- Stochastic
- CCI (Commodity Channel Index)
- Volume indicators

### Data Access
- Yahoo Finance via `yfinance` library
- 4H and 1D timeframes recommended
- Forex pairs available: All major pairs

---

## 📊 Development Process

### Phase 1: Research & Exploration (2-3 hours)

**Goal**: Understand market behavior during 2020-2025

1. **Market Analysis**
   - Analyze volatility patterns across 2020-2025
   - Identify major market events (COVID crash, recovery, etc.)
   - Study trend vs. range-bound periods
   
2. **Indicator Research**
   - Test correlation between indicators and price movements
   - Identify which indicators work best in different regimes
   - Consider: EMAs, ADX, RSI, ATR, MACD

3. **Signal Generation Ideas**
   - EMA crossovers (various periods)
   - Momentum breakouts
   - Volatility expansion/contraction
   - Trend-following signals
   - Mean reversion signals

**Deliverable**: Document with 3-5 promising strategy concepts

---

### Phase 2: Strategy Development (4-6 hours)

**Goal**: Build and test multiple strategy variants

1. **Core Strategy Types to Test**
   
   **A. Dual Strategy (Recommended)**
   - High R:R "sniper" component
   - Higher frequency "background" component
   - Test different EMA periods (5/13, 8/21, 3/9, etc.)
   - Test different ADX thresholds
   
   **B. Single Strategy Variants**
   - Pure trend-following
   - Momentum-based
   - Volatility breakout
   
   **C. Enhancement Ideas**
   - Time-of-day filters
   - Session-based trading (London, NY, Asian)
   - Multi-timeframe confluence
   - Volatility regime adaptation

2. **Parameter Optimization**
   
   **Key Parameters to Test**:
   ```python
   # EMA periods
   fast_ema_range = [3, 5, 8, 13]
   slow_ema_range = [9, 13, 21, 34]
   
   # ADX thresholds
   adx_threshold_range = [10, 15, 20, 25, 30]
   
   # Risk levels (% per trade)
   risk_range = [1.0, 1.5, 2.0, 2.5, 3.0, 5.0]
   
   # ATR multipliers
   stop_mult_range = [0.75, 1.0, 1.25, 1.5, 2.0]
   target_mult_range = [2.0, 3.0, 4.0, 5.0, 7.5, 10.0]
   ```

3. **Backtesting Framework**
   
   **Requirements**:
   - Use realistic costs (OANDA spreads: 1.2-1.5 pips)
   - Include slippage (0.5-1.0 pips)
   - Proper position sizing with leverage constraints
   - Track drawdown continuously
   - Log all trades for analysis
   
   **Validation Method**:
   - Walk-forward analysis (6-month train, 3-month test)
   - Out-of-sample testing (2024-2025 data)
   - Monte Carlo simulation (100+ runs)

**Deliverable**: 5-10 strategy configurations with backtest results

---

### Phase 3: Optimization & Selection (3-4 hours)

**Goal**: Identify the best strategy configuration

1. **Multi-Factor Scoring**
   
   Weight strategies by:
   ```python
   composite_score = (
       return_pct * 0.25 +
       sharpe_ratio * 20 * 0.25 +
       (100 - max_drawdown) * 0.20 +
       win_rate * 0.15 +
       consistency_score * 0.15
   )
   ```

2. **Robustness Testing**
   - Test on different 2-year windows within 2020-2025
   - Verify performance across different pairs
   - Check performance in trending vs. ranging markets
   - Stress test with reduced win rates (-10%)

3. **Risk Management Validation**
   - Confirm max drawdown stays < 20%
   - Test different capital allocation scenarios
   - Verify position sizing logic
   - Check for correlation between pairs

**Deliverable**: Top 3 strategy configurations ranked by composite score

---

### Phase 4: Documentation & Deliverables (1-2 hours)

**Goal**: Create comprehensive documentation

1. **Strategy Documentation**
   ```markdown
   # Final Strategy Specification
   
   ## Configuration
   - Entry signals: [detailed logic]
   - Exit signals: [detailed logic]
   - Position sizing: [formula]
   - Risk management: [rules]
   
   ## Performance (2020-2025)
   - Total return: X%
   - Annualized return: Y%
   - Max drawdown: Z%
   - Sharpe ratio: N
   - Win rate: W%
   - Total trades: T
   
   ## Parameter Settings
   [List all parameters with final values]
   ```

2. **Code Implementation**
   - Clean, production-ready Python scripts
   - Backtesting script with all logic
   - Strategy execution script (ready for API integration)
   - Visualization scripts for performance charts

3. **Backtest Results**
   - CSV files with all trades
   - Equity curves for each year
   - Monthly performance breakdown
   - Drawdown analysis

**Deliverable**: Complete strategy package ready for forward testing

---

## 🎨 Creative Freedom Guidelines

### What You CAN Change
✅ **Indicator combinations** (try different EMAs, add RSI/MACD, etc.)
✅ **Parameter values** (EMA periods, ADX thresholds, R:R ratios)
✅ **Entry/exit logic** (crossovers, divergence, breakouts)
✅ **Risk levels** (1-5% per trade range)
✅ **Timeframes** (4H, 1H, daily - test what works)
✅ **Filters** (time-of-day, session, volatility regime)
✅ **Enhancement features** (partial exits, dynamic targets, etc.)

### What You MUST Keep
⚠️ **Forex pairs**: Must include EURUSD, GBPUSD, USDJPY, AUDUSD
⚠️ **Leverage**: 50:1 maximum (US legal limit)
⚠️ **Risk management**: Max 20% drawdown, position sizing rules
⚠️ **Cost model**: OANDA spreads (1.2-1.5 pips) + slippage
⚠️ **Data range**: 2020-2025 only
⚠️ **Platform compatibility**: Must work with OANDA API

### What to AVOID
❌ Don't overfit to specific events (e.g., COVID crash)
❌ Don't use more than 10-15 parameters (keep it simple)
❌ Don't create strategies that only work in one market condition
❌ Don't ignore transaction costs
❌ Don't optimize for backtests without walk-forward validation

---

## 📈 Expected Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Research & Exploration | 2-3 hours | Market analysis + 3-5 strategy concepts |
| Strategy Development | 4-6 hours | 5-10 backtested configurations |
| Optimization & Selection | 3-4 hours | Top 3 strategies with robustness tests |
| Documentation | 1-2 hours | Final strategy package |
| **Total** | **10-15 hours** | **Complete strategy ready for forward testing** |

---

## 🧪 Testing Requirements

### Minimum Tests Required

1. **Long-term backtest**: Full 2020-2025 period
2. **Walk-forward analysis**: 6 rolling windows minimum
3. **Out-of-sample test**: 2024-2025 data (after training on 2020-2023)
4. **Monte Carlo simulation**: 100 runs with win rate variation
5. **Drawdown stress test**: Reduce win rate by 10%, verify DD < 25%
6. **Multi-pair correlation**: Ensure pairs aren't 100% correlated
7. **Cost sensitivity**: Test with 2x and 3x costs

### Success Criteria

Your strategy must achieve:
- ✅ Positive returns in at least **4 out of 6 years** (2020-2025)
- ✅ Sharpe ratio > **1.5** over full period
- ✅ Max drawdown < **20%**
- ✅ Win rate > **55%**
- ✅ At least **50 trades per year** (not too sparse)
- ✅ Works on all 4 major pairs

---

## 📁 File Structure

Organize your work as follows:

```
/workspace/
├── historical_strategy_2020_2025/
│   ├── research/
│   │   ├── market_analysis_2020_2025.md
│   │   ├── indicator_correlations.csv
│   │   └── strategy_concepts.md
│   │
│   ├── development/
│   │   ├── backtest_results/
│   │   │   ├── config_1_results.csv
│   │   │   ├── config_2_results.csv
│   │   │   └── ...
│   │   ├── test_strategy_variants.py
│   │   └── optimize_parameters.py
│   │
│   ├── validation/
│   │   ├── walk_forward_results.csv
│   │   ├── monte_carlo_results.csv
│   │   ├── out_of_sample_results.csv
│   │   └── robustness_report.md
│   │
│   ├── final_strategy/
│   │   ├── STRATEGY_SPECIFICATION.md
│   │   ├── strategy_implementation.py
│   │   ├── backtest_full_period.py
│   │   ├── performance_charts.py
│   │   └── config.json
│   │
│   └── README.md (overview of entire process)
```

---

## 💡 Hints & Tips

### From Previous Agent's Experience

1. **Dual strategy works well**
   - Combining high R:R sniper with frequent background trades
   - Balances risk vs. opportunity
   
2. **ADX is a strong filter**
   - Helps avoid ranging markets
   - Improves win rate significantly
   
3. **Dynamic targets help**
   - Adjusting SL/TP based on volatility
   - Prevents getting stopped out in high volatility
   
4. **Position sizing matters**
   - Fixed % risk per trade works well
   - Capital allocation between strategies (60/40 split)
   
5. **Don't overtrade**
   - Quality > quantity
   - 2 trades per pair per month for high R:R setups is good

### What Might Work Even Better

1. **Time filters**
   - Trade only during high-liquidity sessions
   - Avoid rollover times
   
2. **Correlation filters**
   - Don't take correlated trades simultaneously
   - Reduce overall portfolio risk
   
3. **Machine learning enhancement**
   - Use ML to predict signal quality
   - Filter out low-probability setups
   
4. **Partial profit taking**
   - Exit 50% at 2:1, let rest run to 5:1
   - Improves win rate while maintaining R:R

---

## 🎯 Success Metrics for This Task

At the end, you should deliver:

1. ✅ **Strategy specification document** (detailed, reproducible)
2. ✅ **Backtest results** showing profitability over 2020-2025
3. ✅ **Python implementation** (clean, commented code)
4. ✅ **Performance analysis** (equity curves, drawdown charts, statistics)
5. ✅ **Robustness validation** (walk-forward, out-of-sample, Monte Carlo)
6. ✅ **Comparison vs. reference strategy** (how does it stack up?)
7. ✅ **Forward testing readiness** (ready to test on 2026 data)

---

## 🚀 Getting Started

### Step 1: Data Exploration
```python
# Load 2020-2025 data for all pairs
from core.data_handler import DataHandler
from datetime import datetime

handler = DataHandler()
start = datetime(2020, 1, 1)
end = datetime(2025, 12, 31)

pairs = ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'AUDUSD=X']

for pair in pairs:
    df = handler.fetch_data(pair, start.strftime('%Y-%m-%d'), 
                           end.strftime('%Y-%m-%d'), '4h')
    print(f"{pair}: {len(df)} candles from {df.index[0]} to {df.index[-1]}")
```

### Step 2: Indicator Testing
```python
from core.indicators import TechnicalIndicators

# Test various indicators
df['ema_3'] = TechnicalIndicators.ema(df, 3)
df['ema_9'] = TechnicalIndicators.ema(df, 9)
df['atr'] = TechnicalIndicators.atr(df)
adx, plus_di, minus_di = TechnicalIndicators.adx(df)
df['adx'] = adx

# Analyze correlations and patterns
```

### Step 3: Build First Strategy
```python
# Start with a simple EMA crossover
# Add ADX filter
# Implement position sizing
# Run backtest
# Iterate and improve
```

---

## 📞 Questions to Answer

As you develop, continuously ask yourself:

1. **Does this strategy make logical sense?**
   - Why would this edge exist in the market?
   - Is it based on sound principles or curve-fitting?

2. **Is it robust?**
   - Does it work in trending AND ranging markets?
   - Does it work across all pairs?
   - Does it work in different years?

3. **Can it be traded in real-time?**
   - Are signals clear and unambiguous?
   - Can it be automated?
   - Does it require constant monitoring?

4. **What are the risks?**
   - What could cause this strategy to fail?
   - How will it perform in extreme volatility?
   - What's the worst-case drawdown scenario?

5. **How does it compare to the reference strategy?**
   - Is it simpler or more complex?
   - Is it more or less profitable?
   - Is it more or less robust?

---

## 🏁 Final Deliverable

Create a final report with:

```markdown
# Forex Trading Strategy - 2020-2025 Backtest

## Executive Summary
[2-3 paragraphs summarizing the strategy and results]

## Strategy Specification
[Detailed entry/exit rules, position sizing, risk management]

## Performance Summary (2020-2025)
- Total return: X%
- Annualized return: Y%
- Sharpe ratio: Z
- Max drawdown: D%
- Win rate: W%
- Total trades: T

## Year-by-Year Breakdown
[Table showing performance each year]

## Robustness Validation
- Walk-forward results
- Out-of-sample results
- Monte Carlo results
- Stress test results

## Comparison vs Reference Strategy
[How does it compare to the 2023-2026 strategy?]

## Forward Testing Plan
[How should we test this on 2026 data?]

## Risk Disclosures
[Potential failure modes and limitations]

## Implementation Notes
[Any practical considerations for live trading]
```

---

## 🎓 Learning Objectives

By the end of this task, you should understand:

1. How to develop a trading strategy from scratch
2. How to avoid look-ahead bias and overfitting
3. How to validate strategy robustness
4. How to balance simplicity vs. sophistication
5. How to prepare a strategy for live trading

---

## ✅ Checklist Before Submission

- [ ] Used ONLY 2020-2025 data (no 2026 data)
- [ ] Tested on all 4 major pairs
- [ ] Included realistic costs (OANDA spreads)
- [ ] Max drawdown < 20% validated
- [ ] Walk-forward analysis completed
- [ ] Out-of-sample testing completed
- [ ] Monte Carlo simulation (100+ runs)
- [ ] Code is clean and documented
- [ ] Strategy specification is detailed and clear
- [ ] Ready for forward testing on 2026 data

---

## 🤝 Collaboration & Iteration

- Feel free to ask questions during development
- Share intermediate results for feedback
- Iterate based on backtest findings
- Don't be afraid to restart if a direction isn't working
- The goal is a **robust, tradeable strategy**, not perfect backtests

---

**Good luck! Your goal is to recreate the magic that worked on 2023-2026 data, but using only 2020-2025 data. Then we'll see if it truly has predictive power by forward-testing on 2026.** 🚀
