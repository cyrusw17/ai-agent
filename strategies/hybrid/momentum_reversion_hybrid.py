"""
Hybrid Momentum-Reversion Strategy

Combines trend-following (EMA/MACD) with mean-reversion (RSI/Bollinger Bands)
Based on research showing hybrid strategies outperform single-mode approaches

Strategy Logic:
- Trend Mode: EMA crossover + MACD confirmation
- Mean Reversion Mode: RSI extremes + Bollinger Band touches
- Volatility filter to select appropriate mode
- Regime detection for strategy switching
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple
import sys
sys.path.append('/workspace')
from utils.indicators import TechnicalIndicators, VolatilityMetrics


class HybridMomentumReversionStrategy:
    """
    Adaptive strategy that switches between momentum and mean reversion
    based on market regime
    """
    
    def __init__(self,
                 ema_fast: int = 20,
                 ema_slow: int = 50,
                 macd_fast: int = 12,
                 macd_slow: int = 26,
                 macd_signal: int = 9,
                 rsi_period: int = 14,
                 rsi_oversold: int = 30,
                 rsi_overbought: int = 70,
                 bb_period: int = 20,
                 bb_std: float = 2.0,
                 atr_period: int = 14,
                 atr_multiplier: float = 2.0,
                 vol_threshold: float = 1.5):
        """
        Initialize hybrid strategy
        
        Args:
            ema_fast: Fast EMA period
            ema_slow: Slow EMA period
            macd_fast: MACD fast period
            macd_slow: MACD slow period
            macd_signal: MACD signal period
            rsi_period: RSI period
            rsi_oversold: RSI oversold threshold
            rsi_overbought: RSI overbought threshold
            bb_period: Bollinger Bands period
            bb_std: Bollinger Bands standard deviation
            atr_period: ATR period
            atr_multiplier: ATR multiplier for stops
            vol_threshold: Volatility threshold for regime detection
        """
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.vol_threshold = vol_threshold
        
    def calculate_trend_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate trend-following signals (EMA + MACD)
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with trend signals
        """
        signals = df.copy()
        
        signals['ema_fast'] = TechnicalIndicators.ema(df['close'], self.ema_fast)
        signals['ema_slow'] = TechnicalIndicators.ema(df['close'], self.ema_slow)
        
        macd, macd_signal, macd_hist = TechnicalIndicators.macd(
            df['close'], 
            self.macd_fast, 
            self.macd_slow, 
            self.macd_signal
        )
        signals['macd'] = macd
        signals['macd_signal'] = macd_signal
        signals['macd_hist'] = macd_hist
        
        signals['trend_signal'] = 0
        
        long_condition = (
            (signals['ema_fast'] > signals['ema_slow']) &
            (signals['macd'] > signals['macd_signal']) &
            (signals['macd_hist'] > 0)
        )
        signals.loc[long_condition, 'trend_signal'] = 1
        
        short_condition = (
            (signals['ema_fast'] < signals['ema_slow']) &
            (signals['macd'] < signals['macd_signal']) &
            (signals['macd_hist'] < 0)
        )
        signals.loc[short_condition, 'trend_signal'] = -1
        
        return signals
    
    def calculate_mean_reversion_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate mean-reversion signals (RSI + Bollinger Bands)
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with mean reversion signals
        """
        signals = df.copy()
        
        signals['rsi'] = TechnicalIndicators.rsi(df['close'], self.rsi_period)
        
        bb_upper, bb_middle, bb_lower = TechnicalIndicators.bollinger_bands(
            df['close'],
            self.bb_period,
            self.bb_std
        )
        signals['bb_upper'] = bb_upper
        signals['bb_middle'] = bb_middle
        signals['bb_lower'] = bb_lower
        
        signals['mr_signal'] = 0
        
        long_condition = (
            (signals['rsi'] < self.rsi_oversold) &
            (signals['close'] <= signals['bb_lower'])
        )
        signals.loc[long_condition, 'mr_signal'] = 1
        
        short_condition = (
            (signals['rsi'] > self.rsi_overbought) &
            (signals['close'] >= signals['bb_upper'])
        )
        signals.loc[short_condition, 'mr_signal'] = -1
        
        return signals
    
    def detect_regime(self, df: pd.DataFrame) -> pd.Series:
        """
        Detect market regime (trending vs ranging)
        
        Returns 1 for trending, 0 for ranging
        
        Args:
            df: DataFrame with returns
            
        Returns:
            Regime series
        """
        regime = VolatilityMetrics.volatility_regime(
            df['returns'],
            threshold=self.vol_threshold
        )
        
        return regime
    
    def generate_signals(self, df: pd.DataFrame, regime_mode: str = 'adaptive') -> pd.DataFrame:
        """
        Generate combined signals based on regime
        
        Args:
            df: DataFrame with OHLCV data
            regime_mode: 'adaptive', 'trend', or 'mean_reversion'
            
        Returns:
            DataFrame with final signals
        """
        trend_signals = self.calculate_trend_signals(df)
        
        mr_signals = self.calculate_mean_reversion_signals(df)
        
        combined = trend_signals.copy()
        combined['mr_signal'] = mr_signals['mr_signal']
        combined['rsi'] = mr_signals['rsi']
        combined['bb_upper'] = mr_signals['bb_upper']
        combined['bb_middle'] = mr_signals['bb_middle']
        combined['bb_lower'] = mr_signals['bb_lower']
        
        if 'high' in df.columns and 'low' in df.columns:
            combined['atr'] = TechnicalIndicators.atr(
                df['high'],
                df['low'],
                df['close'],
                self.atr_period
            )
        
        if regime_mode == 'adaptive':
            regime = self.detect_regime(df)
            combined['regime'] = regime
            
            combined['signal'] = 0
            
            combined.loc[regime == 1, 'signal'] = combined.loc[regime == 1, 'trend_signal']
            
            combined.loc[regime == 0, 'signal'] = combined.loc[regime == 0, 'mr_signal']
            
        elif regime_mode == 'trend':
            combined['signal'] = combined['trend_signal']
            combined['regime'] = 1
            
        elif regime_mode == 'mean_reversion':
            combined['signal'] = combined['mr_signal']
            combined['regime'] = 0
            
        else:
            raise ValueError(f"Invalid regime_mode: {regime_mode}")
        
        return combined
    
    def calculate_stops(self, df: pd.DataFrame, position: int) -> Tuple[float, float]:
        """
        Calculate stop loss and take profit levels
        
        Args:
            df: DataFrame with signals and ATR
            position: Current position (1 = long, -1 = short)
            
        Returns:
            stop_loss, take_profit
        """
        if 'atr' not in df.columns:
            return None, None
        
        current_price = df['close'].iloc[-1]
        current_atr = df['atr'].iloc[-1]
        
        if position == 1:
            stop_loss = current_price - (current_atr * self.atr_multiplier)
            take_profit = current_price + (current_atr * self.atr_multiplier * 1.5)
        elif position == -1:
            stop_loss = current_price + (current_atr * self.atr_multiplier)
            take_profit = current_price - (current_atr * self.atr_multiplier * 1.5)
        else:
            stop_loss = None
            take_profit = None
        
        return stop_loss, take_profit
    
    def backtest(self, df: pd.DataFrame, initial_capital: float = 100000,
                position_size: float = 0.95, regime_mode: str = 'adaptive') -> pd.DataFrame:
        """
        Backtest the hybrid strategy
        
        Args:
            df: DataFrame with OHLCV data
            initial_capital: Starting capital
            position_size: Fraction of capital to use per trade
            regime_mode: Strategy mode
            
        Returns:
            Equity curve and trade log
        """
        signals = self.generate_signals(df, regime_mode)
        
        equity = initial_capital
        cash = initial_capital
        position = 0
        shares = 0
        entry_price = 0
        
        equity_curve = []
        
        for i in range(len(signals)):
            if i < max(self.ema_slow, self.bb_period):
                equity_curve.append({
                    'date': signals.index[i],
                    'equity': equity,
                    'position': position,
                    'signal': 0,
                    'regime': 0
                })
                continue
            
            current_signal = signals['signal'].iloc[i]
            current_price = signals['close'].iloc[i]
            current_regime = signals.get('regime', pd.Series([0]*len(signals))).iloc[i]
            
            if position == 0 and current_signal != 0:
                position = current_signal
                shares = (cash * position_size) / current_price
                entry_price = current_price
                cash = cash * (1 - position_size)
            
            elif position != 0 and current_signal == 0:
                pnl = shares * (current_price - entry_price) * position
                cash += shares * current_price
                position = 0
                shares = 0
                entry_price = 0
            
            elif position != 0 and current_signal == -position:
                pnl = shares * (current_price - entry_price) * position
                cash += shares * current_price
                
                position = current_signal
                shares = (cash * position_size) / current_price
                entry_price = current_price
                cash = cash * (1 - position_size)
            
            equity = cash + (shares * current_price if position != 0 else 0)
            
            equity_curve.append({
                'date': signals.index[i],
                'equity': equity,
                'position': position,
                'signal': current_signal,
                'regime': current_regime,
                'price': current_price
            })
        
        results = pd.DataFrame(equity_curve).set_index('date')
        results['returns'] = results['equity'].pct_change()
        
        return results
    
    def get_performance_stats(self, equity_curve: pd.DataFrame) -> Dict[str, float]:
        """Calculate performance statistics"""
        if equity_curve.empty:
            return {}
        
        returns = equity_curve['returns'].dropna()
        
        total_return = (equity_curve['equity'].iloc[-1] / equity_curve['equity'].iloc[0]) - 1
        annual_return = (1 + total_return) ** (252 / len(equity_curve)) - 1
        annual_vol = returns.std() * np.sqrt(252)
        sharpe = (annual_return - 0.02) / annual_vol if annual_vol > 0 else 0
        
        running_max = equity_curve['equity'].expanding().max()
        drawdown = (equity_curve['equity'] - running_max) / running_max
        max_dd = abs(drawdown.min())
        
        winning_trades = (returns > 0).sum()
        total_trades = len(returns[returns != 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        if 'regime' in equity_curve.columns:
            trend_pct = equity_curve['regime'].mean()
        else:
            trend_pct = 0
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'annual_volatility': annual_vol,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_dd,
            'win_rate': win_rate,
            'trend_regime_pct': trend_pct,
            'num_trades': total_trades
        }
