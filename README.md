# Quantitative Trading Strategy Framework

A comprehensive multi-strategy quantitative trading framework implementing advanced algorithmic trading strategies for both day trading and swing trading.

## 🎯 Overview

This framework implements multiple quantitative trading strategies based on cutting-edge research in market microstructure, momentum, mean reversion, machine learning, and risk management.

## 📊 Implemented Strategies

### 1. **Liquidity-Adjusted Momentum**
- Filters positions by Amihud illiquidity ratio
- Volume confirmation with ratio-based signals
- Reduces drawdowns from -52% to -29% (research-backed)
- Implements position sizing inversely proportional to illiquidity

### 2. **Hybrid Momentum-Reversion Strategy**
- Combines EMA/MACD for trend following
- RSI/Bollinger Bands for mean reversion
- XGBoost ML layer for signal confirmation
- Volatility filters and regime detection

### 3. **Market Microstructure (Order Flow)**
- Order Flow Imbalance (OFI) analysis
- Kyle's Lambda estimation for price impact
- Cumulative Volume Delta (CVD) tracking
- Depth-weighted book pressure signals

### 4. **Statistical Arbitrage (Pairs Trading)**
- Cointegration testing (Engle-Granger & Johansen)
- Kalman filter for dynamic hedge ratios
- Z-score based entry/exit signals
- Half-life mean reversion estimation

### 5. **Volume Profile Strategies**
- VWAP deviation trading
- Volume profile support/resistance
- POV (Percentage of Volume) execution
- Time-weighted vs volume-weighted optimization

### 6. **Machine Learning Ensemble**
- LSTM for temporal pattern recognition
- XGBoost for feature-based predictions
- Random Forest for robust classification
- Hybrid ensemble weighting system

## 🛡️ Risk Management

- **Kelly Criterion**: Fractional Kelly (0.25x-0.5x) for position sizing
- **Drawdown Control**: Maximum drawdown limits with kill switches
- **ATR-Based Stops**: Volatility-adjusted stop losses
- **Portfolio Diversification**: Strategy and asset correlation management
- **VAR/CVaR**: Risk metrics for tail risk management

## 📁 Project Structure

```
quant-trading-framework/
├── strategies/
│   ├── momentum/
│   │   ├── liquidity_adjusted_momentum.py
│   │   └── momentum_volume.py
│   ├── mean_reversion/
│   │   ├── pairs_trading.py
│   │   └── rsi_bollinger.py
│   ├── hybrid/
│   │   ├── momentum_reversion_hybrid.py
│   │   └── ml_hybrid.py
│   ├── microstructure/
│   │   ├── order_flow_imbalance.py
│   │   └── vwap_strategies.py
│   └── ml/
│       ├── lstm_predictor.py
│       ├── xgboost_strategy.py
│       └── ensemble.py
├── risk_management/
│   ├── position_sizing.py
│   ├── kelly_criterion.py
│   └── drawdown_control.py
├── backtesting/
│   ├── backtest_engine.py
│   └── performance_metrics.py
├── utils/
│   ├── data_loader.py
│   ├── indicators.py
│   └── visualization.py
├── config/
│   └── strategy_config.yaml
└── main.py
```

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run backtests for all strategies
python main.py --mode backtest --strategies all

# Run specific strategy
python main.py --mode backtest --strategies liquidity_momentum

# Live trading simulation
python main.py --mode live --strategies hybrid_ml
```

## 📈 Strategy Selection Criteria

| Market Condition | Recommended Strategy |
|-----------------|---------------------|
| High Volatility Trending | Liquidity-Adjusted Momentum |
| Range-bound | Mean Reversion (RSI/Bollinger) |
| Mixed/Uncertain | Hybrid Momentum-Reversion |
| High Liquidity Assets | Order Flow Imbalance |
| Correlated Pairs | Statistical Arbitrage |

## 🔬 Research References

All strategies are based on peer-reviewed research and industry best practices from 2024-2026:
- Liquidity-adjusted momentum (Amihud 2002, Quant Decoded 2026)
- Market microstructure (Cont-Kukanov-Stoikov 2014, Kyle 1985)
- Hybrid ML systems (LSTM-XGBoost frameworks 2026)
- Kelly Criterion optimization (Busseti-Ryu-Boyd risk-constrained Kelly)

## ⚠️ Disclaimer

This framework is for educational and research purposes. Always test thoroughly before deploying with real capital. Past performance does not guarantee future results.

## 📝 License

MIT License - See LICENSE file for details
