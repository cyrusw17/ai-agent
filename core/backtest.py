"""
Backtesting Module
Evaluates trading strategies on historical data
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import config


class Backtester:
    """Backtests trading strategies"""
    
    def __init__(self, initial_capital: float = None,
                 commission: float = None,
                 slippage: float = None):
        """
        Initialize backtester
        
        Args:
            initial_capital: Starting capital
            commission: Commission per trade (as decimal, e.g., 0.001 = 0.1%)
            slippage: Slippage per trade (as decimal)
        """
        self.initial_capital = initial_capital or config.BACKTEST['initial_capital']
        self.commission = commission or config.BACKTEST['commission']
        self.slippage = slippage or config.BACKTEST['slippage']
        
        self.capital = self.initial_capital
        self.positions = []
        self.closed_trades = []
        self.equity_curve = []
        
    def run_backtest(self, df: pd.DataFrame, signals: pd.DataFrame,
                    max_risk_per_trade: float = None) -> Dict:
        """
        Run backtest on signals
        
        Args:
            df: Price dataframe
            signals: Signals dataframe with entry, stop, take profit levels
            max_risk_per_trade: Maximum risk per trade as decimal
            
        Returns:
            Dictionary with backtest results
        """
        if max_risk_per_trade is None:
            max_risk_per_trade = config.RISK['max_risk_per_trade']
        
        self.capital = self.initial_capital
        self.positions = []
        self.closed_trades = []
        self.equity_curve = []
        
        for idx, row in df.iterrows():
            current_price = row['close']
            current_high = row['high']
            current_low = row['low']
            
            self._update_positions(idx, current_price, current_high, current_low)
            
            signals_at_bar = signals[signals['index'] == df.index.get_loc(idx)]
            
            for _, signal in signals_at_bar.iterrows():
                if len(self.positions) >= config.RISK['max_positions']:
                    continue
                
                position_size = self._calculate_position_size(
                    signal['entry_price'],
                    signal['stop_loss'],
                    max_risk_per_trade
                )
                
                if position_size > 0:
                    self._open_position(signal, position_size, idx)
            
            current_equity = self._calculate_equity(current_price)
            self.equity_curve.append({
                'timestamp': idx,
                'equity': current_equity,
                'capital': self.capital,
                'positions': len(self.positions)
            })
        
        self._close_all_positions(df.iloc[-1]['close'], df.index[-1])
        
        return self._calculate_performance_metrics()
    
    def _calculate_position_size(self, entry_price: float, 
                                 stop_loss: float,
                                 max_risk: float) -> float:
        """Calculate position size based on risk"""
        risk_per_share = abs(entry_price - stop_loss)
        
        if risk_per_share == 0:
            return 0
        
        max_risk_amount = self.capital * max_risk
        
        position_size = max_risk_amount / risk_per_share
        
        max_position_value = self.capital * 0.95
        if position_size * entry_price > max_position_value:
            position_size = max_position_value / entry_price
        
        return position_size
    
    def _open_position(self, signal: pd.Series, size: float, timestamp):
        """Open a new position"""
        entry_price = signal['entry_price']
        
        slippage_cost = entry_price * self.slippage
        if signal['type'] == 'LONG':
            actual_entry = entry_price + slippage_cost
        else:
            actual_entry = entry_price - slippage_cost
        
        commission_cost = actual_entry * size * self.commission
        
        position = {
            'id': len(self.closed_trades) + len(self.positions),
            'type': signal['type'],
            'entry_timestamp': timestamp,
            'entry_price': actual_entry,
            'size': size,
            'stop_loss': signal['stop_loss'],
            'take_profit_1': signal['take_profit_1'],
            'take_profit_2': signal.get('take_profit_2', signal['take_profit_1']),
            'take_profit_3': signal.get('take_profit_3', signal['take_profit_1']),
            'commission_paid': commission_cost,
            'signal_score': signal.get('composite_score', 0)
        }
        
        self.positions.append(position)
        self.capital -= commission_cost
    
    def _update_positions(self, timestamp, close_price: float,
                         high_price: float, low_price: float):
        """Update all open positions and check for exits"""
        positions_to_remove = []
        
        for i, position in enumerate(self.positions):
            if position['type'] == 'LONG':
                if low_price <= position['stop_loss']:
                    self._close_position(position, position['stop_loss'], 
                                       timestamp, 'stop_loss')
                    positions_to_remove.append(i)
                
                elif high_price >= position['take_profit_1']:
                    self._close_position(position, position['take_profit_1'],
                                       timestamp, 'take_profit')
                    positions_to_remove.append(i)
            
            elif position['type'] == 'SHORT':
                if high_price >= position['stop_loss']:
                    self._close_position(position, position['stop_loss'],
                                       timestamp, 'stop_loss')
                    positions_to_remove.append(i)
                
                elif low_price <= position['take_profit_1']:
                    self._close_position(position, position['take_profit_1'],
                                       timestamp, 'take_profit')
                    positions_to_remove.append(i)
        
        for i in reversed(positions_to_remove):
            self.positions.pop(i)
    
    def _close_position(self, position: Dict, exit_price: float,
                       timestamp, exit_reason: str):
        """Close a position"""
        commission_cost = exit_price * position['size'] * self.commission
        
        if position['type'] == 'LONG':
            pnl = (exit_price - position['entry_price']) * position['size']
        else:
            pnl = (position['entry_price'] - exit_price) * position['size']
        
        pnl -= commission_cost + position['commission_paid']
        
        self.capital += pnl + (position['entry_price'] * position['size'])
        
        trade_record = {
            **position,
            'exit_timestamp': timestamp,
            'exit_price': exit_price,
            'exit_reason': exit_reason,
            'pnl': pnl,
            'pnl_percent': (pnl / (position['entry_price'] * position['size'])) * 100,
            'duration': (timestamp - position['entry_timestamp']),
            'winner': pnl > 0
        }
        
        self.closed_trades.append(trade_record)
    
    def _close_all_positions(self, price: float, timestamp):
        """Close all remaining positions at end of backtest"""
        for position in self.positions:
            self._close_position(position, price, timestamp, 'end_of_backtest')
        
        self.positions = []
    
    def _calculate_equity(self, current_price: float) -> float:
        """Calculate current equity including open positions"""
        equity = self.capital
        
        for position in self.positions:
            if position['type'] == 'LONG':
                unrealized_pnl = (current_price - position['entry_price']) * position['size']
            else:
                unrealized_pnl = (position['entry_price'] - current_price) * position['size']
            
            equity += unrealized_pnl
        
        return equity
    
    def _calculate_performance_metrics(self) -> Dict:
        """Calculate comprehensive performance metrics"""
        if not self.closed_trades:
            return {'error': 'No closed trades'}
        
        trades_df = pd.DataFrame(self.closed_trades)
        equity_df = pd.DataFrame(self.equity_curve)
        
        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df['winner']])
        losing_trades = total_trades - winning_trades
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        total_pnl = trades_df['pnl'].sum()
        final_equity = self.capital
        total_return = ((final_equity - self.initial_capital) / self.initial_capital) * 100
        
        avg_win = trades_df[trades_df['winner']]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = abs(trades_df[~trades_df['winner']]['pnl'].mean()) if losing_trades > 0 else 0
        
        profit_factor = (
            trades_df[trades_df['winner']]['pnl'].sum() / 
            abs(trades_df[~trades_df['winner']]['pnl'].sum())
            if losing_trades > 0 and trades_df[~trades_df['winner']]['pnl'].sum() != 0
            else float('inf')
        )
        
        largest_win = trades_df['pnl'].max()
        largest_loss = trades_df['pnl'].min()
        
        equity_df['drawdown'] = equity_df['equity'].cummax() - equity_df['equity']
        equity_df['drawdown_pct'] = (equity_df['drawdown'] / equity_df['equity'].cummax()) * 100
        
        max_drawdown = equity_df['drawdown'].max()
        max_drawdown_pct = equity_df['drawdown_pct'].max()
        
        equity_df['returns'] = equity_df['equity'].pct_change()
        
        returns_std = equity_df['returns'].std()
        avg_return = equity_df['returns'].mean()
        
        sharpe_ratio = (avg_return / returns_std * np.sqrt(252)) if returns_std != 0 else 0
        
        if avg_loss != 0:
            expectancy = (win_rate/100 * avg_win) - ((1 - win_rate/100) * avg_loss)
        else:
            expectancy = avg_win
        
        avg_duration = trades_df['duration'].mean()
        
        long_trades = trades_df[trades_df['type'] == 'LONG']
        short_trades = trades_df[trades_df['type'] == 'SHORT']
        
        long_win_rate = (len(long_trades[long_trades['winner']]) / len(long_trades) * 100) if len(long_trades) > 0 else 0
        short_win_rate = (len(short_trades[short_trades['winner']]) / len(short_trades) * 100) if len(short_trades) > 0 else 0
        
        return {
            'initial_capital': self.initial_capital,
            'final_equity': final_equity,
            'total_pnl': total_pnl,
            'total_return_pct': total_return,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate_pct': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': max_drawdown_pct,
            'sharpe_ratio': sharpe_ratio,
            'expectancy': expectancy,
            'avg_trade_duration': avg_duration,
            'long_trades': len(long_trades),
            'short_trades': len(short_trades),
            'long_win_rate_pct': long_win_rate,
            'short_win_rate_pct': short_win_rate
        }
    
    def get_equity_curve(self) -> pd.DataFrame:
        """Get equity curve dataframe"""
        return pd.DataFrame(self.equity_curve)
    
    def get_trades_dataframe(self) -> pd.DataFrame:
        """Get closed trades as dataframe"""
        return pd.DataFrame(self.closed_trades)
    
    def print_summary(self, metrics: Dict):
        """Print backtest summary"""
        print("\n" + "="*60)
        print("BACKTEST RESULTS SUMMARY")
        print("="*60)
        
        print(f"\nCapital:")
        print(f"  Initial: ${metrics['initial_capital']:,.2f}")
        print(f"  Final:   ${metrics['final_equity']:,.2f}")
        print(f"  P&L:     ${metrics['total_pnl']:,.2f}")
        print(f"  Return:  {metrics['total_return_pct']:.2f}%")
        
        print(f"\nTrades:")
        print(f"  Total:   {metrics['total_trades']}")
        print(f"  Winners: {metrics['winning_trades']}")
        print(f"  Losers:  {metrics['losing_trades']}")
        print(f"  Win Rate: {metrics['win_rate_pct']:.2f}%")
        
        print(f"\nPerformance:")
        print(f"  Profit Factor: {metrics['profit_factor']:.2f}")
        print(f"  Sharpe Ratio:  {metrics['sharpe_ratio']:.2f}")
        print(f"  Expectancy:    ${metrics['expectancy']:.2f}")
        print(f"  Avg Win:       ${metrics['avg_win']:.2f}")
        print(f"  Avg Loss:      ${metrics['avg_loss']:.2f}")
        
        print(f"\nRisk:")
        print(f"  Max Drawdown:     ${metrics['max_drawdown']:,.2f}")
        print(f"  Max Drawdown %:   {metrics['max_drawdown_pct']:.2f}%")
        print(f"  Largest Win:      ${metrics['largest_win']:,.2f}")
        print(f"  Largest Loss:     ${metrics['largest_loss']:,.2f}")
        
        print(f"\nDirectional:")
        print(f"  Long Trades:      {metrics['long_trades']} ({metrics['long_win_rate_pct']:.1f}% win rate)")
        print(f"  Short Trades:     {metrics['short_trades']} ({metrics['short_win_rate_pct']:.1f}% win rate)")
        
        print("\n" + "="*60 + "\n")
