"""
Statistical Arbitrage - Pairs Trading Strategy

Based on cointegration and mean reversion principles.
Uses Kalman filter for dynamic hedge ratio estimation.

Key Features:
- Engle-Granger cointegration testing
- Dynamic hedge ratios via Kalman filter
- Z-score based entry/exit
- Half-life mean reversion filtering
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
from pykalman import KalmanFilter
import sys
sys.path.append('/workspace')
from utils.indicators import StatisticalTests


class PairsTradingStrategy:
    """
    Pairs Trading using cointegration and mean reversion
    """
    
    def __init__(self,
                 lookback_period: int = 252,
                 entry_z: float = 2.0,
                 exit_z: float = 0.5,
                 stop_loss_z: float = 3.5,
                 min_half_life: int = 5,
                 max_half_life: int = 60,
                 use_kalman: bool = True):
        """
        Initialize pairs trading strategy
        
        Args:
            lookback_period: Period for cointegration testing
            entry_z: Z-score threshold for entry
            exit_z: Z-score threshold for exit
            stop_loss_z: Z-score stop loss
            min_half_life: Minimum half-life for tradeable pairs
            max_half_life: Maximum half-life for tradeable pairs
            use_kalman: Use Kalman filter for hedge ratio
        """
        self.lookback_period = lookback_period
        self.entry_z = entry_z
        self.exit_z = exit_z
        self.stop_loss_z = stop_loss_z
        self.min_half_life = min_half_life
        self.max_half_life = max_half_life
        self.use_kalman = use_kalman
        
        self.pairs = []
        self.positions = {}
        
    def find_cointegrated_pairs(self, data: Dict[str, pd.DataFrame], 
                               min_p_value: float = 0.05) -> list:
        """
        Find cointegrated pairs from universe of stocks
        
        Args:
            data: Dictionary of DataFrames (symbol -> data)
            min_p_value: Maximum p-value for cointegration
            
        Returns:
            List of cointegrated pairs with metadata
        """
        symbols = list(data.keys())
        pairs = []
        
        for i in range(len(symbols)):
            for j in range(i+1, len(symbols)):
                symbol1, symbol2 = symbols[i], symbols[j]
                
                df1 = data[symbol1]
                df2 = data[symbol2]
                
                common_dates = df1.index.intersection(df2.index)
                if len(common_dates) < self.lookback_period:
                    continue
                
                prices1 = df1.loc[common_dates, 'close']
                prices2 = df2.loc[common_dates, 'close']
                
                beta, adf_stat, p_value, is_cointegrated = StatisticalTests.cointegration_test(
                    prices1, prices2
                )
                
                if is_cointegrated and p_value < min_p_value:
                    spread = prices1 - beta * prices2
                    
                    half_life = StatisticalTests.half_life_mean_reversion(spread)
                    
                    if self.min_half_life <= half_life <= self.max_half_life:
                        pairs.append({
                            'symbol1': symbol1,
                            'symbol2': symbol2,
                            'hedge_ratio': beta,
                            'p_value': p_value,
                            'half_life': half_life,
                            'spread_mean': spread.mean(),
                            'spread_std': spread.std()
                        })
        
        self.pairs = sorted(pairs, key=lambda x: x['p_value'])
        
        print(f"Found {len(self.pairs)} cointegrated pairs")
        return self.pairs
    
    def kalman_hedge_ratio(self, prices1: pd.Series, prices2: pd.Series) -> pd.Series:
        """
        Estimate dynamic hedge ratio using Kalman filter
        
        Args:
            prices1: First price series
            prices2: Second price series
            
        Returns:
            Time-varying hedge ratios
        """
        obs_mat = np.expand_dims(prices2.values, axis=1)
        
        kf = KalmanFilter(
            n_dim_obs=1,
            n_dim_state=1,
            initial_state_mean=0,
            initial_state_covariance=1,
            transition_matrices=[[1]],
            observation_matrices=obs_mat,
            observation_covariance=1,
            transition_covariance=0.01
        )
        
        state_means, state_covs = kf.filter(prices1.values)
        
        hedge_ratios = pd.Series(state_means.flatten(), index=prices1.index)
        
        return hedge_ratios
    
    def calculate_spread(self, prices1: pd.Series, prices2: pd.Series, 
                         hedge_ratio: float = None) -> pd.Series:
        """
        Calculate spread between two assets
        
        Args:
            prices1: First price series
            prices2: Second price series
            hedge_ratio: Hedge ratio (if None, estimated from data)
            
        Returns:
            Spread series
        """
        if hedge_ratio is None:
            if self.use_kalman:
                hedge_ratio = self.kalman_hedge_ratio(prices1, prices2)
                spread = prices1 - hedge_ratio * prices2
            else:
                from statsmodels.regression.linear_model import OLS
                model = OLS(prices1, prices2).fit()
                hedge_ratio = model.params[0]
                spread = prices1 - hedge_ratio * prices2
        else:
            spread = prices1 - hedge_ratio * prices2
        
        return spread
    
    def generate_signals(self, pair: Dict, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Generate trading signals for a pair
        
        Args:
            pair: Pair metadata
            data: Price data dictionary
            
        Returns:
            DataFrame with signals
        """
        symbol1 = pair['symbol1']
        symbol2 = pair['symbol2']
        
        df1 = data[symbol1]
        df2 = data[symbol2]
        
        common_dates = df1.index.intersection(df2.index)
        prices1 = df1.loc[common_dates, 'close']
        prices2 = df2.loc[common_dates, 'close']
        
        if self.use_kalman:
            hedge_ratios = self.kalman_hedge_ratio(prices1, prices2)
            spread = prices1 - hedge_ratios * prices2
        else:
            spread = self.calculate_spread(prices1, prices2, pair['hedge_ratio'])
            hedge_ratios = pd.Series(pair['hedge_ratio'], index=spread.index)
        
        z_score = StatisticalTests.z_score(spread, window=self.lookback_period // 10)
        
        signals = pd.DataFrame(index=common_dates)
        signals['spread'] = spread
        signals['z_score'] = z_score
        signals['hedge_ratio'] = hedge_ratios
        signals['signal'] = 0
        
        signals.loc[z_score > self.entry_z, 'signal'] = -1
        signals.loc[z_score < -self.entry_z, 'signal'] = 1
        
        signals.loc[abs(z_score) < self.exit_z, 'signal'] = 0
        
        signals.loc[abs(z_score) > self.stop_loss_z, 'signal'] = 0
        
        return signals
    
    def backtest_pair(self, pair: Dict, data: Dict[str, pd.DataFrame], 
                     capital_per_pair: float = 50000) -> pd.DataFrame:
        """
        Backtest a single pair
        
        Args:
            pair: Pair metadata
            data: Price data
            capital_per_pair: Capital allocated to this pair
            
        Returns:
            Equity curve
        """
        signals = self.generate_signals(pair, data)
        
        symbol1 = pair['symbol1']
        symbol2 = pair['symbol2']
        
        df1 = data[symbol1]
        df2 = data[symbol2]
        
        common_dates = signals.index
        returns1 = df1.loc[common_dates, 'returns']
        returns2 = df2.loc[common_dates, 'returns']
        
        positions = signals['signal'].shift(1).fillna(0)
        
        hedge_ratios = signals['hedge_ratio'].shift(1).fillna(pair['hedge_ratio'])
        
        strategy_returns = positions * (returns1 - hedge_ratios * returns2)
        
        equity = capital_per_pair * (1 + strategy_returns).cumprod()
        
        results = pd.DataFrame({
            'date': common_dates,
            'equity': equity,
            'returns': strategy_returns,
            'position': positions,
            'z_score': signals['z_score']
        }).set_index('date')
        
        return results
    
    def backtest_portfolio(self, data: Dict[str, pd.DataFrame], 
                          initial_capital: float = 100000,
                          max_pairs: int = 5) -> pd.DataFrame:
        """
        Backtest portfolio of pairs
        
        Args:
            data: Price data dictionary
            initial_capital: Starting capital
            max_pairs: Maximum number of pairs to trade
            
        Returns:
            Portfolio equity curve
        """
        if not self.pairs:
            self.find_cointegrated_pairs(data)
        
        selected_pairs = self.pairs[:max_pairs]
        capital_per_pair = initial_capital / len(selected_pairs)
        
        pair_results = []
        for pair in selected_pairs:
            try:
                result = self.backtest_pair(pair, data, capital_per_pair)
                pair_results.append(result['returns'])
            except Exception as e:
                print(f"Error backtesting pair {pair['symbol1']}-{pair['symbol2']}: {e}")
        
        if not pair_results:
            return pd.DataFrame()
        
        portfolio_returns = pd.concat(pair_results, axis=1).mean(axis=1)
        
        portfolio_equity = initial_capital * (1 + portfolio_returns).cumprod()
        
        results = pd.DataFrame({
            'equity': portfolio_equity,
            'returns': portfolio_returns,
            'num_pairs': len(selected_pairs)
        })
        
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
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'annual_volatility': annual_vol,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_dd,
            'num_trades': len(equity_curve)
        }
