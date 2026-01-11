"""
Technical indicators module for NSE Market Sector Analysis Tool
Implements RSI, ADX, and CMF calculations with Wilder's smoothing
"""

import pandas as pd
import numpy as np

from config import RSI_PERIOD, ADX_PERIOD, CMF_PERIOD


def calculate_rsi(data, period=RSI_PERIOD):
    """
    Calculate Relative Strength Index (RSI) using Wilder's smoothing method.
    This matches TradingView's RSI calculation.
    
    Args:
        data: DataFrame with 'Close' column
        period: RSI period (default 14)
        
    Returns:
        Series with RSI values
    """
    delta = data['Close'].diff()
    
    # Separate gains and losses
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    # Use Wilder's smoothing (exponential moving average with alpha = 1/period)
    # This is equivalent to TradingView's method
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_adx(data, period=ADX_PERIOD):
    """
    Calculate Average Directional Index (ADX) using Wilder's smoothing.
    Uses the TradingView-standard method.
    
    Args:
        data: DataFrame with OHLC data
        period: ADX period (default 14)
        
    Returns:
        Tuple of (ADX, +DI, -DI, DI_Spread)
    """
    high = data['High']
    low = data['Low']
    close = data['Close']
    
    # Calculate True Range
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Calculate Directional Movement
    up_move = high - high.shift()
    down_move = low.shift() - low
    
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0), index=data.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0), index=data.index)
    
    # Apply Wilder's smoothing
    def wilders_smoothing(series, period):
        """Apply Wilder's smoothing method (RMA)."""
        result = pd.Series(index=series.index, dtype=float)
        result.iloc[period - 1] = series.iloc[:period].mean()
        
        for i in range(period, len(series)):
            result.iloc[i] = (result.iloc[i - 1] * (period - 1) + series.iloc[i]) / period
        
        return result
    
    # Smooth TR, +DM, -DM using Wilder's method
    atr = wilders_smoothing(tr, period)
    plus_dm_smooth = wilders_smoothing(plus_dm, period)
    minus_dm_smooth = wilders_smoothing(minus_dm, period)
    
    # Calculate Directional Indicators
    plus_di = 100 * (plus_dm_smooth / atr)
    minus_di = 100 * (minus_dm_smooth / atr)
    
    # Calculate DX (Directional Movement Index)
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    dx = dx.fillna(0)
    
    # Apply Wilder's smoothing to DX to get ADX
    adx = wilders_smoothing(dx, period)
    
    di_spread = plus_di - minus_di
    
    return adx, plus_di, minus_di, di_spread


def calculate_cmf(data, period=CMF_PERIOD):
    """
    Calculate Chaikin Money Flow (CMF).
    
    Args:
        data: DataFrame with OHLCV data
        period: CMF period (default 20)
        
    Returns:
        Series with CMF values
    """
    high = data['High']
    low = data['Low']
    close = data['Close']
    volume = data['Volume']
    
    mf_multiplier = ((close - low) - (high - close)) / (high - low)
    mf_multiplier = mf_multiplier.fillna(0)
    
    mf_volume = mf_multiplier * volume
    cmf = mf_volume.rolling(window=period).sum() / volume.rolling(window=period).sum()
    
    return cmf


def calculate_z_score(series):
    """
    Calculate Z-Score for a series.
    
    Args:
        series: Pandas Series
        
    Returns:
        Z-Score value for the last element
    """
    if series.isna().all() or len(series) < 2:
        return 0.0
        
    mean = series.mean()
    std = series.std()
    
    if std == 0 or pd.isna(std):
        return 0.0
        
    latest_value = series.iloc[-1]
    z_score = (latest_value - mean) / std
    
    return z_score


def calculate_mansfield_rs(sector_data, benchmark_data, period=None, interval='1d'):
    """
    Calculate Mansfield Relative Strength.
    
    Formula: ((Current Ratio / Average Ratio) - 1) * 10
    where Ratio = Sector Close / Benchmark Close
    
    Args:
        sector_data: Sector price data DataFrame
        benchmark_data: Benchmark (Nifty 50) data DataFrame
        period: Period for moving average (if None, auto-calculated based on interval)
        interval: Data interval ('1d' for daily, '1wk' for weekly, '1h' for hourly)
        
    Returns:
        Latest Mansfield RS value
    """
    if len(sector_data) < 2 or len(benchmark_data) < 2:
        return 0.0
    
    # Auto-calculate period based on interval if not provided
    if period is None:
        if interval == '1wk':
            period = 52  # 52 weeks = 1 year
        elif interval == '1h':
            period = 250  # ~250 hours of trading
        else:  # '1d' or default
            period = 250  # 250 days = ~52 weeks = 1 year
    
    try:
        # Align indices
        common_index = sector_data.index.intersection(benchmark_data.index)
        if len(common_index) < period:
            # If insufficient data, use what's available (at least 20 periods)
            if len(common_index) < 20:
                return 0.0
            period = len(common_index)
        
        sector_close = sector_data['Close'].loc[common_index]
        benchmark_close = benchmark_data['Close'].loc[common_index]
        
        # Calculate RS Ratio
        rs_ratio = sector_close / benchmark_close
        
        # Calculate moving average of the ratio
        rs_ratio_ma = rs_ratio.rolling(window=period).mean()
        
        # Calculate Mansfield RS
        mansfield_rs = ((rs_ratio / rs_ratio_ma) - 1) * 10
        
        return mansfield_rs.iloc[-1] if not mansfield_rs.isna().all() else 0.0
        
    except Exception as e:
        return 0.0

