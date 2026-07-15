"""
Liquidity-Adjusted Momentum Strategy

Based on research by Quant Decoded (2026) showing that adjusting momentum
positions by liquidity improves Sharpe from 0.55 to 0.82 and reduces max
drawdown from -52% to -29%.

Key Features:
- 12-1 month momentum signal
- Amihud illiquidity ratio filtering
- Volume confirmation
- Position sizing inversely proportional to illiquidity
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple
import sys
sys.path.append('/workspace')
from utils.indicators import TechnicalIndicators, MarketMicrostructure


class LiquidityAdjustedMomentum:
    """
    Liquidity-Adjusted Momentum Strategy
    
    Filters momentum stocks by liquidity to reduce crash risk
    """
    
    def __init__(self, 
                 momentum_lookback: int = 252,
                 momentum_skip: int = 21,
                 volume_lookback: int = 20,
                 volume_ratio_threshold: float = 1.5,
                 illiquidity_percentile: int = 80,
                 rebalance_frequency: int = 21):
        """
        Initialize strategy
        
        Args:
            momentum_lookback: Momentum formation period (252 days = 12 months)
            momentum_skip: Skip period to avoid reversal (21 days = 1 month)
            volume_lookback: Volume ratio calculation period
            volume_ratio_threshold: Minimum volume ratio for entry
            illiquidity_percentile: Filter out stocks above this percentile
            rebalance_frequency: Days between rebalancing
        """
        self.momentum_lookback = momentum_lookback
        self.momentum_skip = momentum_skip
        self.volume_lookback = volume_lookback
        self.volume_ratio_threshold = volume_ratio_threshold
        self.illiquidity_percentile = illiquidity_percentile
        self.rebalance_frequency = rebalance_frequency
        
        self.signals = None
        self.positions = {}
        
    def calculate_momentum_signal(self, prices: pd.Series) -> pd.Series:
        """
        Calculate 12-1 month momentum
        
        12-month total return excluding most recent month
        
        Args:
            prices: Price series
            
        Returns:
            Momentum signal
        """
        momentum = (prices / prices.shift(self.momentum_lookback + self.momentum_skip)) - 1
        return momentum
    
    def calculate_liquidity_filter(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate liquidity filter based on Amihud ratio
        
        Args:
            df: DataFrame with returns, volume, dollar_volume
            
        Returns:
            Boolean series (True = liquid enough to trade)
        """
        illiquidity = MarketMicrostructure.amihud_illiquidity(
            df['returns'],
            df['volume'],
            df.get('dollar_volume', df['volume'])
        )
        
        illiquidity_threshold = illiquidity.quantile(self.illiquidity_percentile / 100)
        
        liquid_filter = illiquidity <= illiquidity_threshold
        
        return liquid_filter
    
    def calculate_volume_confirmation(self, volume: pd.Series) -> pd.Series:
        """
        Volume confirmation signal
        
        Args:
            volume: Volume series
            
        Returns:
            Boolean series (True = volume confirms signal)
        """
        volume_ratio = MarketMicrostructure.volume_ratio(volume, self.volume_lookback)
        
        volume_confirmed = volume_ratio >= self.volume_ratio_threshold
        
        return volume_confirmed
    
    def generate_signals(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Generate trading signals for multiple stocks
        
        Args:
            data: Dictionary of DataFrames (symbol -> data)
            
        Returns:
            DataFrame with signals for all stocks
        """
        signals_list = []
        
        for symbol, df in data.items():
            if len(df) < self.momentum_lookback + self.momentum_skip:
                continue
            
            df = df.copy()
            
            momentum = self.calculate_momentum_signal(df['close'])
            
            liquid_filter = self.calculate_liquidity_filter(df)
            
            volume_confirmed = self.calculate_volume_confirmation(df['volume'])
            
            illiquidity = MarketMicrostructure.amihud_illiquidity(
                df['returns'],
                df['volume'],
                df.get('dollar_volume', df['volume'])
            )
            
            position_weight = 1 / (1 + illiquidity)
            position_weight = position_weight / position_weight.sum()
            
            signal_df = pd.DataFrame({
                'symbol': symbol,
                'date': df.index,
                'momentum': momentum,
                'liquid': liquid_filter,
                'volume_confirmed': volume_confirmed,
                'illiquidity': illiquidity,
                'position_weight': position_weight
            })
            
            signal_df['signal'] = 0
            signal_df.loc[
                (signal_df['momentum'] > 0) & 
                signal_df['liquid'] & 
                signal_df['volume_confirmed'],
                'signal'
            ] = 1
            
            signals_list.append(signal_df)
        
        if signals_list:
            self.signals = pd.concat(signals_list, ignore_index=True)
            return self.signals
        else:
            return pd.DataFrame()
    
    def rank_stocks(self, signals: pd.DataFrame, date: pd.Timestamp, top_n: int = 20) -> pd.DataFrame:
        """
        Rank stocks by momentum and select top N
        
        Args:
            signals: Signals DataFrame
            date: Current date
            top_n: Number of top stocks to select
            
        Returns:
            Top-ranked stocks
        """
        current_signals = signals[signals['date'] == date].copy()
        
        long_candidates = current_signals[current_signals['signal'] == 1].copy()
        
        long_candidates = long_candidates.sort_values('momentum', ascending=False)
        
        top_longs = long_candidates.head(top_n)
        
        return top_longs
    
    def calculate_position_sizes(self, ranked_stocks: pd.DataFrame, total_capital: float) -> Dict[str, float]:
        """
        Calculate position sizes based on liquidity weights
        
        Args:
            ranked_stocks: Top-ranked stocks
            total_capital: Total capital to allocate
            
        Returns:
            Dictionary of position sizes
        """
        if len(ranked_stocks) == 0:
            return {}
        
        weights = ranked_stocks['position_weight'].values
        weights = weights / weights.sum()
        
        positions = {}
        for idx, row in ranked_stocks.iterrows():
            symbol = row['symbol']
            weight = weights[list(ranked_stocks.index).index(idx)]
            positions[symbol] = total_capital * weight
        
        return positions
    
    def backtest(self, data: Dict[str, pd.DataFrame], initial_capital: float = 100000) -> pd.DataFrame:
        """
        Backtest the strategy
        
        Args:
            data: Dictionary of price data
            initial_capital: Starting capital
            
        Returns:
            Equity curve and performance metrics
        """
        signals = self.generate_signals(data)
        
        if signals.empty:
            return pd.DataFrame()
        
        dates = sorted(signals['date'].unique())
        
        rebalance_dates = dates[::self.rebalance_frequency]
        
        equity = initial_capital
        equity_curve = []
        positions = {}
        
        for i, date in enumerate(dates):
            if date in rebalance_dates:
                ranked = self.rank_stocks(signals, date, top_n=20)
                positions = self.calculate_position_sizes(ranked, equity)
            
            daily_return = 0
            for symbol, position_size in positions.items():
                symbol_data = data.get(symbol)
                if symbol_data is not None and date in symbol_data.index:
                    daily_ret = symbol_data.loc[date, 'returns']
                    if not np.isnan(daily_ret):
                        daily_return += (position_size / equity) * daily_ret
            
            equity *= (1 + daily_return)
            equity_curve.append({
                'date': date,
                'equity': equity,
                'return': daily_return,
                'num_positions': len(positions)
            })
        
        equity_df = pd.DataFrame(equity_curve).set_index('date')
        
        return equity_df
    
    def get_performance_stats(self, equity_curve: pd.DataFrame) -> Dict[str, float]:
        """Calculate performance statistics"""
        if equity_curve.empty:
            return {}
        
        returns = equity_curve['return'].dropna()
        
        total_return = (equity_curve['equity'].iloc[-1] / equity_curve['equity'].iloc[0]) - 1
        
        annual_return = (1 + total_return) ** (252 / len(equity_curve)) - 1
        
        annual_vol = returns.std() * np.sqrt(252)
        
        sharpe = (annual_return - 0.02) / annual_vol if annual_vol > 0 else 0
        
        running_max = equity_curve['equity'].expanding().max()
        drawdown = (equity_curve['equity'] - running_max) / running_max
        max_dd = abs(drawdown.min())
        
        winning_days = (returns > 0).sum()
        total_days = len(returns)
        win_rate = winning_days / total_days if total_days > 0 else 0
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'annual_volatility': annual_vol,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_dd,
            'win_rate': win_rate,
            'total_trades': len(equity_curve)
        }
