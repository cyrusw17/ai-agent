"""
XGBoost-Based Trading Strategy

Uses gradient boosting for feature-based predictions
Combines technical indicators with ML predictions

Features:
- Feature engineering from technical indicators
- Walk-forward validation
- Probability-based signal generation
- Risk-adjusted position sizing
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, classification_report
import sys
sys.path.append('/workspace')
from utils.indicators import TechnicalIndicators, VolatilityMetrics


class XGBoostTradingStrategy:
    """
    Machine Learning trading strategy using XGBoost
    """
    
    def __init__(self,
                 feature_lookbacks: List[int] = [5, 10, 20],
                 prediction_horizon: int = 1,
                 prob_threshold: float = 0.55,
                 train_size: int = 252,
                 retrain_frequency: int = 21,
                 xgb_params: Dict = None):
        """
        Initialize XGBoost strategy
        
        Args:
            feature_lookbacks: Lookback periods for features
            prediction_horizon: Days ahead to predict
            prob_threshold: Probability threshold for signals
            train_size: Training window size
            retrain_frequency: How often to retrain (days)
            xgb_params: XGBoost hyperparameters
        """
        self.feature_lookbacks = feature_lookbacks
        self.prediction_horizon = prediction_horizon
        self.prob_threshold = prob_threshold
        self.train_size = train_size
        self.retrain_frequency = retrain_frequency
        
        self.xgb_params = xgb_params or {
            'objective': 'binary:logistic',
            'max_depth': 5,
            'learning_rate': 0.1,
            'n_estimators': 100,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': 42
        }
        
        self.model = None
        self.feature_names = []
        
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Engineer features for ML model
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with features
        """
        features = df.copy()
        
        features['rsi_14'] = TechnicalIndicators.rsi(df['close'], 14)
        
        macd, macd_signal, macd_hist = TechnicalIndicators.macd(df['close'])
        features['macd'] = macd
        features['macd_signal'] = macd_signal
        features['macd_hist'] = macd_hist
        
        bb_upper, bb_middle, bb_lower = TechnicalIndicators.bollinger_bands(df['close'])
        features['bb_position'] = (df['close'] - bb_lower) / (bb_upper - bb_lower)
        features['bb_width'] = (bb_upper - bb_lower) / bb_middle
        
        if 'high' in df.columns and 'low' in df.columns:
            features['atr'] = TechnicalIndicators.atr(df['high'], df['low'], df['close'])
            features['atr_percent'] = features['atr'] / df['close']
        
        for period in self.feature_lookbacks:
            features[f'return_{period}'] = df['close'].pct_change(period)
            features[f'volatility_{period}'] = df['returns'].rolling(period).std()
            features[f'ma_{period}'] = TechnicalIndicators.sma(df['close'], period)
            features[f'price_to_ma_{period}'] = df['close'] / features[f'ma_{period}']
            
            if 'volume' in df.columns:
                features[f'volume_ma_{period}'] = df['volume'].rolling(period).mean()
                features[f'volume_ratio_{period}'] = df['volume'] / features[f'volume_ma_{period}']
        
        features['momentum_5_20'] = (features['ma_5'] - features['ma_20']) / features['ma_20']
        
        if 'volume' in df.columns:
            features['volume_trend'] = df['volume'].pct_change()
        
        features['volatility_regime'] = VolatilityMetrics.volatility_regime(df['returns'])
        
        return features
    
    def create_labels(self, df: pd.DataFrame) -> pd.Series:
        """
        Create binary labels for classification
        
        Label = 1 if future return > 0, else 0
        
        Args:
            df: DataFrame with returns
            
        Returns:
            Label series
        """
        future_returns = df['close'].pct_change(self.prediction_horizon).shift(-self.prediction_horizon)
        
        labels = (future_returns > 0).astype(int)
        
        return labels
    
    def prepare_ml_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare features and labels for ML
        
        Args:
            df: Raw DataFrame
            
        Returns:
            features_df, labels
        """
        features_df = self.engineer_features(df)
        labels = self.create_labels(df)
        
        features_df = features_df.dropna()
        labels = labels[features_df.index]
        
        feature_cols = [col for col in features_df.columns 
                       if col not in ['open', 'high', 'low', 'close', 'volume', 'returns', 'log_returns']]
        
        self.feature_names = feature_cols
        
        return features_df[feature_cols], labels
    
    def train_model(self, X_train: pd.DataFrame, y_train: pd.Series) -> xgb.XGBClassifier:
        """
        Train XGBoost model
        
        Args:
            X_train: Training features
            y_train: Training labels
            
        Returns:
            Trained model
        """
        model = xgb.XGBClassifier(**self.xgb_params)
        model.fit(X_train, y_train, verbose=False)
        
        return model
    
    def generate_predictions(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate predictions using walk-forward approach
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with predictions and probabilities
        """
        X, y = self.prepare_ml_data(df)
        
        predictions = []
        probabilities = []
        dates = []
        
        for i in range(self.train_size, len(X), self.retrain_frequency):
            train_end = i
            train_start = max(0, train_end - self.train_size)
            test_end = min(len(X), i + self.retrain_frequency)
            
            X_train = X.iloc[train_start:train_end]
            y_train = y.iloc[train_start:train_end]
            X_test = X.iloc[train_end:test_end]
            
            if len(y_train) < 50:
                continue
            
            model = self.train_model(X_train, y_train)
            
            preds = model.predict(X_test)
            probs = model.predict_proba(X_test)[:, 1]
            
            predictions.extend(preds)
            probabilities.extend(probs)
            dates.extend(X_test.index)
        
        results = pd.DataFrame({
            'date': dates,
            'prediction': predictions,
            'probability': probabilities
        }).set_index('date')
        
        return results
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals from predictions
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with signals
        """
        predictions = self.generate_predictions(df)
        
        signals = df.loc[predictions.index].copy()
        signals['prediction'] = predictions['prediction']
        signals['probability'] = predictions['probability']
        
        signals['signal'] = 0
        signals.loc[signals['probability'] >= self.prob_threshold, 'signal'] = 1
        signals.loc[signals['probability'] <= (1 - self.prob_threshold), 'signal'] = -1
        
        signals['confidence'] = abs(signals['probability'] - 0.5) * 2
        
        return signals
    
    def backtest(self, df: pd.DataFrame, initial_capital: float = 100000,
                position_size: float = 0.95) -> pd.DataFrame:
        """
        Backtest the XGBoost strategy
        
        Args:
            df: DataFrame with OHLCV data
            initial_capital: Starting capital
            position_size: Base position size
            
        Returns:
            Equity curve
        """
        signals = self.generate_signals(df)
        
        equity = initial_capital
        cash = initial_capital
        position = 0
        shares = 0
        entry_price = 0
        
        equity_curve = []
        
        for i in range(len(signals)):
            current_signal = signals['signal'].iloc[i]
            current_price = signals['close'].iloc[i]
            confidence = signals['confidence'].iloc[i]
            
            adjusted_size = position_size * confidence
            
            if position == 0 and current_signal != 0:
                position = current_signal
                shares = (cash * adjusted_size) / current_price
                entry_price = current_price
                cash = cash * (1 - adjusted_size)
            
            elif position != 0 and current_signal == 0:
                pnl = shares * (current_price - entry_price) * position
                cash += shares * current_price
                position = 0
                shares = 0
                entry_price = 0
            
            elif position != 0 and current_signal == -position:
                cash += shares * current_price
                position = current_signal
                shares = (cash * adjusted_size) / current_price
                entry_price = current_price
                cash = cash * (1 - adjusted_size)
            
            equity = cash + (shares * current_price if position != 0 else 0)
            
            equity_curve.append({
                'date': signals.index[i],
                'equity': equity,
                'position': position,
                'signal': current_signal,
                'confidence': confidence,
                'price': current_price
            })
        
        results = pd.DataFrame(equity_curve).set_index('date')
        results['returns'] = results['equity'].pct_change()
        
        return results
    
    def get_feature_importance(self, df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
        """
        Get feature importance from trained model
        
        Args:
            df: DataFrame with data
            top_n: Number of top features to return
            
        Returns:
            DataFrame with feature importances
        """
        X, y = self.prepare_ml_data(df)
        
        X_train = X.iloc[-self.train_size:]
        y_train = y.iloc[-self.train_size:]
        
        model = self.train_model(X_train, y_train)
        
        importance_df = pd.DataFrame({
            'feature': model.feature_names_in_,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        return importance_df.head(top_n)
    
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
        
        avg_confidence = equity_curve['confidence'].mean()
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'annual_volatility': annual_vol,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_dd,
            'win_rate': win_rate,
            'avg_confidence': avg_confidence,
            'num_trades': total_trades
        }
