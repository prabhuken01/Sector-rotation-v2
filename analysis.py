"""
Analysis module for NSE Market Sector Analysis Tool
Handles sector analysis, scoring, and ranking with configurable weights
"""

import pandas as pd
import numpy as np

from indicators import calculate_rsi, calculate_adx, calculate_cmf, calculate_z_score, calculate_mansfield_rs
from config import (REVERSAL_BUY_DIV, REVERSAL_WATCH, DEFAULT_MOMENTUM_WEIGHTS, 
                    DEFAULT_REVERSAL_WEIGHTS, DECIMAL_PLACES, MANSFIELD_RS_PERIOD)


def calculate_relative_strength(sector_returns, benchmark_returns):
    """
    Calculate Relative Strength Rating vs benchmark.
    
    Args:
        sector_returns: Series of sector returns
        benchmark_returns: Series of benchmark returns
        
    Returns:
        Relative strength rating (0-10 scale)
    """
    if len(sector_returns) < 2 or len(benchmark_returns) < 2:
        return 5.0
        
    # Calculate cumulative returns
    sector_cumret = (1 + sector_returns).prod() - 1
    benchmark_cumret = (1 + benchmark_returns).prod() - 1
    
    if pd.isna(sector_cumret) or pd.isna(benchmark_cumret):
        return 5.0
        
    relative_perf = sector_cumret - benchmark_cumret
    
    # Convert to 0-10 scale
    rs_rating = 5 + (relative_perf * 25)
    rs_rating = max(0, min(10, rs_rating))
    
    return rs_rating


def analyze_sector(name, data, benchmark_data, momentum_weights=None, reversal_weights=None, symbol=None, interval='1d', reversal_thresholds=None):
    """
    Perform comprehensive analysis on a sector.
    
    Args:
        name: Sector name
        data: Sector data DataFrame
        benchmark_data: Benchmark sector data (Nifty 50)
        momentum_weights: Dict with weights for momentum score (default: DEFAULT_MOMENTUM_WEIGHTS)
        reversal_weights: Dict with weights for reversal score (default: DEFAULT_REVERSAL_WEIGHTS)
        symbol: Symbol/ticker for the sector (optional)
        interval: Data interval ('1d', '1wk', '1h') for Mansfield RS calculation
        reversal_thresholds: Dict with RSI and ADX_Z thresholds for reversal filtering
        
    Returns:
        Dictionary with analysis results or None if error
    """
    if momentum_weights is None:
        momentum_weights = DEFAULT_MOMENTUM_WEIGHTS
    if reversal_weights is None:
        reversal_weights = DEFAULT_REVERSAL_WEIGHTS
        
    try:
        # Calculate indicators
        rsi = calculate_rsi(data)
        adx, plus_di, minus_di, di_spread = calculate_adx(data)
        cmf = calculate_cmf(data)
        
        # Get latest values
        latest_rsi = rsi.iloc[-1] if not rsi.isna().all() else 50.0
        latest_adx = adx.iloc[-1] if not adx.isna().all() else 0.0
        latest_di_spread = di_spread.iloc[-1] if not di_spread.isna().all() else 0.0
        latest_cmf = cmf.iloc[-1] if not cmf.isna().all() else 0.0
        
        # Calculate Z-Score for ADX
        adx_z_score = calculate_z_score(adx.dropna())
        
        # Calculate Mansfield RS with interval-appropriate period
        mansfield_rs = calculate_mansfield_rs(data, benchmark_data, interval=interval)
        
        # Calculate Relative Strength vs Benchmark
        if benchmark_data is not None and len(benchmark_data) > 0:
            sector_returns = data['Close'].pct_change().dropna()
            benchmark_returns = benchmark_data['Close'].pct_change().dropna()
            
            # Align data
            common_index = sector_returns.index.intersection(benchmark_returns.index)
            if len(common_index) > 0:
                sector_returns = sector_returns.loc[common_index]
                benchmark_returns = benchmark_returns.loc[common_index]
                rs_rating = calculate_relative_strength(sector_returns, benchmark_returns)
            else:
                rs_rating = 5.0
        else:
            rs_rating = 5.0
        
        # Store values for ranking-based momentum score calculation
        momentum_score = 0  # Will be calculated after all sectors are analyzed
        
        # Calculate Reversal Score with configurable weights
        reversal_score = calculate_reversal_score(
            latest_rsi, adx_z_score, latest_cmf, rs_rating, reversal_weights
        )
        
        # Determine Reversal Status (with user-defined thresholds)
        reversal_status = determine_reversal_status(latest_rsi, adx_z_score, latest_cmf, reversal_thresholds)
        
        # Get current price and previous close for % change calculation
        current_price = data['Close'].iloc[-1] if len(data) > 0 else 0.0
        prev_close = data['Close'].iloc[-2] if len(data) > 1 else current_price
        pct_change = ((current_price - prev_close) / prev_close * 100) if prev_close != 0 else 0.0
        
        return {
            'Sector': name,
            'Symbol': symbol if symbol else 'N/A',
            'Price': current_price,
            'Change_%': pct_change,
            'RSI': latest_rsi,
            'ADX': latest_adx,
            'ADX_Z': adx_z_score,
            'DI_Spread': latest_di_spread,
            'CMF': latest_cmf,
            'Mansfield_RS': mansfield_rs,
            'RS_Rating': rs_rating,
            'Momentum_Score': momentum_score,
            'Reversal_Score': reversal_score,
            'Reversal_Status': reversal_status
        }
        
    except Exception as e:
        print(f"Error analyzing {name}: {e}")
        return None


def calculate_reversal_score(rsi, adx_z, cmf, rs_rating, weights):
    """
    Calculate reversal score with configurable percentage-based weights.
    
    Args:
        rsi: RSI value
        adx_z: ADX Z-Score
        cmf: CMF value
        rs_rating: RS Rating value (0-10 scale)
        weights: Dictionary with percentage weights for each indicator (should sum to 100%)
        
    Returns:
        Reversal score (rank-based, higher is better for reversal potential)
    """
    # Normalize indicators to 0-10 scale for consistency
    rsi_normalized = (100 - rsi) / 10  # Lower RSI = higher reversal potential (0-10 scale)
    adx_z_normalized = max(0, -adx_z) * 2  # Negative ADX_Z indicates weak trend (higher is better)
    cmf_normalized = (cmf + 1) * 5  # CMF ranges from -1 to 1, normalize to 0-10
    rs_rating_normalized = (10 - rs_rating)  # Lower RS_Rating = more underperforming (0-10 scale)
    
    # Calculate weighted score using percentages
    total_weight = sum(weights.values())
    reversal_score = (
        rsi_normalized * weights.get('RSI', 10.0) / total_weight * 100 +
        adx_z_normalized * weights.get('ADX_Z', 10.0) / total_weight * 100 +
        cmf_normalized * weights.get('CMF', 40.0) / total_weight * 100 +
        rs_rating_normalized * weights.get('RS_Rating', 40.0) / total_weight * 100
    )
    
    return reversal_score


def determine_reversal_status(rsi, adx_z, cmf, reversal_thresholds=None):
    """
    Determine reversal status based on technical indicators and user-defined thresholds.
    
    Args:
        rsi: Current RSI value
        adx_z: Current ADX Z-Score
        cmf: Current CMF value
        reversal_thresholds: Dict with RSI and ADX_Z thresholds (optional)
        
    Returns:
        Reversal status string: 'BUY_DIV', 'Watch', or 'No'
    """
    # Apply user-defined thresholds if provided
    if reversal_thresholds:
        rsi_threshold = reversal_thresholds.get('RSI', 40.0)
        adx_z_threshold = reversal_thresholds.get('ADX_Z', 0.0)
        
        # First check if sector meets the user-defined filters
        if not (rsi < rsi_threshold and adx_z < adx_z_threshold):
            return "No"  # Doesn't meet basic filter criteria
    
    # Then apply standard reversal logic for those that pass filters
    if (rsi < REVERSAL_BUY_DIV['RSI'] and 
        adx_z < REVERSAL_BUY_DIV['ADX_Z'] and 
        cmf > REVERSAL_BUY_DIV['CMF']):
        return "BUY_DIV"
    elif (rsi < REVERSAL_WATCH['RSI'] and 
          adx_z < REVERSAL_WATCH['ADX_Z'] and 
          cmf > REVERSAL_WATCH['CMF']):
        return "Watch"
    else:
        return "No"


def analyze_all_sectors(sector_data_dict, benchmark_data, momentum_weights=None, reversal_weights=None, symbols_dict=None, interval='1d', reversal_thresholds=None):
    """
    Analyze all sectors and return results DataFrame.
    Excludes Nifty 50 benchmark from rankings.
    Uses ranking-based momentum score calculation.
    
    Args:
        sector_data_dict: Dictionary of sector name to data DataFrame
        benchmark_data: Benchmark data DataFrame
        momentum_weights: Dict with percentage weights for momentum score (sum to 100%)
        reversal_weights: Dict with weights for reversal score
        symbols_dict: Dictionary mapping sector names to their symbols
        interval: Data interval ('1d', '1wk', '1h') for Mansfield RS calculation
        reversal_thresholds: Dict with RSI and ADX_Z thresholds for reversal filtering
        
    Returns:
        DataFrame with analysis results for all sectors (excluding Nifty 50)
    """
    if momentum_weights is None:
        momentum_weights = DEFAULT_MOMENTUM_WEIGHTS
    
    results = []
    
    for sector_name, data in sector_data_dict.items():
        if sector_name == 'Nifty 50':  # Skip benchmark from rankings
            continue
        
        symbol = symbols_dict.get(sector_name, 'N/A') if symbols_dict else 'N/A'
        result = analyze_sector(sector_name, data, benchmark_data, momentum_weights, reversal_weights, symbol, interval, reversal_thresholds)
        if result:
            results.append(result)
    
    if not results:
        return None
    
    df = pd.DataFrame(results)
    
    # Calculate ranking-based momentum score
    # Rank each indicator (higher value = better rank, i.e., rank 1 is best)
    # For sectors where Mansfield_RS < 0, they should have lower composite scores
    df['ADX_Z_Rank'] = df['ADX_Z'].rank(ascending=True, method='min')
    df['RS_Rating_Rank'] = df['RS_Rating'].rank(ascending=True, method='min')
    df['RSI_Rank'] = df['RSI'].rank(ascending=True, method='min')  # Higher RSI = stronger momentum
    df['DI_Spread_Rank'] = df['DI_Spread'].rank(ascending=True, method='min')
    
    # Calculate composite momentum score using percentage weights
    # Convert percentages to decimals (e.g., 20% = 0.20)
    df['Momentum_Score'] = (
        (df['ADX_Z_Rank'] * momentum_weights.get('ADX_Z', 20.0) / 100.0) +
        (df['RS_Rating_Rank'] * momentum_weights.get('RS_Rating', 40.0) / 100.0) +
        (df['RSI_Rank'] * momentum_weights.get('RSI', 30.0) / 100.0) +
        (df['DI_Spread_Rank'] * momentum_weights.get('DI_Spread', 10.0) / 100.0)
    )
    
    # Calculate rank-based reversal score ONLY for sectors with Reversal_Status != 'No'
    # This ensures reversal scores are relative only among eligible reversal candidates
    eligible_reversals = df[df['Reversal_Status'] != 'No'].copy()
    
    if len(eligible_reversals) > 0:
        # Rank within eligible sectors only
        # Lower RS_Rating, RSI, ADX_Z are better → rank ascending=True (lowest gets highest rank)
        # Higher CMF is better → rank ascending=False (highest gets highest rank)
        eligible_reversals['RS_Rating_Reversal_Rank'] = eligible_reversals['RS_Rating'].rank(ascending=True, method='min')
        eligible_reversals['CMF_Reversal_Rank'] = eligible_reversals['CMF'].rank(ascending=False, method='min')
        eligible_reversals['RSI_Reversal_Rank'] = eligible_reversals['RSI'].rank(ascending=True, method='min')
        eligible_reversals['ADX_Z_Reversal_Rank'] = eligible_reversals['ADX_Z'].rank(ascending=True, method='min')
        
        # Calculate rank-based reversal score using percentage weights (same approach as momentum)
        if reversal_weights:
            total_weight = sum(reversal_weights.values())
            eligible_reversals['Reversal_Score_Ranked'] = (
                (eligible_reversals['RS_Rating_Reversal_Rank'] * reversal_weights.get('RS_Rating', 40.0) / total_weight * 100) +
                (eligible_reversals['CMF_Reversal_Rank'] * reversal_weights.get('CMF', 40.0) / total_weight * 100) +
                (eligible_reversals['RSI_Reversal_Rank'] * reversal_weights.get('RSI', 10.0) / total_weight * 100) +
                (eligible_reversals['ADX_Z_Reversal_Rank'] * reversal_weights.get('ADX_Z', 10.0) / total_weight * 100)
            )
        else:
            eligible_reversals['Reversal_Score_Ranked'] = (
                (eligible_reversals['RS_Rating_Reversal_Rank'] * 0.40 * 100) +
                (eligible_reversals['CMF_Reversal_Rank'] * 0.40 * 100) +
                (eligible_reversals['RSI_Reversal_Rank'] * 0.10 * 100) +
                (eligible_reversals['ADX_Z_Reversal_Rank'] * 0.10 * 100)
            )
        
        # Update the main dataframe with rank-based reversal scores for eligible sectors
        df.loc[eligible_reversals.index, 'Reversal_Score'] = eligible_reversals['Reversal_Score_Ranked']
    
    # Optionally: Penalize sectors with negative Mansfield RS (commented out for now, can enable if needed)
    # df.loc[df['Mansfield_RS'] < 0, 'Momentum_Score'] = df.loc[df['Mansfield_RS'] < 0, 'Momentum_Score'] * 0.8
    
    return df


def format_results_dataframe(df):
    """
    Format the results DataFrame with proper decimal places per user preference.
    1 decimal for most indicators, 2 for CMF.
    
    Args:
        df: Results DataFrame
        
    Returns:
        Formatted DataFrame
    """
    for col in df.columns:
        if col in DECIMAL_PLACES:
            decimals = DECIMAL_PLACES[col]
            df[col] = df[col].round(decimals)
    
    return df
