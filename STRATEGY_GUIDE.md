# Quantitative Trading Strategy Guide

## Table of Contents
1. [Strategy Overview](#strategy-overview)
2. [Liquidity-Adjusted Momentum](#liquidity-adjusted-momentum)
3. [Pairs Trading](#pairs-trading)
4. [Hybrid Momentum-Reversion](#hybrid-momentum-reversion)
5. [Machine Learning Strategies](#machine-learning-strategies)
6. [Risk Management](#risk-management)
7. [Strategy Selection Guide](#strategy-selection-guide)

---

## Strategy Overview

This framework implements four distinct quantitative trading approaches, each designed for different market conditions and trader objectives.

### Strategy Classification

| Strategy | Type | Time Horizon | Market Regime | Complexity |
|----------|------|--------------|---------------|------------|
| Liquidity-Adjusted Momentum | Trend Following | Swing (weeks) | Trending | Medium |
| Pairs Trading | Mean Reversion | Swing/Position | Any | High |
| Hybrid Momentum-Reversion | Adaptive | Day/Swing | Any | Medium |
| XGBoost ML | Predictive | Day/Swing | Any | High |

---

## Liquidity-Adjusted Momentum

### Theoretical Foundation

Based on **Fama-French momentum factor** with liquidity adjustments (Amihud 2002). Traditional momentum strategies suffer from:
- **Crash risk**: -52% maximum drawdown
- **Illiquidity premium**: Loading on small, illiquid stocks
- **Execution costs**: High slippage in illiquid names

### Key Innovation

**Liquidity filtering + position sizing** inversely proportional to Amihud illiquidity ratio reduces max drawdown from -52% to -29% while maintaining positive alpha.

### Implementation

```python
momentum = (price_t / price_t-252) - 1  # 12-month momentum
skip_period = 21 days  # Avoid 1-month reversal

# Amihud Illiquidity
ILLIQ = |daily_return| / dollar_volume

# Position weight
weight_i = 1 / (1 + ILLIQ_i)

# Volume confirmation
volume_ratio = current_volume / avg_volume_20d
signal = momentum > 0 AND volume_ratio > 1.5 AND liquid
```

### When to Use

✅ **Best For:**
- Strong trending markets
- Large-cap universe with liquidity data
- Swing trading horizon (weeks to months)
- Portfolio with 20+ positions

❌ **Avoid When:**
- Range-bound, choppy markets
- Small universe (<10 stocks)
- Need daily turnover
- High transaction costs

### Performance Expectations

- **Sharpe Ratio**: 0.7-0.9 (liquidity-adjusted)
- **Max Drawdown**: 25-30%
- **Win Rate**: 45-55%
- **Turnover**: 50-100% monthly

---

## Pairs Trading (Statistical Arbitrage)

### Theoretical Foundation

Based on **cointegration theory** (Engle-Granger 1987). Two assets are cointegrated if:

```
Y_t - β × X_t = ε_t  (where ε_t is stationary)
```

The spread mean-reverts, creating arbitrage opportunities.

### Key Components

1. **Cointegration Testing**
   - Engle-Granger two-step
   - Johansen trace test (optional)
   - ADF test on residuals (p < 0.05)

2. **Dynamic Hedge Ratio (Kalman Filter)**
   - Adapts to regime shifts
   - More robust than static OLS
   - State-space model:
     ```
     β_t = β_t-1 + ω_t
     Y_t = β_t × X_t + ε_t
     ```

3. **Signal Generation**
   ```python
   spread = Y - β × X
   z_score = (spread - mean) / std
   
   # Entry signals
   LONG spread if z < -2.0   # Short Y, Long X
   SHORT spread if z > +2.0  # Long Y, Short X
   
   # Exit signals
   EXIT if |z| < 0.5
   STOP if |z| > 3.5
   ```

4. **Half-Life Filtering**
   ```
   half_life = -ln(2) / ln(1 - θ)
   ```
   Keep pairs with 5 < half_life < 60 days

### When to Use

✅ **Best For:**
- Market-neutral strategies
- Low-volatility returns
- Sector pairs (e.g., XLE/XOP, KO/PEP)
- ETF arbitrage
- Risk-off environments

❌ **Avoid When:**
- Structural breaks (mergers, regulatory changes)
- High correlation without cointegration
- Extremely low liquidity
- Single-sided short restrictions

### Performance Expectations

- **Sharpe Ratio**: 1.0-1.5
- **Max Drawdown**: 10-20%
- **Win Rate**: 55-65%
- **Correlation to market**: ~0.2 (low)

---

## Hybrid Momentum-Reversion

### Theoretical Foundation

Markets alternate between **trending** and **mean-reverting** regimes. A hybrid strategy adapts based on volatility regime detection.

### Dual-Mode System

#### **Trend Mode** (High Volatility)
- EMA crossover (20/50)
- MACD confirmation (12/26/9)
- Rides strong directional moves
- ATR-based stops

```python
LONG if:
  EMA_20 > EMA_50
  AND MACD > MACD_signal
  AND volatility_regime == HIGH

SHORT if:
  EMA_20 < EMA_50
  AND MACD < MACD_signal
  AND volatility_regime == HIGH
```

#### **Mean Reversion Mode** (Low Volatility)
- RSI extremes (30/70)
- Bollinger Band touches (20-period, 2σ)
- Fades extremes
- Quick profit targets

```python
LONG if:
  RSI < 30
  AND close <= BB_lower
  AND volatility_regime == LOW

SHORT if:
  RSI > 70
  AND close >= BB_upper
  AND volatility_regime == LOW
```

### Regime Detection

```python
volatility_ratio = current_vol / median_vol_100d

regime = HIGH if volatility_ratio > 1.5
regime = LOW  if volatility_ratio <= 1.5
```

### When to Use

✅ **Best For:**
- Single-asset trading
- Adaptive to market conditions
- Day/swing hybrid approach
- Don't want to manually switch strategies

❌ **Avoid When:**
- Need pure directional exposure
- Transaction costs are prohibitive
- Regime switches too frequently

### Performance Expectations

- **Sharpe Ratio**: 0.8-1.2
- **Max Drawdown**: 15-25%
- **Win Rate**: 50-60%
- **Regime switching**: ~50/50 time in each mode

---

## Machine Learning Strategies

### XGBoost Implementation

### Feature Engineering

**Technical Indicators:**
- RSI (14-period)
- MACD + Signal + Histogram
- Bollinger Band position & width
- ATR / ATR%

**Momentum Features:**
- Multi-period returns (5d, 10d, 20d)
- Price to MA ratios
- Momentum crossovers

**Volume Features:**
- Volume ratios (vs MA)
- Volume trend
- Dollar volume changes

**Volatility Features:**
- Rolling volatility (multiple windows)
- Volatility regime indicator
- Parkinson volatility

### Training Strategy

**Walk-Forward Optimization:**
```
Train Window: 252 days (1 year)
Test Window: 21 days (1 month)
Retrain Frequency: 21 days
```

This prevents look-ahead bias and mimics real deployment.

### Signal Generation

```python
probability = model.predict_proba(features)

LONG if prob > 0.55 (55% confidence bullish)
SHORT if prob < 0.45 (55% confidence bearish)
NEUTRAL otherwise

position_size = base_size × (|prob - 0.5| × 2)  # Scale by confidence
```

### Model Configuration

```python
xgb_params = {
    'objective': 'binary:logistic',
    'max_depth': 5,              # Prevent overfitting
    'learning_rate': 0.1,
    'n_estimators': 100,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'random_state': 42
}
```

### When to Use

✅ **Best For:**
- Feature-rich environments
- Non-linear relationships
- Sufficient data (2+ years)
- Computational resources available

❌ **Avoid When:**
- Limited data (<500 observations)
- High-frequency trading (latency)
- Market regime shifts frequently
- Lack of domain knowledge for features

### Performance Expectations

- **Sharpe Ratio**: 0.6-1.0 (highly dependent on features)
- **Max Drawdown**: 20-30%
- **Win Rate**: 52-58%
- **Data requirements**: Minimum 2 years

---

## Risk Management

### Position Sizing Methods

#### 1. **Kelly Criterion**

```python
f* = (p × b - q) / b

where:
  p = win rate
  q = 1 - p
  b = avg_win / avg_loss
```

**Best Practice:** Use fractional Kelly (0.25x - 0.5x)

**Risk-Constrained Kelly:**
```python
# Busseti-Ryu-Boyd (2016)
kelly_constrained = kelly_full × (-log(P_dd) / max_dd_level)

# Example: Max 10% probability of 30% drawdown
kelly_constrained = kelly_full × (-log(0.10) / 0.30)
```

#### 2. **ATR-Based Sizing**

```python
stop_distance = ATR × multiplier  # e.g., 2.0 × ATR
position_size = (account × risk%) / stop_distance
```

#### 3. **Volatility-Adjusted**

```python
target_vol = 0.15  # 15% annual vol target
asset_vol = realized_volatility(asset)

position_scalar = target_vol / asset_vol
position_size = base_size × position_scalar
```

### Drawdown Control

#### Kill Switches

```python
if current_drawdown > MAX_DD_THRESHOLD (e.g., 20%):
    HALT_TRADING()
    REDUCE_POSITIONS_TO_ZERO()
    NOTIFY_MANAGER()
```

#### Position Heat

```python
portfolio_heat = sum(|position_i × risk_i|)

if portfolio_heat > MAX_PORTFOLIO_RISK (e.g., 10%):
    REJECT_NEW_TRADES()
```

### Risk Metrics

#### Value at Risk (VaR)

```python
VaR_95 = percentile(returns, 5)
# "95% of days, we won't lose more than VaR_95"
```

#### Conditional VaR (CVaR / Expected Shortfall)

```python
CVaR_95 = mean(returns[returns <= VaR_95])
# "When we breach VaR, average loss is CVaR"
```

---

## Strategy Selection Guide

### By Market Condition

| Market Condition | Primary Strategy | Secondary Strategy |
|-----------------|------------------|-------------------|
| Strong Uptrend | Liquidity Momentum | Hybrid (Trend Mode) |
| Strong Downtrend | Hybrid (Trend Mode) | Short Momentum |
| Range-Bound | Pairs Trading | Hybrid (MR Mode) |
| High Volatility | Pairs Trading | Risk-Off |
| Low Volatility | Momentum | Hybrid |
| Uncertain | Pairs Trading | ML (Adaptive) |

### By Trading Style

| Style | Best Strategy | Time Commitment |
|-------|---------------|-----------------|
| Day Trader | Hybrid (adaptive) | High - Active monitoring |
| Swing Trader | Liquidity Momentum | Medium - Weekly rebalance |
| Position Trader | Pairs Trading | Low - Monthly review |
| Quant/Algo | ML (XGBoost) | Medium - Model maintenance |

### By Capital Size

| Capital | Strategy | Reason |
|---------|----------|--------|
| $10k - $50k | Single-asset Hybrid | Lower diversification needs |
| $50k - $250k | ML or Momentum (10-20 stocks) | Sufficient for portfolio |
| $250k - $1M | Momentum Portfolio (20-50 stocks) | Scaling capacity |
| $1M+ | Pairs Portfolio + Momentum | Liquidity, diversification |

### Risk/Return Profiles

```
High Return, High Risk:
  → Momentum (concentrated, 20 stocks)
  
Medium Return, Medium Risk:
  → Hybrid (adaptive)
  → ML (data-driven)
  
Lower Return, Lower Risk:
  → Pairs Trading (market-neutral)
  → Multiple strategies (diversified)
```

### Implementation Checklist

#### Before Going Live:

- [ ] Backtest on out-of-sample data (minimum 2 years)
- [ ] Walk-forward validation (no look-ahead bias)
- [ ] Account for realistic transaction costs
- [ ] Test across multiple market regimes
- [ ] Implement kill switches
- [ ] Define maximum drawdown tolerance
- [ ] Paper trade for 1-3 months
- [ ] Start with 10-25% of target capital
- [ ] Monitor daily for first month
- [ ] Document all trades and decisions

---

## Additional Resources

### Academic Papers

1. **Momentum:**
   - Jegadeesh & Titman (1993) - "Returns to Buying Winners and Selling Losers"
   - Amihud (2002) - "Illiquidity and Stock Returns"

2. **Pairs Trading:**
   - Engle & Granger (1987) - "Co-integration and Error Correction"
   - Gatev, Goetzmann & Rouwenhorst (2006) - "Pairs Trading: Performance of a Relative-Value Arbitrage Rule"

3. **Risk Management:**
   - Kelly (1956) - "A New Interpretation of Information Rate"
   - Busseti, Ryu & Boyd (2016) - "Risk-Constrained Kelly Gambling"

### Recommended Books

- "Quantitative Trading" by Ernest Chan
- "Algorithmic Trading" by Ernie Chan
- "Evidence-Based Technical Analysis" by David Aronson
- "Machine Learning for Asset Managers" by Marcos López de Prado

### Online Resources

- QuantConnect: Algorithmic trading platform
- Quantopian (archived): Educational resources
- QuantStart: Systematic trading tutorials
- Papers on SSRN and arXiv (quant-finance)

---

## Disclaimer

**This framework is for educational and research purposes only.**

- Past performance does not guarantee future results
- All strategies carry risk of loss
- Backtest results are hypothetical
- Real trading involves slippage, commissions, and market impact
- Strategies may stop working as markets evolve
- Always test thoroughly before deploying real capital
- Consider consulting a financial advisor
- Risk management is crucial - never risk more than you can afford to lose

**THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND**
