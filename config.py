"""
Configuration file for the Quantitative Trading Framework
"""

# Trading Sessions (UTC timezone)
SESSIONS = {
    'LONDON': {
        'start_hour': 7,
        'end_hour': 10,
        'weight': 1.0,
        'name': 'London Session'
    },
    'NEW_YORK': {
        'start_hour': 13,
        'end_hour': 16,
        'weight': 0.85,
        'name': 'New York Session'
    },
    'ASIAN': {
        'start_hour': 0,
        'end_hour': 5,
        'weight': 0.45,
        'name': 'Asian Session'
    }
}

# Indicator Settings
INDICATORS = {
    'RSI': {
        'period': 14,
        'overbought': 70,
        'oversold': 30,
        'fast_period': 9
    },
    'MACD': {
        'fast': 12,
        'slow': 26,
        'signal': 9,
        'fast_intraday': 6,
        'slow_intraday': 13,
        'signal_intraday': 5
    },
    'EMA': {
        'fast': 9,
        'medium': 21,
        'slow': 50,
        'very_slow': 200
    },
    'SUPERTREND': {
        'period': 10,
        'multiplier': 3.0
    },
    'BOLLINGER': {
        'period': 20,
        'std_dev': 2.0
    },
    'ADX': {
        'period': 14,
        'threshold': 20
    },
    'ATR': {
        'period': 14
    },
    'VOLUME': {
        'lookback': 20,
        'threshold': 1.5
    }
}

# Market Structure Settings
STRUCTURE = {
    'swing_lookback': 5,
    'min_momentum': 2.0,
    'displacement_threshold': 1.5,
    'wick_rejection_threshold': 0.7
}

# Liquidity Analysis Settings
LIQUIDITY = {
    'sweep_threshold': 0.001,
    'pool_lookback': 50,
    'min_touches': 2,
    'rvol_threshold': 1.5,
    'cvd_window': 20
}

# Scoring Weights for Composite Signal
SCORING_WEIGHTS = {
    'wick_rejection': 0.28,
    'volume_participation': 0.20,
    'cvd_absorption': 0.25,
    'structural_recovery': 0.17,
    'session_timing': 0.10
}

# Risk Management
RISK = {
    'max_risk_per_trade': 0.02,
    'risk_reward_ratio': 2.0,
    'max_daily_loss': 0.06,
    'max_positions': 3
}

# Backtesting Settings
BACKTEST = {
    'initial_capital': 100000,
    'commission': 0.001,
    'slippage': 0.0005
}

# Strategy Filters
FILTERS = {
    'min_composite_score': 60,
    'min_volume_score': 50,
    'require_session_alignment': True,
    'require_trend_alignment': True
}
