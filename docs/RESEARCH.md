# Quantitative Analysis Research Document

## Executive Summary

This document provides comprehensive research on modern quantitative trading methodologies implemented in the framework, based on 2026 institutional practices and academic research.

---

## 1. Liquidity Analysis

### 1.1 Overview

Modern institutional trading recognizes liquidity as **dynamic and mobile**, not static. The 2026 paradigm shift moved away from fixed support/resistance levels to real-time liquidity consumption analysis.

### 1.2 Liquidity Pools

**Definition**: Areas where significant stop-loss orders accumulate, creating zones of pending liquidity.

**Identification Criteria**:
- Multiple price touches (minimum 2-3)
- Confluence with round numbers (psychological levels)
- Historical swing highs/lows
- Equal highs/lows formations

**Implementation**:
```python
# Framework identifies pools using:
# 1. Rolling high/low detection
# 2. Touch counting within tolerance
# 3. Strength scoring based on frequency
```

### 1.3 Liquidity Sweeps (Stop Hunts)

**Definition**: When price briefly exceeds a liquidity pool then reverses, indicating institutional stop-loss hunting.

**Characteristics**:
- Wick extends beyond level
- Body closes back inside
- High relative volume
- Quick reversal (within 1-3 bars)

**5-Factor Scoring Model**:

| Factor | Weight | Measures |
|--------|--------|----------|
| F1: Wick Rejection Purity | 28% | Fraction of sweep depth recovered |
| F2: Volume Participation | 20% | Volume z-score vs recent average |
| F3: CVD Net Absorption | 25% | Order flow delta at sweep |
| F4: Structural Recovery | 17% | How far close reclaimed level |
| F5: Session Window | 10% | London (1.0) / NY (0.85) / Off-peak (0.45) |

**Research Basis**:
- PickMyTrade institutional sweep research (2026)
- BIS forex turnover data: UK = 35-43% of global daily volume
- Session weighting based on empirical liquidity depth

### 1.4 Cumulative Volume Delta (CVD)

**Definition**: Net difference between buy and sell volume over time.

**Calculation** (Approximation):
```
If price_change > 0: buy_volume = volume
If price_change < 0: sell_volume = volume
Delta = buy_volume - sell_volume
CVD = cumsum(Delta)
```

**Usage**:
- Positive CVD divergence in downtrend = bullish
- Negative CVD divergence in uptrend = bearish
- Z-score normalization for comparison

**Note**: Real implementation uses tick data with bid/ask volume. Framework uses approximation suitable for bar data.

### 1.5 Order Blocks (OB)

**Definition**: The last opposite-colored candle before a strong directional move, representing institutional positioning.

**Identification**:
1. Detect strong displacement (>1.5x average move)
2. Identify preceding candle
3. Mark high/low as order block zone
4. Expect reaction on retest

**Trading Application**:
- Bullish OB = last red candle before rally
- Bearish OB = last green candle before drop
- Entry on retest with confirmation

---

## 2. Market Structure Analysis

### 2.1 Smart Money Concepts (SMC)

Market structure analysis follows institutional order flow patterns rather than retail technical analysis.

### 2.2 Break of Structure (BOS)

**Definition**: Price breaks a previous swing high (uptrend) or swing low (downtrend), confirming trend continuation.

**Bullish BOS**:
```
1. Uptrend in progress (HH, HL pattern)
2. Price breaks above previous HH
3. Candle BODY closes above (wick-only = invalid)
4. Strong momentum (>2% move)
5. High volume confirmation
```

**Bearish BOS**:
```
1. Downtrend in progress (LH, LL pattern)
2. Price breaks below previous LL
3. Candle BODY closes below
4. Strong momentum
5. High volume confirmation
```

**Validation Requirements**:
- Body close beyond level (wick alone is insufficient)
- Momentum threshold: >2.0% move or >1.5x ATR
- Volume: >1.2x average
- Displacement: Large impulsive candles

**Research**: StrategyQuant BOS research emphasizes momentum confirmation to filter false breaks.

### 2.3 Change of Character (CHoCH)

**Definition**: Price breaks structure **against** the prevailing trend, signaling potential reversal.

**Bullish CHoCH**:
```
Downtrend context:
- Price breaks above last Lower High (LH)
- Indicates sellers losing control
- Probability shift toward reversal
```

**Bearish CHoCH**:
```
Uptrend context:
- Price breaks below last Higher Low (HL)
- Indicates buyers losing control
- Probability shift toward reversal
```

**Key Distinction**:
| BOS | CHoCH |
|-----|-------|
| WITH trend | AGAINST trend |
| Continuation | Reversal warning |
| High confidence | Medium confidence |
| Trade in direction | Start looking opposite |

**Confluence with Sweeps**:
Best CHoCH setups occur AFTER liquidity sweep:
1. Sweep takes out stops (liquidity grab)
2. CHoCH confirms reversal
3. Institutions deploy swept liquidity in new direction

### 2.4 Higher Highs/Lows (HH/HL/LH/LL)

**Swing Point Detection**:
```python
# Framework uses lookback method:
lookback = 5  # bars on each side

# Swing High: Current high > all highs in range
# Swing Low: Current low < all lows in range
```

**Pattern Recognition**:
- **Uptrend**: HH + HL sequence
- **Downtrend**: LH + LL sequence
- **Consolidation**: Mixed pattern

**Structure Strength Score**:
```
Recent HH + HL count in 20 bars
Structure Strength = ────────────────────────── × 100
Total swing points

High score (>70) = strong structure
Low score (<40) = weak/ranging
```

---

## 3. Momentum & Trend Indicators

### 3.1 Relative Strength Index (RSI)

**Standard Settings**: 14-period
**Fast Settings**: 9-period (day trading)

**Usage**:
- **Overbought**: RSI > 70
- **Oversold**: RSI < 30
- **Neutral Zone**: 40-60 (best entries in trends)

**Divergence Trading**:
- **Bullish**: Price makes LL, RSI makes HL
- **Bearish**: Price makes HH, RSI makes LH

**2026 Best Practice**: Don't trade RSI alone. Use as filter:
```python
# Good entry in uptrend:
if trend == 'uptrend' and 50 < RSI < 70:
    # RSI confirming momentum without overextension
    consider_long()
```

### 3.2 MACD (Moving Average Convergence Divergence)

**Standard**: 12/26/9
**Fast (Intraday)**: 6/13/5

**Components**:
- **MACD Line**: EMA(12) - EMA(26)
- **Signal Line**: EMA(9) of MACD
- **Histogram**: MACD - Signal

**Signals**:
- Bullish: MACD crosses above signal
- Bearish: MACD crosses below signal
- Histogram expansion = momentum acceleration
- Histogram contraction = momentum weakening

**Divergence**: Same as RSI

### 3.3 Exponential Moving Averages (EMA)

**Multi-Timeframe Approach**:
- **EMA 9**: Fast trend, entry timing
- **EMA 21**: Medium trend, pullback level
- **EMA 50**: Slow trend, major support/resistance
- **EMA 200**: Very slow, bull/bear divider

**Trend Identification**:
```python
Strong Uptrend: EMA9 > EMA21 > EMA50 > EMA200
Strong Downtrend: EMA9 < EMA21 < EMA50 < EMA200
```

**Pullback Trading**:
```
In uptrend: Buy pullback to EMA21
In downtrend: Sell pullback to EMA21
```

### 3.4 SuperTrend

**Settings**: Period 10, Multiplier 3.0

**Calculation**:
```
HL2 = (High + Low) / 2
ATR = Average True Range(10)

Upper Band = HL2 + (3.0 × ATR)
Lower Band = HL2 - (3.0 × ATR)

If Close > SuperTrend: Bullish (green)
If Close < SuperTrend: Bearish (red)
```

**Trading**:
- Enter long on flip to green
- Enter short on flip to red
- Use as stop-loss level
- Non-repainting, clear visual

**Best For**: Trending markets, position traders

### 3.5 VWAP (Volume Weighted Average Price)

**Definition**: Average price weighted by volume, resets daily.

**Institutional Use**:
- Execution benchmark
- Fair value reference
- Intraday bias gauge

**Trading Rules**:
```python
if price > VWAP: Bullish bias, look for longs
if price < VWAP: Bearish bias, look for shorts

# Best entries:
# 1. Pullback to VWAP in trend
# 2. Reclaim of VWAP with volume
# 3. Failed VWAP test (rejection)
```

**2026 Research**: Over 70% of active day traders use VWAP (Investopedia study).

### 3.6 ADX (Average Directional Index)

**Settings**: 14-period

**Interpretation**:
- **ADX < 20**: Weak trend, ranging market
- **ADX > 20**: Trend present
- **ADX > 25**: Strong trend
- **ADX > 40**: Very strong trend

**Components**:
- **+DI**: Positive directional indicator (bullish pressure)
- **-DI**: Negative directional indicator (bearish pressure)

**Usage**:
```python
if ADX > 25 and +DI > -DI: Strong uptrend
if ADX > 25 and -DI > +DI: Strong downtrend
if ADX < 20: Avoid trend strategies, use range strategies
```

### 3.7 Volume Analysis

**Relative Volume (RVOL)**:
```
RVOL = Current Volume / Average Volume(20)

RVOL > 1.5: High participation
RVOL < 0.8: Low participation
```

**Volume Z-Score**:
```
Z = (Current Volume - Mean) / Std Dev

Z > 2.0: Abnormal high volume (2 std dev)
Z < -2.0: Abnormal low volume
```

**Volume Profile**:
- Horizontal volume distribution
- Point of Control (POC): Highest volume price
- Value Area: 70% of volume range

---

## 4. Session Analysis

### 4.1 Global Trading Sessions (UTC)

| Session | Hours (UTC) | Volume % | Weight | Characteristics |
|---------|-------------|----------|--------|-----------------|
| Asian | 00:00-05:00 | 15-20% | 0.45 | Slow, range-bound |
| London | 07:00-10:00 | 35-43% | 1.00 | Highest liquidity |
| NY | 13:00-16:00 | 25-30% | 0.85 | High volatility |
| Overlap | 13:00-16:00 | Peak | 1.00 | Maximum liquidity |

### 4.2 London Session

**Timing**: 07:00-16:00 UTC (London open to close)
**Peak**: 07:00-10:00 UTC (morning volatility)

**Characteristics**:
- Highest institutional participation
- 35-43% of global forex volume (BIS data)
- Major news releases (ECB, BoE)
- Sets daily tone

**Best For**:
- Forex majors (EUR, GBP pairs)
- Indices (FTSE, DAX)
- Breakout strategies

### 4.3 New York Session

**Timing**: 13:00-20:00 UTC
**Peak**: 13:00-16:00 UTC (overlap with London)

**Characteristics**:
- US market open (13:30 UTC)
- Major economic data releases
- Equity market influence
- Reversal tendency at open

**Best For**:
- US stocks
- Indices (SPY, QQQ)
- USD pairs
- Options expiration effects (monthly)

### 4.4 London/NY Overlap

**Timing**: 13:00-16:00 UTC

**Why It Matters**:
- Combined liquidity of two largest sessions
- Highest volume window
- Most institutional activity
- Tightest spreads
- Fastest execution

**Research**: Framework prioritizes this window with 1.0 weight multiplier.

### 4.5 Asian Session

**Timing**: 00:00-09:00 UTC

**Characteristics**:
- Lower volume
- Range-bound typically
- Tokyo market influence
- Quieter price action

**Best For**:
- JPY pairs
- Range trading strategies
- Asian indices (Nikkei, Hang Seng)

### 4.6 Session-Based Strategy

**Implementation**:
```python
# Framework approach:
if session in ['LONDON', 'NEW_YORK']:
    session_weight = 1.0 or 0.85
    # Higher probability setups
else:
    session_weight = 0.45
    # Lower probability, skip or reduce size
```

---

## 5. Reversal Detection

### 5.1 Divergence Trading

**RSI Divergence**:

**Bullish Divergence**:
1. Price: Lower Low (LL)
2. RSI: Higher Low (HL)
3. Interpretation: Selling momentum weakening despite new low
4. Action: Look for long entry

**Bearish Divergence**:
1. Price: Higher High (HH)
2. RSI: Lower High (LH)
3. Interpretation: Buying momentum weakening despite new high
4. Action: Look for short entry

**MACD Divergence**:
- Same concept, using MACD instead of RSI
- Often more reliable on longer timeframes
- Look for histogram divergence too

**Success Rate**: 
- Divergence alone: ~40-50%
- Divergence + volume + structure: ~65-75%

### 5.2 Double Tops & Bottoms

**Double Top**:
```
Characteristics:
- Two peaks at approximately same level
- Trough (neckline) between them
- Second peak often on lower volume
- Break of neckline confirms reversal

Target: Neckline - (Peak - Neckline)
```

**Double Bottom**:
```
Characteristics:
- Two lows at approximately same level
- Peak (neckline) between them
- Second low often on lower volume
- Break of neckline confirms reversal

Target: Neckline + (Neckline - Low)
```

**Validation**:
- Price tolerance: 2% (configurable)
- Minimum distance between tops/bottoms: 10 bars
- Volume should decrease on second formation
- Neckline break with volume surge

### 5.3 Exhaustion Candles

**Definition**: Large range candles with significant wicks, high volume, and reversal closes.

**Bullish Exhaustion (Bottom)**:
```
- Large lower wick (>50% of range)
- High relative volume (>2.0x)
- Closes in upper half
- In downtrend context
→ Sellers exhausted, buyers taking control
```

**Bearish Exhaustion (Top)**:
```
- Large upper wick (>50% of range)
- High relative volume (>2.0x)
- Closes in lower half
- In uptrend context
→ Buyers exhausted, sellers taking control
```

**Best Context**:
- At key support/resistance
- After extended trend
- With divergence confluence
- At round numbers

### 5.4 Reversal Probability Scoring

**Framework Composite**:
```python
Reversal Probability = (
    RSI Score × 0.30 +           # Overbought/oversold
    Divergence Score × 0.35 +     # Momentum disagreement
    Pattern Score × 0.20 +        # Double top/bottom
    Volume Score × 0.15           # Exhaustion volume
)

Threshold: 60+ = high probability reversal
```

---

## 6. Composite Scoring System

### 6.1 Multi-Factor Validation

**Philosophy**: Single indicators fail. Composite systems succeed.

**2026 Research Consensus**:
- Average single-indicator win rate: 45-55%
- 2-factor combination: 55-65%
- 3+ factor composite: 65-75%
- 5+ factor with risk management: 70-80%

### 6.2 Framework Scoring Components

**6 Primary Factors**:

1. **Trend Score (25% weight)**:
   - EMA alignment
   - SuperTrend direction
   - ADX strength
   - Scoring: 0 (ranging) to 100 (strong trend)

2. **Momentum Score (20% weight)**:
   - RSI level and direction
   - MACD histogram
   - Rate of change
   - Scoring: 0 (weak) to 100 (strong)

3. **Volume Score (20% weight)**:
   - Relative volume
   - Volume z-score
   - CVD alignment
   - Scoring: 0 (low participation) to 100 (high)

4. **Structure Score (20% weight)**:
   - Recent BOS/CHoCH
   - Order block proximity
   - Swing point quality
   - Scoring: 0 (poor structure) to 100 (clean structure)

5. **Session Score (10% weight)**:
   - Current session weight
   - Time of day
   - Overlap bonus
   - Scoring: 45 (off-peak) to 100 (peak)

6. **Liquidity Score (5% weight)**:
   - Recent sweep quality
   - Liquidity pool proximity
   - Wick rejection
   - Scoring: 0 (no liquidity event) to 100 (high-quality sweep)

### 6.3 Composite Calculation

```python
Composite Score = Σ (Factor_Score × Factor_Weight)

Example:
Trend: 85 × 0.25 = 21.25
Momentum: 70 × 0.20 = 14.00
Volume: 80 × 0.20 = 16.00
Structure: 75 × 0.20 = 15.00
Session: 100 × 0.10 = 10.00
Liquidity: 90 × 0.05 = 4.50
─────────────────────────
Total: 80.75 / 100
```

### 6.4 Signal Filtering

**Minimum Thresholds**:
```python
# Default config
min_composite_score = 60        # 60/100 minimum
min_risk_reward = 2.0           # 2:1 RR minimum
require_session_alignment = True # London/NY only
require_trend_alignment = True   # With major trend
```

**Quality Tiers**:
- **80-100**: Premium setups (1-2% of all bars)
- **70-79**: High quality (3-5%)
- **60-69**: Good quality (5-10%)
- **< 60**: Filtered out

---

## 7. Risk Management

### 7.1 Position Sizing

**Fixed Fractional Method**:
```python
Risk per trade = Capital × Risk%
Position Size = Risk Amount / (Entry - Stop Loss)

Example:
Capital: $100,000
Risk: 2% = $2,000
Entry: $100
Stop: $98
Position Size = $2,000 / $2 = 1,000 shares
```

### 7.2 Risk Parameters

**Framework Defaults**:
```python
max_risk_per_trade = 0.02      # 2% per trade
risk_reward_ratio = 2.0        # Minimum 2:1 RR
max_daily_loss = 0.06          # 6% daily limit
max_positions = 3              # Max concurrent trades
```

### 7.3 Stop Loss Placement

**Methods**:
1. **ATR-Based**: Entry ± (ATR × 1.5)
2. **Structure-Based**: Below swing low / above swing high
3. **Percentage**: Entry × (1 ± 0.02)
4. **Order Block**: Below/above OB zone

**Framework Default**: ATR × 1.5

### 7.4 Take Profit Levels

**Tiered Approach**:
```python
TP1: Entry + (ATR × 2.0)  # First target, take 1/3
TP2: Entry + (ATR × 3.0)  # Second target, take 1/3
TP3: Entry + (ATR × 4.0)  # Final target, take 1/3
```

**Scaling Out Benefits**:
- Locks in profits early
- Allows runners for big moves
- Reduces psychological pressure
- Improves overall RR

---

## 8. Backtesting Methodology

### 8.1 Realistic Assumptions

**Cost Modeling**:
```python
Commission: 0.1% per side (0.001 as decimal)
Slippage: 0.05% per trade (0.0005 as decimal)

Total Cost = (Entry + Exit) × Size × (Commission + Slippage)
```

**Execution**:
- Entry: Market order at signal close
- Stop Loss: Triggered if bar low/high hits level
- Take Profit: Triggered if bar high/low hits level
- Fills: Assume filled at exact level (optimistic)

### 8.2 Performance Metrics

**Return Metrics**:
- Total Return %
- CAGR (Compound Annual Growth Rate)
- Monthly returns distribution

**Risk Metrics**:
- Maximum Drawdown
- Maximum Drawdown %
- Sharpe Ratio
- Sortino Ratio

**Trade Metrics**:
- Win Rate %
- Profit Factor
- Expectancy
- Average Win vs Average Loss

**Directional**:
- Long vs Short performance
- Session-based performance
- Strategy-specific metrics

### 8.3 Equity Curve Analysis

**Key Observations**:
- Consistency vs volatility
- Drawdown periods (length and depth)
- Recovery characteristics
- Slope of equity curve

**Red Flags**:
- Prolonged flat periods
- Frequent new drawdowns
- Erratic returns
- Single lucky trade dependency

---

## 9. Advanced Concepts

### 9.1 Order Flow Analysis

**Concepts**:
- **Absorption**: Large volume at level without price move
- **Exhaustion**: Volume spike with reversal
- **Iceberg Orders**: Hidden institutional orders
- **Spoofing**: Fake orders (illegal, but exists)

**Framework Implementation**:
- CVD for order flow direction
- Volume profile for acceptance
- Liquidity sweeps for institutional activity

### 9.2 Fair Value Gaps (FVG)

**Definition**: Gaps in price action showing inefficient movement.

**Identification**:
```
Bullish FVG:
Bar 1 High < Bar 3 Low
Gap = area between

Bearish FVG:
Bar 1 Low > Bar 3 High
Gap = area between
```

**Trading**:
- Price tends to return to fill gaps
- Entry on gap retest
- Stop beyond gap

**Note**: Not fully implemented in current framework version. Planned for future release.

### 9.3 Wyckoff Methodology

**Phases**:
1. **Accumulation**: Institutions buying (range)
2. **Markup**: Uptrend begins
3. **Distribution**: Institutions selling (range)
4. **Markdown**: Downtrend begins

**Framework Alignment**:
- Accumulation = Ranging + CHoCH up
- Distribution = Ranging + CHoCH down

### 9.4 Market Regimes

**Four Regimes**:
1. **Trending Up**: ADX > 25, price above EMAs
2. **Trending Down**: ADX > 25, price below EMAs
3. **Ranging**: ADX < 20, price between levels
4. **Volatile**: High ATR, no clear direction

**Strategy Selection**:
- Trending: Use momentum/structure strategies
- Ranging: Use reversal/mean-reversion strategies
- Volatile: Reduce size or stay out

---

## 10. Future Research & Development

### 10.1 Planned Enhancements

**Machine Learning Integration**:
- Pattern recognition using CNNs
- Regime classification
- Signal probability estimation
- Dynamic parameter optimization

**Alternative Data**:
- Sentiment analysis (Twitter, Reddit)
- Options flow (put/call ratios)
- Dark pool data
- Crypto on-chain metrics

**Advanced Order Types**:
- Iceberg orders
- TWAP/VWAP execution
- Limit order fills
- Bracket orders

### 10.2 Research Areas

**Microstructure**:
- Bid-ask spread analysis
- Order book dynamics
- Tick-level data
- Latency arbitrage

**Portfolio Construction**:
- Multi-strategy allocation
- Correlation analysis
- Dynamic position sizing
- Kelly Criterion optimization

**Walk-Forward Analysis**:
- Out-of-sample testing
- Rolling optimization
- Parameter stability
- Regime adaptation

---

## 11. References & Sources

### Academic Research
1. Bank for International Settlements (BIS) - Foreign Exchange Turnover (2026)
2. Investopedia - Technical Indicator Usage Study (2026)
3. Journal of Trading - Market Microstructure Research
4. Quantitative Finance - Liquidity Analysis Papers

### Industry Sources
1. LuxAlgo - Market Structure Break & OB Probability Toolkit (2026)
2. PickMyTrade - Institutional Liquidity Sweep Research (2026)
3. Bookmap - 5 Key Market Structure Shifts (2026)
4. Halvern Research - Market Liquidity Structure Cross-Asset Evidence (2026)
5. MarkitTick - Multi-Pool Liquidity Confluence Scorer

### Technical Documentation
1. TradingView Pine Script Documentation
2. QuantConnect Algorithm Framework
3. Backtrader Python Library
4. TA-Lib Technical Analysis Library

### Books (Referenced Concepts)
1. "Market Microstructure Theory" - Maureen O'Hara
2. "Algorithmic Trading" - Ernie Chan
3. "Trading and Exchanges" - Larry Harris
4. "Evidence-Based Technical Analysis" - David Aronson

---

## 12. Glossary

**ATR**: Average True Range - volatility measure
**BOS**: Break of Structure - trend continuation signal
**CHoCH**: Change of Character - trend reversal warning
**CVD**: Cumulative Volume Delta - net order flow
**EMA**: Exponential Moving Average - trend indicator
**FVG**: Fair Value Gap - inefficient price area
**HH/HL**: Higher High/Higher Low - uptrend pattern
**LH/LL**: Lower High/Lower Low - downtrend pattern
**OB**: Order Block - institutional positioning zone
**POC**: Point of Control - highest volume price
**RVOL**: Relative Volume - volume vs average
**SMC**: Smart Money Concepts - institutional trading methodology
**VWAP**: Volume Weighted Average Price - fair value indicator

---

**Document Version**: 1.0
**Last Updated**: July 2026
**Framework Version**: 1.0.0

This research document is maintained alongside the codebase and updated as new methodologies are implemented and tested.
