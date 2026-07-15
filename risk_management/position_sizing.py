"""
Position Sizing and Risk Management
Implements Kelly Criterion, fixed-fraction, and risk-constrained sizing
"""

import numpy as np
import pandas as pd
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class PositionSizeResult:
    """Result of position sizing calculation"""
    position_size: float
    risk_amount: float
    kelly_fraction: float
    method: str
    warnings: list


class PositionSizer:
    """Position sizing calculator"""
    
    def __init__(self, account_size: float, max_risk_per_trade: float = 0.02, max_portfolio_risk: float = 0.10):
        """
        Initialize position sizer
        
        Args:
            account_size: Total account size
            max_risk_per_trade: Maximum risk per trade (default 2%)
            max_portfolio_risk: Maximum portfolio risk (default 10%)
        """
        self.account_size = account_size
        self.max_risk_per_trade = max_risk_per_trade
        self.max_portfolio_risk = max_portfolio_risk
        
    def fixed_fraction(self, risk_per_trade: Optional[float] = None) -> PositionSizeResult:
        """
        Fixed fraction position sizing
        
        Args:
            risk_per_trade: Risk per trade (uses max_risk_per_trade if None)
            
        Returns:
            PositionSizeResult
        """
        risk_pct = risk_per_trade or self.max_risk_per_trade
        risk_amount = self.account_size * risk_pct
        
        return PositionSizeResult(
            position_size=risk_pct,
            risk_amount=risk_amount,
            kelly_fraction=0.0,
            method='fixed_fraction',
            warnings=[]
        )
    
    def kelly_criterion(self, win_rate: float, win_loss_ratio: float, 
                       fraction: float = 0.25, max_kelly: float = 0.25) -> PositionSizeResult:
        """
        Kelly Criterion position sizing
        
        Formula: f* = (p * b - q) / b
        where p = win rate, q = 1 - p, b = win/loss ratio
        
        Args:
            win_rate: Historical win rate (0-1)
            win_loss_ratio: Average win / average loss
            fraction: Fractional Kelly (0.25 = quarter Kelly, 0.5 = half Kelly)
            max_kelly: Maximum Kelly fraction (hard cap)
            
        Returns:
            PositionSizeResult
        """
        warnings = []
        
        if win_rate <= 0 or win_rate >= 1:
            warnings.append(f"Invalid win rate: {win_rate}")
            win_rate = np.clip(win_rate, 0.01, 0.99)
        
        if win_loss_ratio <= 0:
            warnings.append(f"Invalid win/loss ratio: {win_loss_ratio}")
            return self.fixed_fraction()
        
        p = win_rate
        q = 1 - p
        b = win_loss_ratio
        
        kelly_full = (p * b - q) / b
        
        if kelly_full <= 0:
            warnings.append("Negative Kelly suggests no edge")
            return PositionSizeResult(
                position_size=0.0,
                risk_amount=0.0,
                kelly_fraction=kelly_full,
                method='kelly_negative',
                warnings=warnings
            )
        
        kelly_fraction = kelly_full * fraction
        kelly_fraction = min(kelly_fraction, max_kelly)
        
        if kelly_fraction > self.max_risk_per_trade:
            warnings.append(f"Kelly ({kelly_fraction:.2%}) exceeds max risk, capping at {self.max_risk_per_trade:.2%}")
            kelly_fraction = self.max_risk_per_trade
        
        risk_amount = self.account_size * kelly_fraction
        
        return PositionSizeResult(
            position_size=kelly_fraction,
            risk_amount=risk_amount,
            kelly_fraction=kelly_full,
            method=f'kelly_{fraction}x',
            warnings=warnings
        )
    
    def volatility_adjusted(self, volatility: float, target_volatility: float = 0.15) -> PositionSizeResult:
        """
        Volatility-adjusted position sizing
        
        Scales position size inversely to volatility
        
        Args:
            volatility: Asset's annualized volatility
            target_volatility: Target portfolio volatility
            
        Returns:
            PositionSizeResult
        """
        if volatility <= 0:
            return self.fixed_fraction()
        
        vol_scalar = target_volatility / volatility
        position_size = self.max_risk_per_trade * vol_scalar
        position_size = np.clip(position_size, 0, self.max_risk_per_trade * 2)
        
        risk_amount = self.account_size * position_size
        
        return PositionSizeResult(
            position_size=position_size,
            risk_amount=risk_amount,
            kelly_fraction=0.0,
            method='volatility_adjusted',
            warnings=[]
        )
    
    def atr_based(self, entry_price: float, atr: float, atr_multiplier: float = 2.0) -> Tuple[float, float]:
        """
        ATR-based position sizing
        
        Args:
            entry_price: Entry price
            atr: Average True Range
            atr_multiplier: Stop loss multiplier (2.0 = 2x ATR stop)
            
        Returns:
            position_size (shares), stop_loss_price
        """
        stop_distance = atr * atr_multiplier
        stop_loss = entry_price - stop_distance
        
        risk_amount = self.account_size * self.max_risk_per_trade
        
        position_size_shares = risk_amount / stop_distance
        
        return position_size_shares, stop_loss
    
    def optimal_f(self, returns: pd.Series, f_values: np.ndarray = None) -> PositionSizeResult:
        """
        Optimal F (Ralph Vince method)
        
        Finds fraction that maximizes geometric growth
        
        Args:
            returns: Series of trade returns
            f_values: Array of f values to test (default: 0 to 1 in 0.01 steps)
            
        Returns:
            PositionSizeResult
        """
        if f_values is None:
            f_values = np.arange(0.01, 1.0, 0.01)
        
        returns_array = returns.values
        max_loss = abs(returns_array.min())
        
        if max_loss == 0:
            return self.fixed_fraction()
        
        terminal_wealth = []
        
        for f in f_values:
            wealth = 1.0
            for ret in returns_array:
                wealth *= (1 + f * ret / max_loss)
                if wealth <= 0:
                    break
            terminal_wealth.append(wealth)
        
        optimal_idx = np.argmax(terminal_wealth)
        optimal_f = f_values[optimal_idx]
        
        optimal_f = min(optimal_f, self.max_risk_per_trade)
        
        risk_amount = self.account_size * optimal_f
        
        return PositionSizeResult(
            position_size=optimal_f,
            risk_amount=risk_amount,
            kelly_fraction=0.0,
            method='optimal_f',
            warnings=[]
        )


class RiskConstraints:
    """Risk constraint enforcement"""
    
    def __init__(self, max_drawdown: float = 0.20, max_var_95: float = 0.05):
        """
        Initialize risk constraints
        
        Args:
            max_drawdown: Maximum allowed drawdown (20%)
            max_var_95: Maximum 95% VaR
        """
        self.max_drawdown = max_drawdown
        self.max_var_95 = max_var_95
        
    def check_drawdown_constraint(self, equity_curve: pd.Series) -> Tuple[bool, float]:
        """
        Check if current drawdown violates constraint
        
        Args:
            equity_curve: Equity curve series
            
        Returns:
            constraint_violated, current_drawdown
        """
        running_max = equity_curve.expanding().max()
        drawdown = (equity_curve - running_max) / running_max
        current_dd = abs(drawdown.iloc[-1])
        
        violated = current_dd > self.max_drawdown
        
        return violated, current_dd
    
    def calculate_var(self, returns: pd.Series, confidence: float = 0.95) -> float:
        """
        Calculate Value at Risk
        
        Args:
            returns: Return series
            confidence: Confidence level (0.95 = 95%)
            
        Returns:
            VaR value
        """
        var = np.percentile(returns.dropna(), (1 - confidence) * 100)
        return abs(var)
    
    def calculate_cvar(self, returns: pd.Series, confidence: float = 0.95) -> float:
        """
        Calculate Conditional Value at Risk (Expected Shortfall)
        
        Args:
            returns: Return series
            confidence: Confidence level
            
        Returns:
            CVaR value
        """
        var = self.calculate_var(returns, confidence)
        cvar = abs(returns[returns <= -var].mean())
        return cvar
    
    def position_heat(self, positions: dict) -> float:
        """
        Calculate current portfolio heat (total risk)
        
        Args:
            positions: Dictionary of position sizes
            
        Returns:
            Total portfolio risk as fraction
        """
        total_heat = sum(abs(pos) for pos in positions.values())
        return total_heat
    
    def risk_constrained_kelly(self, win_rate: float, win_loss_ratio: float, 
                              max_dd_prob: float = 0.10, max_dd_level: float = 0.30) -> float:
        """
        Risk-constrained Kelly (Busseti-Ryu-Boyd 2016)
        
        Computes Kelly fraction with explicit drawdown probability constraint
        
        Args:
            win_rate: Historical win rate
            win_loss_ratio: Win/loss ratio
            max_dd_prob: Maximum probability of drawdown (10%)
            max_dd_level: Maximum drawdown level (30%)
            
        Returns:
            Constrained Kelly fraction
        """
        p = win_rate
        b = win_loss_ratio
        
        kelly_full = (p * b - (1-p)) / b
        
        if kelly_full <= 0:
            return 0.0
        
        dd_scalar = -np.log(max_dd_prob) / max_dd_level
        constrained_kelly = kelly_full * dd_scalar
        
        return min(constrained_kelly, kelly_full * 0.5)
