#!/usr/bin/env python3
"""
NSE Market Sector Analysis Tool - Streamlit Web Interface
Enhanced with configurable weights, ETF proxy, and improved aesthetics
Version: 2.3.8 - Stock screener export fix, market breadth simplified (Feb 2026)
"""

# Visible app version (shown on main page for deploy verification)
APP_VERSION = "2.3.8"

import os
import io
from io import BytesIO
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import warnings
import traceback

warnings.filterwarnings("ignore")


# ------------------------------------------------------------
# Helper: Top N sectors by momentum (RSI + CMF, Z-score based)
# Used to focus Stock Screener & Confluence on momentum sectors
# ------------------------------------------------------------
def get_top_n_sectors_by_momentum(sector_data_dict, momentum_weights, n=4):
    """
    Get top N sectors based on RSI+CMF momentum ranking.

    Identifies sectors with strongest momentum and money flow,
    following the "money flows where momentum is" principle.

    Parameters
    ----------
    sector_data_dict : dict
        Dictionary mapping sector names to their price data (DataFrames).
    momentum_weights : dict
        Momentum weights configuration (not used in calculation but kept for signature).
    n : int
        Number of top sectors to return (default 4).

    Returns


    
    -------
    list
        Top N sector names sorted by combined RSI+CMF momentum score.
    """
    if not sector_data_dict or len(sector_data_dict) < n:
        # If fewer sectors than requested, return all available sectors
        return list(sector_data_dict.keys()) if sector_data_dict else []

    sector_scores = []

    for sector_name, data in sector_data_dict.items():
        # Need at least ~14 bars to get a reasonable RSI/CMF reading
        if data is None or len(data) < 14:
            continue

        try:
            # Calculate momentum indicators on the sector index/ETF
            rsi = calculate_rsi(data)
            cmf = calculate_cmf(data)

            # Latest values with safe fallbacks
            rsi_val = float(rsi.iloc[-1]) if not rsi.isna().all() else 50.0
            cmf_val = float(cmf.iloc[-1]) if not cmf.isna().all() else 0.0

            sector_scores.append(
                {
                    "Sector": sector_name,
                    "RSI": rsi_val,
                    "CMF": cmf_val,
                }
            )
        except Exception:
            # Best-effort only; if any sector fails, just skip it
            continue

    if not sector_scores:
        # Fall back to all sectors if nothing could be scored
        return list(sector_data_dict.keys())

    df = pd.DataFrame(sector_scores)

    # Z-score normalize RSI and CMF separately, then combine 50/50
    if len(df) > 1:
        rsi_mean, rsi_std = df["RSI"].mean(), df["RSI"].std()
        cmf_mean, cmf_std = df["CMF"].mean(), df["CMF"].std()

        # Avoid division by zero
        rsi_z = (df["RSI"] - rsi_mean) / rsi_std if rsi_std > 0 else pd.Series(0, index=df.index)
        cmf_z = (df["CMF"] - cmf_mean) / cmf_std if cmf_std > 0 else pd.Series(0, index=df.index)

        df["Momentum_Score"] = 0.5 * rsi_z + 0.5 * cmf_z
    else:
        df["Momentum_Score"] = 0.0

    # Sort by momentum score (highest first) and return top N sectors
    df_sorted = df.sort_values("Momentum_Score", ascending=False)
    top_sectors = df_sorted.head(n)["Sector"].tolist()
    return top_sectors


try:
    from config import (
        SECTORS,
        SECTOR_ETFS,
        SECTOR_ETFS_ALTERNATE,
        MOMENTUM_SCORE_PERCENTILE_THRESHOLD,
        DEFAULT_MOMENTUM_WEIGHTS,
        DEFAULT_MOMENTUM_WEIGHTS_TRENDING,
        DEFAULT_REVERSAL_WEIGHTS,
        DECIMAL_PLACES,
    )
    from data_fetcher import (
        fetch_sector_data,
        fetch_sector_data_with_alternate,
        fetch_all_sectors_parallel,
        clear_data_cache,
    )
    from analysis import analyze_all_sectors, format_results_dataframe, analyze_sector
    from indicators import (
        calculate_rsi,
        calculate_adx,
        calculate_cmf,
        calculate_z_score,
        calculate_mansfield_rs,
    )
    from company_analysis import (
        display_company_momentum_tab,
        display_company_reversal_tab,
    )
except ImportError as e:
    st.error(f"❌ Import Error: {str(e)}")
    st.info("Please ensure all required modules are installed: yfinance, pandas, numpy")
    st.stop()


# Page configuration
st.set_page_config(
    page_title="NSE Market Sector Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better aesthetics, center alignment, and improved visibility
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #333;
        text-align: center;
        padding-bottom: 1rem;
    }
    .date-info {
        font-size: 0.95rem;
        color: #fff;
        text-align: center;
        padding: 0.75rem;
        background-color: #2c3e50;
        border-radius: 0.3rem;
        margin-bottom: 1rem;
        font-weight: 500;
    }
    /* Dataframe styling */
    .dataframe td {
        text-align: center !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        padding: 8px !important;
    }
    .dataframe th {
        text-align: center !important;
        background-color: #34495e !important;
        color: #ffffff !important;
        font-weight: bold !important;
        font-size: 14px !important;
        padding: 10px !important;
    }
    /* Fix text color on dark row backgrounds */
    div[data-testid="stDataFrame"] tbody tr {
        background-color: transparent !important;
    }
    div[data-testid="stDataFrame"] tbody tr:nth-child(odd) {
        background-color: rgba(255, 255, 255, 0.05) !important;
    }
    div[data-testid="stDataFrame"] tbody td {
        color: #ffffff !important;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    /* Improved visibility for styled cells */
    [data-testid="stDataFrame"] {
        font-size: 14px;
    }
    </style>
""", unsafe_allow_html=True)


# Tooltip definitions for all technical indicators
INDICATOR_TOOLTIPS = {
    'RSI': 'Relative Strength Index (0-100). >70 = overbought, <30 = oversold. Shows momentum strength.',
    'ADX': 'Average Directional Index (0-50). >25 = strong trend, <20 = weak trend. Measures trend strength.',
    'ADX_Z': 'Z-Score of ADX normalized relative to other sectors. Negative = weaker trend vs peers, Positive = stronger.',
    '+DI': 'Positive Directional Indicator. Shows upward pressure/bullish strength in the trend.',
    '-DI': 'Negative Directional Indicator. Shows downward pressure/bearish strength in the trend.',
    'DI_Spread': 'Difference between +DI and -DI. Positive = more bullish, Negative = more bearish.',
    'CMF': 'Chaikin Money Flow (-1 to +1). >0 = money flowing in (accumulation), <0 = flowing out (distribution).',
    'RS_Rating': 'Relative Strength Rating (0-10) vs Nifty 50. >7 = outperformer, <3 = underperformer.',
    'Mansfield_RS': 'Relative strength based on 52-week moving average. >0 = outperforming Nifty 50, <0 = underperforming.',
    'Momentum_Score': 'Composite rank-based score. Top sectors = strongest momentum across all indicators.',
    'Reversal_Score': 'Score for reversal candidates. Only calculated for eligible sectors (RSI/ADX filters met).',
    'Status': 'Reversal Status: BUY_DIV = strong buy divergence, Watch = potential zone, No = ineligible.',
    'Rank': 'Sector/Company rank by score. 1 = strongest, N = weakest within analysis group.',
    'Weight': 'Index weight (%). Shows company/sector importance in the index.',
}

def get_column_with_tooltip(col_name, show_tooltip=True):
    """Return column name with tooltip hover text."""
    if show_tooltip and col_name in INDICATOR_TOOLTIPS:
        return f"{col_name} ℹ️"
    return col_name

def display_tooltip_legend():
    """Display tooltip legend at bottom of page."""
    with st.expander("📋 **Indicator Definitions** (Click to expand)", expanded=False):
        cols = st.columns(2)
        indicators = list(INDICATOR_TOOLTIPS.items())
        for idx, (indicator, tooltip) in enumerate(indicators):
            with cols[idx % 2]:
                st.markdown(f"**{indicator}**: {tooltip}")


def get_sidebar_controls():
    """Create sidebar controls for user configuration."""
    st.sidebar.header("⚙️ Analysis Settings")
    
    # Date selection with navigation
    st.sidebar.subheader("📅 Select Analysis Date")
    
    # Initialize session state for date if not exists
    if 'analysis_date_state' not in st.session_state:
        st.session_state.analysis_date_state = datetime.now().date()
    
    # Date input
    analysis_date = st.sidebar.date_input(
        "Analysis Date",
        value=st.session_state.analysis_date_state,
        max_value=datetime.now().date(),
        help="Select date for historical analysis"
    )
    
    # Update session state if date changed via input
    if analysis_date != st.session_state.analysis_date_state:
        st.session_state.analysis_date_state = analysis_date
    
    # Date navigation buttons
    col_left, col_middle, col_right = st.sidebar.columns([1, 2, 1])
    
    with col_left:
        if st.button("⬅️", key="btn_prev_date", use_container_width=True, help="Previous day"):
            st.session_state.analysis_date_state = st.session_state.analysis_date_state - timedelta(days=1)
            st.rerun()
    
    with col_middle:
        st.caption(f"📆 {st.session_state.analysis_date_state.strftime('%b %d')}")
    
    with col_right:
        if st.button("➡️", key="btn_next_date", use_container_width=True, help="Next day"):
            if st.session_state.analysis_date_state < datetime.now().date():
                st.session_state.analysis_date_state = st.session_state.analysis_date_state + timedelta(days=1)
                st.rerun()
            else:
                st.warning("Already at latest date")
    
    # Update analysis_date to use session state
    analysis_date = st.session_state.analysis_date_state
    
    # Color coding toggle
    st.sidebar.subheader("📊 Display Options")
    enable_color_coding = st.sidebar.checkbox("Enable Bullish/Bearish Colors", value=True,
                                               help="Color code cells to highlight strong/weak signals")
    
    # Time period (interval) selection
    time_interval = st.sidebar.radio(
        "Analysis Interval",
        options=["Daily", "Weekly", "Hourly"],
        index=0,
        help="Select data granularity. Note: Hourly data limited to ~60 days history"
    )
    
    # Data source selection
    st.sidebar.subheader("Data Source")
    
    # Initialize session state for ETF selection
    if 'use_etf_state' not in st.session_state:
        st.session_state.use_etf_state = True  # Default to True (ETF as Proxy ticked)
    
    use_etf = st.sidebar.checkbox("Use ETF Proxy", value=st.session_state.use_etf_state, 
                                   help="Toggle between Index and ETF data")
    
    # Update session state when checkbox changes
    if use_etf != st.session_state.use_etf_state:
        st.session_state.use_etf_state = use_etf
    
    # Momentum weights: toggle Historical vs Trending (default Trending)
    st.sidebar.subheader("Momentum Score Weights (%)")
    momentum_mode = st.sidebar.radio(
        "Momentum weight mode",
        options=["Trending", "Historical"],
        index=0,
        help="Trending: 50% Z(RSI) + 50% Z(CMF). Historical: RS Rating, ADX Z, RSI, DI Spread (CMF = 0%)."
    )
    
    if momentum_mode == "Trending":
        st.sidebar.caption("Trending: CMF + RSI (sum = 100%; changing one auto-adjusts the other)")
        cmf_weight = st.sidebar.slider("CMF Weight (%)", 0.0, 100.0, 
                                       DEFAULT_MOMENTUM_WEIGHTS_TRENDING['CMF'], 1.0, key="momentum_cmf")
        rsi_trending_weight = 100.0 - cmf_weight
        st.sidebar.caption(f"RSI Weight: **{rsi_trending_weight:.1f}%** (auto)")
        momentum_weights = {
            'CMF': cmf_weight,
            'RSI': rsi_trending_weight,
            'ADX_Z': 0.0,
            'RS_Rating': 0.0,
            'DI_Spread': 0.0
        }
        total_momentum_weight = 100.0
        st.sidebar.success(f"✅ Weights sum to {total_momentum_weight:.1f}%")
    else:
        st.sidebar.caption("Historical: RS Rating, ADX Z, RSI, DI Spread. CMF = 0%.")
        rs_weight = st.sidebar.slider("RS Rating Weight (%)", 0.0, 100.0, 
                                       DEFAULT_MOMENTUM_WEIGHTS['RS_Rating'], 1.0, key="momentum_rs")
        adx_weight = st.sidebar.slider("ADX Z-Score Weight (%)", 0.0, 100.0, 
                                        DEFAULT_MOMENTUM_WEIGHTS['ADX_Z'], 1.0, key="momentum_adx")
        rsi_momentum_weight = st.sidebar.slider("RSI Weight (%)", 0.0, 100.0, 
                                                 DEFAULT_MOMENTUM_WEIGHTS['RSI'], 1.0, key="momentum_rsi")
        di_spread_weight = st.sidebar.slider("DI Spread Weight (%)", 0.0, 100.0, 
                                              DEFAULT_MOMENTUM_WEIGHTS['DI_Spread'], 1.0, key="momentum_di")
        st.sidebar.caption("CMF Weight: **0%** (fixed in Historical)")
        total_momentum_weight = adx_weight + rs_weight + rsi_momentum_weight + di_spread_weight
        if abs(total_momentum_weight - 100.0) > 0.1:
            st.sidebar.warning(f"⚠️ Weights sum to {total_momentum_weight:.1f}% (should be 100%)")
        else:
            st.sidebar.success(f"✅ Weights sum to {total_momentum_weight:.1f}%")
        momentum_weights = {
            'ADX_Z': adx_weight,
            'RS_Rating': rs_weight,
            'RSI': rsi_momentum_weight,
            'DI_Spread': di_spread_weight,
            'CMF': 0.0
        }
    
    # Reversal filter thresholds (moved before weights)
    st.sidebar.subheader("Reversal Filters")
    st.sidebar.caption("Only show sectors meeting BOTH conditions")
    rsi_threshold = st.sidebar.slider("RSI must be below", 20.0, 60.0, 40.0, 1.0,
                                      help="Only show reversal candidates with RSI below this value")
    adx_z_threshold = st.sidebar.slider("ADX Z-Score must be below", -2.0, 2.0, 2.0, 0.1,
                                        help="RSI alone can indicate trend reversal. Use ADX_Z threshold only if you want to filter by trend strength. Default 2 = no filter")
    
    # Reversal weights
    st.sidebar.subheader("Reversal Score Weights (%)")
    st.sidebar.caption("Weights should sum to 100%")
    rs_ranking_weight = st.sidebar.slider("RS Ranking Weight (%)", 0.0, 100.0, 
                                          DEFAULT_REVERSAL_WEIGHTS['RS_Rating'], 1.0)
    cmf_reversal_weight = st.sidebar.slider("CMF Weight (%)", 0.0, 100.0, 
                                            DEFAULT_REVERSAL_WEIGHTS['CMF'], 1.0)
    rsi_reversal_weight = st.sidebar.slider("RSI Weight (%)", 0.0, 100.0, 
                                            DEFAULT_REVERSAL_WEIGHTS['RSI'], 1.0)
    adx_z_reversal_weight = st.sidebar.slider("ADX Z Weight (%)", 0.0, 100.0, 
                                              DEFAULT_REVERSAL_WEIGHTS['ADX_Z'], 1.0)
    
    # Calculate and display total
    total_reversal_weight = rs_ranking_weight + cmf_reversal_weight + rsi_reversal_weight + adx_z_reversal_weight
    if abs(total_reversal_weight - 100.0) > 0.1:
        st.sidebar.warning(f"⚠️ Weights sum to {total_reversal_weight:.1f}% (should be 100%)")
    else:
        st.sidebar.success(f"✅ Weights sum to {total_reversal_weight:.1f}%")
    
    reversal_weights = {
        'RS_Rating': rs_ranking_weight,
        'CMF': cmf_reversal_weight,
        'RSI': rsi_reversal_weight,
        'ADX_Z': adx_z_reversal_weight
    }
    
    reversal_thresholds = {
        'RSI': rsi_threshold,
        'ADX_Z': adx_z_threshold,
        'CMF': 0.0  # CMF must be positive for reversal candidates
    }
    
    return use_etf, momentum_weights, reversal_weights, analysis_date, time_interval, reversal_thresholds, enable_color_coding


@st.cache_data(ttl=300, show_spinner=False)
def fetch_all_sector_data_cached(data_source_key, analysis_date_str, yf_interval, use_etf):
    """
    Cached function to fetch all sector data in parallel.
    Uses string keys for cache compatibility.
    """
    data_source = SECTOR_ETFS if use_etf else SECTORS
    alternates = SECTOR_ETFS_ALTERNATE if use_etf else None
    
    # Parse date if provided
    from datetime import datetime
    analysis_date = datetime.strptime(analysis_date_str, '%Y-%m-%d').date() if analysis_date_str else None
    
    sector_data = {}
    failed_sectors = []
    
    for sector_name, symbol in data_source.items():
        if not symbol or str(symbol).strip() == 'N/A':
            continue
        try:
            alternate_symbol = alternates.get(sector_name) if alternates else None
            if alternate_symbol and str(alternate_symbol).strip() == 'N/A':
                alternate_symbol = None
            data, used_symbol = fetch_sector_data_with_alternate(
                symbol, 
                alternate_symbol=alternate_symbol,
                end_date=analysis_date, 
                interval=yf_interval
            )
            
            if data is not None and len(data) > 0:
                sector_data[sector_name] = data
            else:
                failed_sectors.append(sector_name)
        except Exception:
            failed_sectors.append(sector_name)
    
    return sector_data, failed_sectors


def analyze_sectors_with_progress(use_etf, momentum_weights, reversal_weights, analysis_date=None, time_interval='Daily', reversal_thresholds=None):
    """Run analysis with progress indicators and optimized data fetching."""
    try:
        # Map interval to yfinance format
        interval_map = {'Daily': '1d', 'Weekly': '1wk', 'Hourly': '1h'}
        yf_interval = interval_map.get(time_interval, '1d')
        
        # Select data source
        data_source = SECTOR_ETFS if use_etf else SECTORS
        source_label = "ETF" if use_etf else "Index"
        
        # Create cache key from parameters
        data_source_key = 'etf' if use_etf else 'index'
        analysis_date_str = analysis_date.strftime('%Y-%m-%d') if analysis_date else None
        
        # Show loading spinner during data fetch
        with st.spinner(f"🔄 Fetching {time_interval.lower()} sector data..."):
            # Use cached parallel fetch
            sector_data, failed_sectors = fetch_all_sector_data_cached(
                data_source_key, 
                analysis_date_str, 
                yf_interval, 
                use_etf
            )
        
        # Get benchmark data from fetched data
        benchmark_data = sector_data.get('Nifty 50')
        
        if benchmark_data is None:
            st.error("❌ Failed to fetch benchmark data (Nifty 50). Please check internet connection and try again.")
            return None, None, None
        
        if len(benchmark_data) == 0:
            st.error("❌ Benchmark data is empty. No data available for Nifty 50.")
            return None, None, None
        
        if failed_sectors:
            # Display only first 3 failed sectors
            failed_display = failed_sectors[:3]
            if len(failed_sectors) > 3:
                st.info(f"⚠️ Failed to fetch data for: {', '.join(failed_display)}, and {len(failed_sectors) - 3} more")
            elif failed_display:
                st.info(f"⚠️ Failed to fetch data for: {', '.join(failed_display)}")
        
        if len(sector_data) <= 1:  # Only benchmark
            st.error("❌ No sector data available for analysis. Please check your internet connection.")
            return None, None, None
        
        # Store the last market date from the data with proper interval logic
        if benchmark_data is not None and len(benchmark_data) > 0:
            last_data_timestamp = benchmark_data.index[-1]
            if yf_interval == '1h':
                market_date = last_data_timestamp.strftime('%Y-%m-%d %H:%M')
            elif yf_interval == '1wk':
                week_start = last_data_timestamp - pd.Timedelta(days=last_data_timestamp.weekday())
                market_date = f"Week of {week_start.strftime('%Y-%m-%d')}"
            else:
                market_date = last_data_timestamp.strftime('%Y-%m-%d')
        else:
            market_date = "N/A"
        
        # Analyze all sectors (excludes Nifty 50 from rankings)
        with st.spinner("📊 Analyzing sectors..."):
            try:
                df = analyze_all_sectors(sector_data, benchmark_data, momentum_weights, reversal_weights, data_source, yf_interval, reversal_thresholds)
            except Exception as e:
                st.error(f"❌ Analysis failed: {str(e)}")
                st.info("Please try again or adjust the parameters.")
                return None, None, None
        
        if df is None or df.empty:
            st.error("❌ Analysis returned empty results. Please try again.")
            return None, None, None
        
        # Format results
        try:
            df = format_results_dataframe(df)
        except Exception as e:
            st.error(f"❌ Error formatting results: {str(e)}")
            return None, None, None
        
        return df, sector_data, market_date
        
    except Exception as e:
        st.error(f"❌ Unexpected error during analysis: {str(e)}")
        st.text(traceback.format_exc())
        return None, None, None


def color_mansfield_rs(val):
    """Color code Mansfield RS: green if > 0, red if < 0."""
    try:
        if float(val) > 0:
            return 'background-color: #27AE60; color: #fff; font-weight: bold'  # Green
        else:
            return 'background-color: #E74C3C; color: #fff; font-weight: bold'  # Red
    except:
        return ''


def color_momentum_score(df_row, enable_coloring=True):
    """Color code momentum score cells: green for top 3, red for bottom 3."""
    if not enable_coloring:
        return [''] * len(df_row)
    
    try:
        momentum_scores = pd.to_numeric(df_row.get('Momentum_Score', []), errors='coerce')
        if len(momentum_scores) == 0:
            return [''] * len(df_row)
        
        top_3_threshold = momentum_scores.nlargest(3).min()
        bottom_3_threshold = momentum_scores.nsmallest(3).max()
        current_score = float(df_row.get('Momentum_Score', 0))
        
        result = [''] * len(df_row)
        
        # Find the index of Momentum_Score column
        if 'Momentum_Score' in df_row.index:
            idx = list(df_row.index).index('Momentum_Score')
            if current_score >= top_3_threshold:
                result[idx] = 'background-color: #27AE60; color: #fff; font-weight: bold'  # Green
            elif current_score <= bottom_3_threshold:
                result[idx] = 'background-color: #E74C3C; color: #fff; font-weight: bold'  # Red
        
        return result
    except:
        return [''] * len(df_row)


def color_reversal_status(val, enable_coloring=True):
    """Color code reversal status: green for BUY_DIV, yellow for Watch."""
    if not enable_coloring:
        return ''
    
    try:
        if val == 'BUY_DIV':
            return 'background-color: #27AE60; color: #fff; font-weight: bold'  # Green
        elif val == 'Watch':
            return 'background-color: #F39C12; color: #fff; font-weight: bold'  # Yellow/Orange
    except:
        pass
    return ''


def format_value(val, decimals=1):
    """Format numerical value with specified decimal places."""
    try:
        return f"{float(val):.{decimals}f}"
    except:
        return val


def calculate_sector_trend(sector_name, data, benchmark_data, all_sector_data, periods=7):
    """
    Calculate trend for a sector over the last N periods with ACTUAL rank-based momentum scores.
    This calculates momentum scores by ranking all sectors at each historical period.
    
    Args:
        sector_name: Name of the sector to analyze
        data: Price data for the selected sector
        benchmark_data: Benchmark (Nifty 50) data
        all_sector_data: Dictionary of all sector data for ranking
        periods: Number of periods to look back
    
    Returns:
        DataFrame with historical indicators and actual momentum scores
    """
    try:
        if data is None or len(data) < periods:
            return None
        
        trend_data = []
        
        for i in range(periods, 0, -1):
            try:
                # Get the actual date for this period from the data index
                period_index = -i if i > 0 else -1
                if abs(period_index) <= len(data):
                    period_date = data.index[period_index]
                    date_str = period_date.strftime('%d-%b')
                else:
                    date_str = ""
                
                period_label = f'T-{i-1} ({date_str})' if i > 1 else f'T ({date_str})'
                
                # For each period, analyze ALL sectors to get rankings
                period_results = []
                
                for sect_name, sect_data in all_sector_data.items():
                    if sect_name == 'Nifty 50':  # Skip benchmark
                        continue
                    
                    # Get data up to that historical point
                    subset_data = sect_data.iloc[:-i+1] if i > 1 else sect_data
                    bench_subset = benchmark_data.iloc[:-i+1] if i > 1 else benchmark_data
                    
                    if len(subset_data) < 14:  # Minimum for most indicators
                        continue
                    
                    # Calculate all indicators for this sector at this point in time
                    rsi = calculate_rsi(subset_data)
                    adx, plus_di, minus_di, di_spread = calculate_adx(subset_data)
                    cmf = calculate_cmf(subset_data)
                    # Note: interval info not available here - using default behavior
                    mansfield_rs = calculate_mansfield_rs(subset_data, bench_subset)
                    adx_z = calculate_z_score(adx.dropna())
                    
                    # Calculate RS Rating
                    if bench_subset is not None and len(bench_subset) > 0:
                        sector_returns = subset_data['Close'].pct_change().dropna()
                        benchmark_returns = bench_subset['Close'].pct_change().dropna()
                        
                        common_index = sector_returns.index.intersection(benchmark_returns.index)
                        if len(common_index) > 1:
                            sector_returns_aligned = sector_returns.loc[common_index]
                            benchmark_returns_aligned = benchmark_returns.loc[common_index]
                            
                            sector_cumret = (1 + sector_returns_aligned).prod() - 1
                            benchmark_cumret = (1 + benchmark_returns_aligned).prod() - 1
                            
                            if not pd.isna(sector_cumret) and not pd.isna(benchmark_cumret):
                                relative_perf = sector_cumret - benchmark_cumret
                                rs_rating = 5 + (relative_perf * 25)
                                rs_rating = max(0, min(10, rs_rating))
                            else:
                                rs_rating = 5.0
                        else:
                            rs_rating = 5.0
                    else:
                        rs_rating = 5.0
                    
                    # Store results for this sector
                    period_results.append({
                        'Sector': sect_name,
                        'ADX_Z': adx_z if not pd.isna(adx_z) else 0,
                        'RS_Rating': rs_rating,
                        'RSI': rsi.iloc[-1] if not rsi.isna().all() else 50,
                        'DI_Spread': di_spread.iloc[-1] if not di_spread.isna().all() else 0,
                        'Mansfield_RS': mansfield_rs,
                        'ADX': adx.iloc[-1] if not adx.isna().all() else 0,
                        'CMF': cmf.iloc[-1] if not cmf.isna().all() else 0
                    })
                
                if not period_results:
                    continue
                
                # Create DataFrame and rank all sectors at this point in time
                period_df = pd.DataFrame(period_results)
                num_sectors = len(period_df)
                
                # Calculate ranks: Higher values = better = rank 1 (ascending=False)
                period_df['ADX_Z_Rank'] = period_df['ADX_Z'].rank(ascending=False, method='min')
                period_df['RS_Rating_Rank'] = period_df['RS_Rating'].rank(ascending=False, method='min')
                period_df['RSI_Rank'] = period_df['RSI'].rank(ascending=False, method='min')
                period_df['DI_Spread_Rank'] = period_df['DI_Spread'].rank(ascending=False, method='min')
                
                # Calculate weighted average rank (lower = better)
                period_df['Weighted_Avg_Rank'] = (
                    (period_df['ADX_Z_Rank'] * 0.20) +
                    (period_df['RS_Rating_Rank'] * 0.40) +
                    (period_df['RSI_Rank'] * 0.30) +
                    (period_df['DI_Spread_Rank'] * 0.10)
                )
                
                # Scale to 1-10 where 10 = best momentum, 1 = worst
                if num_sectors > 1:
                    min_rank = period_df['Weighted_Avg_Rank'].min()
                    max_rank = period_df['Weighted_Avg_Rank'].max()
                    if max_rank > min_rank:
                        period_df['Momentum_Score'] = 10 - ((period_df['Weighted_Avg_Rank'] - min_rank) / (max_rank - min_rank)) * 9
                    else:
                        period_df['Momentum_Score'] = 5.0
                else:
                    period_df['Momentum_Score'] = 5.0
                
                # Extract data for the selected sector
                sector_row = period_df[period_df['Sector'] == sector_name]
                if len(sector_row) > 0:
                    trend_data.append({
                        'Period': period_label,
                        'Mansfield_RS': format_value(sector_row['Mansfield_RS'].iloc[0], 1),
                        'RS_Rating': format_value(sector_row['RS_Rating'].iloc[0], 1),
                        'ADX': format_value(sector_row['ADX'].iloc[0], 1),
                        'ADX_Z': format_value(sector_row['ADX_Z'].iloc[0], 1),
                        'DI_Spread': format_value(sector_row['DI_Spread'].iloc[0], 1),
                        'RSI': format_value(sector_row['RSI'].iloc[0], 1),
                        'CMF': format_value(sector_row['CMF'].iloc[0], 2),
                        'Momentum_Score': format_value(sector_row['Momentum_Score'].iloc[0], 1),
                        'Rank': int(period_df['Momentum_Score'].rank(ascending=False, method='min')[sector_row.index[0]])
                    })
            except Exception as e:
                st.warning(f"⚠️ Error calculating period {period_label}: {str(e)}")
                continue
        
        if not trend_data:
            return None
        
        df = pd.DataFrame(trend_data)
        return df
        
    except Exception as e:
        st.warning(f"⚠️ Error calculating trend: {str(e)}")
        return None


def calculate_reversal_trend(sector_name, data, benchmark_data, all_sector_data, reversal_weights, reversal_thresholds, periods=7):
    """
    Calculate reversal trend for a sector over the last N periods with ACTUAL rank-based reversal scores.
    This calculates reversal scores by ranking eligible sectors at each historical period.
    
    Args:
        sector_name: Name of the sector to analyze
        data: Price data for the selected sector
        benchmark_data: Benchmark (Nifty 50) data
        all_sector_data: Dictionary of all sector data for ranking
        reversal_weights: Dict with reversal score weights (percentages)
        reversal_thresholds: Dict with RSI and ADX_Z thresholds
        periods: Number of periods to look back
    
    Returns:
        DataFrame with historical indicators and actual reversal scores
    """
    try:
        if data is None or len(data) < periods:
            return None
        
        trend_data = []
        
        for i in range(periods, 0, -1):
            try:
                # Get the actual date for this period from the data index
                period_index = -i if i > 0 else -1
                if abs(period_index) <= len(data):
                    period_date = data.index[period_index]
                    date_str = period_date.strftime('%d-%b')
                else:
                    date_str = ""
                
                period_label = f'T-{i-1} ({date_str})' if i > 1 else f'T ({date_str})'
                
                # For each period, analyze ALL sectors to get rankings
                period_results = []
                
                for sect_name, sect_data in all_sector_data.items():
                    if sect_name == 'Nifty 50':  # Skip benchmark
                        continue
                    
                    # Get data up to that historical point
                    subset_data = sect_data.iloc[:-i+1] if i > 1 else sect_data
                    bench_subset = benchmark_data.iloc[:-i+1] if i > 1 else benchmark_data
                    
                    if len(subset_data) < 14:  # Minimum for most indicators
                        continue
                    
                    # Calculate all indicators for this sector at this point in time
                    rsi = calculate_rsi(subset_data)
                    adx, plus_di, minus_di, di_spread = calculate_adx(subset_data)
                    cmf = calculate_cmf(subset_data)
                    mansfield_rs = calculate_mansfield_rs(subset_data, bench_subset)
                    adx_z = calculate_z_score(adx.dropna())
                    
                    # Calculate RS Rating
                    if bench_subset is not None and len(bench_subset) > 0:
                        sector_returns = subset_data['Close'].pct_change().dropna()
                        benchmark_returns = bench_subset['Close'].pct_change().dropna()
                        
                        common_index = sector_returns.index.intersection(benchmark_returns.index)
                        if len(common_index) > 1:
                            sector_returns_aligned = sector_returns.loc[common_index]
                            benchmark_returns_aligned = benchmark_returns.loc[common_index]
                            
                            sector_cumret = (1 + sector_returns_aligned).prod() - 1
                            benchmark_cumret = (1 + benchmark_returns_aligned).prod() - 1
                            
                            if not pd.isna(sector_cumret) and not pd.isna(benchmark_cumret):
                                relative_perf = sector_cumret - benchmark_cumret
                                rs_rating = 5 + (relative_perf * 25)
                                rs_rating = max(0, min(10, rs_rating))
                            else:
                                rs_rating = 5.0
                        else:
                            rs_rating = 5.0
                    else:
                        rs_rating = 5.0
                    
                    # Get final values
                    rsi_val = rsi.iloc[-1] if not rsi.isna().all() else 50
                    adx_z_val = adx_z if not pd.isna(adx_z) else 0
                    cmf_val = cmf.iloc[-1] if not cmf.isna().all() else 0
                    
                    # Check reversal eligibility
                    meets_rsi = rsi_val < reversal_thresholds.get('RSI', 40)
                    meets_adx_z = adx_z_val < reversal_thresholds.get('ADX_Z', -0.5)
                    
                    period_results.append({
                        'Sector': sect_name,
                        'RSI': rsi_val,
                        'ADX_Z': adx_z_val,
                        'CMF': cmf_val,
                        'RS_Rating': rs_rating,
                        'Mansfield_RS': mansfield_rs,
                        'Meets_RSI': meets_rsi,
                        'Meets_ADX_Z': meets_adx_z,
                        'Eligible': meets_rsi and meets_adx_z
                    })
                
                if not period_results:
                    continue
                
                # Create DataFrame
                period_df = pd.DataFrame(period_results)
                
                # Filter to eligible reversals only
                eligible_reversals = period_df[period_df['Eligible']].copy()
                
                if len(eligible_reversals) > 0:
                    num_eligible = len(eligible_reversals)
                    # Calculate ranks within eligible sectors
                    # Lower RS_Rating, RSI, ADX_Z are better for reversals → rank ascending=True (lowest = rank 1)
                    # Higher CMF is better → rank ascending=False (highest = rank 1)
                    eligible_reversals['RS_Rating_Rank'] = eligible_reversals['RS_Rating'].rank(ascending=True, method='min')
                    eligible_reversals['CMF_Rank'] = eligible_reversals['CMF'].rank(ascending=False, method='min')
                    eligible_reversals['RSI_Rank'] = eligible_reversals['RSI'].rank(ascending=True, method='min')
                    eligible_reversals['ADX_Z_Rank'] = eligible_reversals['ADX_Z'].rank(ascending=True, method='min')
                    
                    # Calculate weighted average rank (lower = better reversal candidate)
                    total_weight = sum(reversal_weights.values())
                    eligible_reversals['Weighted_Avg_Rank'] = (
                        (eligible_reversals['RS_Rating_Rank'] * reversal_weights.get('RS_Rating', 40) / total_weight) +
                        (eligible_reversals['CMF_Rank'] * reversal_weights.get('CMF', 40) / total_weight) +
                        (eligible_reversals['RSI_Rank'] * reversal_weights.get('RSI', 10) / total_weight) +
                        (eligible_reversals['ADX_Z_Rank'] * reversal_weights.get('ADX_Z', 10) / total_weight)
                    )
                    
                    # Scale to 1-10 where 10 = best reversal candidate, 1 = worst
                    if num_eligible > 1:
                        min_rank = eligible_reversals['Weighted_Avg_Rank'].min()
                        max_rank = eligible_reversals['Weighted_Avg_Rank'].max()
                        if max_rank > min_rank:
                            eligible_reversals['Reversal_Score'] = 10 - ((eligible_reversals['Weighted_Avg_Rank'] - min_rank) / (max_rank - min_rank)) * 9
                        else:
                            eligible_reversals['Reversal_Score'] = 5.0
                    else:
                        eligible_reversals['Reversal_Score'] = 10.0  # Single eligible gets max score
                    
                    # Merge back to get reversal scores
                    period_df = period_df.merge(
                        eligible_reversals[['Sector', 'Reversal_Score']], 
                        on='Sector', 
                        how='left'
                    )
                    period_df['Reversal_Score'].fillna(0, inplace=True)
                else:
                    period_df['Reversal_Score'] = 0
                
                # Extract data for the selected sector
                sector_row = period_df[period_df['Sector'] == sector_name]
                if len(sector_row) > 0:
                    reversal_score = sector_row['Reversal_Score'].iloc[0]
                    is_eligible = sector_row['Eligible'].iloc[0]
                    rsi_val = sector_row['RSI'].iloc[0]
                    adx_z_val = sector_row['ADX_Z'].iloc[0]
                    cmf_val = sector_row['CMF'].iloc[0]
                    
                    # Determine reversal status based on thresholds (same as main table)
                    status = 'No'
                    if is_eligible:
                        # Check if BUY_DIV or Watch based on standard thresholds
                        if rsi_val < reversal_thresholds.get('RSI', 40) * 0.75 and adx_z_val < reversal_thresholds.get('ADX_Z', -0.5) - 0.5 and cmf_val > 0.1:
                            status = 'BUY_DIV'
                        else:
                            status = 'Watch'
                    
                    # Rank should show number if eligible and has reversal_score > 0
                    rank = 'N/A'
                    if status != 'No' and reversal_score > 0:  # Only if eligible with score
                        ranked_df = period_df[period_df['Reversal_Score'] > 0].copy()
                        if len(ranked_df) > 0:
                            rank = int(ranked_df['Reversal_Score'].rank(ascending=False, method='min')[sector_row.index[0]])
                    
                    trend_data.append({
                        'Period': period_label,
                        'Status': status,
                        'RS_Rating': format_value(sector_row['RS_Rating'].iloc[0], 1),
                        'CMF': format_value(sector_row['CMF'].iloc[0], 2),
                        'RSI': format_value(sector_row['RSI'].iloc[0], 1),
                        'ADX_Z': format_value(sector_row['ADX_Z'].iloc[0], 1),
                        'Mansfield_RS': format_value(sector_row['Mansfield_RS'].iloc[0], 1),
                        'Reversal_Score': format_value(reversal_score, 1) if reversal_score > 0 else 'N/A',
                        'Rank': rank
                    })
            except Exception as e:
                st.warning(f"⚠️ Error calculating period {period_label}: {str(e)}")
                continue
        
        if not trend_data:
            return None
        
        df = pd.DataFrame(trend_data)
        return df
        
    except Exception as e:
        st.warning(f"⚠️ Error calculating reversal trend: {str(e)}")
        return None


def calculate_historical_momentum_performance(sector_data_dict, benchmark_data, momentum_weights, use_etf, interval='1d', months=6):
    """
    Calculate historical top 2 momentum ETFs with forward returns over the past N months.
    
    Args:
        sector_data_dict: Dictionary of sector name to data DataFrame
        benchmark_data: Benchmark data DataFrame
        momentum_weights: Dict with momentum score weights
        use_etf: Whether using ETF or Index data
        interval: Data interval ('1d', '1wk', '1h')
        months: Number of months to look back (default 6)
    
    Returns:
        DataFrame with date, top 2 ETFs, and their forward returns
    """
    try:
        from datetime import timedelta
        import pandas as pd
        
        # Determine lookback period based on interval
        if interval == '1wk':
            # For weekly, approximate 6 months = 26 weeks
            lookback_periods = min(26, len(benchmark_data) - 20)
        elif interval == '1h':
            # For hourly, limited history, use what's available
            lookback_periods = min(len(benchmark_data) - 20, 500)
        else:  # Daily
            # For daily, 6 months ≈ 126 trading days
            lookback_periods = min(126, len(benchmark_data) - 20)
        
        if lookback_periods < 10:
            return None
        
        historical_results = []
        
        # Loop through historical dates
        for i in range(lookback_periods, 0, -1):
            try:
                analysis_date = benchmark_data.index[-i]
                
                # Analyze all sectors at this point in time
                period_results = []
                
                for sect_name, sect_data in sector_data_dict.items():
                    if sect_name == 'Nifty 50':  # Skip benchmark
                        continue
                    
                    # Get data up to this historical point
                    subset_data = sect_data.iloc[:-i] if i > 0 else sect_data
                    bench_subset = benchmark_data.iloc[:-i] if i > 0 else benchmark_data
                    
                    if len(subset_data) < 50:  # Need sufficient history
                        continue
                    
                    # Calculate indicators
                    from indicators import calculate_rsi, calculate_adx, calculate_z_score
                    
                    rsi = calculate_rsi(subset_data)
                    adx, plus_di, minus_di, di_spread = calculate_adx(subset_data)
                    adx_z = calculate_z_score(adx.dropna())
                    
                    # Calculate RS Rating
                    if bench_subset is not None and len(bench_subset) > 0:
                        sector_returns = subset_data['Close'].pct_change().dropna()
                        benchmark_returns = bench_subset['Close'].pct_change().dropna()
                        
                        common_index = sector_returns.index.intersection(benchmark_returns.index)
                        if len(common_index) > 1:
                            sector_returns_aligned = sector_returns.loc[common_index]
                            benchmark_returns_aligned = benchmark_returns.loc[common_index]
                            
                            sector_cumret = (1 + sector_returns_aligned).prod() - 1
                            benchmark_cumret = (1 + benchmark_returns_aligned).prod() - 1
                            
                            if not pd.isna(sector_cumret) and not pd.isna(benchmark_cumret):
                                relative_perf = sector_cumret - benchmark_cumret
                                rs_rating = 5 + (relative_perf * 25)
                                rs_rating = max(0, min(10, rs_rating))
                            else:
                                rs_rating = 5.0
                        else:
                            rs_rating = 5.0
                    else:
                        rs_rating = 5.0
                    
                    period_results.append({
                        'Sector': sect_name,
                        'ADX_Z': adx_z if not pd.isna(adx_z) else 0,
                        'RS_Rating': rs_rating,
                        'RSI': rsi.iloc[-1] if not rsi.isna().all() else 50,
                        'DI_Spread': di_spread.iloc[-1] if not di_spread.isna().all() else 0,
                        'Price': subset_data['Close'].iloc[-1]
                    })
                
                if not period_results or len(period_results) < 2:
                    continue
                
                # Create DataFrame and rank
                period_df = pd.DataFrame(period_results)
                num_sectors = len(period_df)
                
                # Calculate ranks: Higher values = better = rank 1 (ascending=False)
                period_df['ADX_Z_Rank'] = period_df['ADX_Z'].rank(ascending=False, method='min')
                period_df['RS_Rating_Rank'] = period_df['RS_Rating'].rank(ascending=False, method='min')
                period_df['RSI_Rank'] = period_df['RSI'].rank(ascending=False, method='min')
                period_df['DI_Spread_Rank'] = period_df['DI_Spread'].rank(ascending=False, method='min')
                
                # Calculate weighted average rank (lower = better)
                total_weight = sum(momentum_weights.values())
                period_df['Weighted_Avg_Rank'] = (
                    (period_df['ADX_Z_Rank'] * momentum_weights.get('ADX_Z', 20) / total_weight) +
                    (period_df['RS_Rating_Rank'] * momentum_weights.get('RS_Rating', 40) / total_weight) +
                    (period_df['RSI_Rank'] * momentum_weights.get('RSI', 30) / total_weight) +
                    (period_df['DI_Spread_Rank'] * momentum_weights.get('DI_Spread', 10) / total_weight)
                )
                
                # Scale to 1-10 where 10 = best momentum, 1 = worst
                if num_sectors > 1:
                    min_rank = period_df['Weighted_Avg_Rank'].min()
                    max_rank = period_df['Weighted_Avg_Rank'].max()
                    if max_rank > min_rank:
                        period_df['Momentum_Score'] = 10 - ((period_df['Weighted_Avg_Rank'] - min_rank) / (max_rank - min_rank)) * 9
                    else:
                        period_df['Momentum_Score'] = 5.0
                else:
                    period_df['Momentum_Score'] = 5.0
                
                # Get top 2 by momentum score (higher score = better)
                period_df = period_df.sort_values('Momentum_Score', ascending=False)
                top_2 = period_df.head(2)
                
                if len(top_2) < 2:
                    continue
                
                # Calculate forward returns (7-day and 14-day)
                rank_1_sector = top_2.iloc[0]['Sector']
                rank_2_sector = top_2.iloc[1]['Sector']
                
                # Get forward price data
                rank_1_data = sector_data_dict[rank_1_sector]
                rank_2_data = sector_data_dict[rank_2_sector]
                
                # Find current price index
                current_idx = len(rank_1_data) - i
                
                # Calculate returns
                def calc_forward_return(data, current_idx, forward_periods):
                    if current_idx + forward_periods < len(data):
                        current_price = data.iloc[current_idx]['Close']
                        future_price = data.iloc[current_idx + forward_periods]['Close']
                        return ((future_price - current_price) / current_price) * 100
                    return None
                
                rank_1_7day = calc_forward_return(rank_1_data, current_idx, 7)
                rank_1_14day = calc_forward_return(rank_1_data, current_idx, 14)
                rank_2_7day = calc_forward_return(rank_2_data, current_idx, 7)
                rank_2_14day = calc_forward_return(rank_2_data, current_idx, 14)
                
                # Get symbols
                from config import SECTORS, SECTOR_ETFS
                data_source = SECTOR_ETFS if use_etf else SECTORS
                
                historical_results.append({
                    'Date': analysis_date.strftime('%Y-%m-%d'),
                    'Rank_1_Sector': rank_1_sector,
                    'Rank_1_Symbol': data_source.get(rank_1_sector, 'N/A'),
                    'Rank_1_7Day_Return_%': round(rank_1_7day, 2) if rank_1_7day is not None else 'N/A',
                    'Rank_1_14Day_Return_%': round(rank_1_14day, 2) if rank_1_14day is not None else 'N/A',
                    'Rank_2_Sector': rank_2_sector,
                    'Rank_2_Symbol': data_source.get(rank_2_sector, 'N/A'),
                    'Rank_2_7Day_Return_%': round(rank_2_7day, 2) if rank_2_7day is not None else 'N/A',
                    'Rank_2_14Day_Return_%': round(rank_2_14day, 2) if rank_2_14day is not None else 'N/A'
                })
                
            except Exception as e:
                continue
        
        if not historical_results:
            return None
        
        return pd.DataFrame(historical_results)
        
    except Exception as e:
        st.warning(f"⚠️ Error calculating historical performance: {str(e)}")
        return None


def calculate_historical_reversal_performance(sector_data_dict, benchmark_data, reversal_weights, reversal_thresholds, use_etf, interval='1d', months=6):
    """
    Calculate historical top 2 reversal candidates over the past N months.
    Shows only sector names (no return tracking).
    
    Args:
        sector_data_dict: Dictionary of sector name to data DataFrame
        benchmark_data: Benchmark data DataFrame
        reversal_weights: Dict with reversal score weights
        reversal_thresholds: Dict with RSI and ADX_Z thresholds
        use_etf: Whether using ETF or Index data
        interval: Data interval ('1d', '1wk', '1h')
        months: Number of months to look back (default 6)
    
    Returns:
        DataFrame with date and top 2 reversal candidates
    """
    try:
        from datetime import timedelta
        import pandas as pd
        
        # Determine lookback period based on interval
        if interval == '1wk':
            # For weekly, approximate 6 months = 26 weeks
            lookback_periods = min(26, len(benchmark_data) - 20)
        elif interval == '1h':
            # For hourly, limited history, use what's available
            lookback_periods = min(len(benchmark_data) - 20, 500)
        else:  # Daily
            # For daily, 6 months ≈ 126 trading days
            lookback_periods = min(126, len(benchmark_data) - 20)
        
        if lookback_periods < 10:
            return None
        
        historical_results = []
        
        # Loop through historical dates
        for i in range(lookback_periods, 0, -1):
            try:
                analysis_date = benchmark_data.index[-i]
                
                # Analyze all sectors at this point in time
                period_results = []
                
                for sect_name, sect_data in sector_data_dict.items():
                    if sect_name == 'Nifty 50':  # Skip benchmark
                        continue
                    
                    # Get data up to this historical point
                    subset_data = sect_data.iloc[:-i] if i > 0 else sect_data
                    bench_subset = benchmark_data.iloc[:-i] if i > 0 else benchmark_data
                    
                    if len(subset_data) < 50:  # Need sufficient history
                        continue
                    
                    # Calculate indicators
                    from indicators import calculate_rsi, calculate_adx, calculate_z_score, calculate_mansfield_rs
                    
                    rsi = calculate_rsi(subset_data)
                    adx, plus_di, minus_di, di_spread = calculate_adx(subset_data)
                    adx_z = calculate_z_score(adx.dropna())
                    cmf = calculate_cmf(subset_data)
                    mansfield_rs = calculate_mansfield_rs(subset_data, bench_subset)
                    
                    # Calculate RS Rating
                    if bench_subset is not None and len(bench_subset) > 0:
                        sector_returns = subset_data['Close'].pct_change().dropna()
                        benchmark_returns = bench_subset['Close'].pct_change().dropna()
                        
                        common_index = sector_returns.index.intersection(benchmark_returns.index)
                        if len(common_index) > 1:
                            sector_returns_aligned = sector_returns.loc[common_index]
                            benchmark_returns_aligned = benchmark_returns.loc[common_index]
                            
                            sector_cumret = (1 + sector_returns_aligned).prod() - 1
                            benchmark_cumret = (1 + benchmark_returns_aligned).prod() - 1
                            
                            if not pd.isna(sector_cumret) and not pd.isna(benchmark_cumret):
                                relative_perf = sector_cumret - benchmark_cumret
                                rs_rating = 5 + (relative_perf * 25)
                                rs_rating = max(0, min(10, rs_rating))
                            else:
                                rs_rating = 5.0
                        else:
                            rs_rating = 5.0
                    else:
                        rs_rating = 5.0
                    
                    # Get final values
                    rsi_val = rsi.iloc[-1] if not rsi.isna().all() else 50
                    adx_z_val = adx_z if not pd.isna(adx_z) else 0
                    cmf_val = cmf.iloc[-1] if not cmf.isna().all() else 0
                    
                    # Check reversal eligibility
                    meets_rsi = rsi_val < reversal_thresholds.get('RSI', 40)
                    meets_adx_z = adx_z_val < reversal_thresholds.get('ADX_Z', -0.5)
                    
                    period_results.append({
                        'Sector': sect_name,
                        'RSI': rsi_val,
                        'ADX_Z': adx_z_val,
                        'CMF': cmf_val,
                        'RS_Rating': rs_rating,
                        'Mansfield_RS': mansfield_rs,
                        'Meets_RSI': meets_rsi,
                        'Meets_ADX_Z': meets_adx_z,
                        'Eligible': meets_rsi and meets_adx_z
                    })
                
                if not period_results:
                    continue
                
                # Create DataFrame
                period_df = pd.DataFrame(period_results)
                
                # Filter to eligible reversals only
                eligible_reversals = period_df[period_df['Eligible']].copy()
                
                if len(eligible_reversals) > 0:
                    # Calculate ranks within eligible sectors
                    eligible_reversals['RS_Rating_Rank'] = eligible_reversals['RS_Rating'].rank(ascending=True, method='min')
                    eligible_reversals['CMF_Rank'] = eligible_reversals['CMF'].rank(ascending=False, method='min')
                    eligible_reversals['RSI_Rank'] = eligible_reversals['RSI'].rank(ascending=True, method='min')
                    eligible_reversals['ADX_Z_Rank'] = eligible_reversals['ADX_Z'].rank(ascending=True, method='min')
                    
                    # Calculate reversal score with percentage weights
                    total_weight = sum(reversal_weights.values())
                    eligible_reversals['Reversal_Score'] = (
                        (eligible_reversals['RS_Rating_Rank'] * reversal_weights.get('RS_Rating', 40) / total_weight * 100) +
                        (eligible_reversals['CMF_Rank'] * reversal_weights.get('CMF', 40) / total_weight * 100) +
                        (eligible_reversals['RSI_Rank'] * reversal_weights.get('RSI', 10) / total_weight * 100) +
                        (eligible_reversals['ADX_Z_Rank'] * reversal_weights.get('ADX_Z', 10) / total_weight * 100)
                    )
                    
                    # Get top 2 reversals
                    top_2_reversals = eligible_reversals.nlargest(2, 'Reversal_Score')
                    
                    if len(top_2_reversals) > 0:
                        # Get symbols
                        from config import SECTORS, SECTOR_ETFS
                        data_source = SECTOR_ETFS if use_etf else SECTORS
                        
                        rank_1_sector = top_2_reversals.iloc[0]['Sector'] if len(top_2_reversals) >= 1 else 'N/A'
                        rank_1_symbol = data_source.get(rank_1_sector, 'N/A') if rank_1_sector != 'N/A' else 'N/A'
                        
                        rank_2_sector = top_2_reversals.iloc[1]['Sector'] if len(top_2_reversals) >= 2 else 'N/A'
                        rank_2_symbol = data_source.get(rank_2_sector, 'N/A') if rank_2_sector != 'N/A' else 'N/A'
                        
                        historical_results.append({
                            'Date': analysis_date.strftime('%Y-%m-%d'),
                            'Rank_1_Sector': rank_1_sector,
                            'Rank_1_Symbol': rank_1_symbol,
                            'Rank_2_Sector': rank_2_sector,
                            'Rank_2_Symbol': rank_2_symbol
                        })
                
            except Exception as e:
                continue
        
        if not historical_results:
            return None
        
        return pd.DataFrame(historical_results)
        
    except Exception as e:
        st.warning(f"⚠️ Error calculating historical reversal performance: {str(e)}")
        return None


def display_momentum_tab(df, sector_data_dict, benchmark_data, enable_color_coding=True):
    """Display momentum ranking tab with improved formatting."""
    st.markdown("### 📈 Momentum Ranking (Sorted by Momentum Score)")
    st.markdown("---")
    
    # Store original df for reference in trend analysis
    original_df = df.copy()
    
    # Select columns for display
    momentum_df = df[['Sector', 'Symbol', 'Price', 'Change_%', 'Momentum_Score', 'Mansfield_RS', 'RS_Rating', 
                      'ADX', 'ADX_Z', 'RSI', 'DI_Spread', 'CMF']].copy()
    
    # SORT FIRST by Momentum_Score (before formatting to strings)
    momentum_df = momentum_df.sort_values('Momentum_Score', ascending=False)
    
    # Format decimal places AFTER sorting
    for col in ['Momentum_Score', 'Mansfield_RS', 'RS_Rating', 'ADX', 'ADX_Z', 'RSI', 'DI_Spread']:
        momentum_df[col] = momentum_df[col].apply(lambda x: format_value(x, 1))
    momentum_df['CMF'] = momentum_df['CMF'].apply(lambda x: format_value(x, 2))
    momentum_df['Price'] = momentum_df['Price'].apply(lambda x: format_value(x, 2))
    momentum_df['Change_%'] = momentum_df['Change_%'].apply(lambda x: f"{format_value(x, 2)}%")
    
    # Apply color styling if enabled
    if enable_color_coding:
        def style_row(row):
            result = [''] * len(row)
            
            # Color Mansfield RS (green for positive, red for negative)
            if 'Mansfield_RS' in row.index:
                idx = list(row.index).index('Mansfield_RS')
                try:
                    if float(row['Mansfield_RS']) > 0:
                        result[idx] = 'background-color: #27AE60; color: #fff; font-weight: bold'
                    else:
                        result[idx] = 'background-color: #E74C3C; color: #fff; font-weight: bold'
                except:
                    pass
            
            # Color CMF (green for positive, red for negative)
            if 'CMF' in row.index:
                idx = list(row.index).index('CMF')
                try:
                    if float(row['CMF']) > 0:
                        result[idx] = 'background-color: #27AE60; color: #fff; font-weight: bold'
                    else:
                        result[idx] = 'background-color: #E74C3C; color: #fff; font-weight: bold'
                except:
                    pass
            
            # Color RSI (green for >65, red for <35, gray for neutral)
            if 'RSI' in row.index:
                idx = list(row.index).index('RSI')
                try:
                    rsi_val = float(row['RSI'])
                    if rsi_val > 65:
                        result[idx] = 'background-color: #27AE60; color: #fff; font-weight: bold'
                    elif rsi_val < 35:
                        result[idx] = 'background-color: #E74C3C; color: #fff; font-weight: bold'
                except:
                    pass
            
            # Color Momentum_Score (top 3 green, bottom 3 red)
            if 'Momentum_Score' in row.index:
                idx = list(row.index).index('Momentum_Score')
                try:
                    scores = pd.to_numeric(momentum_df['Momentum_Score'], errors='coerce')
                    top_3_threshold = scores.nlargest(3).min()
                    bottom_3_threshold = scores.nsmallest(3).max()
                    current_score = float(row['Momentum_Score'])
                    
                    if current_score >= top_3_threshold:
                        result[idx] = 'background-color: #27AE60; color: #fff; font-weight: bold'
                    elif current_score <= bottom_3_threshold:
                        result[idx] = 'background-color: #E74C3C; color: #fff; font-weight: bold'
                except:
                    pass
            
            return result
        
        momentum_df_styled = momentum_df.style.apply(style_row, axis=1)
    else:
        momentum_df_styled = momentum_df.style
    
    # Display the dataframe with sorting enabled (already sorted by Momentum_Score descending)
    st.dataframe(
        momentum_df_styled,
        use_container_width=True,
        height=500,
        hide_index=True,
        column_config={
            "Sector": st.column_config.TextColumn(
                "Sector",
                help="Market sector name"
            ),
            "Symbol": st.column_config.TextColumn(
                "Symbol",
                help="Index or ETF ticker symbol"
            ),
            "Price": st.column_config.NumberColumn(
                "Price",
                help="Current closing price",
                format="%.2f"
            ),
            "Change_%": st.column_config.TextColumn(
                "Change %",
                help="Percentage change vs previous close"
            ),
            "Momentum_Score": st.column_config.NumberColumn(
                "Momentum Score",
                help="Ranking-based composite score: (ADX_Z Rank × 20%) + (RS_Rating Rank × 40%) + (RSI Rank × 30%) + (DI_Spread Rank × 10%). Higher is better.",
                format="%.1f"
            ),
            "Mansfield_RS": st.column_config.NumberColumn(
                "Mansfield RS",
                help="Relative strength vs Nifty 50 benchmark. Positive = outperforming, Negative = underperforming.",
                format="%.1f"
            ),
            "RS_Rating": st.column_config.NumberColumn(
                "RS Rating",
                help="Relative strength rating (0-10 scale) based on weighted average performance vs Nifty 50",
                format="%.1f"
            ),
            "ADX": st.column_config.NumberColumn(
                "ADX",
                help="Average Directional Index - measures trend strength. >25 = strong trend, <20 = weak/no trend",
                format="%.1f"
            ),
            "ADX_Z": st.column_config.NumberColumn(
                "ADX Z-Score",
                help="ADX Z-Score - normalized ADX relative to other sectors. Higher values indicate stronger relative trend.",
                format="%.1f"
            ),
            "RSI": st.column_config.NumberColumn(
                "RSI",
                help="Relative Strength Index (14-period). >70 = overbought, <30 = oversold, 40-60 = neutral",
                format="%.1f"
            ),
            "DI_Spread": st.column_config.NumberColumn(
                "DI Spread",
                help="Directional Indicator Spread (+DI minus -DI). Positive = bullish, Negative = bearish",
                format="%.1f"
            ),
            "CMF": st.column_config.NumberColumn(
                "CMF",
                help="Chaikin Money Flow (20-period). >0 = accumulation, <0 = distribution, >0.1 = strong buying",
                format="%.2f"
            )
        }
    )
    
    # Key metrics summary with CMF sum total (2x2 matrix for better space usage)
    metric_col1, metric_col2 = st.columns(2)
    momentum_df_numeric = df[['Sector', 'Momentum_Score', 'Mansfield_RS', 'CMF']].copy()
    
    # Calculate super bullish threshold (top 30% of sectors)
    momentum_threshold = momentum_df_numeric['Momentum_Score'].quantile(MOMENTUM_SCORE_PERCENTILE_THRESHOLD / 100.0)
    
    with metric_col1:
        super_bullish = len(momentum_df_numeric[momentum_df_numeric['Momentum_Score'] >= momentum_threshold])
        st.metric("Top Momentum Sectors", super_bullish, 
                  help=f"Top {100-MOMENTUM_SCORE_PERCENTILE_THRESHOLD}% by Momentum Score (>= {momentum_threshold:.1f})")
    with metric_col2:
        positive_mansfield = len(momentum_df_numeric[momentum_df_numeric['Mansfield_RS'] > 0])
        st.metric("Positive Mansfield RS", positive_mansfield,
                  help="Outperforming vs Nifty 50")
    
    metric_col3, metric_col4 = st.columns(2)
    with metric_col3:
        avg_momentum = momentum_df_numeric['Momentum_Score'].mean()
        st.metric("Average Momentum", f"{avg_momentum:.1f}")
    with metric_col4:
        # CMF Sum Total - indicates overall sector rotation direction
        cmf_sum = momentum_df_numeric['CMF'].sum()
        cmf_delta = "↑ Net Inflow" if cmf_sum > 0 else "↓ Net Outflow"
        st.metric("CMF Sum (Sector Rotation)", f"{cmf_sum:.2f}", delta=cmf_delta,
                  help="Sum of all sector CMF values. Positive = net money flowing into sectors (bullish rotation), Negative = net money flowing out (bearish rotation). Value near 1 indicates clear sector rotation.")
    
    # Sector Trend Analysis
    st.markdown("---")
    st.markdown("### 📊 Sector Trend Analysis (T-7 to T)")
    
    # Find #1 ranked sector and set as default
    # The #1 sector is the one with the highest Momentum_Score
    sectors_list = sorted(df['Sector'].tolist())
    rank_1_sector = None
    rank_1_idx = 0
    
    # Get the sector with highest momentum score
    if not df.empty:
        # Create a copy and sort by Momentum_Score to find rank 1
        df_sorted = df.sort_values('Momentum_Score', ascending=False)
        rank_1_sector = df_sorted.iloc[0]['Sector']
        # Find the index in sectors_list for default selection
        if rank_1_sector in sectors_list:
            rank_1_idx = sectors_list.index(rank_1_sector)
    
    selected_sector = st.selectbox("Select a sector for trend view:", sectors_list, index=rank_1_idx)
    
    if selected_sector and selected_sector in sector_data_dict:
        with st.spinner(f"Calculating historical momentum rankings for {selected_sector}..."):
            trend_df = calculate_sector_trend(selected_sector, sector_data_dict[selected_sector], benchmark_data, sector_data_dict, periods=8)
        
        if trend_df is not None:
            st.markdown(f"#### Trend for **{selected_sector}**")
            
            # Display current rank and momentum score
            # Find the row that starts with 'T (' (the current period)
            current_row = trend_df[trend_df['Period'].str.startswith('T (')]
            if len(current_row) > 0:
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("Current Momentum Score", current_row['Momentum_Score'].iloc[0])
                with col_b:
                    st.metric("Current Rank", f"#{int(current_row['Rank'].iloc[0])}")
            
            # Add note about momentum score calculation
            st.caption("✅ **Note:** All Momentum Scores are actual rank-based values calculated by comparing all sectors at each historical period. This shows the true momentum evolution over time.")
            
            # Transpose for better view with color coding
            trend_display = trend_df.set_index('Period').T
            
            # Apply color styling to trend data
            def style_trend(val):
                """Apply mild green/red colors based on indicator values."""
                try:
                    num_val = float(val)
                    # Mansfield_RS: positive = green, negative = red
                    if 'Mansfield' in str(val):
                        if num_val > 0:
                            return 'background-color: #d4edda; color: #000'
                        elif num_val < 0:
                            return 'background-color: #f8d7da; color: #000'
                    # RSI: >65 = green, <35 = red (mild shades)
                    elif 'RSI' in str(val):
                        if num_val > 65:
                            return 'background-color: #d4edda; color: #000'
                        elif num_val < 35:
                            return 'background-color: #f8d7da; color: #000'
                    # ADX: >25 = green, <20 = red (mild shades)
                    elif 'ADX' in str(val) and 'ADX_Z' not in str(val):
                        if num_val > 25:
                            return 'background-color: #d4edda; color: #000'
                        elif num_val < 20:
                            return 'background-color: #f8d7da; color: #000'
                    # ADX_Z: >0 = green, <0 = red (mild shades)
                    elif 'ADX_Z' in str(val):
                        if num_val > 0:
                            return 'background-color: #d4edda; color: #000'
                        elif num_val < 0:
                            return 'background-color: #f8d7da; color: #000'
                    # DI_Spread: >0 = green, <0 = red (mild shades)
                    elif 'DI_Spread' in str(val):
                        if num_val > 0:
                            return 'background-color: #d4edda; color: #000'
                        elif num_val < 0:
                            return 'background-color: #f8d7da; color: #000'
                    # CMF: >0 = green, <0 = red (mild shades)
                    elif 'CMF' in str(val):
                        if num_val > 0:
                            return 'background-color: #d4edda; color: #000'
                        elif num_val < 0:
                            return 'background-color: #f8d7da; color: #000'
                except:
                    pass
                return ''
            
            # Add color code legend for sector trend analysis
            with st.expander("🎨 **Color Code Legend** - Bullish/Bearish Signals", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Green (Bullish Signals)**")
                    st.markdown("- **Mansfield_RS:** > 0 (sector outperforming benchmark)")
                    st.markdown("- **RS_Rating:** > 5 (strong relative strength)")
                    st.markdown("- **ADX:** > 25 (strong trend)")
                    st.markdown("- **ADX_Z:** > 0 (above average trend strength)")
                    st.markdown("- **DI_Spread:** > 0 (uptrend momentum)")
                    st.markdown("- **CMF:** > 0 (money inflow)")
                with col2:
                    st.markdown("**Red (Bearish Signals)**")
                    st.markdown("- **Mansfield_RS:** < 0 (sector underperforming)")
                    st.markdown("- **RS_Rating:** < 5 (weak relative strength)")
                    st.markdown("- **ADX:** < 20 (weak trend)")
                    st.markdown("- **ADX_Z:** < 0 (below average trend strength)")
                    st.markdown("- **DI_Spread:** < 0 (downtrend momentum)")
                    st.markdown("- **CMF:** < 0 (money outflow)")
                st.markdown("**Blue (Rank Row)**")
                st.markdown("- Shows sector's rank among all sectors at each historical period")
            
            trend_styled = trend_display.style.applymap(style_trend)
            st.dataframe(trend_styled, use_container_width=True, height=400)
            
            # Show momentum trend visualization
            if len(trend_df) > 1:
                st.markdown("##### Momentum Score Trend")
                try:
                    momentum_scores = [float(x) for x in trend_df['Momentum_Score'].tolist()]
                    periods = trend_df['Period'].tolist()
                    
                    import plotly.graph_objects as go
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=periods,
                        y=momentum_scores,
                        mode='lines+markers',
                        name='Momentum Score',
                        line=dict(color='#1f77b4', width=3),
                        marker=dict(size=8)
                    ))
                    fig.update_layout(
                        title=f"Momentum Score Evolution - {selected_sector}",
                        xaxis_title="Period",
                        yaxis_title="Momentum Score",
                        height=300,
                        template="plotly_white"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    pass  # Skip chart if error
        else:
            st.warning(f"Insufficient data to calculate trend for {selected_sector}")
    
    # Historical Top 2 Momentum Performance
    st.markdown("---")
    st.markdown("### 📊 Historical Top 2 Momentum Performance (6 Months)")
    st.markdown("See how the top 2 momentum-ranked sectors performed over the past 6 months with forward returns.")
    
    st.info("💡 **Note:** Historical rankings are recalculated point-in-time using data available on each date. "
            "Live analysis may differ slightly due to data updates. Use the '📅 Historical Rankings' tab for recent T-7 to T comparison.")
    
    if st.button("🔍 Generate Historical Performance Report"):
        with st.spinner("Analyzing 6 months of historical data..."):
            # Get interval from session state or default
            interval_map = {'Daily': '1d', 'Weekly': '1wk', 'Hourly': '1h'}
            # Try to get momentum weights from somewhere, or use defaults
            from config import DEFAULT_MOMENTUM_WEIGHTS
            
            # Determine if using ETF from the data
            use_etf = 'Symbol' in df.columns and any('.NS' not in str(s) for s in df['Symbol'].values)
            
            # Get current interval from the analysis
            current_interval = '1d'  # Default, will be passed from main
            
            historical_df = calculate_historical_momentum_performance(
                sector_data_dict, 
                benchmark_data, 
                DEFAULT_MOMENTUM_WEIGHTS,
                use_etf,
                current_interval,
                months=6
            )
        
        if historical_df is not None and not historical_df.empty:
            st.success(f"✅ Generated report for {len(historical_df)} historical dates")
            
            # Display summary statistics
            col1, col2, col3, col4 = st.columns(4)
            
            # Calculate average returns (excluding N/A values)
            def calc_avg(column):
                vals = [v for v in historical_df[column].values if v != 'N/A']
                return sum(vals) / len(vals) if vals else 0
            
            with col1:
                avg_r1_7d = calc_avg('Rank_1_7Day_Return_%')
                st.metric("Rank 1 Avg 7-Day Return", f"{avg_r1_7d:.2f}%")
            with col2:
                avg_r1_14d = calc_avg('Rank_1_14Day_Return_%')
                st.metric("Rank 1 Avg 14-Day Return", f"{avg_r1_14d:.2f}%")
            with col3:
                avg_r2_7d = calc_avg('Rank_2_7Day_Return_%')
                st.metric("Rank 2 Avg 7-Day Return", f"{avg_r2_7d:.2f}%")
            with col4:
                avg_r2_14d = calc_avg('Rank_2_14Day_Return_%')
                st.metric("Rank 2 Avg 14-Day Return", f"{avg_r2_14d:.2f}%")
            
            # Display the dataframe
            st.dataframe(historical_df, use_container_width=True, height=400)
            
            # Download button
            csv_historical = historical_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Historical Performance Report",
                data=csv_historical,
                file_name=f"historical_momentum_performance_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.warning("⚠️ Unable to generate historical report. Insufficient data available.")
    
    # Download button
    csv = momentum_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Momentum Data",
        data=csv,
        file_name=f"momentum_ranking_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )


def display_reversal_tab(df, sector_data_dict, benchmark_data, reversal_weights, reversal_thresholds, enable_color_coding=True):
    """Display reversal candidates tab with scoring and trend analysis."""
    st.markdown("### 🔄 Reversal Candidates (Bottom Fishing Opportunities)")
    st.markdown("---")
    
    # Select columns: include Price and Change % now
    reversal_df = df[['Sector', 'Price', 'Change_%', 'Reversal_Status', 'Reversal_Score', 'RS_Rating',
                      'CMF', 'RSI', 'ADX_Z', 'Mansfield_RS', 'Momentum_Score']].copy()
    
    # Filter FIRST (before formatting)
    reversal_candidates = reversal_df[reversal_df['Reversal_Status'] != 'No'].copy()
    
    if not reversal_candidates.empty:
        # SORT FIRST by Reversal_Score (before formatting to strings)
        reversal_candidates = reversal_candidates.sort_values('Reversal_Score', ascending=False)
        
        # Format decimal places AFTER sorting
        for col in ['Reversal_Score', 'RS_Rating', 'RSI', 'ADX_Z', 'Mansfield_RS', 'Momentum_Score']:
            reversal_candidates[col] = reversal_candidates[col].apply(lambda x: format_value(x, 1))
        reversal_candidates['CMF'] = reversal_candidates['CMF'].apply(lambda x: format_value(x, 2))
        reversal_candidates['Price'] = reversal_candidates['Price'].apply(lambda x: format_value(x, 2))
        reversal_candidates['Change_%'] = reversal_candidates['Change_%'].apply(lambda x: f"{format_value(x, 2)}%")
        
        # Apply color styling if enabled
        if enable_color_coding:
            def style_row(row):
                result = [''] * len(row)
                
                # Color Reversal_Status (green for BUY_DIV, yellow for Watch)
                if 'Reversal_Status' in row.index:
                    idx = list(row.index).index('Reversal_Status')
                    if row['Reversal_Status'] == 'BUY_DIV':
                        result[idx] = 'background-color: #27AE60; color: #fff; font-weight: bold'
                    elif row['Reversal_Status'] == 'Watch':
                        result[idx] = 'background-color: #F39C12; color: #fff; font-weight: bold'
                
                # Color Mansfield_RS (green for positive, red for negative)
                if 'Mansfield_RS' in row.index:
                    idx = list(row.index).index('Mansfield_RS')
                    try:
                        if float(row['Mansfield_RS']) > 0:
                            result[idx] = 'background-color: #27AE60; color: #fff; font-weight: bold'
                        else:
                            result[idx] = 'background-color: #E74C3C; color: #fff; font-weight: bold'
                    except:
                        pass
                
                # Color CMF (green for positive, red for negative)
                if 'CMF' in row.index:
                    idx = list(row.index).index('CMF')
                    try:
                        if float(row['CMF']) > 0:
                            result[idx] = 'background-color: #27AE60; color: #fff; font-weight: bold'
                        else:
                            result[idx] = 'background-color: #E74C3C; color: #fff; font-weight: bold'
                    except:
                        pass
                
                # Color RSI (green for <35, yellow for neutral, red for >65)
                if 'RSI' in row.index:
                    idx = list(row.index).index('RSI')
                    try:
                        rsi_val = float(row['RSI'])
                        if rsi_val < 35:
                            result[idx] = 'background-color: #27AE60; color: #fff; font-weight: bold'
                        elif rsi_val > 65:
                            result[idx] = 'background-color: #E74C3C; color: #fff; font-weight: bold'
                    except:
                        pass
                
                return result
            
            reversal_candidates_styled = reversal_candidates.style.apply(style_row, axis=1)
        else:
            reversal_candidates_styled = reversal_candidates.style
        
        st.dataframe(
            reversal_candidates_styled,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Sector": st.column_config.TextColumn(
                    "Sector",
                    help="Market sector name"
                ),
                "Reversal_Status": st.column_config.TextColumn(
                    "Status",
                    help="BUY_DIV = Strong buy divergence signal, Watch = Potential reversal zone"
                ),
                "Reversal_Score": st.column_config.NumberColumn(
                    "Reversal Score",
                    help="Rank-based score for reversal potential. Higher rank = stronger reversal candidate based on RS Rating, CMF, RSI, and ADX Z rankings among eligible sectors.",
                    format="%.1f"
                ),
                "RS_Rating": st.column_config.NumberColumn(
                    "RS Rating",
                    help="Relative strength rating (0-10 scale). Lower values indicate underperformance with recovery potential",
                    format="%.1f"
                ),
                "CMF": st.column_config.NumberColumn(
                    "CMF",
                    help="Chaikin Money Flow. Positive values indicate accumulation/buying pressure",
                    format="%.2f"
                ),
                "RSI": st.column_config.NumberColumn(
                    "RSI",
                    help="Relative Strength Index. Lower values indicate oversold conditions",
                    format="%.1f"
                ),
                "ADX_Z": st.column_config.NumberColumn(
                    "ADX Z-Score",
                    help="Negative values indicate weak trend, favorable for reversals",
                    format="%.1f"
                ),
                "Mansfield_RS": st.column_config.NumberColumn(
                    "Mansfield RS",
                    help="Negative values indicate underperformance with recovery potential",
                    format="%.1f"
                ),
                "Momentum_Score": st.column_config.NumberColumn(
                    "Momentum Score",
                    help="Current momentum score for reference",
                    format="%.1f"
                )
            }
        )
        
        # Summary metrics
        col1, col2 = st.columns(2)
        with col1:
            buy_div_count = len(reversal_candidates[reversal_candidates['Reversal_Status'] == 'BUY_DIV'])
            st.metric("BUY_DIV Signals", buy_div_count, help="Strong reversal signals")
        with col2:
            watch_count = len(reversal_candidates[reversal_candidates['Reversal_Status'] == 'Watch'])
            st.metric("Watch List", watch_count, help="Potential reversals")
        
        # Download button
        csv = reversal_candidates.to_csv(index=False)
        st.download_button(
            label="📥 Download Reversal Candidates",
            data=csv,
            file_name=f"reversal_candidates_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("ℹ️ No reversal candidates found at this time.")
    
    # Historical Top 2 Reversal Performance
    st.markdown("---")
    st.markdown("### 📊 Historical Top 2 Reversal Candidate Performance (6 Months)")
    st.markdown("See which sectors were identified as top reversal candidates over the past 6 months.")
    
    if st.button("🔍 Generate Historical Reversal Report", key="btn_historical_reversal"):
        with st.spinner("Analyzing 6 months of historical reversal data..."):
            # Get interval from session state or default
            interval_map = {'Daily': '1d', 'Weekly': '1wk', 'Hourly': '1h'}
            current_interval = '1d'  # Will be passed from main if available
            
            historical_reversal_df = calculate_historical_reversal_performance(
                sector_data_dict, 
                benchmark_data, 
                reversal_weights,
                reversal_thresholds,
                'Symbol' in df.columns and any('.NS' not in str(s) for s in df['Symbol'].values),
                current_interval,
                months=6
            )
        
        if historical_reversal_df is not None and not historical_reversal_df.empty:
            st.success(f"✅ Generated report for {len(historical_reversal_df)} historical dates")
            
            # Display the dataframe
            st.dataframe(
                historical_reversal_df,
                use_container_width=True,
                height=400,
                hide_index=True,
                column_config={
                    "Date": st.column_config.TextColumn(
                        "Date",
                        help="Analysis date"
                    ),
                    "Rank_1_Sector": st.column_config.TextColumn(
                        "Top Reversal #1",
                        help="Strongest reversal candidate on this date"
                    ),
                    "Rank_1_Symbol": st.column_config.TextColumn(
                        "Symbol #1",
                        help="Ticker symbol for top reversal candidate"
                    ),
                    "Rank_2_Sector": st.column_config.TextColumn(
                        "Top Reversal #2",
                        help="Second strongest reversal candidate on this date"
                    ),
                    "Rank_2_Symbol": st.column_config.TextColumn(
                        "Symbol #2",
                        help="Ticker symbol for second reversal candidate"
                    )
                }
            )
            
            # Download button
            csv_historical_reversal = historical_reversal_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Historical Top 2 Reversal Candidates (6 Months)",
                data=csv_historical_reversal,
                file_name=f"historical_reversal_candidates_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key="download_historical_reversal"
            )
        else:
            st.warning("⚠️ Unable to generate historical reversal report. Insufficient data available.")
    
    # Sector Trend Analysis for Reversals
    st.markdown("---")
    st.markdown("### 📊 Sector Trend Analysis - Reversal Metrics (T-7 to T)")
    
    sectors_list = sorted(df['Sector'].tolist())
    selected_reversal_sector = st.selectbox(
        "Select Sector for Reversal Trend Analysis",
        options=sectors_list,
        key="reversal_trend_sector"
    )
    
    if selected_reversal_sector and sector_data_dict and benchmark_data is not None and not benchmark_data.empty:
        sector_data_for_trend = sector_data_dict.get(selected_reversal_sector)
        
        if sector_data_for_trend is not None:
            with st.spinner(f"Calculating reversal trend for {selected_reversal_sector}..."):
                reversal_trend_df = calculate_reversal_trend(
                    selected_reversal_sector,
                    sector_data_for_trend,
                    benchmark_data,
                    sector_data_dict,
                    reversal_weights,
                    reversal_thresholds,
                    periods=8
                )
            
            if reversal_trend_df is not None and not reversal_trend_df.empty:
                st.markdown(f"**Historical Reversal Indicators for {selected_reversal_sector}**")
                st.caption("Shows how reversal metrics evolved over the last 8 periods. Score shown only when sector is eligible (passes RSI and ADX Z filters).")
                
                # Transpose the dataframe: periods as columns, parameters as rows
                reversal_trend_transposed = reversal_trend_df.set_index('Period').T
                reversal_trend_transposed.index.name = 'Metric'
                reversal_trend_transposed = reversal_trend_transposed.reset_index()
                
                # Apply color styling to reversal trend
                def style_reversal_trend(val):
                    """Apply mild green/red colors based on indicator values."""
                    try:
                        num_val = float(val)
                        # Mansfield_RS: positive = green, negative = red
                        if 'Mansfield' in str(val):
                            if num_val > 0:
                                return 'background-color: #d4edda; color: #000'
                            elif num_val < 0:
                                return 'background-color: #f8d7da; color: #000'
                        # RSI: <40 is good for reversal (green), else neutral
                        elif 'RSI' in str(val):
                            if num_val < 40:
                                return 'background-color: #d4edda; color: #000'
                            elif num_val > 50:
                                return 'background-color: #f8d7da; color: #000'
                        # ADX: >20 = green (strong trend), <15 = red
                        elif 'ADX' in str(val) and 'ADX_Z' not in str(val):
                            if num_val > 20:
                                return 'background-color: #d4edda; color: #000'
                            elif num_val < 15:
                                return 'background-color: #f8d7da; color: #000'
                        # ADX_Z: >-0.5 = better for reversal (green)
                        elif 'ADX_Z' in str(val):
                            if num_val > -0.5:
                                return 'background-color: #d4edda; color: #000'
                            elif num_val < -1.0:
                                return 'background-color: #f8d7da; color: #000'
                        # CMF: >0.1 = green (strong buying)
                        elif 'CMF' in str(val):
                            if num_val > 0.1:
                                return 'background-color: #d4edda; color: #000'
                            elif num_val < 0:
                                return 'background-color: #f8d7da; color: #000'
                    except:
                        pass
                    return ''
                
                # Add color code legend for reversal trend analysis
                with st.expander("🎨 **Color Code Legend** - Reversal Signals", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Green (Good for Reversal)**")
                        st.markdown("- **RS_Rating:** < 5 (weak relative strength)")
                        st.markdown("- **CMF:** > 0.1 (money inflow)")
                        st.markdown("- **ADX_Z:** > -0.5 (weak trend)")
                        st.markdown("- **ADX:** < 20 (no strong trend)")
                    with col2:
                        st.markdown("**Red (Bad for Reversal)**")
                        st.markdown("- **RS_Rating:** > 5 (strong momentum)")
                        st.markdown("- **CMF:** < 0 (money outflow)")
                        st.markdown("- **ADX_Z:** < -1.0 (strong downtrend)")
                        st.markdown("- **ADX:** > 20 (strong trend momentum)")
                    st.markdown("**Blue (Rank Row)**")
                    st.markdown("- Shows sector's reversal rank at each historical period")
                
                reversal_styled = reversal_trend_transposed.style.applymap(style_reversal_trend)
                st.dataframe(
                    reversal_styled,
                    use_container_width=True,
                    hide_index=True
                )
                
                # Download button for reversal trend
                reversal_trend_csv = reversal_trend_df.to_csv(index=False)
                st.download_button(
                    label=f"📥 Download {selected_reversal_sector} Reversal Trend",
                    data=reversal_trend_csv,
                    file_name=f"reversal_trend_{selected_reversal_sector}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    key="download_reversal_trend"
                )
            else:
                st.info(f"ℹ️ Unable to calculate reversal trend for {selected_reversal_sector}. Insufficient data.")
        else:
            st.warning(f"⚠️ No data available for {selected_reversal_sector}")
    
    # Show all sectors with reversal scores (regardless of filters)
    st.markdown("---")
    st.markdown("#### All Sectors - Reversal Scores")
    st.caption("Note: Shows all sectors including those not meeting reversal filters. Reversal_Score = 0 means ineligible.")
    # Use original df to show ALL sectors
    all_reversal = df[['Sector', 'Reversal_Status', 'Reversal_Score', 'RS_Rating',
                       'CMF', 'RSI', 'ADX_Z', 'Mansfield_RS', 'Momentum_Score']].copy()
    
    # Format decimal places
    for col in ['Reversal_Score', 'RS_Rating', 'RSI', 'ADX_Z', 'Mansfield_RS', 'Momentum_Score']:
        all_reversal[col] = all_reversal[col].apply(lambda x: format_value(x, 1))
    all_reversal['CMF'] = all_reversal['CMF'].apply(lambda x: format_value(x, 2))
    
    all_reversal = all_reversal.sort_values('Reversal_Score', ascending=False)
    
    def color_reversal_mansfield(val):
        try:
            if float(val) > 0:
                return 'background-color: #27AE60; color: #fff; font-weight: bold'  # Green
            else:
                return 'background-color: #E67E22; color: #fff; font-weight: bold'  # Orange
        except:
            return ''
    
    st.dataframe(
        all_reversal,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Reversal_Score": st.column_config.NumberColumn(
                "Reversal_Score",
                format="%.1f"
            ),
            "CMF": st.column_config.NumberColumn(
                "CMF",
                format="%.2f"
            )
        }
    )


def display_interpretation_tab():
    """Display interpretation guide tab."""
    st.markdown("### 📊 Interpretation Guide")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        #### Momentum Score
        **Formula:** Ranking-based composite score
        ```
        (ADX_Z Rank × 20%) + 
        (RS_Rating Rank × 40%) + 
        (RSI Rank × 30%) + 
        (DI_Spread Rank × 10%)
        ```
        
        - Sectors are ranked on each indicator (1 = lowest, N = highest)
        - Higher ranks get higher scores
        - Weights sum to 100% and are configurable
        - **Higher Score** = Stronger momentum across all indicators
        - Look for scores in top 3-5 sectors for best momentum
        
        **Note:** Sectors with negative Mansfield RS may still have positive 
        momentum scores but should be watched carefully.
        
        #### Mansfield Relative Strength
        **Formula:** `((RS_Ratio / RS_Ratio_MA) - 1) × 10`
        
        - 🟢 **> 0**: Outperforming Nifty 50
        - 🔴 **< 0**: Underperforming Nifty 50
        - Based on 52-week (250-day) moving average
        
        #### Reversal Score
        Weighted combination of:
        - RSI (lower = higher potential)
        - ADX Z-Score (negative = weak trend)
        - CMF (positive = accumulation)
        - Mansfield RS (negative = recovery potential)
        """)
    
    with col2:
        st.markdown("""
        #### Reversal Status
        **⚠️ For Reversal Candidates (Bottom Fishing):**
        
        Look for sectors showing:
        - **BUY_DIV** = Strong buy divergence (Best)
          - RSI < 40 (oversold)
          - ADX Z-Score < -0.5 (weak trend)
          - CMF > 0.1 (money flowing in)
          - Signs of accumulation at bottom
        
        - **Watch** = Potential reversal zone
          - RSI < 50
          - ADX Z-Score < 0.5
          - CMF > 0 (positive money flow)
          - Monitor for entry opportunity
        
        **Note:** Reversal candidates are high-risk, high-reward opportunities. 
        Always validate with price action and volume before entering.
        
        #### Technical Indicators
        
        **RSI (Relative Strength Index) - TradingView Method**
        - Uses Wilder's smoothing (14-period)
        - > 70: Overbought
        - < 30: Oversold
        - 40-60: Neutral zone
        
        **ADX (Average Directional Index)**
        - > 25: Strong trend
        - < 20: Weak/no trend
        - Z-Score: Relative strength vs other sectors
        
        **CMF (Chaikin Money Flow)**
        - > 0: Money flowing in
        - < 0: Money flowing out
        - > 0.1: Strong accumulation
        
        **RS Rating**
        - 0-10 scale vs Nifty 50
        - > 7: Strong outperformer
        - < 3: Underperformer
        """)
    
    st.markdown("---")
    st.caption(f"⏰ Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


@st.cache_data(ttl=3600)
def test_symbol_availability():
    """Test connectivity for all symbols at page load."""
    import yfinance as yf
    from datetime import datetime, timedelta
    
    results = {}
    
    # Add Nifty 50 benchmark
    all_symbols = {'Nifty 50': '^NSEI'}
    all_symbols.update(SECTORS)
    all_symbols.update({f"{k}_ETF": v for k, v in SECTOR_ETFS.items()})
    all_symbols.update({f"{k}_ALT_ETF": v for k, v in SECTOR_ETFS_ALTERNATE.items()})
    
    test_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
    
    for sector, symbol in all_symbols.items():
        try:
            data = yf.download(symbol, start=test_date, end=datetime.now().strftime('%Y-%m-%d'), 
                              progress=False, interval='1d')
            
            if data is not None and len(data) > 0:
                results[sector] = {'status': '✅', 'bars': len(data)}
            else:
                results[sector] = {'status': '❌', 'bars': 0}
        except:
            results[sector] = {'status': '❌', 'bars': 0}
    
    return results


def display_historical_rankings_tab(sector_data_dict, benchmark_data, momentum_weights, reversal_weights, reversal_thresholds, use_etf):
    """
    Display historical rankings.
    
    Primary content: date-wise table for the last 15 trading days with:
    - Market breadth: Advance/Total %
    - Stocks % above 10 DMA (Nifty 50)
    - Momentum Ranked #1 Sector
    - Bullish Stock #1 and #2 (sectors) with next 1-day and 2-day returns
    
    Secondary content: existing Momentum and Reversal evolution sub-tabs (T-7 to T).
    """
    st.markdown("### 📅 Historical Rankings (Last 30 Trading Days)")
    st.markdown("---")
    
    if sector_data_dict is None or benchmark_data is None:
        st.error("❌ No data available for historical analysis")
        return
    
    from indicators import calculate_rsi, calculate_adx, calculate_z_score, calculate_cmf, calculate_mansfield_rs
    from company_symbols import SECTOR_COMPANIES
    from confluence_fixed import _GATE_FAIL_SCORE

    def _is_trending_mode(mw):
        return (mw.get('CMF', 0) != 0 and mw.get('RSI', 0) != 0 and
                mw.get('ADX_Z', 0) == 0 and mw.get('RS_Rating', 0) == 0 and mw.get('DI_Spread', 0) == 0)
    
    # --- Confluence timeframe selector (must match Part 3: 1D+2H or 4H+1H) ---
    # Synced with Part 3 via session_state (unique key to avoid duplicate widget key across tabs)
    hist_conf_tf = st.radio(
        "Confluence timeframe (synced with Part 3):",
        ["1D + 2H", "4H + 1H (default)"],
        horizontal=True,
        index=st.session_state.get("_conf_tf_idx", 1),
        key="hist_conf_timeframe",
    )
    st.session_state["_conf_tf_idx"] = ["1D + 2H", "4H + 1H (default)"].index(hist_conf_tf)
    hist_conf_tf_code  = '2h' if "1D + 2H" in hist_conf_tf else '4h'
    hist_conf_tf_label = "1D + 2H" if "1D + 2H" in hist_conf_tf else "4H + 1H"

    # Synced with Part 3 via session_state (unique key to avoid duplicate widget key across tabs)
    hist_conf_sector_filter = st.radio(
        "Confluence sector universe (synced with Part 3):",
        options=["Top 4 + Bottom 6 (per Momentum Ranking)", "Universal (All Sectors)"],
        index=st.session_state.get("_conf_sector_idx", 0),
        key="hist_conf_sector_filter",
    )
    st.session_state["_conf_sector_idx"] = [
        "Top 4 + Bottom 6 (per Momentum Ranking)",
        "Universal (All Sectors)",
    ].index(hist_conf_sector_filter)

    top_hist_conf_sectors  = None
    bot_hist_conf_sectors  = None

    if sector_data_dict and momentum_weights:
        try:
            from confluence_fixed import get_bottom_n_sectors_by_momentum
            if hist_conf_sector_filter == "Top 4 + Bottom 6 (per Momentum Ranking)":
                top_hist_conf_sectors = get_top_n_sectors_by_momentum(sector_data_dict, momentum_weights, n=4)
                bot_hist_conf_sectors = get_bottom_n_sectors_by_momentum(sector_data_dict, momentum_weights, n=6)
                if top_hist_conf_sectors:
                    st.success(f"**Bullish (current date, top 4):** {', '.join(top_hist_conf_sectors)}")
                if bot_hist_conf_sectors:
                    st.warning(f"**Bearish (current date, bottom 6):** {', '.join(bot_hist_conf_sectors)}")
        except Exception:
            pass
    st.caption("**Confluence pertains to top 4 sectors (bullish) and bottom 6 sectors (bearish) per Momentum Ranking for that date.** Table rows are computed **per date** from the same Momentum Ranking (ADX, RS Rating, RSI, DI Spread) as the Momentum tab.")

    if hist_conf_sector_filter == "Top 4 + Bottom 6 (per Momentum Ranking)":
        hist_conf_sector_code = 'top4_bot6'
    else:
        hist_conf_sector_code = 'universal'

    # --- Primary content: date-wise table (last 30 days for confluence) ---
    st.markdown("#### 📋 Primary: Date-wise summary (MA+RSI+VWAP) – last 30 trading days")
    st.caption("Scoring: MA+RSI+VWAP (1 pt each RSI 1W/1D/1H up, 1 pt each Price > 8/20/50 SMA, + VWAP). Last 30 days; Next 1D/2D/3D/1W % may be blank for latest rows.")
    NIFTY50_SYMBOLS = [
        'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS',
        'SBIN.NS', 'BHARTIARTL.NS', 'HINDUNILVR.NS', 'ITC.NS', 'KOTAKBANK.NS',
        'LT.NS', 'AXISBANK.NS', 'ASIANPAINT.NS', 'MARUTI.NS', 'TITAN.NS',
        'NESTLEIND.NS', 'ULTRACEMCO.NS', 'WIPRO.NS', 'SUNPHARMA.NS', 'TATAMOTORS.NS',
        'TECHM.NS', 'HCLTECH.NS', 'BAJFINANCE.NS', 'JSWSTEEL.NS', 'TATASTEEL.NS',
        'POWERGRID.NS', 'NTPC.NS', 'ONGC.NS', 'COALINDIA.NS', 'ADANIENT.NS',
        'ADANIPORTS.NS', 'GRASIM.NS', 'DIVISLAB.NS', 'CIPLA.NS', 'DRREDDY.NS',
        'BAJAJFINSV.NS', 'M&M.NS', 'HEROMOTOCO.NS', 'EICHERMOT.NS', 'MARICO.NS',
        'GODREJCP.NS', 'DABUR.NS', 'BRITANNIA.NS', 'HDFCLIFE.NS', 'SBILIFE.NS',
        'ICICIPRULI.NS', 'HDFCAMC.NS', 'BAJAJ-AUTO.NS', 'INDUSINDBK.NS', 'APOLLOHOSP.NS'
    ]
    
    # Need a reasonable history window for the 30-day table
    if len(benchmark_data) < 31:
        st.warning("⚠️ Need at least 31 trading days of data for the 30-day table.")
    else:
        # Use last 30 trading days for confluence historical view
        lookback_days = min(30, len(benchmark_data))
        dates_10 = benchmark_data.index[-lookback_days:].tolist()
        table_rows = []

        # Load historical rankings cache (CSV) so we only compute missing dates
        cache_dir = 'data_cache'
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(cache_dir, f'historical_rankings_cache_v11_{hist_conf_tf_code}_{hist_conf_sector_code}.csv')
        cache_by_date = {}
        if os.path.isfile(cache_path):
            try:
                df_cache = pd.read_csv(cache_path)
                if len(df_cache) > 0 and 'Bullish #1 Stock' in df_cache.columns:
                    for _, r in df_cache.iterrows():
                        d = r.to_dict()
                        if 'Date' in d and pd.notna(d.get('Date')):
                            cache_by_date[str(d['Date']).strip()] = d
            except Exception:
                pass

        with st.spinner("Building 30-day historical table (Advance/Total %, sectors, bullish/bearish stocks)..."):
            progress_bar = st.progress(0)
            status_text = st.empty()

            # 1) Nifty 50 advance/decline: fetch in parallel
            end_dt = benchmark_data.index[-1]
            nifty_symbols_dict = {s: s for s in NIFTY50_SYMBOLS[:50]}
            nifty_fetched, _ = fetch_all_sectors_parallel(nifty_symbols_dict, end_date=end_dt, interval='1d')
            nifty_closes = {sym: d['Close'] for sym, d in nifty_fetched.items() if d is not None and len(d) >= 2}
            
            # 2) All companies: fetch in parallel (same universe as Stock Screener)
            all_companies = []
            for sector, syms in SECTOR_COMPANIES.items():
                for sym, info in syms.items():
                    all_companies.append((sector, sym, info.get('name', sym)))
            
            company_symbols_dict = {sym: sym for _, sym, _ in all_companies}
            company_fetched, _ = fetch_all_sectors_parallel(company_symbols_dict, end_date=end_dt, interval='1d')
            company_data = {}
            for sector, sym, name in all_companies:
                d = company_fetched.get(sym)
                if d is not None and len(d) >= 14:
                    company_data[sym] = {'sector': sector, 'name': name, 'data': d}
            
            # Confluence-only keys (cleared when no confluence data; breadth columns stay in row)
            _CONF_COLS_ALL = [
                'Conf Bull #1', 'Conf Bull #1 Sector', 'Conf Bull #1 CMP', 'Conf Bull #1 Dir', 'Conf Bull #1 Score',
                'Conf Bull #1 1D %', 'Conf Bull #1 2D %', 'Conf Bull #1 3D %', 'Conf Bull #1 1W %',
                'Conf Bull #2', 'Conf Bull #2 Sector', 'Conf Bull #2 CMP', 'Conf Bull #2 Dir', 'Conf Bull #2 Score',
                'Conf Bull #2 1D %', 'Conf Bull #2 2D %', 'Conf Bull #2 3D %', 'Conf Bull #2 1W %',
                'Conf Bear #1', 'Conf Bear #1 Sector', 'Conf Bear #1 CMP', 'Conf Bear #1 Dir', 'Conf Bear #1 Score',
                'Conf Bear #1 1D %', 'Conf Bear #1 2D %', 'Conf Bear #1 3D %', 'Conf Bear #1 1W %',
                'Conf Bear #2', 'Conf Bear #2 Sector', 'Conf Bear #2 CMP', 'Conf Bear #2 Dir', 'Conf Bear #2 Score',
                'Conf Bear #2 1D %', 'Conf Bear #2 2D %', 'Conf Bear #2 3D %', 'Conf Bear #2 1W %',
            ]

            total_dates = len(dates_10)
            for di, date_t in enumerate(dates_10):
                progress_bar.progress((di + 1) / total_dates)
                date_str = date_t.strftime('%Y-%m-%d')
                status_text.text(f"Processing date {date_str} ({di + 1}/{total_dates})...")

                # Use cache if we have this date (avoid heavy computation)
                if date_str in cache_by_date:
                    table_rows.append(cache_by_date[date_str])
                    continue

                row = {'Date': date_str}
                # a1) Advance/Total % and Stocks % above 10 DMA (Nifty 50)
                advances = 0
                declines = 0
                stocks_above_10dma = 0
                total_10dma = 0
                for sym, series in nifty_closes.items():
                    try:
                        idx = series.index.get_indexer([date_t], method='ffill')[0]
                        if idx < 0 or idx >= len(series) or idx == 0:
                            continue
                        close_t = series.iloc[idx]
                        close_prev = series.iloc[idx - 1]
                        if close_t > close_prev:
                            advances += 1
                        elif close_t < close_prev:
                            declines += 1
                        # 10 DMA breadth
                        sma10 = series.rolling(10).mean()
                        if idx >= 9:
                            dma10 = sma10.iloc[idx]
                            if not pd.isna(dma10):
                                total_10dma += 1
                                if close_t > dma10:
                                    stocks_above_10dma += 1
                    except Exception:
                        continue
                total_ad = advances + declines
                row['Advance/Total %'] = round((advances / total_ad * 100), 1) if total_ad else None
                row['Stocks % above 10 DMA'] = (
                    round((stocks_above_10dma / total_10dma * 100), 1) if total_10dma else None
                )
                
                # a2) Momentum #1, b) Momentum #2 sectors (point-in-time)
                sector_scores = []
                for sect_name, sect_data in sector_data_dict.items():
                    if sect_name == 'Nifty 50':
                        continue
                    if len(sect_data) < 14:
                        continue
                    try:
                        idx = sect_data.index.get_indexer([date_t], method='ffill')[0]
                        if idx < 0 or idx < 13:
                            continue
                        subset = sect_data.iloc[: idx + 1]
                        bench_sub = benchmark_data.iloc[: idx + 1]
                        if len(bench_sub) < 14:
                            continue
                        rsi = calculate_rsi(subset)
                        adx, _, _, di_spread = calculate_adx(subset)
                        adx_z = calculate_z_score(adx.dropna())
                        cmf = calculate_cmf(subset)
                        sr = subset['Close'].pct_change().dropna()
                        br = bench_sub['Close'].pct_change().dropna()
                        common = sr.index.intersection(br.index)
                        rs_rating = 5.0
                        if len(common) > 1:
                            cr = (1 + sr.loc[common]).prod() - 1
                            cb = (1 + br.loc[common]).prod() - 1
                            if not pd.isna(cr) and not pd.isna(cb):
                                rs_rating = max(0, min(10, 5 + (cr - cb) * 25))
                        rsi_val = rsi.iloc[-1] if not rsi.isna().all() else 50
                        di_val = di_spread.iloc[-1] if not di_spread.isna().all() else 0
                        cmf_val = cmf.iloc[-1] if not cmf.isna().all() else 0
                        sector_scores.append({
                            'sector': sect_name,
                            'rsi': rsi_val,
                            'adx_z': adx_z if not pd.isna(adx_z) else 0,
                            'rs_rating': rs_rating,
                            'di_spread': di_val,
                            'cmf': cmf_val,
                        })
                    except Exception:
                        continue
                
                top_4_this_date = None
                bot_6_this_date = None
                if sector_scores:
                    df_sec = pd.DataFrame(sector_scores)
                    use_trending = _is_trending_mode(momentum_weights)
                    if use_trending and 'rsi' in df_sec.columns and 'cmf' in df_sec.columns and len(df_sec) > 1:
                        # Trending mode: 50% Z(RSI) + 50% Z(CMF) cross-sectional, same idea as Momentum tab
                        rsi_mean, rsi_std = df_sec['rsi'].mean(), df_sec['rsi'].std()
                        cmf_mean, cmf_std = df_sec['cmf'].mean(), df_sec['cmf'].std()
                        rsi_z = (df_sec['rsi'] - rsi_mean) / rsi_std if rsi_std and not pd.isna(rsi_std) else pd.Series(0.0, index=df_sec.index)
                        cmf_z = (df_sec['cmf'] - cmf_mean) / cmf_std if cmf_std and not pd.isna(cmf_std) else pd.Series(0.0, index=df_sec.index)
                        rsi_z = rsi_z.fillna(0.0)
                        cmf_z = cmf_z.fillna(0.0)
                        df_sec['Score'] = 0.5 * rsi_z + 0.5 * cmf_z
                        # Higher Score = stronger momentum → sort descending
                        df_sec = df_sec.sort_values('Score', ascending=False)
                    else:
                        # Historical / mixed mode: rank-based momentum (same weights as main Momentum tab)
                        for c in ['ADX_Z', 'RS_Rating', 'RSI', 'DI_Spread']:
                            col = c.lower().replace('_', ' ').title() if c == 'DI_Spread' else c
                            if c == 'DI_Spread':
                                df_sec['DI_Spread'] = df_sec['di_spread']
                            df_sec[c + '_Rank'] = df_sec[c.lower() if c != 'DI_Spread' else 'di_spread'].rank(ascending=False, method='average')
                        tw = sum(momentum_weights.values()) or 1
                        df_sec['Score'] = (
                            df_sec['ADX_Z_Rank'] * momentum_weights.get('ADX_Z', 20) / tw +
                            df_sec['RS_Rating_Rank'] * momentum_weights.get('RS_Rating', 40) / tw +
                            df_sec['RSI_Rank'] * momentum_weights.get('RSI', 30) / tw +
                            df_sec['DI_Spread_Rank'] * momentum_weights.get('DI_Spread', 10) / tw
                        )
                        # Lower weighted average rank = better → sort ascending
                        df_sec = df_sec.sort_values('Score', ascending=True)

                    top2 = df_sec.head(2)['sector'].tolist()
                    row['Momentum #1 Sector'] = top2[0] if len(top2) >= 1 else ''
                    row['Momentum #2 Sector'] = top2[1] if len(top2) >= 2 else ''
                    # Per-date Top 4 / Bottom 6 from same Momentum Ranking (for confluence sector filter)
                    top_4_this_date = df_sec.head(4)['sector'].tolist()
                    bot_6_this_date = df_sec.tail(6)['sector'].tolist()
                else:
                    row['Momentum #1 Sector'] = ''
                    row['Momentum #2 Sector'] = ''
                
                # c) d) Bullish #1, #2 and e) f) Bearish #1, #2 — same scoring as Stock Screener
                company_hourly, _ = fetch_all_sectors_parallel(company_symbols_dict, end_date=date_t, interval='1h')
                screener_list = []
                for sym, rec in company_data.items():
                    try:
                        d = rec['data']
                        idx = d.index.get_indexer([date_t], method='ffill')[0]
                        if idx < 59:
                            continue
                        subset = d.iloc[: idx + 1]
                        hourly = company_hourly.get(sym) if company_hourly else None
                        score = _compute_screener_score(subset, hourly)
                        if score is not None:
                            screener_list.append((sym, rec['sector'], rec['name'], score, d, idx))
                    except Exception:
                        continue

                def next_returns_from_list(rec_list):
                    out = []
                    for (sym, sector, name, _s, d, idx) in rec_list:
                        c0 = d['Close'].iloc[idx]
                        r1 = (d['Close'].iloc[idx + 1] / c0 - 1) * 100 if idx + 1 < len(d) else None
                        r2 = (d['Close'].iloc[idx + 2] / c0 - 1) * 100 if idx + 2 < len(d) else None
                        r3 = (d['Close'].iloc[idx + 3] / c0 - 1) * 100 if idx + 3 < len(d) else None
                        r1w = (d['Close'].iloc[idx + 5] / c0 - 1) * 100 if idx + 5 < len(d) else None  # ~1 week (5 trading days)
                        out.append((sector, name, r1, r2, r3, r1w))
                    return out

                if screener_list:
                    screener_list.sort(key=lambda x: x[3], reverse=True)
                    bull2_list = screener_list[:2]
                    bear2_list = screener_list[-2:]
                    b1 = next_returns_from_list(bull2_list)
                    b2 = next_returns_from_list(bear2_list)
                    row['Bullish #1 Stock'] = b1[0][1] if len(b1) >= 1 else ''
                    row['Bullish #1 Next 1D %'] = round(b1[0][2], 1) if len(b1) >= 1 and b1[0][2] is not None else None
                    row['Bullish #1 Next 2D %'] = round(b1[0][3], 1) if len(b1) >= 1 and b1[0][3] is not None else None
                    row['Bullish #2 Stock'] = b1[1][1] if len(b1) >= 2 else ''
                    row['Bullish #2 Next 1D %'] = round(b1[1][2], 1) if len(b1) >= 2 and b1[1][2] is not None else None
                    row['Bullish #2 Next 2D %'] = round(b1[1][3], 1) if len(b1) >= 2 and b1[1][3] is not None else None
                    row['Bearish #1 Stock'] = b2[0][1] if len(b2) >= 1 else ''
                    row['Bearish #1 Next 1D %'] = round(b2[0][2], 1) if len(b2) >= 1 and b2[0][2] is not None else None
                    row['Bearish #1 Next 2D %'] = round(b2[0][3], 1) if len(b2) >= 1 and b2[0][3] is not None else None
                    row['Bearish #2 Stock'] = b2[1][1] if len(b2) >= 2 else ''
                    row['Bearish #2 Next 1D %'] = round(b2[1][2], 1) if len(b2) >= 2 and b2[1][2] is not None else None
                    row['Bearish #2 Next 2D %'] = round(b2[1][3], 1) if len(b2) >= 2 and b2[1][3] is not None else None
                    # Confluence table: bullish #1/#2 and bearish #1/#2 by FIXED dual scoring
                    conf_bull_list = []   # (sym, sector, name, bull_score, d, _idx)
                    conf_bear_list = []   # (sym, sector, name, bear_score, d, _idx)
                    confluence_details = {}  # sym -> details dict
                    for (sym, sector, name, _s, d, _idx) in screener_list:
                        # (a) Sector filter — per-date Top 4 (bullish) / Bottom 6 (bearish) from Momentum Ranking
                        bull_sector_ok = (
                            hist_conf_sector_filter == "Universal (All Sectors)"
                            or (top_4_this_date and sector in top_4_this_date)
                            or (top_4_this_date is None and bot_6_this_date is None)
                        )
                        bear_sector_ok = (
                            hist_conf_sector_filter == "Universal (All Sectors)"
                            or (bot_6_this_date and sector in bot_6_this_date)
                            or (top_4_this_date is None and bot_6_this_date is None)
                        )
                        if not bull_sector_ok and not bear_sector_ok:
                            continue
                        if hist_conf_tf_code == '1d':
                            conf_data_entry = d.iloc[: _idx + 1] if _idx + 1 <= len(d) else d
                            conf_data_1d = conf_data_entry
                            _conf_tf_used = hist_conf_tf_code
                        else:
                            # 2h or 4h: use 1H data; same as Stock Screener — require min bars, no 1D fallback so Historical matches Part 3
                            min_bars = 80 if hist_conf_tf_code == '4h' else 40
                            conf_data_entry = company_hourly.get(sym) if company_hourly else None
                            conf_data_1d = d.iloc[: _idx + 1] if _idx + 1 <= len(d) else d
                            if conf_data_entry is None or len(conf_data_entry) < min_bars:
                                continue  # skip so Confluence Bullish #1/#2 stay in sync with Stock Screener
                            _conf_tf_used = hist_conf_tf_code
                        b_score, s_score, c_details = _compute_confluence_score(
                            conf_data_entry, data_1d=conf_data_1d, timeframe=_conf_tf_used
                        )
                        if b_score is not None:
                            if bull_sector_ok and b_score > _GATE_FAIL_SCORE:
                                conf_bull_list.append((sym, sector, name, b_score, d, _idx))
                            if bear_sector_ok and s_score is not None and s_score > _GATE_FAIL_SCORE:
                                conf_bear_list.append((sym, sector, name, s_score, d, _idx))
                            if c_details:
                                confluence_details[sym] = c_details
                    if conf_bull_list:
                        # Bullish: top 2 by bullish score
                        conf_bull_list.sort(key=lambda x: x[3], reverse=True)
                        conf_bull2 = conf_bull_list[:2]
                        cb_ret = next_returns_from_list(conf_bull2)
                        # Bearish: top 2 by bearish score
                        conf_bear_list.sort(key=lambda x: x[3], reverse=True)
                        conf_bear2 = conf_bear_list[:2]
                        cr_ret = next_returns_from_list(conf_bear2)

                        # Bullish #1 (tuple: sym, sector, name, b_score, d, _idx); cb_ret[i] = (sector, name, r1d, r2d, r3d, r1w)
                        row['Conf Bull #1'] = cb_ret[0][1] if len(cb_ret) >= 1 else ''
                        row['Conf Bull #1 Sector'] = cb_ret[0][0] if len(cb_ret) >= 1 else ''
                        row['Conf Bull #1 CMP'] = round(float(conf_bull2[0][4]['Close'].iloc[conf_bull2[0][5]]), 0) if len(conf_bull2) >= 1 else None
                        row['Conf Bull #1 Dir'] = confluence_details.get(conf_bull2[0][0], {}).get('Direction', '') if len(conf_bull2) >= 1 else ''
                        row['Conf Bull #1 Score'] = int(round(conf_bull2[0][3])) if len(conf_bull2) >= 1 else None
                        row['Conf Bull #1 1D %'] = round(cb_ret[0][2], 1) if len(cb_ret) >= 1 and cb_ret[0][2] is not None else None
                        row['Conf Bull #1 2D %'] = round(cb_ret[0][3], 1) if len(cb_ret) >= 1 and cb_ret[0][3] is not None else None
                        row['Conf Bull #1 3D %'] = round(cb_ret[0][4], 1) if len(cb_ret) >= 1 and cb_ret[0][4] is not None else None
                        row['Conf Bull #1 1W %'] = round(cb_ret[0][5], 1) if len(cb_ret) >= 1 and len(cb_ret[0]) > 5 and cb_ret[0][5] is not None else None
                        # Bullish #2
                        row['Conf Bull #2'] = cb_ret[1][1] if len(cb_ret) >= 2 else ''
                        row['Conf Bull #2 Sector'] = cb_ret[1][0] if len(cb_ret) >= 2 else ''
                        row['Conf Bull #2 CMP'] = round(float(conf_bull2[1][4]['Close'].iloc[conf_bull2[1][5]]), 0) if len(conf_bull2) >= 2 else None
                        row['Conf Bull #2 Dir'] = confluence_details.get(conf_bull2[1][0], {}).get('Direction', '') if len(conf_bull2) >= 2 else ''
                        row['Conf Bull #2 Score'] = int(round(conf_bull2[1][3])) if len(conf_bull2) >= 2 else None
                        row['Conf Bull #2 1D %'] = round(cb_ret[1][2], 1) if len(cb_ret) >= 2 and cb_ret[1][2] is not None else None
                        row['Conf Bull #2 2D %'] = round(cb_ret[1][3], 1) if len(cb_ret) >= 2 and cb_ret[1][3] is not None else None
                        row['Conf Bull #2 3D %'] = round(cb_ret[1][4], 1) if len(cb_ret) >= 2 and cb_ret[1][4] is not None else None
                        row['Conf Bull #2 1W %'] = round(cb_ret[1][5], 1) if len(cb_ret) >= 2 and len(cb_ret[1]) > 5 and cb_ret[1][5] is not None else None
                        # Bearish #1
                        row['Conf Bear #1'] = cr_ret[0][1] if len(cr_ret) >= 1 else ''
                        row['Conf Bear #1 Sector'] = cr_ret[0][0] if len(cr_ret) >= 1 else ''
                        row['Conf Bear #1 CMP'] = round(float(conf_bear2[0][4]['Close'].iloc[conf_bear2[0][5]]), 0) if len(conf_bear2) >= 1 else None
                        row['Conf Bear #1 Dir'] = confluence_details.get(conf_bear2[0][0], {}).get('Direction', '') if len(conf_bear2) >= 1 else ''
                        row['Conf Bear #1 Score'] = int(round(conf_bear2[0][3])) if len(conf_bear2) >= 1 else None
                        row['Conf Bear #1 1D %'] = round(cr_ret[0][2], 1) if len(cr_ret) >= 1 and cr_ret[0][2] is not None else None
                        row['Conf Bear #1 2D %'] = round(cr_ret[0][3], 1) if len(cr_ret) >= 1 and cr_ret[0][3] is not None else None
                        row['Conf Bear #1 3D %'] = round(cr_ret[0][4], 1) if len(cr_ret) >= 1 and cr_ret[0][4] is not None else None
                        row['Conf Bear #1 1W %'] = round(cr_ret[0][5], 1) if len(cr_ret) >= 1 and len(cr_ret[0]) > 5 and cr_ret[0][5] is not None else None
                        # Bearish #2
                        row['Conf Bear #2'] = cr_ret[1][1] if len(cr_ret) >= 2 else ''
                        row['Conf Bear #2 Sector'] = cr_ret[1][0] if len(cr_ret) >= 2 else ''
                        row['Conf Bear #2 CMP'] = round(float(conf_bear2[1][4]['Close'].iloc[conf_bear2[1][5]]), 0) if len(conf_bear2) >= 2 else None
                        row['Conf Bear #2 Dir'] = confluence_details.get(conf_bear2[1][0], {}).get('Direction', '') if len(conf_bear2) >= 2 else ''
                        row['Conf Bear #2 Score'] = int(round(conf_bear2[1][3])) if len(conf_bear2) >= 2 else None
                        row['Conf Bear #2 1D %'] = round(cr_ret[1][2], 1) if len(cr_ret) >= 2 and cr_ret[1][2] is not None else None
                        row['Conf Bear #2 2D %'] = round(cr_ret[1][3], 1) if len(cr_ret) >= 2 and cr_ret[1][3] is not None else None
                        row['Conf Bear #2 3D %'] = round(cr_ret[1][4], 1) if len(cr_ret) >= 2 and cr_ret[1][4] is not None else None
                        row['Conf Bear #2 1W %'] = round(cr_ret[1][5], 1) if len(cr_ret) >= 2 and len(cr_ret[1]) > 5 and cr_ret[1][5] is not None else None
                    else:
                        for k in _CONF_COLS_ALL:
                            row[k] = None
                else:
                    for k in ['Bullish #1 Stock', 'Bullish #1 Next 1D %', 'Bullish #1 Next 2D %',
                              'Bullish #2 Stock', 'Bullish #2 Next 1D %', 'Bullish #2 Next 2D %',
                              'Bearish #1 Stock', 'Bearish #1 Next 1D %', 'Bearish #1 Next 2D %',
                              'Bearish #2 Stock', 'Bearish #2 Next 1D %', 'Bearish #2 Next 2D %'] + _CONF_COLS_ALL:
                        row[k] = None
                
                table_rows.append(row)
                cache_by_date[date_str] = row.copy()

            progress_bar.empty()
            status_text.empty()

            # Persist cache so next run can skip computed dates
            if cache_by_date:
                try:
                    df_save = pd.DataFrame(sorted(cache_by_date.values(), key=lambda r: r['Date'], reverse=True))
                    df_save.to_csv(cache_path, index=False)
                except Exception:
                    pass

        if table_rows:
            df_primary = pd.DataFrame(table_rows)
            df_primary = df_primary.sort_values('Date', ascending=False)
            # Restrict to the columns requested for the summary table
            display_cols = [
                'Date',
                'Advance/Total %',
                'Stocks % above 10 DMA',
                'Momentum #1 Sector',
                'Bullish #1 Stock',
                'Bullish #1 Next 1D %',
                'Bullish #1 Next 2D %',
                'Bullish #2 Stock',
                'Bullish #2 Next 1D %',
                'Bullish #2 Next 2D %',
                'Bearish #1 Stock',
                'Bearish #1 Next 1D %',
                'Bearish #1 Next 2D %',
                'Bearish #2 Stock',
                'Bearish #2 Next 1D %',
                'Bearish #2 Next 2D %',
            ]
            cols_existing = [c for c in display_cols if c in df_primary.columns]
            df_show = df_primary[cols_existing] if cols_existing else df_primary

            # Ensure all percentage/return columns are numeric and rounded to 1 decimal
            percent_cols = [
                'Advance/Total %',
                'Stocks % above 10 DMA',
                'Bullish #1 Next 1D %',
                'Bullish #1 Next 2D %',
                'Bullish #2 Next 1D %',
                'Bullish #2 Next 2D %',
                'Bearish #1 Next 1D %',
                'Bearish #1 Next 2D %',
                'Bearish #2 Next 1D %',
                'Bearish #2 Next 2D %',
            ]
            for c in percent_cols:
                if c in df_show.columns:
                    df_show[c] = pd.to_numeric(df_show[c], errors='coerce').round(1)

            # Color coding similar to Market Breadth tab for breadth columns
            def style_row(row):
                res = [''] * len(row)
                if 'Advance/Total %' in row.index:
                    idx = list(row.index).index('Advance/Total %')
                    try:
                        v = float(row['Advance/Total %'])
                        if v > 60:
                            res[idx] = 'background-color: #27AE60; color: #fff; font-weight: bold'
                        elif v < 40:
                            res[idx] = 'background-color: #E74C3C; color: #fff; font-weight: bold'
                    except Exception:
                        pass
                if 'Stocks % above 10 DMA' in row.index:
                    idx = list(row.index).index('Stocks % above 10 DMA')
                    try:
                        v = float(row['Stocks % above 10 DMA'])
                        if v > 60:
                            res[idx] = 'background-color: #27AE60; color: #fff; font-weight: bold'
                        elif v < 40:
                            res[idx] = 'background-color: #E74C3C; color: #fff; font-weight: bold'
                    except Exception:
                        pass
                return res

            df_show_styled = (
                df_show.style
                .apply(style_row, axis=1)
                .format({c: "{:.1f}" for c in percent_cols if c in df_show.columns})
            )
            st.dataframe(df_show_styled, use_container_width=True, hide_index=True)
            st.caption(
                "**Scoring (MA+RSI+VWAP, same as Stock Screener):** Bullish #1/#2 and Bearish #1/#2 by same score: "
                "1 pt each for RSI (1W/1D/1H) up, 1 pt each for Price > 8/20/50 SMA, + VWAP (1H). RSI divergence not used. "
                "Higher score = stronger bullish setup; top 2 = Bullish, bottom 2 = Bearish."
            )
            # Confluence table: Advance/Total %, Stocks % above 10 DMA, Sector, then stock/CMP/returns (1D/2D/3D/1W)
            conf_bull_cols = ['Date', 'Advance/Total %', 'Stocks % above 10 DMA',
                              'Conf Bull #1 Sector', 'Conf Bull #2 Sector',
                              'Conf Bull #1', 'Conf Bull #1 CMP', 'Conf Bull #1 Dir', 'Conf Bull #1 Score',
                              'Conf Bull #1 1D %', 'Conf Bull #1 2D %', 'Conf Bull #1 3D %', 'Conf Bull #1 1W %',
                              'Conf Bull #2', 'Conf Bull #2 CMP', 'Conf Bull #2 Dir', 'Conf Bull #2 Score',
                              'Conf Bull #2 1D %', 'Conf Bull #2 2D %', 'Conf Bull #2 3D %', 'Conf Bull #2 1W %']
            conf_bear_cols = ['Date', 'Advance/Total %', 'Stocks % above 10 DMA',
                              'Conf Bear #1 Sector', 'Conf Bear #2 Sector',
                              'Conf Bear #1', 'Conf Bear #1 CMP', 'Conf Bear #1 Dir', 'Conf Bear #1 Score',
                              'Conf Bear #1 1D %', 'Conf Bear #1 2D %', 'Conf Bear #1 3D %', 'Conf Bear #1 1W %',
                              'Conf Bear #2', 'Conf Bear #2 CMP', 'Conf Bear #2 Dir', 'Conf Bear #2 Score',
                              'Conf Bear #2 1D %', 'Conf Bear #2 2D %', 'Conf Bear #2 3D %', 'Conf Bear #2 1W %']

            conf_bull_present = [c for c in conf_bull_cols if c in df_primary.columns]
            conf_bear_present = [c for c in conf_bear_cols if c in df_primary.columns]

            def _color_breadth_rows(df_subset, breadth_cols):
                """Return list of style lists for each row: color Advance/Total % and Stocks % above 10 DMA."""
                def style_row(row):
                    res = [''] * len(row)
                    for col in breadth_cols:
                        if col not in row.index:
                            continue
                        try:
                            v = float(row[col])
                            idx = list(row.index).index(col)
                            if v > 60:
                                res[idx] = 'background-color: #27AE60; color: #fff; font-weight: bold'
                            elif v < 40:
                                res[idx] = 'background-color: #E74C3C; color: #fff; font-weight: bold'
                        except Exception:
                            pass
                    return res
                return style_row

            breadth_cols = [c for c in ['Advance/Total %', 'Stocks % above 10 DMA'] if c in df_primary.columns]

            if len(conf_bull_present) >= 4:
                st.markdown(f"#### 🟢 Confluence Bullish #1/#2 ({hist_conf_tf_label}, Advance/Total, % 10 DMA, CMP)")
                df_conf_bull = df_primary[conf_bull_present].sort_values('Date', ascending=False)
                score_cols_b = [c for c in ['Conf Bull #1 Score', 'Conf Bull #2 Score'] if c in df_conf_bull.columns]
                cmp_cols_b = [c for c in ['Conf Bull #1 CMP', 'Conf Bull #2 CMP'] if c in df_conf_bull.columns]
                pct_cols_b = [c for c in ['Advance/Total %', 'Stocks % above 10 DMA', 'Conf Bull #1 1D %', 'Conf Bull #1 2D %', 'Conf Bull #1 3D %', 'Conf Bull #1 1W %', 'Conf Bull #2 1D %', 'Conf Bull #2 2D %', 'Conf Bull #2 3D %', 'Conf Bull #2 1W %'] if c in df_conf_bull.columns]
                fmt = {c: '{:.0f}' for c in score_cols_b + cmp_cols_b}
                fmt.update({c: '{:.1f}' for c in pct_cols_b})
                style_bull = _color_breadth_rows(df_conf_bull, breadth_cols)
                st.dataframe(
                    df_conf_bull.style.apply(style_bull, axis=1).format(fmt, na_rep=''),
                    use_container_width=True, hide_index=True
                )
                # Win-ratio summary (past 30 days): separate for Bullish #1 and Bullish #2 (no sampling)
                w1 = df_primary.get('Conf Bull #1 1W %')
                w2 = df_primary.get('Conf Bull #2 1W %')
                list_1 = pd.to_numeric(w1, errors='coerce').dropna().tolist() if w1 is not None else []
                list_2 = pd.to_numeric(w2, errors='coerce').dropna().tolist() if w2 is not None else []
                n1, n2 = len(list_1), len(list_2)
                st.markdown("**Historical analysis — Confluence Bullish next 1-week return (past 30 days)**")
                rows_win = []
                if n1 > 0:
                    win_1_a = sum(1 for x in list_1 if float(x) >= 1.0) / n1 * 100
                    win_15_a = sum(1 for x in list_1 if float(x) >= 1.5) / n1 * 100
                    win_2_a = sum(1 for x in list_1 if float(x) >= 2.0) / n1 * 100
                    rows_win.append({"Pick": "Bullish #1", "Sample size": n1, ">= 1.0%": f"{win_1_a:.1f}%", ">= 1.5%": f"{win_15_a:.1f}%", ">= 2.0%": f"{win_2_a:.1f}%"})
                else:
                    rows_win.append({"Pick": "Bullish #1", "Sample size": 0, ">= 1.0%": "N/A", ">= 1.5%": "N/A", ">= 2.0%": "N/A"})
                if n2 > 0:
                    win_1_b = sum(1 for x in list_2 if float(x) >= 1.0) / n2 * 100
                    win_15_b = sum(1 for x in list_2 if float(x) >= 1.5) / n2 * 100
                    win_2_b = sum(1 for x in list_2 if float(x) >= 2.0) / n2 * 100
                    rows_win.append({"Pick": "Bullish #2", "Sample size": n2, ">= 1.0%": f"{win_1_b:.1f}%", ">= 1.5%": f"{win_15_b:.1f}%", ">= 2.0%": f"{win_2_b:.1f}%"})
                else:
                    rows_win.append({"Pick": "Bullish #2", "Sample size": 0, ">= 1.0%": "N/A", ">= 1.5%": "N/A", ">= 2.0%": "N/A"})
                df_win = pd.DataFrame(rows_win)
                st.dataframe(df_win, use_container_width=True, hide_index=True)
                st.caption("Win ratio = % of days (past 30) that pick achieved at least the given return in the next one week. Bullish #1 and Bullish #2 computed separately (no sampling).")

            if len(conf_bear_present) >= 4:
                st.markdown(f"#### 🔴 Confluence Bearish #1/#2 ({hist_conf_tf_label}, Advance/Total, % 10 DMA, CMP)")
                df_conf_bear = df_primary[conf_bear_present].sort_values('Date', ascending=False)
                score_cols_be = [c for c in ['Conf Bear #1 Score', 'Conf Bear #2 Score'] if c in df_conf_bear.columns]
                cmp_cols_be = [c for c in ['Conf Bear #1 CMP', 'Conf Bear #2 CMP'] if c in df_conf_bear.columns]
                pct_cols_be = [c for c in ['Advance/Total %', 'Stocks % above 10 DMA', 'Conf Bear #1 1D %', 'Conf Bear #1 2D %', 'Conf Bear #1 3D %', 'Conf Bear #1 1W %', 'Conf Bear #2 1D %', 'Conf Bear #2 2D %', 'Conf Bear #2 3D %', 'Conf Bear #2 1W %'] if c in df_conf_bear.columns]
                fmt = {c: '{:.0f}' for c in score_cols_be + cmp_cols_be}
                fmt.update({c: '{:.1f}' for c in pct_cols_be})
                style_bear = _color_breadth_rows(df_conf_bear, breadth_cols)
                st.dataframe(
                    df_conf_bear.style.apply(style_bear, axis=1).format(fmt, na_rep=''),
                    use_container_width=True, hide_index=True
                )

            if len(conf_bull_present) >= 4 or len(conf_bear_present) >= 4:
                st.caption(
                    f"**Confluence scoring ({hist_conf_tf_label}):** Trend (HH/HL = W₁, Sideways = W₁×0.33, LL/LH = 0), "
                    "Direction (Bullish = W₂, Mixed = W₂×0.33, Bearish = 0), "
                    "RSI (rising+zone = W₃, rising = W₃×0.5), Setup (crossover+bullish = W₄), "
                    "Divergence (bullish = W₅, bearish = −W₅×0.5). "
                    "Dir = confluence direction. 1D/2D/3D/1W % = next 1/2/3/5-day return. Sector = stock sector. "
                    f"Last 30 trading days. Switch timeframe or sector filter above to recompute."
                )
        else:
            st.info("No rows computed for the 30-day table.")
    
    st.markdown("---")
    st.markdown("#### 📈 Secondary: Sector evolution (Momentum & Reversal)")
    
    # Get current top 2 momentum sectors (for sub-tabs)
    current_results = []
    for sect_name, sect_data in sector_data_dict.items():
        if sect_name == 'Nifty 50':
            continue
        
        if len(sect_data) < 50:
            continue
        
        # Calculate current indicators
        rsi = calculate_rsi(sect_data)
        adx, _, _, di_spread = calculate_adx(sect_data)
        cmf = calculate_cmf(sect_data)
        adx_z = calculate_z_score(adx.dropna())
        
        # RS Rating
        sector_returns = sect_data['Close'].pct_change().dropna()
        benchmark_returns = benchmark_data['Close'].pct_change().dropna()
        common_index = sector_returns.index.intersection(benchmark_returns.index)
        
        rs_rating = 5.0
        if len(common_index) > 1:
            sector_ret = sector_returns.loc[common_index]
            bench_ret = benchmark_returns.loc[common_index]
            sector_cumret = (1 + sector_ret).prod() - 1
            bench_cumret = (1 + bench_ret).prod() - 1
            if not pd.isna(sector_cumret) and not pd.isna(bench_cumret):
                relative_perf = sector_cumret - bench_cumret
                rs_rating = 5 + (relative_perf * 25)
                rs_rating = max(0, min(10, rs_rating))
        
        current_results.append({
            'Sector': sect_name,
            'RSI': rsi.iloc[-1] if not rsi.isna().all() else 50,
            'CMF': cmf.iloc[-1] if not cmf.isna().all() else 0,
            'ADX_Z': adx_z if not pd.isna(adx_z) else 0,
            'RS_Rating': rs_rating,
            'DI_Spread': di_spread.iloc[-1] if not di_spread.isna().all() else 0,
        })
    
    if not current_results:
        st.error("❌ Unable to calculate rankings")
        return
    
    # Rank and get top 2 (Trending: 50% Z(RSI) + 50% Z(CMF); Historical: rank-based)
    df_current = pd.DataFrame(current_results)
    if _is_trending_mode(momentum_weights) and len(df_current) > 1:
        rsi_m, rsi_s = df_current['RSI'].mean(), df_current['RSI'].std()
        cmf_m, cmf_s = df_current['CMF'].mean(), df_current['CMF'].std()
        rsi_z = (df_current['RSI'] - rsi_m) / rsi_s if (rsi_s and not pd.isna(rsi_s)) else pd.Series(0.0, index=df_current.index)
        cmf_z = (df_current['CMF'] - cmf_m) / cmf_s if (cmf_s and not pd.isna(cmf_s)) else pd.Series(0.0, index=df_current.index)
        rsi_z = rsi_z.fillna(0) if hasattr(rsi_z, 'fillna') else rsi_z
        cmf_z = cmf_z.fillna(0) if hasattr(cmf_z, 'fillna') else cmf_z
        raw = 0.5 * rsi_z + 0.5 * cmf_z
        rmin, rmax = raw.min(), raw.max()
        df_current['Momentum_Score'] = (1 + (raw - rmin) / (rmax - rmin) * 9) if rmax > rmin else 5.0
    else:
        df_current['ADX_Z_Rank'] = df_current['ADX_Z'].rank(ascending=False)
        df_current['RS_Rating_Rank'] = df_current['RS_Rating'].rank(ascending=False)
        df_current['RSI_Rank'] = df_current['RSI'].rank(ascending=False)
        df_current['DI_Spread_Rank'] = df_current['DI_Spread'].rank(ascending=False)
        total_weight = sum(momentum_weights.values()) or 1
        df_current['Momentum_Score'] = (
            (df_current['ADX_Z_Rank'] * momentum_weights.get('ADX_Z', 20) / total_weight) +
            (df_current['RS_Rating_Rank'] * momentum_weights.get('RS_Rating', 40) / total_weight) +
            (df_current['RSI_Rank'] * momentum_weights.get('RSI', 30) / total_weight) +
            (df_current['DI_Spread_Rank'] * momentum_weights.get('DI_Spread', 10) / total_weight)
        )
        num_sectors = len(df_current)
        if num_sectors > 1:
            min_rank = df_current['Momentum_Score'].min()
            max_rank = df_current['Momentum_Score'].max()
            if max_rank > min_rank:
                df_current['Momentum_Score'] = 10 - ((df_current['Momentum_Score'] - min_rank) / (max_rank - min_rank)) * 9
            else:
                df_current['Momentum_Score'] = 5.0
        else:
            df_current['Momentum_Score'] = 5.0

    df_current = df_current.sort_values('Momentum_Score', ascending=False)
    top_2_sectors = df_current.head(2)['Sector'].tolist()
    
    # Create tabs for Momentum and Reversal
    hist_tab1, hist_tab2 = st.tabs(["📈 Momentum Rankings (T-7 to T)", "🔄 Reversal Rankings (T-7 to T)"])
    
    with hist_tab1:
        st.markdown("#### Momentum Strategy - Top 2 Sectors Evolution")
        
        if len(top_2_sectors) >= 2:
            col1, col2 = st.columns(2)
            
            for col_idx, sector_name in enumerate(top_2_sectors):
                with [col1, col2][col_idx]:
                    st.markdown(f"**#{col_idx + 1}: {sector_name}**")
                    
                    if sector_name in sector_data_dict:
                        sect_data = sector_data_dict[sector_name]
                        
                        # Show last 7 periods (or available)
                        periods = min(7, len(sect_data) - 1)
                        hist_data = []
                        
                        for i in range(periods, 0, -1):
                            date = sect_data.index[-i].strftime('%d-%b')
                            subset = sect_data.iloc[:-i] if i > 0 else sect_data
                            
                            if len(subset) < 14:
                                continue
                            
                            rsi = calculate_rsi(subset)
                            adx, _, _, di_spread = calculate_adx(subset)
                            adx_z = calculate_z_score(adx.dropna())
                            
                            hist_data.append({
                                'Date': date,
                                'RSI': f"{rsi.iloc[-1]:.1f}" if not rsi.isna().all() else "N/A",
                                'ADX_Z': f"{adx_z:.2f}" if not pd.isna(adx_z) else "N/A",
                                'DI_Spread': f"{di_spread.iloc[-1]:.2f}" if not di_spread.isna().all() else "N/A",
                            })
                        
                        if hist_data:
                            df_hist = pd.DataFrame(hist_data)
                            st.dataframe(df_hist, use_container_width=True, hide_index=True)
                        else:
                            st.warning("⚠️ Insufficient historical data")
        else:
            st.info("ℹ️ Need at least 2 sectors to compare")
    
    with hist_tab2:
        st.markdown("#### Reversal Strategy - Top 2 Reversal Candidates Evolution")
        
        # Similar logic for reversal (show top reversal candidates)
        reversal_results = []
        for sect_name, sect_data in sector_data_dict.items():
            if sect_name == 'Nifty 50':
                continue
            
            if len(sect_data) < 50:
                continue
            
            rsi = calculate_rsi(sect_data)
            adx, _, _, _ = calculate_adx(sect_data)
            cmf = calculate_cmf(sect_data)
            adx_z = calculate_z_score(adx.dropna())
            
            rsi_val = rsi.iloc[-1] if not rsi.isna().all() else 50
            cmf_val = cmf.iloc[-1] if not cmf.isna().all() else 0
            adx_z_val = adx_z if not pd.isna(adx_z) else 0
            
            reversal_results.append({
                'Sector': sect_name,
                'RSI': rsi_val,
                'CMF': cmf_val,
                'ADX_Z': adx_z_val,
            })
        
        if reversal_results:
            df_reversal = pd.DataFrame(reversal_results)
            
            # Rank for reversal (lower RSI/ADX_Z better, higher CMF better)
            df_reversal['RSI_Rank'] = df_reversal['RSI'].rank(ascending=True)
            df_reversal['CMF_Rank'] = df_reversal['CMF'].rank(ascending=False)
            df_reversal['ADX_Z_Rank'] = df_reversal['ADX_Z'].rank(ascending=True)
            
            total_weight = sum(reversal_weights.values())
            df_reversal['Reversal_Score'] = (
                (df_reversal['RSI_Rank'] * reversal_weights.get('RSI', 10) / total_weight) +
                (df_reversal['CMF_Rank'] * reversal_weights.get('CMF', 40) / total_weight) +
                (df_reversal['ADX_Z_Rank'] * reversal_weights.get('ADX_Z', 10) / total_weight)
            )
            
            # Scale 1-10
            num_reversals = len(df_reversal)
            if num_reversals > 1:
                min_rank = df_reversal['Reversal_Score'].min()
                max_rank = df_reversal['Reversal_Score'].max()
                if max_rank > min_rank:
                    df_reversal['Reversal_Score'] = 10 - ((df_reversal['Reversal_Score'] - min_rank) / (max_rank - min_rank)) * 9
            
            df_reversal = df_reversal.sort_values('Reversal_Score', ascending=False)
            top_2_reversal = df_reversal.head(2)['Sector'].tolist()
            
            if len(top_2_reversal) >= 1:
                col1, col2 = st.columns(2) if len(top_2_reversal) >= 2 else (st.columns(1)[0], None)
                
                for col_idx, sector_name in enumerate(top_2_reversal):
                    with [col1, col2][col_idx] if col2 else col1:
                        st.markdown(f"**#{col_idx + 1}: {sector_name}**")
                        
                        if sector_name in sector_data_dict:
                            sect_data = sector_data_dict[sector_name]
                            
                            # Show last 7 periods
                            periods = min(7, len(sect_data) - 1)
                            hist_data = []
                            
                            for i in range(periods, 0, -1):
                                date = sect_data.index[-i].strftime('%d-%b')
                                subset = sect_data.iloc[:-i] if i > 0 else sect_data
                                
                                if len(subset) < 14:
                                    continue
                                
                                rsi = calculate_rsi(subset)
                                cmf = calculate_cmf(subset)
                                adx, _, _, _ = calculate_adx(subset)
                                adx_z = calculate_z_score(adx.dropna())
                                
                                hist_data.append({
                                    'Date': date,
                                    'RSI': f"{rsi.iloc[-1]:.1f}" if not rsi.isna().all() else "N/A",
                                    'CMF': f"{cmf.iloc[-1]:.2f}" if not cmf.isna().all() else "N/A",
                                    'ADX_Z': f"{adx_z:.2f}" if not pd.isna(adx_z) else "N/A",
                                })
                            
                            if hist_data:
                                df_hist = pd.DataFrame(hist_data)
                                st.dataframe(df_hist, use_container_width=True, hide_index=True)
                            else:
                                st.warning("⚠️ Insufficient historical data")
        else:
            st.info("ℹ️ Unable to analyze reversal candidates")



def display_sector_companies_tab():
    """Display sector-wise company mappings with symbols."""
    st.markdown("### 🏢 Sector-wise Company Mappings")
    st.markdown("---")
    
    st.info("📋 **Top companies by weight in each sector/ETF** - These are the companies tracked for company-level analysis.")
    
    from company_symbols import SECTOR_COMPANIES, SECTOR_COMPANY_EXCEL_PATH_USED
    # Show what the app actually uses (SECTOR_COMPANIES); reload button updates it from Excel
    display_data = SECTOR_COMPANIES
    excel_loaded = SECTOR_COMPANY_EXCEL_PATH_USED
    
    # Download/Upload section
    st.markdown("#### 📥 Export / 📤 Import Company Mappings")
    dl_col, reload_col = st.columns(2)
    
    with dl_col:
        # Create consolidated dataframe for download
        all_company_data = []
        for sector, companies in display_data.items():
            for symbol, info in companies.items():
                all_company_data.append({
                    'Sector': sector,
                    'Company Name': info['name'],
                    'Symbol': symbol,
                    'Weight (%)': info['weight']
                })
        
        download_df = pd.DataFrame(all_company_data)
        csv_data = download_df.to_csv(index=False)
        
        st.download_button(
            label="📥 Download All Companies (CSV)",
            data=csv_data,
            file_name=f"sector_companies_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            help="Download current sector-company mappings"
        )
    
    with reload_col:
        try:
            from company_symbols import SECTOR_COMPANY_EXCEL_PATH_USED, reload_sector_companies_from_excel
            path_display = SECTOR_COMPANY_EXCEL_PATH_USED or "Sector-Company.xlsx"
            st.caption(f"✅ Loaded from: **{path_display}**")
            if st.button("🔄 Reload from Excel", help="Re-read Sector-Company.xlsx and refresh company names (no restart needed)"):
                ok, msg = reload_sector_companies_from_excel()
                if ok:
                    st.cache_data.clear()
                    st.success("Reloaded. Refreshing...")
                    st.rerun()
                else:
                    st.error(msg)
        except Exception as e:
            st.caption("📁 Place Sector-Company.xlsx in project folder to load custom weights")
    
    st.markdown("---")
    
    # Create columns for better layout
    col1, col2 = st.columns(2)
    
    sectors = sorted(display_data.keys())
    half = len(sectors) // 2
    
    # Left column
    with col1:
        for sector in sectors[:half]:
            with st.expander(f"📊 **{sector}**", expanded=False):
                companies = display_data[sector]
                
                # Create dataframe for this sector
                company_data = []
                for symbol, info in companies.items():
                    company_data.append({
                        'Symbol': symbol,
                        'Company Name': info['name'],
                        'Weight (%)': f"{info['weight']:.1f}"
                    })
                
                df = pd.DataFrame(company_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.caption(f"Total companies: {len(companies)}")
    
    # Right column
    with col2:
        for sector in sectors[half:]:
            with st.expander(f"📊 **{sector}**", expanded=False):
                companies = display_data[sector]
                
                # Create dataframe for this sector
                company_data = []
                for symbol, info in companies.items():
                    company_data.append({
                        'Symbol': symbol,
                        'Company Name': info['name'],
                        'Weight (%)': f"{info['weight']:.1f}"
                    })
                
                df = pd.DataFrame(company_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.caption(f"Total companies: {len(companies)}")
    
    # Summary statistics
    # Summary statistics
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    total_sectors = len(display_data)
    total_companies = sum(len(companies) for companies in display_data.values())
    avg_companies = total_companies / total_sectors if total_sectors > 0 else 0
    
    with col1:
        st.metric("Total Sectors", total_sectors)
    
    with col2:
        st.metric("Total Companies", total_companies)
    
    with col3:
        st.metric("Avg Companies/Sector", f"{avg_companies:.1f}")


def display_data_sources_tab():
    """Display data sources connectivity status."""
    st.markdown("### 📊 Data Sources & Connectivity")
    st.markdown("---")
    
    st.info("🔄 **Real-time connectivity test completed on page load.** Status shows availability of each Index and ETF proxy.")
    
    # Get connectivity status
    availability_status = test_symbol_availability()
    
    # Prepare data for display
    display_data = []
    
    # Add Nifty 50 benchmark first
    nifty_50_status = availability_status.get('Nifty 50', {}).get('status', '❌')
    nifty_50_alt_status = availability_status.get('Nifty 50_ALT', {}).get('status', '❌')
    display_data.append({
        'Sector': '🔵 Nifty 50 (Benchmark)',
        'Index Symbol': '^NSEI',
        'Index Status': nifty_50_status,
        'ETF Symbol': 'NIFTYBEES.NS',
        'ETF Status': nifty_50_status,
        'Alternate ETF': '',
        'Alternate Status': ''
    })
    
    # Add all sectors
    for sector in sorted(SECTORS.keys()):
        if sector == 'Nifty 50':
            continue
        
        index_sym = SECTORS[sector]
        etf_sym = SECTOR_ETFS.get(sector, 'N/A')
        alt_etf_sym = SECTOR_ETFS_ALTERNATE.get(sector, '')
        
        index_status = availability_status.get(sector, {}).get('status', '❌')
        etf_key = f"{sector}_ETF"
        etf_status = availability_status.get(etf_key, {}).get('status', '❌')
        
        alt_key = f"{sector}_ALT_ETF"
        alt_status = availability_status.get(alt_key, {}).get('status', '') if alt_etf_sym else ''
        
        display_data.append({
            'Sector': sector,
            'Index Symbol': index_sym,
            'Index Status': index_status,
            'ETF Symbol': etf_sym if etf_sym != 'N/A' else 'N/A',
            'ETF Status': etf_status if etf_sym != 'N/A' else 'N/A',
            'Alternate ETF': alt_etf_sym,
            'Alternate Status': alt_status if alt_etf_sym else ''
        })
    
    # Create and display dataframe
    df_sources = pd.DataFrame(display_data)
    
    # Style the dataframe
    def color_status(val):
        if val == '✅':
            return 'background-color: #27AE60; color: #fff; font-weight: bold'
        elif val == '❌':
            return 'background-color: #E74C3C; color: #fff; font-weight: bold'
        elif val == 'N/A':
            return 'background-color: #95A5A6; color: #fff'
        return ''
    
    styled_df = df_sources.style.map(color_status, subset=['Index Status', 'ETF Status', 'Alternate Status'])
    st.dataframe(styled_df, use_container_width=True)
    
    # Summary statistics
    col1, col2, col3 = st.columns(3)
    
    total_symbols = len([s for s in availability_status.values() if s.get('status') != 'N/A'])
    working_symbols = len([s for s in availability_status.values() if s.get('status') == '✅'])
    failed_symbols = total_symbols - working_symbols
    
    with col1:
        st.metric("Total Symbols", total_symbols, f"{working_symbols} working")
    
    with col2:
        st.metric("✅ Successful", working_symbols, f"{(working_symbols/total_symbols*100):.1f}%")
    
    with col3:
        st.metric("❌ Failed", failed_symbols, f"{(failed_symbols/total_symbols*100):.1f}%")
    
    st.markdown("---")
    st.caption(f"⏰ Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Sector / Company / Symbol / Weight (%) table so user knows the data source
    st.markdown("### 📋 Sector–Company data (used by all tabs)")
    try:
        from company_symbols import SECTOR_COMPANIES
        table_rows = []
        for sector in sorted(SECTOR_COMPANIES.keys()):
            for symbol, info in SECTOR_COMPANIES[sector].items():
                table_rows.append({
                    'Sector': sector,
                    'Company Name': info.get('name', symbol),
                    'Symbol': symbol,
                    'Weight (%)': info.get('weight', 0),
                })
        if table_rows:
            df_sc = pd.DataFrame(table_rows)
            st.dataframe(
                df_sc,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Sector": st.column_config.TextColumn("Sector", width="medium"),
                    "Company Name": st.column_config.TextColumn("Company Name", width="large"),
                    "Symbol": st.column_config.TextColumn("Symbol", width="small"),
                    "Weight (%)": st.column_config.NumberColumn("Weight (%)", width="small", format="%.1f"),
                },
            )
            st.caption("This list is loaded from Sector-Company.xlsx (sheet 'Main'). **Restart the app** after editing the Excel to see updated company names. No company appears in more than one sector.")
        else:
            st.info("No sector–company data loaded.")
    except Exception as e:
        st.warning(f"Could not load sector–company table: {e}")


def calculate_fibonacci_levels(high, low):
    """
    Calculate Fibonacci retracement levels.
    Returns dict with fib levels: 0.236, 0.382, 0.5, 0.618, 0.786
    """
    diff = high - low
    return {
        0.236: high - (diff * 0.236),
        0.382: high - (diff * 0.382),
        0.5: high - (diff * 0.5),
        0.618: high - (diff * 0.618),
        0.786: high - (diff * 0.786)
    }


def find_swing_high_low(data, lookback_days=20):
    """
    Find swing high and swing low based on day's HIGH and LOW (not close).
    Looks within last N days.
    
    Args:
        data: DataFrame with daily OHLC data
        lookback_days: Number of days to look back (default 20)
    
    Returns:
        Tuple of (swing_high, swing_low, swing_high_date, swing_low_date)
    """
    if len(data) < lookback_days:
        lookback_days = len(data)
    
    recent_data = data.tail(lookback_days)
    
    # Find swing high (highest HIGH in the period)
    swing_high_idx = recent_data['High'].idxmax()
    swing_high = recent_data.loc[swing_high_idx, 'High']
    swing_high_date = swing_high_idx
    
    # Find swing low (lowest LOW in the period)
    swing_low_idx = recent_data['Low'].idxmin()
    swing_low = recent_data.loc[swing_low_idx, 'Low']
    swing_low_date = swing_low_idx
    
    return swing_high, swing_low, swing_high_date, swing_low_date


def check_fibonacci_golden_zone(price, fib_levels):
    """
    Check if price is near Fibonacci 0.5 (golden level) within 2%.
    
    Returns:
        Tuple of (is_in_zone, fib_level, distance_pct)
        fib_level: '0.5' or None
        distance_pct: % distance from fib 0.5 level
    """
    fib_50 = fib_levels[0.5]
    
    # Check if price is near 0.5 (within 2%)
    dist = abs(price - fib_50) / fib_50 * 100
    if dist < 2.0:
        return True, '0.5', dist
    
    return False, None, None


def find_last_crossing_time(data, fib_level, current_price):
    """
    Find last time when stock price crossed the Fibonacci level.
    
    Args:
        data: DataFrame with OHLC data
        fib_level: Fibonacci level value
        current_price: Current stock price
    
    Returns:
        String with last crossing time or "N/A"
    """
    # Check if price crossed from below to above or vice versa
    for i in range(len(data) - 1, 0, -1):
        prev_price = data.iloc[i-1]['Close']
        curr_price = data.iloc[i]['Close']
        
        # Check if crossed the fib level
        if (prev_price <= fib_level <= curr_price) or (prev_price >= fib_level >= curr_price):
            return data.index[i].strftime('%Y-%m-%d %H:%M')
    
    return "N/A"


def display_market_breadth_block(benchmark_data, analysis_date=None):
    """
    Display Market Breadth: Nifty 50 price, Advance/Total %, Advances, Declines.
    Always visible above the tabs.
    """
    if benchmark_data is None or len(benchmark_data) == 0:
        st.markdown("### 📈 Market Breadth (Nifty 50)")
        st.info("⚠️ Benchmark data not available for market breadth.")
        st.markdown("---")
        return
    
    NIFTY50_SYMBOLS = [
        'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS',
        'SBIN.NS', 'BHARTIARTL.NS', 'HINDUNILVR.NS', 'ITC.NS', 'KOTAKBANK.NS',
        'LT.NS', 'AXISBANK.NS', 'ASIANPAINT.NS', 'MARUTI.NS', 'TITAN.NS',
        'NESTLEIND.NS', 'ULTRACEMCO.NS', 'WIPRO.NS', 'SUNPHARMA.NS', 'TATAMOTORS.NS',
        'TECHM.NS', 'HCLTECH.NS', 'BAJFINANCE.NS', 'JSWSTEEL.NS', 'TATASTEEL.NS',
        'POWERGRID.NS', 'NTPC.NS', 'ONGC.NS', 'COALINDIA.NS', 'ADANIENT.NS',
        'ADANIPORTS.NS', 'GRASIM.NS', 'DIVISLAB.NS', 'CIPLA.NS', 'DRREDDY.NS',
        'BAJAJFINSV.NS', 'M&M.NS', 'HEROMOTOCO.NS', 'EICHERMOT.NS', 'MARICO.NS',
        'GODREJCP.NS', 'DABUR.NS', 'BRITANNIA.NS', 'HDFCLIFE.NS', 'SBILIFE.NS',
        'ICICIPRULI.NS', 'HDFCAMC.NS', 'BAJAJ-AUTO.NS', 'INDUSINDBK.NS', 'APOLLOHOSP.NS'
    ]
    
    from datetime import datetime as dt
    end_dt = dt.combine(analysis_date, dt.min.time()) if analysis_date else None
    
    # Use actual Nifty index (^NSEI), not benchmark/ETF proxy, for the displayed price
    nifty_price = None
    nifty_index_data = fetch_sector_data('^NSEI', end_date=end_dt, interval='1d')
    if nifty_index_data is not None and len(nifty_index_data) > 0:
        nifty_price = float(nifty_index_data['Close'].iloc[-1])
    
    # Fetch Nifty 50 constituents in parallel for Advance/Total (no end_dt so we get latest)
    symbols_dict = {sym: sym for sym in NIFTY50_SYMBOLS[:50]}
    breadth_data, _ = fetch_all_sectors_parallel(symbols_dict, end_date=end_dt, interval='1d')
    if not breadth_data and end_dt is not None:
        breadth_data, _ = fetch_all_sectors_parallel(symbols_dict, end_date=None, interval='1d')
    # Build Close series per symbol (same pattern as Market Breadth tab)
    nifty_closes = {}
    for sym, data in (breadth_data or {}).items():
        if data is not None and len(data) >= 2 and 'Close' in data.columns:
            nifty_closes[sym] = data['Close']
    advances = 0
    declines = 0
    # Use last two bars directly (most reliable for advance/decline)
    if nifty_closes:
        for sym, series in nifty_closes.items():
            if len(series) < 2:
                continue
            try:
                close_t = float(series.iloc[-1])
                close_prev = float(series.iloc[-2])
                if close_t > close_prev:
                    advances += 1
                elif close_t < close_prev:
                    declines += 1
            except Exception:
                continue
    total_ad = advances + declines
    unchanged = len(nifty_closes) - total_ad if nifty_closes else 0
    advance_total_pct = round((advances / total_ad * 100), 1) if total_ad else None

    # Display Market Breadth metrics (always show Advances, Declines, Advance/Total %)
    st.markdown("### 📈 Market Breadth (Nifty 50)")
    bc1, bc2, bc3, bc4 = st.columns(4)
    with bc1:
        nifty_display = f"₹{int(round(nifty_price, 0)):,}" if nifty_price is not None else "N/A"
        st.metric("Nifty 50", nifty_display)
    with bc2:
        st.metric("Advances", advances if total_ad else "0")
    with bc3:
        st.metric("Declines", declines if total_ad else "0")
    with bc4:
        val = f"{advance_total_pct}%" if advance_total_pct is not None else "N/A"
        delta = None
        if advance_total_pct is not None:
            if advance_total_pct > 60:
                delta = "Bullish"
            elif advance_total_pct < 40:
                delta = "Bearish"
        st.metric("Advance/Total %", val, delta=delta)
    if not total_ad and (breadth_data or nifty_closes):
        st.caption("Advance/Decline could not be computed for the last trading day. Check data delay or try again.")
    st.markdown("---")


def display_market_breadth_tab(benchmark_data, analysis_date=None, sector_data_dict=None, momentum_weights=None):
    """
    Market breadth tab: last 20 trading days table.
    Columns: Date, Day, Advances, Declines, Advance/Total %, % Above 20 DMA, % Above 50 DMA, Nifty, Nifty Chg %
    Color: Red <25%, Yellow 25-50%, Green >50%. Bottom row = 20-day average for % 20 DMA, % 50 DMA, Nifty Chg %.
    """
    if benchmark_data is None or len(benchmark_data) < 22:
        st.markdown("### 📊 Market breadth")
        st.warning("⚠️ Need at least 22 trading days of benchmark data for the 20-day table.")
        return

    # Use the same universe as Sector-Company.xlsx; fallback to Nifty 50 if empty (e.g. Cloud deploy without Excel)
    from company_symbols import SECTOR_COMPANIES
    _breadth_nifty50 = [
        'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS',
        'SBIN.NS', 'BHARTIARTL.NS', 'HINDUNILVR.NS', 'ITC.NS', 'KOTAKBANK.NS',
        'LT.NS', 'AXISBANK.NS', 'ASIANPAINT.NS', 'MARUTI.NS', 'TITAN.NS',
        'NESTLEIND.NS', 'ULTRACEMCO.NS', 'WIPRO.NS', 'SUNPHARMA.NS', 'TATAMOTORS.NS',
        'TECHM.NS', 'HCLTECH.NS', 'BAJFINANCE.NS', 'JSWSTEEL.NS', 'TATASTEEL.NS',
        'POWERGRID.NS', 'NTPC.NS', 'ONGC.NS', 'COALINDIA.NS', 'ADANIENT.NS',
        'ADANIPORTS.NS', 'GRASIM.NS', 'DIVISLAB.NS', 'CIPLA.NS', 'DRREDDY.NS',
        'BAJAJFINSV.NS', 'M&M.NS', 'HEROMOTOCO.NS', 'EICHERMOT.NS', 'MARICO.NS',
        'GODREJCP.NS', 'DABUR.NS', 'BRITANNIA.NS', 'HDFCLIFE.NS', 'SBILIFE.NS',
        'ICICIPRULI.NS', 'HDFCAMC.NS', 'BAJAJ-AUTO.NS', 'INDUSINDBK.NS', 'APOLLOHOSP.NS'
    ]
    universe_symbols = sorted({sym for sector_dict in SECTOR_COMPANIES.values() for sym in sector_dict.keys()})
    if not universe_symbols:
        universe_symbols = _breadth_nifty50
    n_stocks = len(universe_symbols)
    _min_bars_breadth = 25

    st.markdown("### 📊 Market breadth")
    st.caption(
        f"Last 20 trading days on {n_stocks}-stock universe. "
        "Advance/Total %, % Above 8/20/50 DMA, Nifty Chg %: "
        "🔴 <25% weak | 🟡 25–50% neutral | 🟢 >50% positive (breadth columns)."
    )
    st.markdown("---")

    with st.spinner("Building 20-day market breadth table..."):
        end_dt = benchmark_data.index[-1]
        nifty_index_data = fetch_sector_data('^NSEI', end_date=end_dt, interval='1d')
        symbols_dict = {s: s for s in universe_symbols}
        nifty_fetched, _ = fetch_all_sectors_parallel(symbols_dict, end_date=end_dt, interval='1d')
        nifty_closes = {}
        for sym, d in nifty_fetched.items():
            if d is not None and len(d) >= _min_bars_breadth:
                nifty_closes[sym] = d['Close']
        if not nifty_closes and universe_symbols != _breadth_nifty50:
            symbols_dict_fb = {s: s for s in _breadth_nifty50}
            nifty_fetched, _ = fetch_all_sectors_parallel(symbols_dict_fb, end_date=end_dt, interval='1d')
            for sym, d in nifty_fetched.items():
                if d is not None and len(d) >= _min_bars_breadth:
                    nifty_closes[sym] = d['Close']
        if not nifty_closes:
            st.warning("⚠️ Could not load price data for breadth universe. Table will show Nifty only. Check data source or try again later.")

        # Use last 20 business days (Mon–Fri). Always include T (current/latest trading day).
        t_date = pd.Timestamp(benchmark_data.index[-1]).normalize().date()
        dates_20 = pd.bdate_range(end=t_date, periods=20, freq='B').tolist()
        dates_20 = list(reversed(dates_20))  # oldest first, current day last
        if dates_20 and dates_20[-1].date() != t_date:
            dates_20 = dates_20[:-1] + [pd.Timestamp(t_date)]
        table_rows = []

        for i, date_t in enumerate(dates_20):
            row = {}
            date_str = date_t.strftime('%Y-%m-%d')
            row['Date'] = date_str
            row['Day'] = date_t.strftime('%A')
            # Label the most recent date (last in list) as Current day, not the oldest
            if i == len(dates_20) - 1:
                row['Date'] = date_str + " (Current day)"

            advances = 0
            declines = 0
            above_8 = 0
            above_20 = 0
            above_50 = 0
            total_ad = 0
            total_8 = 0
            total_20 = 0
            total_50 = 0

            for sym, series in nifty_closes.items():
                try:
                    # Normalize index to tz-naive dates so get_indexer matches (avoid datetime vs Timestamp mismatch)
                    series_dates = series.index.tz_localize(None).normalize() if series.index.tz is not None else series.index.normalize()
                    date_ts = pd.Timestamp(date_t).normalize()
                    idx = series_dates.get_indexer([date_ts], method='ffill')[0]
                    if idx < 0 or idx >= len(series) or idx == 0:
                        continue
                    close_t = series.iloc[idx]
                    close_prev = series.iloc[idx - 1]
                    if close_t > close_prev:
                        advances += 1
                    elif close_t < close_prev:
                        declines += 1
                    total_ad += 1
                    if idx >= 7:
                        sma8 = series.rolling(8).mean().iloc[idx]
                        if not pd.isna(sma8):
                            total_8 += 1
                            if close_t > sma8:
                                above_8 += 1
                    if idx >= 19:
                        sma20 = series.rolling(20).mean().iloc[idx]
                        if not pd.isna(sma20):
                            total_20 += 1
                            if close_t > sma20:
                                above_20 += 1
                    if idx >= 49:
                        sma50 = series.rolling(50).mean().iloc[idx]
                        if not pd.isna(sma50):
                            total_50 += 1
                            if close_t > sma50:
                                above_50 += 1
                except Exception:
                    continue

            row['Advances'] = advances
            row['Declines'] = declines
            adv_pct = (advances / total_ad * 100) if total_ad else None
            row['Advance/Total %'] = round(adv_pct, 1) if adv_pct is not None else None
            row['% Above 8 DMA'] = round((above_8 / total_8 * 100), 1) if total_8 else None
            row['% Above 20 DMA'] = round((above_20 / total_20 * 100), 1) if total_20 else None
            row['% Above 50 DMA'] = round((above_50 / total_50 * 100), 1) if total_50 else None

            try:
                if nifty_index_data is not None and len(nifty_index_data) > 0:
                    nifty_dates = nifty_index_data.index.tz_localize(None).normalize() if nifty_index_data.index.tz is not None else nifty_index_data.index.normalize()
                    date_ts_nifty = pd.Timestamp(date_t).normalize()
                    nifty_idx = nifty_dates.get_indexer([date_ts_nifty], method='ffill')[0]
                    if 0 <= nifty_idx < len(nifty_index_data):
                        nifty_close = nifty_index_data['Close'].iloc[nifty_idx]
                        row['Nifty'] = int(round(nifty_close, 0))
                        if nifty_idx > 0:
                            nifty_prev = nifty_index_data['Close'].iloc[nifty_idx - 1]
                            chg = (nifty_close / nifty_prev - 1) * 100
                            row['Nifty Chg %'] = round(chg, 1)
                        else:
                            row['Nifty Chg %'] = None
                    else:
                        row['Nifty'] = None
                        row['Nifty Chg %'] = None
                else:
                    row['Nifty'] = None
                    row['Nifty Chg %'] = None
            except Exception:
                row['Nifty'] = None
                row['Nifty Chg %'] = None

            table_rows.append(row)

        if not table_rows:
            st.info("No rows computed for market breadth.")
            return

        df = pd.DataFrame(table_rows)
        # Sort by Date descending so newest (T) and T-1 appear at top
        if 'Date' in df.columns:
            df['_sort_date'] = df['Date'].str.replace(' (Current day)', '', regex=False)
            df = df.sort_values('_sort_date', ascending=False).drop(columns=['_sort_date'], errors='ignore')
        display_cols = [
            'Date',
            'Day',
            'Advances',
            'Declines',
            'Advance/Total %',
            '% Above 8 DMA',
            '% Above 20 DMA',
            '% Above 50 DMA',
            'Nifty',
            'Nifty Chg %',
        ]
        df = df[[c for c in display_cols if c in df.columns]]

        avg_8 = pd.to_numeric(df['% Above 8 DMA'], errors='coerce').mean()
        avg_20 = pd.to_numeric(df['% Above 20 DMA'], errors='coerce').mean()
        avg_50 = pd.to_numeric(df['% Above 50 DMA'], errors='coerce').mean()
        avg_nifty_chg = pd.to_numeric(df['Nifty Chg %'], errors='coerce').mean()
        summary_row = pd.DataFrame([{
            'Date': '20-day avg',
            'Day': '',
            'Advances': '',
            'Declines': '',
            'Advance/Total %': '',
            '% Above 8 DMA': round(avg_8, 1),
            '% Above 20 DMA': round(avg_20, 1),
            '% Above 50 DMA': round(avg_50, 1),
            'Nifty': '',
            'Nifty Chg %': round(avg_nifty_chg, 1)
        }])
        df = pd.concat([df, summary_row], ignore_index=True)

        def _breadth_color(val):
            if pd.isna(val):
                return ''
            try:
                v = float(val)
                if v < 25:
                    return 'background-color: #E74C3C; color: #fff; font-weight: bold'
                if v <= 50:
                    return 'background-color: #F1C40F; color: #000; font-weight: bold'
                return 'background-color: #27AE60; color: #fff; font-weight: bold'
            except Exception:
                return ''

        def _nifty_chg_color(val):
            """Color for Nifty Chg % based on absolute move (small moves stay neutral)."""
            if pd.isna(val):
                return ''
            try:
                v = float(val)
                av = abs(v)
                if av < 0.3:
                    return ''
                if av <= 0.8:
                    return 'background-color: #F1C40F; color: #000; font-weight: bold'
                if v > 0:
                    return 'background-color: #27AE60; color: #fff; font-weight: bold'
                return 'background-color: #E74C3C; color: #fff; font-weight: bold'
            except Exception:
                return ''

        def style_breadth_row(row):
            res = [''] * len(row)
            for col in ['Advance/Total %', '% Above 8 DMA', '% Above 20 DMA', '% Above 50 DMA', 'Nifty Chg %']:
                if col in row.index:
                    idx = list(row.index).index(col)
                    if col == 'Nifty Chg %':
                        res[idx] = _nifty_chg_color(row[col])
                    else:
                        res[idx] = _breadth_color(row[col])
            return res

        df_styled = df.style.apply(style_breadth_row, axis=1)

        col_config = {
            "Date": st.column_config.TextColumn("Date", width="small"),
            "Day": st.column_config.TextColumn("Day", width="small"),
            "Advances": st.column_config.NumberColumn("Advances", width="small", format="%d"),
            "Declines": st.column_config.NumberColumn("Declines", width="small", format="%d"),
            "Advance/Total %": st.column_config.NumberColumn("Advance/Total %", width="small", format="%.1f"),
            "% Above 8 DMA": st.column_config.NumberColumn("% Above 8 DMA", width="small", format="%.1f"),
            "% Above 20 DMA": st.column_config.NumberColumn("% Above 20 DMA", width="small", format="%.1f"),
            "% Above 50 DMA": st.column_config.NumberColumn("% Above 50 DMA", width="small", format="%.1f"),
            "Nifty": st.column_config.NumberColumn("Nifty", width="small", format="%d"),
            "Nifty Chg %": st.column_config.NumberColumn("Nifty Chg %", width="small", format="%.1f"),
        }

        st.dataframe(
            df_styled,
            use_container_width=True,
            hide_index=True,
            column_config=col_config,
        )

    # ---- Nifty Put-Call Ratio (PCR) ----
    st.markdown("---")
    st.markdown("## 📉 Nifty Put-Call Ratio (PCR)")
    st.caption(
        "PCR = Total Put OI ÷ Total Call OI. "
        "🟢 PCR > 1 = More puts (bullish for market) | 🟡 0.7–1.0 = Neutral | 🔴 PCR < 0.7 = More calls (bearish for market). "
        "Extreme PCR (>1.3 or <0.5) may signal reversal."
    )

    # ------------------------------------------------------------------
    # PCR data source: NSE option chain CSV file (downloaded by user)
    # ------------------------------------------------------------------
    def _pcr_from_csv(csv_path):
        """
        Read NSE option chain CSV and compute PCR.
        NSE CSV format: first row is a title/header, actual column headers in row 2.
        CALLS side has an 'OI' column; PUTS side also has an 'OI' column.
        We look for columns containing 'OI' and sum them for CE and PE sides.
        Returns (pcr, put_oi, call_oi, file_date_str) or (None, None, None, None).
        """
        import os
        from datetime import datetime as _dt
        if not csv_path or not os.path.isfile(csv_path):
            return None, None, None, None
        try:
            file_mod = _dt.fromtimestamp(os.path.getmtime(csv_path)).strftime('%Y-%m-%d %H:%M')
            # NSE CSV has a messy header — try reading with different strategies
            raw = pd.read_csv(csv_path, header=None, dtype=str)

            # Strategy 1: Find the row that contains 'CALLS' and 'PUTS' or 'Strike Price'
            header_row = None
            for i in range(min(5, len(raw))):
                row_str = ' '.join(str(v) for v in raw.iloc[i].values)
                if 'Strike Price' in row_str or 'STRIKE' in row_str.upper():
                    header_row = i
                    break
            if header_row is None:
                # Fallback: just use row 0 or 1
                header_row = 1 if len(raw) > 1 else 0

            df = pd.read_csv(csv_path, header=header_row, dtype=str)
            df.columns = [str(c).strip() for c in df.columns]

            # Find OI columns — NSE typically has two 'OI' columns (one for CE, one for PE)
            # The CE OI is to the LEFT of Strike Price, PE OI is to the RIGHT
            oi_cols = [c for c in df.columns if 'OI' == c.strip().upper() or 'OI' in c.upper()]
            strike_col = None
            for c in df.columns:
                if 'strike' in c.lower():
                    strike_col = c
                    break

            if len(oi_cols) >= 2 and strike_col:
                strike_idx = list(df.columns).index(strike_col)
                call_oi_col = None
                put_oi_col = None
                for c in oi_cols:
                    col_idx = list(df.columns).index(c)
                    if col_idx < strike_idx:
                        call_oi_col = c
                    else:
                        put_oi_col = c
                if call_oi_col and put_oi_col:
                    call_oi = pd.to_numeric(df[call_oi_col].str.replace(',', '').str.replace('-', '0'), errors='coerce').sum()
                    put_oi = pd.to_numeric(df[put_oi_col].str.replace(',', '').str.replace('-', '0'), errors='coerce').sum()
                    if call_oi > 0:
                        return round(put_oi / call_oi, 2), int(put_oi), int(call_oi), file_mod

            # Strategy 2: Sum all numeric columns that look like OI
            # Try matching column names more broadly
            for attempt_cols in [
                ('CALLS_OI', 'PUTS_OI'),
                ('Call OI', 'Put OI'),
            ]:
                if attempt_cols[0] in df.columns and attempt_cols[1] in df.columns:
                    call_oi = pd.to_numeric(df[attempt_cols[0]].str.replace(',', '').str.replace('-', '0'), errors='coerce').sum()
                    put_oi = pd.to_numeric(df[attempt_cols[1]].str.replace(',', '').str.replace('-', '0'), errors='coerce').sum()
                    if call_oi > 0:
                        return round(put_oi / call_oi, 2), int(put_oi), int(call_oi), file_mod

            return None, None, None, file_mod
        except Exception:
            return None, None, None, None

    # Default CSV path on E: drive (user downloads NSE option chain CSV here)
    _pcr_default_dir = r"E:\Personal\Trading_Champion\Projects\Sector-rotation-v2\Sector-rotation-v2"
    _pcr_csv_path = None

    # Auto-detect: look for any CSV with "option" or "NIFTY" in the name in the project folder
    import glob as _glob
    _pcr_candidates = sorted(
        _glob.glob(os.path.join(_pcr_default_dir, '*option*chain*.csv')) +
        _glob.glob(os.path.join(_pcr_default_dir, '*NIFTY*.csv')) +
        _glob.glob(os.path.join(_pcr_default_dir, 'OC-NIFTY*.csv')) +
        _glob.glob(os.path.join(_pcr_default_dir, 'nifty_oc*.csv')),
        key=lambda f: os.path.getmtime(f) if os.path.isfile(f) else 0,
        reverse=True
    )

    pcr_val = None
    put_oi = None
    call_oi = None
    pcr_source = None
    pcr_file_date = None

    # Option 1: Upload CSV directly in the app
    with st.expander("📂 Load Nifty Option Chain CSV for PCR", expanded=not bool(_pcr_candidates)):
        st.markdown(
            "**How to get the CSV:** Go to [NSE Option Chain](https://www.nseindia.com/option-chain) → "
            "Select **NIFTY** → Click **Download (.csv)** → Save to your E: drive project folder, "
            "or upload it here."
        )

        uploaded_csv = st.file_uploader(
            "Upload NSE Option Chain CSV",
            type=['csv'],
            key="pcr_csv_upload"
        )

        if uploaded_csv is not None:
            # Save uploaded file temporarily and parse
            _tmp_path = os.path.join(_pcr_default_dir, 'nifty_oc_uploaded.csv')
            try:
                with open(_tmp_path, 'wb') as f:
                    f.write(uploaded_csv.getvalue())
                pcr_val, put_oi, call_oi, pcr_file_date = _pcr_from_csv(_tmp_path)
                if pcr_val:
                    pcr_source = f"Uploaded CSV"
            except Exception:
                pass

        if not pcr_val and _pcr_candidates:
            st.info(f"Auto-detected CSV: `{os.path.basename(_pcr_candidates[0])}`")

    # Option 2: Auto-detected CSV on E: drive
    if not pcr_val and _pcr_candidates:
        _pcr_csv_path = _pcr_candidates[0]
        pcr_val, put_oi, call_oi, pcr_file_date = _pcr_from_csv(_pcr_csv_path)
        if pcr_val:
            pcr_source = f"CSV: {os.path.basename(_pcr_csv_path)}"

    # Option 3: Manual input fallback
    if not pcr_val:
        st.info(
            "No option chain CSV found. Download from "
            "[NSE Option Chain](https://www.nseindia.com/option-chain) and upload above, "
            "or enter PCR manually."
        )
        pcr_manual = st.number_input(
            "Enter Nifty PCR manually (or leave 0 to skip):",
            min_value=0.0, max_value=3.0, value=0.0, step=0.01,
            key="pcr_manual_input"
        )
        if pcr_manual > 0:
            pcr_val = round(pcr_manual, 2)
            pcr_source = "Manual entry"

    # Display PCR with color coding
    if pcr_val is not None and pcr_val > 0:
        if pcr_val >= 1.3:
            pcr_color = "#E74C3C"
            pcr_label = "Extreme Bearish (potential bullish reversal)"
            pcr_emoji = "🔴"
        elif pcr_val >= 1.0:
            pcr_color = "#27AE60"
            pcr_label = "Bearish bias — Bullish for market"
            pcr_emoji = "🟢"
        elif pcr_val >= 0.7:
            pcr_color = "#F1C40F"
            pcr_label = "Neutral zone"
            pcr_emoji = "🟡"
        elif pcr_val >= 0.5:
            pcr_color = "#E67E22"
            pcr_label = "Bullish bias — Bearish for market"
            pcr_emoji = "🟠"
        else:
            pcr_color = "#E74C3C"
            pcr_label = "Extreme Bullish (potential bearish reversal)"
            pcr_emoji = "🔴"

        col_pcr1, col_pcr2, col_pcr3 = st.columns(3)
        with col_pcr1:
            st.markdown(
                f"<div style='text-align:center; padding:15px; border-radius:10px; "
                f"background-color:{pcr_color}; color:white;'>"
                f"<h2 style='margin:0;'>{pcr_val}</h2>"
                f"<p style='margin:0; font-size:14px;'>Nifty PCR</p></div>",
                unsafe_allow_html=True
            )
        with col_pcr2:
            if put_oi and call_oi:
                st.metric("Total Put OI", f"{put_oi:,.0f}")
                st.metric("Total Call OI", f"{call_oi:,.0f}")
            else:
                st.markdown(f"**Sentiment:** {pcr_emoji} {pcr_label}")
        with col_pcr3:
            st.markdown(f"**Sentiment:** {pcr_emoji} {pcr_label}")
            if pcr_source:
                st.caption(f"Source: {pcr_source}")
            if pcr_file_date:
                st.caption(f"File date: {pcr_file_date}")
            st.markdown("""
**PCR Guide:**
- **> 1.3** — Extreme put buying → potential bullish reversal
- **1.0 – 1.3** — More puts than calls → bullish for market
- **0.7 – 1.0** — Neutral zone
- **0.5 – 0.7** — More calls than puts → bearish for market
- **< 0.5** — Extreme call buying → potential bearish reversal
""")

    # Nifty - Fibonacci Analysis (below breadth table)
    st.markdown("---")
    st.markdown("## 🔢 Nifty - Fibonacci Analysis")
    st.markdown("---")
    with st.spinner("Calculating Nifty Fibonacci levels..."):
        try:
            end_dt = benchmark_data.index[-1]
            nifty_daily = fetch_sector_data('^NSEI', end_date=end_dt, interval='1d')
            if nifty_daily is not None and len(nifty_daily) >= 20:
                swing_high, swing_low, swing_high_date, swing_low_date = find_swing_high_low(nifty_daily, lookback_days=20)
                fib_levels = calculate_fibonacci_levels(swing_high, swing_low)
                current_nifty_price = nifty_daily['Close'].iloc[-1]
                in_zone, fib_level, distance = check_fibonacci_golden_zone(current_nifty_price, fib_levels)
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("### 📊 Swing Points (Last 20 Days)")
                    st.write(f"**Swing High:** ₹{swing_high:,.2f} ({swing_high_date.strftime('%Y-%m-%d')})")
                    st.write(f"**Swing Low:** ₹{swing_low:,.2f} ({swing_low_date.strftime('%Y-%m-%d')})")
                    st.write(f"**Current Price:** ₹{current_nifty_price:,.2f}")
                with col2:
                    st.markdown("### 🔢 Fibonacci Levels")
                    st.write(f"**0.236:** ₹{fib_levels[0.236]:,.2f}")
                    st.write(f"**0.382:** ₹{fib_levels[0.382]:,.2f}")
                    st.write(f"**0.500:** ₹{fib_levels[0.5]:,.2f} ⭐ Golden Level")
                    st.write(f"**0.618:** ₹{fib_levels[0.618]:,.2f}")
                    st.write(f"**0.786:** ₹{fib_levels[0.786]:,.2f}")
                if in_zone:
                    st.success(f"✅ Nifty is near Fib 0.5 (Golden Level) - Distance: {distance:.2f}%")
                else:
                    st.info(f"ℹ️ Nifty is not near Fib 0.5 level")
            else:
                st.warning("⚠️ Insufficient Nifty data for Fibonacci analysis")
        except Exception as e:
            st.error(f"❌ Error in Nifty Fibonacci analysis: {str(e)}")


def display_stock_analysis_tab(analysis_date=None, benchmark_data=None, momentum_weights=None):
    """
    Stock Screener: Top 10 bullish and Top 10 bearish stocks by momentum score.
    
    Args:
        analysis_date: Date for analysis
        benchmark_data: Nifty 50 benchmark data (for RS Rating)
        momentum_weights: Dict of momentum weights for scoring
    """
    from datetime import datetime as dt
    from company_symbols import SECTOR_COMPANIES
    from indicators import calculate_rsi, calculate_adx, calculate_z_score
    
    st.markdown("### 📊 Stock Screener: Top 10 Bullish & Top 10 Bearish")
    st.markdown("---")
    
    if benchmark_data is None or len(benchmark_data) < 14:
        st.warning("⚠️ Benchmark data required for stock screener. Run analysis first.")
        return
    
    if momentum_weights is None:
        momentum_weights = DEFAULT_MOMENTUM_WEIGHTS
    
    # Collect all companies from SECTOR_COMPANIES (exclude Nifty 50)
    all_companies = []
    for sector, syms in SECTOR_COMPANIES.items():
        if sector == 'Nifty 50':
            continue
        for sym, info in syms.items():
            all_companies.append((sector, sym, info.get('name', sym)))
    
    if not all_companies:
        st.warning("⚠️ No companies found in SECTOR_COMPANIES.")
        return
    
    end_dt = dt.combine(analysis_date, dt.min.time()) if analysis_date else None
    symbols_dict = {sym: sym for sector, sym, _ in all_companies}
    
    with st.spinner("Fetching company data for screener..."):
        company_data_raw, _ = fetch_all_sectors_parallel(symbols_dict, end_date=end_dt, interval='1d')
    
    # Score each company by momentum (RS Rating, ADX Z, RSI, DI Spread)
    company_scores = []
    for sector, sym, name in all_companies:
        d = company_data_raw.get(sym)
        if d is None or len(d) < 14:
            continue
        try:
            bench_sub = benchmark_data.iloc[:min(len(d), len(benchmark_data))]
            if len(bench_sub) < 14:
                continue
            rsi = calculate_rsi(d)
            adx, _, _, di_spread = calculate_adx(d)
            adx_z = calculate_z_score(adx.dropna())
            sr = d['Close'].pct_change().dropna()
            br = bench_sub['Close'].pct_change().dropna()
            common = sr.index.intersection(br.index)
            rs_rating = 5.0
            if len(common) > 1:
                cr = (1 + sr.loc[common]).prod() - 1
                cb = (1 + br.loc[common]).prod() - 1
                if not pd.isna(cr) and not pd.isna(cb):
                    rs_rating = max(0, min(10, 5 + (cr - cb) * 25))
            rsi_val = float(rsi.iloc[-1]) if not rsi.isna().all() else 50
            di_val = float(di_spread.iloc[-1]) if not di_spread.isna().all() else 0
            adx_z_val = float(adx_z) if not pd.isna(adx_z) else 0
            company_scores.append({
                'Symbol': sym, 'Name': name, 'Sector': sector,
                'rsi': rsi_val, 'adx_z': adx_z_val, 'rs_rating': rs_rating, 'di_spread': di_val
            })
        except Exception:
            continue
    
    if not company_scores:
        st.warning("⚠️ No company data available for screener")
        return
    
    df_c = pd.DataFrame(company_scores)
    df_c['ADX_Z_Rank'] = df_c['adx_z'].rank(ascending=False, method='average')
    df_c['RS_Rating_Rank'] = df_c['rs_rating'].rank(ascending=False, method='average')
    df_c['RSI_Rank'] = df_c['rsi'].rank(ascending=False, method='average')
    df_c['DI_Spread_Rank'] = df_c['di_spread'].rank(ascending=False, method='average')
    tw = sum(momentum_weights.values()) or 1
    df_c['Score'] = (
        df_c['ADX_Z_Rank'] * momentum_weights.get('ADX_Z', 20) / tw +
        df_c['RS_Rating_Rank'] * momentum_weights.get('RS_Rating', 40) / tw +
        df_c['RSI_Rank'] * momentum_weights.get('RSI', 30) / tw +
        df_c['DI_Spread_Rank'] * momentum_weights.get('DI_Spread', 10) / tw
    )
    df_c = df_c.sort_values('Score', ascending=True)
    
    top15_bullish = df_c.head(10)
    top15_bearish = df_c.tail(10).iloc[::-1]
    
    display_cols = ['Sector', 'Symbol', 'Name', 'RS_Rating', 'RSI', 'ADX_Z', 'DI_Spread', 'Score']
    df_c['RS_Rating'] = df_c['rs_rating']
    df_c['ADX_Z'] = df_c['adx_z']
    df_c['DI_Spread'] = df_c['di_spread']
    
    def style_screener_row(row):
        res = [''] * len(row)
        if 'Score' in row.index:
            idx = list(row.index).index('Score')
            res[idx] = 'background-color: #27AE60; color: #fff; font-weight: bold'
        return res
    
    def style_screener_bear_row(row):
        res = [''] * len(row)
        if 'Score' in row.index:
            idx = list(row.index).index('Score')
            res[idx] = 'background-color: #E74C3C; color: #fff; font-weight: bold'
        return res
    
    st.markdown("#### 🟢 Top 10 Bullish (by Momentum Score)")
    bull_cols = [c for c in display_cols if c in top15_bullish.columns]
    df_bull = top15_bullish[bull_cols].copy()
    df_bull_styled = df_bull.style.apply(lambda r: ['background-color: #d4edda; color: #000' if i < len(r) else '' for i in range(len(r))], axis=1)
    st.dataframe(df_bull, use_container_width=True, hide_index=True)
    
    st.markdown("#### 🔴 Top 10 Bearish (by Momentum Score)")
    bear_cols = [c for c in display_cols if c in top15_bearish.columns]
    df_bear = top15_bearish[bear_cols].copy()
    st.dataframe(df_bear, use_container_width=True, hide_index=True)
    
    st.caption("🟢 Bullish = lowest rank sum (best momentum). 🔴 Bearish = highest rank sum (weakest momentum).")
    st.success(f"✅ Screener complete! Analyzed {len(company_scores)} stocks from SECTOR_COMPANIES.")


def _compute_screener_score(daily, hourly, w_vwap_above=1.0, w_vwap_approach=0.5):
    """
    MA+RSI+VWAP scoring: 1 pt each for RSI (1W/1D/1H) up, 1 pt each for Price > 8/20/50 SMA,
    plus VWAP (1H). RSI divergence not used. Returns score (higher = more bullish).
    """
    if daily is None or len(daily) < 60:
        return None
    try:
        price = float(daily["Close"].iloc[-1])
        sma8 = daily["Close"].rolling(8).mean().iloc[-1]
        sma20 = daily["Close"].rolling(20).mean().iloc[-1]
        sma50 = daily["Close"].rolling(50).mean().iloc[-1]
        p_gt_8 = "Yes" if not pd.isna(sma8) and price > sma8 else "No"
        p_gt_20 = "Yes" if not pd.isna(sma20) and price > sma20 else "No"
        p_gt_50 = "Yes" if not pd.isna(sma50) and price > sma50 else "No"
        rsi_d = calculate_rsi(daily)
        rsi_1d_val = float(rsi_d.iloc[-1]) if len(rsi_d.dropna()) >= 2 else None
        rsi_1d_prev = float(rsi_d.iloc[-2]) if len(rsi_d.dropna()) >= 2 else None
        weekly = daily.resample("W").last()
        rsi_w = calculate_rsi(weekly)
        rsi_1w_val = float(rsi_w.iloc[-1]) if len(rsi_w.dropna()) >= 2 else None
        rsi_1w_prev = float(rsi_w.iloc[-2]) if len(rsi_w.dropna()) >= 2 else None
        rsi_1h_val = rsi_1h_prev = None
        if hourly is not None and len(hourly) >= 30:
            rsi_h = calculate_rsi(hourly)
            rsi_1h_val = float(rsi_h.iloc[-1]) if len(rsi_h.dropna()) >= 2 else None
            rsi_1h_prev = float(rsi_h.iloc[-2]) if len(rsi_h.dropna()) >= 2 else None

        def _dir(cur, prev):
            if cur is None or prev is None:
                return "N/A"
            if cur > prev + 1:
                return "Up"
            if cur < prev - 1:
                return "Down"
            return "Flat"

        rsi_1w_dir = _dir(rsi_1w_val, rsi_1w_prev)
        rsi_1d_dir = _dir(rsi_1d_val, rsi_1d_prev)
        rsi_1h_dir = _dir(rsi_1h_val, rsi_1h_prev)
        vwap_relation = "N/A"
        if hourly is not None and len(hourly) > 0:
            last_day = hourly.index[-1].date()
            day_mask = hourly.index.date == last_day
            day_data = hourly[day_mask]
            if not day_data.empty:
                if "Volume" in day_data.columns and day_data["Volume"].sum() > 0:
                    vwap = (day_data["Close"] * day_data["Volume"]).sum() / day_data["Volume"].sum()
                else:
                    vwap = day_data["Close"].mean()
                if vwap:
                    diff_pct = (price / vwap - 1) * 100
                    vwap_relation = "Above" if diff_pct > 0.5 else ("Approaching" if abs(diff_pct) <= 0.5 else "Below")

        score = 0.0
        if rsi_1w_dir == "Up":
            score += 1.0
        if rsi_1d_dir == "Up":
            score += 1.0
        if rsi_1h_dir == "Up":
            score += 1.0
        if p_gt_8 == "Yes":
            score += 1.0
        if p_gt_20 == "Yes":
            score += 1.0
        if p_gt_50 == "Yes":
            score += 1.0
        if vwap_relation == "Above":
            score += w_vwap_above
        elif vwap_relation == "Approaching":
            score += w_vwap_approach
        return round(score, 2)
    except Exception:
        return None


def _compute_confluence_score(data_entry_raw, data_1d=None, timeframe='2h'):
    """
    Fixed confluence scoring using separate bullish/bearish logic + 2 timeframes.

    Parameters
    ----------
    data_entry_raw : DataFrame
        If timeframe='2h': 1H data (resampled to 2H internally).
        If timeframe='1d': daily data (used directly as entry TF).
    data_1d : DataFrame or None
        Daily data for 1D confirmation. If None and timeframe='1d', data_entry_raw is used for both.
    timeframe : str
        '2h' or '1d'.

    Returns
    -------
    (bullish_score, bearish_score, details_dict) or (None, None, None) on failure.
    """
    from confluence_fixed import (
        analyze_stock_confluence,
        calculate_confluence_score_bullish,
        calculate_confluence_score_bearish,
    )
    if data_entry_raw is None:
        return None, None, None
    try:
        # If no separate daily data provided and timeframe is 1d, use same data for both
        if data_1d is None and timeframe == '1d':
            data_1d = data_entry_raw

        analysis = analyze_stock_confluence(data_entry_raw, data_1d, entry_timeframe=timeframe)
        if analysis is None:
            return None, None, None

        b_score, _ = calculate_confluence_score_bullish(analysis)
        s_score, _ = calculate_confluence_score_bearish(analysis)

        details = {
            'Trend': analysis['trend_entry'],
            'Trend_1D': analysis['trend_1d'],
            'Direction': analysis['ma_alignment_entry'],
            'Direction_1D': analysis['ma_alignment_1d'],
            'RSI': f"{analysis['rsi_entry']}",
            'RSI_1D': f"{analysis['rsi_1d']}",
            'Setup': analysis['ma_crossover_entry'],
            'Divergence': analysis['divergence'],
        }
        return b_score, s_score, details
    except Exception:
        return None, None, None


def display_stock_screener_tab(analysis_date=None, benchmark_data=None, sector_data_dict=None, momentum_weights=None, df_momentum=None):
    """
    Stock Screener (MA+RSI+VWAP) on sector-company universe (from Sector-Company.xlsx, sheet Main).
    Sector filter: **Top 4 + Bottom 6 (per Momentum Ranking)** = stocks from top 4 sectors (bullish) + bottom 6 sectors (bearish); **Universal** = all sectors.

    Scoring: 1 pt each for RSI (1W/1D/1H) up, 1 pt each for Price > 8/20/50 SMA, + VWAP (1H). RSI divergence not used.
    Columns:
    - Company
    - Price (closing at analysis date)
    - RSI (1W) with direction
    - RSI (1D) with direction
    - RSI (1H) with direction
    - Price > 8 SMA / 20 SMA / 50 SMA (daily)
    - Price vs VWAP (1H): Above / Approaching / Below
    - RSI divergence (2H) on same day: Yes / No (simple higher-high / lower-high check)
    - Final score (higher = stronger bullish setup)
    """
    from datetime import datetime as dt
    from company_symbols import SECTOR_COMPANIES, SECTOR_COMPANY_EXCEL_PATH_USED

    # Initialize variables used in export section
    historical_logs = []
    fib_results = []
    stock_results = []
    df_results = pd.DataFrame()
    df_top10 = pd.DataFrame()
    total_market_stocks = 0

    st.markdown("---")
    st.header("📊 Stock Screener")

    # ============================================================
    # SECTOR FILTER TOGGLE – focus on top momentum sectors
    # ============================================================
    st.markdown("### 🎯 Sector Selection Strategy")

    col_toggle, col_info = st.columns([1, 2])

    with col_toggle:
        sector_filter = st.radio(
            "Select sector universe:",
            options=["Top 4 + Bottom 6 (per Momentum Ranking)", "Universal (All Sectors)"],
            index=st.session_state.get("_conf_sector_idx", 0),
            key="stock_screener_sector_filter",
            help="**Top 4 + Bottom 6:** Bullish from top 4 sectors, bearish from bottom 6 (per Momentum Ranking). **Universal:** All sectors.",
        )
        st.session_state["_conf_sector_idx"] = [
            "Top 4 + Bottom 6 (per Momentum Ranking)",
            "Universal (All Sectors)",
        ].index(sector_filter)

    top_sectors = None
    bot_sectors = None

    def _top_bottom_from_df(d):
        """Get top 4 and bottom 6 sector names from Momentum-tab df. Returns (top_list, bottom_list) or (None, None)."""
        if d is None or d.empty or 'Sector' not in d.columns:
            return None, None
        try:
            score_col = 'Momentum_Score' if 'Momentum_Score' in d.columns else None
            if score_col is None:
                return None, None
            scores = pd.to_numeric(d[score_col], errors='coerce')
            if scores.isna().all():
                return None, None
            sorted_df = d.assign(_ms=scores).sort_values('_ms', ascending=False)
            top = sorted_df.head(4)['Sector'].tolist()
            bot = sorted_df.tail(6)['Sector'].tolist()
            return top, bot
        except Exception:
            return None, None

    with col_info:
        top_from_df, bot_from_df = _top_bottom_from_df(df_momentum)
        if top_from_df is not None:
            if sector_filter == "Top 4 + Bottom 6 (per Momentum Ranking)":
                top_sectors = top_from_df
                bot_sectors = bot_from_df
                st.info("**Confluence pertains to top 4 sectors (bullish) and bottom 6 sectors (bearish) per Momentum Ranking** for this date.")
                if top_sectors:
                    st.success(f"**✅ Bullish (top 4):** {', '.join(top_sectors)}")
                if bot_sectors:
                    st.warning(f"**⚠️ Bearish (bottom 6):** {', '.join(bot_sectors)}")
            else:
                st.info("**📊 Universal:** Scanning all stocks from all sectors.")
        elif sector_data_dict and momentum_weights:
            try:
                from confluence_fixed import get_bottom_n_sectors_by_momentum
                if sector_filter == "Top 4 + Bottom 6 (per Momentum Ranking)":
                    top_sectors = get_top_n_sectors_by_momentum(sector_data_dict, momentum_weights, n=4)
                    bot_sectors = get_bottom_n_sectors_by_momentum(sector_data_dict, momentum_weights, n=6)
                    st.info("**Confluence pertains to top 4 (bullish) and bottom 6 (bearish) sectors** per Momentum Ranking.")
                    if top_sectors:
                        st.success(f"**✅ Bullish:** {', '.join(top_sectors)}")
                    if bot_sectors:
                        st.warning(f"**⚠️ Bearish:** {', '.join(bot_sectors)}")
                else:
                    st.info("**📊 Universal:** Scanning all stocks from all sectors.")
            except Exception:
                top_retry, bot_retry = _top_bottom_from_df(df_momentum)
                if top_retry is not None and sector_filter == "Top 4 + Bottom 6 (per Momentum Ranking)":
                    top_sectors, bot_sectors = top_retry, bot_retry
                    st.info("**Confluence pertains to top 4 + bottom 6 sectors** (fallback).")
                    if top_sectors:
                        st.success(f"**✅ Bullish:** {', '.join(top_sectors)}")
                    if bot_sectors:
                        st.warning(f"**⚠️ Bearish:** {', '.join(bot_sectors)}")
                else:
                    st.warning("⚠️ Could not determine sectors — using all sectors.")
        else:
            st.info("**📊 Universal:** Sector data not available — using all sectors.")

    # ============================================================
    # ENTRY STRATEGY GUIDE – HL (Higher Low) explanation
    # ============================================================
    with st.expander("📘 Bullish Entry Strategy: Why enter at HL (Higher Low)?"):
        st.markdown(
            """
        ### 🎯 Higher Low (HL) = Ideal Bullish Entry Point

        1. **Support confirmation** – price bounces from HL support, showing demand.
        2. **Trend intact** – HL in an uptrend means continuation, not reversal.
        3. **Tight stop loss** – stop can sit just below HL (1–2%).
        4. **Great Risk/Reward** – small risk to HL vs. large potential to next HH.

        **Multi-timeframe technique**
        - Daily: identify the HL zone and confirm HH/HL structure.
        - 4H / 1H: wait for bullish engulfing / RSI divergence / breakout near HL
          before entering, rather than buying the first touch.
        """
        )

    st.markdown("---")

    # ============================================================
    # BUILD UNIVERSE WITH SECTOR FILTER
    # ============================================================
    sectors_to_analyze = None
    if sector_filter == "Top 4 + Bottom 6 (per Momentum Ranking)" and (top_sectors or bot_sectors):
        sectors_to_analyze = set(top_sectors or []) | set(bot_sectors or [])

    universe = []
    for sector, syms in SECTOR_COMPANIES.items():
        if sectors_to_analyze and sector not in sectors_to_analyze:
            continue
        for sym, info in syms.items():
            universe.append((sector, sym, info.get("name", sym)))

    if sectors_to_analyze:
        label = "Top 4 + Bottom 6" if sector_filter == "Top 4 + Bottom 6 (per Momentum Ranking)" else "Universal"
        st.markdown(f"### 📊 Stock Screener ({len(universe)} Stocks from {len(sectors_to_analyze)} {label} Sectors)")
    else:
        st.markdown(f"### 📊 Stock Screener ({len(universe)} Stocks from All Sectors)")

    path_display = SECTOR_COMPANY_EXCEL_PATH_USED or "Sector-Company.xlsx"
    st.caption(f"Company names from: **{path_display}** — use **Sector Companies** tab → **Reload from Excel** after editing.")

    # Show TIINDIA.NS name so user can confirm Excel is applied
    _ti_name = None
    for _s, _syms in SECTOR_COMPANIES.items():
        if "TIINDIA.NS" in _syms:
            _ti_name = _syms["TIINDIA.NS"].get("name")
            break
    if _ti_name is not None:
        st.caption(f"✓ Check: TIINDIA.NS is shown as **{_ti_name}** (from Excel).")

    st.markdown("---")

    if not universe:
        st.warning("⚠️ No companies found in selected sectors.")
        return

    # Use last 10 trading days for dropdown, descending (today/latest first)
    if benchmark_data is not None and not benchmark_data.empty:
        all_dates = list(dict.fromkeys([d.date() for d in benchmark_data.index]))
        last_10 = all_dates[-10:] if len(all_dates) > 10 else all_dates
        available_dates = sorted(last_10, reverse=True)
    else:
        today = datetime.today().date()
        available_dates = [today]

    default_date = analysis_date or (available_dates[0] if available_dates else datetime.today().date())
    selected_date = st.selectbox(
        "Select analysis date (past 10 days):",
        options=available_dates,
        index=available_dates.index(default_date) if default_date in available_dates else 0,
        format_func=lambda d: d.strftime("%Y-%m-%d")
    )

    end_dt = dt.combine(selected_date, dt.min.time())

    if not universe:
        st.warning("⚠️ No companies found in Sector-Company universe.")
        return

    # Scoring: MA+RSI+VWAP (1 pt each for RSI 1W/1D/1H up, 1 pt each for Price > 8/20/50 SMA; RSI divergence removed)
    with st.expander("⚙️ Scoring weights (optional) – MA+RSI+VWAP", expanded=False):
        w_vwap_above = st.slider("Weight: Price above VWAP (1H)", 0.0, 5.0, 1.0, 0.5)
        w_vwap_approach = st.slider("Weight: Price approaching VWAP (1H)", 0.0, 5.0, 0.5, 0.5)

    results = []
    progress = st.progress(0.0)
    status = st.empty()

    total = len(universe)
    for idx, (sector, symbol, name) in enumerate(universe):
        status.text(f"Analyzing {name} ({symbol}) [{idx+1}/{total}]...")
        progress.progress((idx + 1) / total)

        try:
            # Daily data
            daily = fetch_sector_data(symbol, end_date=end_dt, interval="1d")
            if daily is None or len(daily) < 60:
                continue

            # Hourly data (for RSI 1H, VWAP, 2H divergence)
            hourly = fetch_sector_data(symbol, end_date=end_dt, interval="1h")

            # --- Price and SMAs (daily) ---
            price = float(daily["Close"].iloc[-1])
            sma8 = daily["Close"].rolling(8).mean().iloc[-1]
            sma20 = daily["Close"].rolling(20).mean().iloc[-1]
            sma50 = daily["Close"].rolling(50).mean().iloc[-1]

            def yesno(cond):
                return "Yes" if cond else "No"

            p_gt_8 = yesno(price > sma8) if not pd.isna(sma8) else "N/A"
            p_gt_20 = yesno(price > sma20) if not pd.isna(sma20) else "N/A"
            p_gt_50 = yesno(price > sma50) if not pd.isna(sma50) else "N/A"

            # --- RSI 1D (daily) ---
            rsi_d = calculate_rsi(daily)
            rsi_1d_val = float(rsi_d.iloc[-1]) if len(rsi_d.dropna()) >= 2 else None
            rsi_1d_prev = float(rsi_d.iloc[-2]) if len(rsi_d.dropna()) >= 2 else None

            # Weekly from daily resample
            weekly = daily.resample("W").last()
            rsi_w = calculate_rsi(weekly)
            rsi_1w_val = float(rsi_w.iloc[-1]) if len(rsi_w.dropna()) >= 2 else None
            rsi_1w_prev = float(rsi_w.iloc[-2]) if len(rsi_w.dropna()) >= 2 else None

            # RSI 1H from hourly
            if hourly is not None and len(hourly) >= 30:
                rsi_h = calculate_rsi(hourly)
                rsi_1h_val = float(rsi_h.iloc[-1]) if len(rsi_h.dropna()) >= 2 else None
                rsi_1h_prev = float(rsi_h.iloc[-2]) if len(rsi_h.dropna()) >= 2 else None
            else:
                rsi_1h_val = rsi_1h_prev = None

            def rsi_direction(cur, prev):
                if cur is None or prev is None:
                    return "N/A"
                if cur > prev + 1:
                    return "Up"
                if cur < prev - 1:
                    return "Down"
                return "Flat"

            rsi_1w_dir = rsi_direction(rsi_1w_val, rsi_1w_prev)
            rsi_1d_dir = rsi_direction(rsi_1d_val, rsi_1d_prev)
            rsi_1h_dir = rsi_direction(rsi_1h_val, rsi_1h_prev)

            # --- VWAP & 2H divergence from hourly data ---
            vwap_relation = "N/A"
            rsi_div_2h = "No"

            if hourly is not None and len(hourly) > 0:
                last_day = hourly.index[-1].date()
                day_mask = hourly.index.date == last_day
                day_data = hourly[day_mask]
                if not day_data.empty:
                    if "Volume" in day_data.columns and day_data["Volume"].sum() > 0:
                        vwap = (day_data["Close"] * day_data["Volume"]).sum() / day_data["Volume"].sum()
                    else:
                        vwap = day_data["Close"].mean()
                    if vwap:
                        diff_pct = (price / vwap - 1) * 100
                        if diff_pct > 0.5:
                            vwap_relation = "Above"
                        elif abs(diff_pct) <= 0.5:
                            vwap_relation = "Approaching"
                        else:
                            vwap_relation = "Below"

                # 2H divergence (simple higher-high / lower-high vs RSI)
                h2 = hourly.resample("2H").last()
                if len(h2) >= 4:
                    rsi_2h = calculate_rsi(h2)
                    if len(rsi_2h.dropna()) >= 3:
                        close = h2["Close"]
                        c3, c2, c1 = float(close.iloc[-3]), float(close.iloc[-2]), float(close.iloc[-1])
                        r3, r2, r1 = float(rsi_2h.iloc[-3]), float(rsi_2h.iloc[-2]), float(rsi_2h.iloc[-1])
                        bullish_div = c1 < c2 < c3 and r1 > r2 > r3
                        bearish_div = c1 > c2 > c3 and r1 < r2 < r3
                        if bullish_div or bearish_div:
                            rsi_div_2h = "Yes"

            # --- Final score (MA+RSI+VWAP): 1 pt each for RSI 1W/1D/1H up, 1 pt each for Price > 8/20/50 SMA; RSI divergence not used
            score = 0.0
            if rsi_1w_dir == "Up":
                score += 1.0
            if rsi_1d_dir == "Up":
                score += 1.0
            if rsi_1h_dir == "Up":
                score += 1.0
            if p_gt_8 == "Yes":
                score += 1.0
            if p_gt_20 == "Yes":
                score += 1.0
            if p_gt_50 == "Yes":
                score += 1.0
            if vwap_relation == "Above":
                score += w_vwap_above
            elif vwap_relation == "Approaching":
                score += w_vwap_approach

            results.append({
                "Sector": sector,
                "Symbol": symbol,
                "Company": name,
                "Price": round(price, 2),
                "Price > 50 SMA": p_gt_50,
                "Price > 20 SMA": p_gt_20,
                "Price > 8 SMA": p_gt_8,
                "RSI (1W)": int(round(rsi_1w_val, 0)) if rsi_1w_val is not None else None,
                "RSI (1W) Dir": rsi_1w_dir,
                "RSI (1D)": int(round(rsi_1d_val, 0)) if rsi_1d_val is not None else None,
                "RSI (1D) Dir": rsi_1d_dir,
                "RSI (1H)": int(round(rsi_1h_val, 0)) if rsi_1h_val is not None else None,
                "RSI (1H) Dir": rsi_1h_dir,
                "Price vs VWAP (1H)": vwap_relation,
                "Final score": round(score, 2),
            })
        except Exception:
            continue

    progress.empty()
    status.empty()

    if not results:
        st.warning("⚠️ No stocks could be analyzed for the screener.")
        return

    df = pd.DataFrame(results)
    df_sorted = df.sort_values(["Final score", "Symbol"], ascending=[False, True])

    # When "Top 4 + Bottom 6": Bullish = top 10 from top 4 sectors only; Bearish = bottom 10 from bottom 6 sectors only (synced with Historical Rankings)
    if sector_filter == "Top 4 + Bottom 6 (per Momentum Ranking)" and (top_sectors or bot_sectors):
        bull_candidates = df_sorted[df_sorted["Sector"].isin(top_sectors or [])] if top_sectors else pd.DataFrame()
        bear_candidates = df_sorted[df_sorted["Sector"].isin(bot_sectors or [])] if bot_sectors else pd.DataFrame()
        top_bullish = bull_candidates.head(10) if not bull_candidates.empty else df_sorted.head(10)
        top_bearish = (bear_candidates.tail(10).iloc[::-1] if not bear_candidates.empty else df_sorted.tail(10).iloc[::-1])
    else:
        top_bullish = df_sorted.head(10)
        top_bearish = df_sorted.tail(10).iloc[::-1]

    def sentiment_color(score):
        if pd.isna(score):
            return ""
        if score < 1.5:
            return "🔴 Weak"
        if score < 3.0:
            return "🟡 Moderate"
        return "🟢 Strong"

    st.markdown("#### 🟢 Top 10 Bullish")
    bull = top_bullish.copy()
    bull["Sentiment"] = bull["Final score"].apply(sentiment_color)
    st.dataframe(bull, use_container_width=True, hide_index=True)

    st.markdown("#### 🔴 Top 10 Bearish")
    bear = top_bearish.copy()
    bear["Sentiment"] = bear["Final score"].apply(sentiment_color)
    st.dataframe(bear, use_container_width=True, hide_index=True)

    st.caption(
        "**Scoring (MA+RSI+VWAP):** Same as Historical Rankings. Score = 1 pt each RSI (1W/1D/1H) up + 1 pt each Price > 8/20/50 SMA + VWAP (1H). "
        "**Sector scope:** When \"Top 4 + Bottom 6\" is selected, tables include stocks from **top 4 sectors (bullish) and bottom 6 sectors (bearish)** per Momentum Ranking; \"Universal\" = all sectors. Tie-break: by Symbol. Top 10 = Bullish, bottom 10 = Bearish."
    )

    # DataFrame for Part 3 (Fibonacci) and Part 4 (Confluence): must have Symbol, Sector, Company Name
    df_stocks = df_sorted.copy()
    df_stocks["Company Name"] = df_stocks["Company"]

    # Legacy experimental market overview / Fibonacci analysis block (disabled)
    # Kept for reference; does not run.
    if False:
        # Get list of Nifty 50 stocks
        nifty_stocks = [
            'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS',
            'SBIN.NS', 'BHARTIARTL.NS', 'HINDUNILVR.NS', 'ITC.NS', 'KOTAKBANK.NS',
            'LT.NS', 'AXISBANK.NS', 'ASIANPAINT.NS', 'MARUTI.NS', 'TITAN.NS',
            'NESTLEIND.NS', 'ULTRACEMCO.NS', 'WIPRO.NS', 'SUNPHARMA.NS', 'TATAMOTORS.NS',
            'TECHM.NS', 'HCLTECH.NS', 'BAJFINANCE.NS', 'JSWSTEEL.NS', 'TATASTEEL.NS',
            'POWERGRID.NS', 'NTPC.NS', 'ONGC.NS', 'COALINDIA.NS', 'ADANIENT.NS',
            'ADANIPORTS.NS', 'GRASIM.NS', 'DIVISLAB.NS', 'CIPLA.NS', 'DRREDDY.NS',
            'BAJAJFINSV.NS', 'M&M.NS', 'HEROMOTOCO.NS', 'EICHERMOT.NS', 'MARICO.NS',
            'GODREJCP.NS', 'DABUR.NS', 'BRITANNIA.NS', 'HDFCLIFE.NS', 'SBILIFE.NS',
            'ICICIPRULI.NS', 'HDFCAMC.NS', 'BAJAJ-AUTO.NS', 'INDUSINDBK.NS', 'APOLLOHOSP.NS'
        ]
        
        # Calculate current day metrics
        advances = 0
        declines = 0
        total_nifty = 0
        above_20dma = 0
        above_50dma = 0
        
        # Store historical data for 7-day trend
        historical_ad_ratios = []
        historical_breadth_20 = []
        historical_breadth_50 = []
        
        # Calculate metrics for last 7 days
        for day_offset in range(7):
            day_advances = 0
            day_declines = 0
            day_total = 0
            day_above_20 = 0
            day_above_50 = 0
            
            for symbol in nifty_stocks[:50]:
                try:
                    # Get data up to (analysis_date - day_offset)
                    check_date = analysis_date - timedelta(days=day_offset) if analysis_date else None
                    stock_data = fetch_sector_data(symbol, end_date=check_date, interval='1d')
                    
                    if stock_data is not None and len(stock_data) > 1:
                        if day_offset == 0:  # Current day
                            current_price = stock_data['Close'].iloc[-1]
                            prev_price = stock_data['Close'].iloc[-2] if len(stock_data) > 1 else current_price
                            
                            if current_price > prev_price:
                                advances += 1
                            elif current_price < prev_price:
                                declines += 1
                            total_nifty += 1
                            
                            # Calculate DMA breadth for current day
                            if len(stock_data) >= 50:
                                dma_20 = stock_data['Close'].rolling(20).mean().iloc[-1]
                                dma_50 = stock_data['Close'].rolling(50).mean().iloc[-1]
                                
                                if current_price > dma_20:
                                    above_20dma += 1
                                if current_price > dma_50:
                                    above_50dma += 1
                        
                        # Historical data for trends
                        if len(stock_data) > 1:
                            hist_price = stock_data['Close'].iloc[-1]
                            hist_prev = stock_data['Close'].iloc[-2] if len(stock_data) > 1 else hist_price
                            
                            if hist_price > hist_prev:
                                day_advances += 1
                            elif hist_price < hist_prev:
                                day_declines += 1
                            day_total += 1
                            
                            if len(stock_data) >= 50:
                                hist_dma_20 = stock_data['Close'].rolling(20).mean().iloc[-1]
                                hist_dma_50 = stock_data['Close'].rolling(50).mean().iloc[-1]
                                
                                if hist_price > hist_dma_20:
                                    day_above_20 += 1
                                if hist_price > hist_dma_50:
                                    day_above_50 += 1
                except:
                    continue
            
            # Calculate ratios for this day
            if day_total > 0:
                day_ad_ratio = day_advances / day_declines if day_declines > 0 else (day_advances / 1 if day_advances > 0 else 1.0)
                day_breadth_20 = (day_above_20 / day_total * 100) if day_total > 0 else 0
                day_breadth_50 = (day_above_50 / day_total * 100) if day_total > 0 else 0
                
                historical_ad_ratios.append(day_ad_ratio)
                historical_breadth_20.append(day_breadth_20)
                historical_breadth_50.append(day_breadth_50)
        
        # Reverse to get chronological order (oldest to newest)
        historical_ad_ratios = historical_ad_ratios[::-1]
        historical_breadth_20 = historical_breadth_20[::-1]
        historical_breadth_50 = historical_breadth_50[::-1]
        
        # Calculate current metrics
        ad_ratio = advances / declines if declines > 0 else (advances / 1 if advances > 0 else 1.0)
        breadth_20dma = (above_20dma / total_nifty * 100) if total_nifty > 0 else 0
        breadth_50dma = (above_50dma / total_nifty * 100) if total_nifty > 0 else 0
        
        # Calculate 7-day trends
        if len(historical_ad_ratios) >= 2:
            ad_trend = historical_ad_ratios[-1] - historical_ad_ratios[0]
            ad_trend_pct = (ad_trend / historical_ad_ratios[0] * 100) if historical_ad_ratios[0] > 0 else 0
        else:
            ad_trend = 0
            ad_trend_pct = 0
        
        if len(historical_breadth_20) >= 2:
            breadth_20_trend = historical_breadth_20[-1] - historical_breadth_20[0]
        else:
            breadth_20_trend = 0
        
        if len(historical_breadth_50) >= 2:
            breadth_50_trend = historical_breadth_50[-1] - historical_breadth_50[0]
        else:
            breadth_50_trend = 0
        
        # Display Market Overview with enhanced formatting
        nifty_price = nifty_data['Close'].iloc[-1]
        
        # Create styled overview table
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Nifty 50 Price", f"₹{nifty_price:,.2f}")
        with col2:
            st.metric("India VIX", f"{vix_value:.2f}" if vix_value else "N/A")
        with col3:
            st.metric("Total Market Stocks", total_market_stocks)
        with col4:
            st.metric("Nifty Stocks Analyzed", total_nifty)
        
        st.markdown("---")
        
        # A/D Section with totals and trend
        st.markdown("### 📊 Advance/Decline Analysis")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Advances", advances, delta=f"{ad_trend:.2f}" if ad_trend != 0 else None)
        with col2:
            st.metric("Declines", declines)
        with col3:
            st.metric("A/D Ratio", f"{ad_ratio:.2f}", delta=f"{ad_trend_pct:+.1f}%" if ad_trend_pct != 0 else None)
        with col4:
            st.metric("Total", advances + declines)
        
        # Breadth Section with trends
        st.markdown("### 📈 Market Breadth Analysis")
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("% Above 20 DMA", f"{breadth_20dma:.1f}%", 
                     delta=f"{breadth_20_trend:+.1f}%" if breadth_20_trend != 0 else None)
        with col2:
            st.metric("% Above 50 DMA", f"{breadth_50dma:.1f}%",
                     delta=f"{breadth_50_trend:+.1f}%" if breadth_50_trend != 0 else None)
        
        # 7-Day Trend Chart
        st.markdown("### 📉 7-Day Trend Analysis")
        
        if len(historical_ad_ratios) >= 2:
            trend_data = pd.DataFrame({
                'Day': [f'T-{6-i}' for i in range(len(historical_ad_ratios))],
                'A/D Ratio': historical_ad_ratios,
                '% Above 20 DMA': historical_breadth_20,
                '% Above 50 DMA': historical_breadth_50
            })
            
            # Add color coding function
            def style_trend_row(row):
                result = [''] * len(row)
                
                # Color A/D Ratio column
                if 'A/D Ratio' in row.index:
                    idx = list(row.index).index('A/D Ratio')
                    try:
                        val = float(row['A/D Ratio'])
                        if val > 1.2:
                            result[idx] = 'background-color: #27AE60; color: #fff; font-weight: bold'
                        elif val < 0.8:
                            result[idx] = 'background-color: #E74C3C; color: #fff; font-weight: bold'
                    except:
                        pass
                
                # Color % Above 20 DMA
                if '% Above 20 DMA' in row.index:
                    idx = list(row.index).index('% Above 20 DMA')
                    try:
                        val = float(row['% Above 20 DMA'])
                        if val > 60:
                            result[idx] = 'background-color: #27AE60; color: #fff; font-weight: bold'
                        elif val < 40:
                            result[idx] = 'background-color: #E74C3C; color: #fff; font-weight: bold'
                    except:
                        pass
                
                # Color % Above 50 DMA
                if '% Above 50 DMA' in row.index:
                    idx = list(row.index).index('% Above 50 DMA')
                    try:
                        val = float(row['% Above 50 DMA'])
                        if val > 60:
                            result[idx] = 'background-color: #27AE60; color: #fff; font-weight: bold'
                        elif val < 40:
                            result[idx] = 'background-color: #E74C3C; color: #fff; font-weight: bold'
                    except:
                        pass
                
                return result
            
            df_trend_styled = trend_data.style.apply(style_trend_row, axis=1)
            st.dataframe(df_trend_styled, use_container_width=True, hide_index=True)
            
            st.caption("🟢 Green: Bullish | 🔴 Red: Bearish")
        
        # Store in historical logs
        historical_logs.append({
            'Date': analysis_date.strftime('%Y-%m-%d') if analysis_date else datetime.now().strftime('%Y-%m-%d'),
            'Nifty_Price': nifty_price,
            'VIX': vix_value if vix_value else None,
            'Advances': advances,
            'Declines': declines,
            'AD_Ratio': ad_ratio,
            'Breadth_20DMA': breadth_20dma,
            'Breadth_50DMA': breadth_50dma
        })
    
    # ============================================================
    # PART 3: INDIVIDUAL STOCK RANKING - CONFLUENCE ANALYSIS (FIXED)
    # ============================================================
    st.markdown("## 🏆 PART 3: Individual Stock Ranking - Confluence Analysis")
    st.caption("**Logic summary (v3.1):** Confluence uses **top 4 sectors (bullish) and bottom 6 sectors (bearish)** per Momentum Ranking when that filter is selected. Only stocks with score > gate-fail threshold are shown in Top 8 tables; rejected stocks appear in the Excel Rejected sheet.")
    st.markdown("---")

    from confluence_fixed import (
        analyze_stock_confluence,
        calculate_confluence_score_bullish,
        calculate_confluence_score_bearish,
        generate_entry_description,
        build_confluence_excel,
        _GATE_FAIL_SCORE,
    )

    # --- Sector universe: Top 4 (bullish) + Bottom 6 (bearish) per Momentum Ranking ---
    st.markdown("### 🎯 Sector Selection for Confluence Analysis")

    col_toggle_conf, col_info_conf = st.columns([1, 2])

    with col_toggle_conf:
        conf_sector_filter = st.radio(
            "Confluence sector universe (synced with Historical Rankings):",
            options=["Top 4 + Bottom 6 (per Momentum Ranking)", "Universal (All Sectors)"],
            index=st.session_state.get("_conf_sector_idx", 0),
            key="part3_conf_sector_filter",
        )
        st.session_state["_conf_sector_idx"] = [
            "Top 4 + Bottom 6 (per Momentum Ranking)",
            "Universal (All Sectors)",
        ].index(conf_sector_filter)

    top_conf_sectors = None
    bot_conf_sectors = None

    with col_info_conf:
        top_conf_from_df, bot_conf_from_df = _top_bottom_from_df(df_momentum)
        if top_conf_from_df is not None:
            if conf_sector_filter == "Top 4 + Bottom 6 (per Momentum Ranking)":
                top_conf_sectors = top_conf_from_df
                bot_conf_sectors = bot_conf_from_df
                st.info("**Confluence pertains to top 4 sectors (bullish) and bottom 6 sectors (bearish) per Momentum Ranking** for this date.")
                if top_conf_sectors:
                    st.success(f"**✅ Bullish (top 4):** {', '.join(top_conf_sectors)}")
                if bot_conf_sectors:
                    st.warning(f"**⚠️ Bearish (bottom 6):** {', '.join(bot_conf_sectors)}")
            else:
                st.info("**Universal:** all stocks from all sectors.")
        elif sector_data_dict and momentum_weights:
            try:
                from confluence_fixed import get_bottom_n_sectors_by_momentum
                if conf_sector_filter == "Top 4 + Bottom 6 (per Momentum Ranking)":
                    top_conf_sectors = get_top_n_sectors_by_momentum(sector_data_dict, momentum_weights, n=4)
                    bot_conf_sectors = get_bottom_n_sectors_by_momentum(sector_data_dict, momentum_weights, n=6)
                    st.info("**Confluence pertains to top 4 (bullish) and bottom 6 (bearish) sectors** per Momentum Ranking.")
                    if top_conf_sectors:
                        st.success(f"**✅ Bullish:** {', '.join(top_conf_sectors)}")
                    if bot_conf_sectors:
                        st.warning(f"**⚠️ Bearish:** {', '.join(bot_conf_sectors)}")
                else:
                    st.info("**Universal:** all stocks from all sectors.")
            except Exception:
                top_retry, bot_retry = _top_bottom_from_df(df_momentum)
                if top_retry is not None and conf_sector_filter == "Top 4 + Bottom 6 (per Momentum Ranking)":
                    top_conf_sectors, bot_conf_sectors = top_retry, bot_retry
                    st.info("**Confluence pertains to top 4 + bottom 6 sectors** (fallback).")
                    if top_conf_sectors:
                        st.success(f"**✅ Bullish:** {', '.join(top_conf_sectors)}")
                    if bot_conf_sectors:
                        st.warning(f"**⚠️ Bearish:** {', '.join(bot_conf_sectors)}")
                else:
                    st.warning("⚠️ Could not resolve sector lists — using all sectors.")
        else:
            st.info("**Analyzing all stocks from all sectors.**")

    st.markdown("---")

    # --- Timeframe selector (synced with Historical Rankings via session_state) ---
    conf_tf = st.radio(
        "Select confluence analysis (synced with Historical Rankings):",
        ["1D + 2H", "4H + 1H (default)"],
        horizontal=True,
        index=st.session_state.get("_conf_tf_idx", 1),
        key="part3_conf_timeframe",
    )
    st.session_state["_conf_tf_idx"] = ["1D + 2H", "4H + 1H (default)"].index(conf_tf)
    conf_tf_label = "1D + 2H" if "1D + 2H" in conf_tf else "4H + 1H"
    conf_tf_code = '2h' if "1D + 2H" in conf_tf else '4h'
    # Column labels: entry TF and confirmation TF only (no "1D+2H" in column names)
    # 1D+2H mode: Entry = 1D, Confirmation = 2H  |  4H+1H mode: Entry = 4H, Confirmation = 1H
    if conf_tf_code == '2h':
        entry_label, conf_label = '1D', '2H'
    else:
        entry_label, conf_label = '4H', '1H'

    # --- Logic explanation (V2: 10 factors, max ~20 pts) ---
    st.markdown(f"""
**How Confluence Scoring works** (entry TF: **{entry_label}** + **{conf_label}** confirmation):

Each stock is scored **separately for Bullish and Bearish** across **10 factors** on two timeframes.
Opposing conditions get **negative (penalty)** points — a downtrending stock cannot rank high in the Bullish table.

| # | Factor | Bullish: +Pts | Bullish: −Pts | Bearish: +Pts | Bearish: −Pts | Description |
|---|--------|---------------|---------------|---------------|---------------|-------------|
| 1 | **Trend ({entry_label})** | Uptrend (HH/HL): **+4** | Downtrend: **−3** | Downtrend (LL/LH): **+4** | Uptrend: **−3** | Swing high/low on last 15 bars. **HH/HL** = at least 3 successive higher highs and higher lows. **LL/LH** = lower lows and lower highs. |
| 2 | **Trend ({conf_label})** | Uptrend: **+3** | Downtrend: **−2** | Downtrend: **+3** | Uptrend: **−2** | Confirmation TF validates or contradicts entry signal. |
| 3 | **MA Align ({entry_label})** | Price>20>50 DMA: **+3** | Bearish: **−2** | Price<20<50 DMA: **+3** | Bullish: **−2** | Price above/below 20 and 50 DMA on entry TF. |
| 4 | **MA Align ({conf_label})** | Bullish: **+2** | Bearish: **−1** | Bearish: **+2** | Bullish: **−1** | Same on confirmation TF. |
| 5 | **Price Position** | Near HL pivot: **+3** | Near LH pivot: **−1** | Near LH pivot: **+3** | Near HL pivot: **−2** | **Near HL** = within 3% of last confirmed pivot LOW (ideal BUY). **Near LH** = within 3% of last confirmed pivot HIGH (ideal SHORT). Uses {entry_label} pivots only; {conf_label} is placeholder. |
| 6 | **RSI ({entry_label})** | Rising 40–70: **+2** | **Falling: −1** (penalised) | At LH falling 50–70: **+2.5** | **Rising: −1** (penalised) | **(c) RSI direction enforced.** Bullish requires RSI rising; bearish requires RSI falling. Wrong direction = penalty. |
| 7 | **RSI ({conf_label})** | Rising 40–70: **+1.5** | OB: **−0.5** | Falling 30–60: **+1.5** | OS: **−0.5** | Confirmation TF RSI. |
| 8 | **MA Crossover ({entry_label})** | Bullish X: **+1.5** | Bearish X: **−1** | Bearish X: **+1.5** | Bullish X: **−1** | 20/50 DMA within 1.5% = crossover forming. |
| 9 | **RSI Divergence** | Bullish div: **+1.5** | Bearish div: **−1** | Bearish div: **+1.5** | Bullish div: **−1** | Price vs RSI divergence on last 10 bars (e.g. price lower low, RSI higher low = bullish). |
| 10 | **Volume** | High: **+1** | — | High at resistance: **+1.5** | — | Recent vol > 1.2× average. At resistance, high vol supports distribution (bearish). |

**Max score ≈ 20 pts** per side. **≥ 12** = excellent, **≥ 9** = good/strong, **5–9** = moderate, **< 5** = weak/avoid. **Negative** = opposite setup.
""")

    st.info(f"Analyzing confluence: **{conf_tf_label}** (entry **{entry_label}** + confirmation **{conf_label}**). This may take a few minutes...")

    # If screener returned no rows (e.g. no data for selected date), build confluence universe from SECTOR_COMPANIES so analysis can still run
    if df_stocks.empty:
        from company_symbols import SECTOR_COMPANIES as _SC
        _conf_sectors = None
        if conf_sector_filter == "Top 4 + Bottom 6 (per Momentum Ranking)" and (top_conf_sectors or bot_conf_sectors):
            _conf_sectors = set(top_conf_sectors or []) | set(bot_conf_sectors or [])
        _rows = []
        for _sec, _syms in _SC.items():
            if _conf_sectors is not None and _sec not in _conf_sectors:
                continue
            for _sym, _info in _syms.items():
                _rows.append({'Symbol': _sym, 'Sector': _sec, 'Company': _info.get('name', _sym), 'Company Name': _info.get('name', _sym)})
        df_stocks = pd.DataFrame(_rows)
        if df_stocks.empty:
            st.warning("⚠️ No sector–company mapping available. Add sectors in Sector Companies / Sector-Company.xlsx and reload.")
        else:
            st.caption("ℹ️ Screener had no rows for this date; using sector–company universe for confluence.")

    stock_results_bullish = []
    stock_results_bearish = []
    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, row in df_stocks.iterrows():
        symbol = row['Symbol']
        sector = row['Sector']
        company_name = row['Company Name']

        # (a+b) Sector filtering — Top 4 (bullish) + Bottom 6 (bearish) or Universal
        use_all_bull = (
            conf_sector_filter == "Universal (All Sectors)"
            or (conf_sector_filter == "Top 4 + Bottom 6 (per Momentum Ranking)" and not top_conf_sectors)
        )
        use_all_bear = (
            conf_sector_filter == "Universal (All Sectors)"
            or (conf_sector_filter == "Top 4 + Bottom 6 (per Momentum Ranking)" and not bot_conf_sectors)
        )
        bull_ok = use_all_bull or (top_conf_sectors and sector in top_conf_sectors)
        bear_ok = use_all_bear or (bot_conf_sectors and sector in bot_conf_sectors)
        if not bull_ok and not bear_ok:
            continue

        status_text.text(f"Confluence ({conf_tf_label}) for {company_name} ({idx+1}/{len(df_stocks)})...")
        progress_bar.progress((idx + 1) / len(df_stocks))

        try:
            # --- Fetch data ---
            # Always need daily data for 1D confirmation timeframe
            data_1d = fetch_sector_data(symbol, end_date=analysis_date, interval='1d')
            if data_1d is None or len(data_1d) < 50:
                continue

            if conf_tf_code in ('2h', '4h'):
                data_entry_raw = fetch_sector_data(symbol, end_date=analysis_date, interval='1h')
                min_bars = 80 if conf_tf_code == '4h' else 40
                if data_entry_raw is None or len(data_entry_raw) < min_bars:
                    continue
            else:
                data_entry_raw = data_1d  # 1D entry uses daily data directly

            # --- Multi-timeframe analysis ---
            analysis_data = analyze_stock_confluence(data_entry_raw, data_1d, entry_timeframe=conf_tf_code)
            if analysis_data is None:
                continue

            # --- Separate bullish & bearish scores ---
            bullish_score, bullish_reasons = calculate_confluence_score_bullish(analysis_data)
            bearish_score, bearish_reasons = calculate_confluence_score_bearish(analysis_data)
            bullish_desc = generate_entry_description(analysis_data, score=bullish_score, is_bullish=True)
            bearish_desc = generate_entry_description(analysis_data, score=bearish_score, is_bullish=False)

            # RSI display strings
            rsi_e = analysis_data['rsi_entry']
            rsi_ep = analysis_data['rsi_entry_prev']
            rsi_entry_disp = f"{rsi_e}" + (" ↑" if rsi_e > rsi_ep else (" ↓" if rsi_e < rsi_ep else ""))
            rsi_d = analysis_data['rsi_1d']
            rsi_dp = analysis_data['rsi_1d_prev']
            rsi_conf_disp = f"{rsi_d}" + (" ↑" if rsi_d > rsi_dp else (" ↓" if rsi_d < rsi_dp else ""))
            # Column naming: entry_label/conf_label only (1D+2H → Trend (1D), Trend (2H) | 4H+1H → Trend (4H), Trend (1H))
            # Data mapping: 1D+2H → entry=1D data (trend_1d), conf=2H data (trend_entry); 4H+1H → entry=4H (trend_entry), conf=1H (trend_1d)
            trend_entry_val = analysis_data['trend_entry']
            trend_conf_val = analysis_data['trend_1d']
            ma_entry_val = analysis_data['ma_alignment_entry']
            ma_conf_val = analysis_data['ma_alignment_1d']
            entry_trend = trend_conf_val if entry_label == '1D' else trend_entry_val
            conf_trend = trend_entry_val if conf_label == '2H' else trend_conf_val
            entry_ma = ma_conf_val if entry_label == '1D' else ma_entry_val
            conf_ma = ma_entry_val if conf_label == '2H' else ma_conf_val
            entry_rsi = rsi_conf_disp if entry_label == '1D' else rsi_entry_disp
            conf_rsi = rsi_entry_disp if conf_label == '2H' else rsi_conf_disp

            common = {
                'Sector': sector,
                'Symbol': symbol,
                'Company': company_name,
                f'Trend ({entry_label})': entry_trend,
                f'Trend ({conf_label})': conf_trend,
                f'MA Align ({entry_label})': entry_ma,
                f'MA Align ({conf_label})': conf_ma,
                f'RSI ({entry_label})': entry_rsi,
                f'RSI ({conf_label})': conf_rsi,
                f'Setup ({entry_label})': analysis_data['ma_crossover_entry'],
                'Divergence': analysis_data['divergence'],
                'Price Pos.': analysis_data.get('price_position', 'Unknown'),
            }

            # v3.1: only include stocks that pass Phase-1 gates (score > _GATE_FAIL_SCORE)
            if bull_ok and bullish_score > _GATE_FAIL_SCORE:
                stock_results_bullish.append({**common, 'Score': int(round(bullish_score)), 'Description': bullish_desc})
            if bear_ok and bearish_score > _GATE_FAIL_SCORE:
                stock_results_bearish.append({**common, 'Score': int(round(bearish_score)), 'Description': bearish_desc})

        except Exception:
            continue

    progress_bar.empty()
    status_text.empty()

    # Build confluence top-8 bullish + top-8 bearish for display and Fibonacci filtering
    df_results = pd.DataFrame()
    df_top10 = pd.DataFrame()  # kept for export compatibility
    confluence_shortlist_symbols = set()

    if not stock_results_bullish:
        st.warning("⚠️ No stock data available for confluence analysis")
    else:
        df_bullish = pd.DataFrame(stock_results_bullish).sort_values('Score', ascending=False)
        df_bearish = pd.DataFrame(stock_results_bearish).sort_values('Score', ascending=False)

        # Rank each table independently
        df_bullish['Rank'] = range(1, len(df_bullish) + 1)
        df_bearish['Rank'] = range(1, len(df_bearish) + 1)

        display_cols_conf = ['Rank', 'Sector', 'Symbol', 'Company',
                             f'Trend ({entry_label})', f'Trend ({conf_label})',
                             f'MA Align ({entry_label})', f'MA Align ({conf_label})',
                             f'RSI ({entry_label})', f'RSI ({conf_label})',
                             f'Setup ({entry_label})', 'Divergence', 'Price Pos.',
                             'Score', 'Description']

        # Top 8 Bullish
        df_bull8 = df_bullish.head(8)[display_cols_conf].copy()
        df_bull8['Rank'] = range(1, len(df_bull8) + 1)

        # Top 8 Bearish
        df_bear8 = df_bearish.head(8)[display_cols_conf].copy()
        df_bear8['Rank'] = range(1, len(df_bear8) + 1)

        confluence_shortlist_symbols = set(df_bull8['Symbol'].tolist()) | set(df_bear8['Symbol'].tolist())

        # --- Display Bullish ---
        st.markdown(f"### 🟢 Top 8 Bullish by Confluence ({conf_tf_label})")
        st.caption("Only stocks **passing Phase-1 gates** (score > -5) are included. Score ≥ 12 = excellent, ≥ 9 = good. **Price Pos. 'Near HL'** = ideal BUY at pivot support.")

        def _color_bull(val):
            try:
                v = int(val) if isinstance(val, (int, float)) else float(val)
            except (ValueError, TypeError):
                return ''
            if v >= 12: return 'background-color: #00aa00; color: white; font-weight: bold'
            if v >= 9: return 'background-color: #44cc44; color: white'
            if v >= 5: return 'background-color: #88ee88'
            if v < 0: return 'background-color: #ffcccc'
            return ''

        def _color_pos_bull(val):
            if val in ('Near Low', 'Near HL'): return 'background-color: #90EE90; color: black'
            if val in ('Near High', 'Near LH'): return 'background-color: #FFB6C1'
            return ''

        st.dataframe(
            df_bull8.style.applymap(_color_bull, subset=['Score'])
                          .applymap(_color_pos_bull, subset=['Price Pos.'])
                          .format({'Score': '{:.0f}'}, na_rep=''),
            use_container_width=True, hide_index=True
        )

        # Breakdown for top 3 bullish
        with st.expander("📊 Scoring breakdown — Top 3 Bullish"):
            for i in range(min(3, len(df_bull8))):
                r = df_bull8.iloc[i]
                st.markdown(f"**{i+1}. {r['Company']} ({r['Symbol']})** — Score: **{r['Score']}**")
                st.markdown(f"  - {r['Description']}")
                st.markdown(f"  - Trend: {entry_label}={r[f'Trend ({entry_label})']}, {conf_label}={r[f'Trend ({conf_label})']}")
                st.markdown(f"  - MA: {r[f'MA Align ({entry_label})']}, {r[f'MA Align ({conf_label})']} | RSI: {r[f'RSI ({entry_label})']}, {r[f'RSI ({conf_label})']}")
                if i < 2: st.markdown("---")

        st.markdown("---")

        # --- Display Bearish ---
        st.markdown(f"### 🔴 Top 8 Bearish by Confluence ({conf_tf_label})")
        st.caption("Only stocks **passing Phase-1 gates** (score > -5) are included. Score ≥ 12 = excellent, ≥ 9 = good. **Price Pos. 'Near LH'** = ideal SHORT at pivot resistance.")

        def _color_bear(val):
            try:
                v = int(val) if isinstance(val, (int, float)) else float(val)
            except (ValueError, TypeError):
                return ''
            if v >= 12: return 'background-color: #aa0000; color: white; font-weight: bold'
            if v >= 9: return 'background-color: #cc4444; color: white'
            if v >= 5: return 'background-color: #ee8888'
            if v < 0: return 'background-color: #ccffcc'
            return ''

        def _color_pos_bear(val):
            if val in ('Near High', 'Near LH'): return 'background-color: #FFB6C1; color: black; font-weight: bold'
            if val in ('Near Low', 'Near HL'): return 'background-color: #90EE90'
            return ''

        st.dataframe(
            df_bear8.style.applymap(_color_bear, subset=['Score'])
                          .applymap(_color_pos_bear, subset=['Price Pos.'])
                          .format({'Score': '{:.0f}'}, na_rep=''),
            use_container_width=True, hide_index=True
        )

        # Breakdown for top 3 bearish
        with st.expander("📊 Scoring breakdown — Top 3 Bearish"):
            for i in range(min(3, len(df_bear8))):
                r = df_bear8.iloc[i]
                st.markdown(f"**{i+1}. {r['Company']} ({r['Symbol']})** — Score: **{r['Score']}**")
                st.markdown(f"  - {r['Description']}")
                st.markdown(f"  - Trend: {entry_label}={r[f'Trend ({entry_label})']}, {conf_label}={r[f'Trend ({conf_label})']}")
                st.markdown(f"  - MA: {r[f'MA Align ({entry_label})']}, {r[f'MA Align ({conf_label})']} | RSI: {r[f'RSI ({entry_label})']}, {r[f'RSI ({conf_label})']}")
                if i < 2: st.markdown("---")

        # Key insights
        st.markdown("---")
        st.markdown("### 🔍 Key Insights")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Strong Bullish (Score ≥ 9)", len(df_bullish[df_bullish['Score'] >= 9]))
            bull_at_support = len(df_bullish[(df_bullish['Score'] >= 9) & (df_bullish['Price Pos.'].isin(['Near Low', 'Near HL']))])
            st.metric("Bullish at Support (Near HL)", bull_at_support)
            st.caption("Ideal bullish entries at HL")
        with col2:
            st.metric("Strong Bearish (Score ≥ 9)", len(df_bearish[df_bearish['Score'] >= 9]))
            bear_at_resist = len(df_bearish[(df_bearish['Score'] >= 9) & (df_bearish['Price Pos.'].isin(['Near High', 'Near LH']))])
            st.metric("Bearish at Resistance (Near LH)", bear_at_resist)
            st.caption("Ideal SHORT entries at LH")

        # Warning for late bearish entries
        bear_too_late = len(df_bearish[(df_bearish['Score'] >= 9) & (df_bearish['Price Pos.'].isin(['Near Low', 'Near HL']))])
        if bear_too_late > 0:
            st.warning(f"⚠️ {bear_too_late} bearish setup(s) are at 'Near HL' — TOO LATE for SHORT (price at support).")

        st.success(f"✅ Confluence analysis complete! Analyzed {len(stock_results_bullish) + len(stock_results_bearish)} stocks on {conf_tf_label} (only stocks passing Phase-1 gates shown in tables).")

        # ── Download button ────────────────────────────────────────────────────
        st.markdown("### 📥 Download Confluence Summary")

        _analysis_date_str = (
            analysis_date.strftime('%Y-%m-%d')
            if hasattr(analysis_date, 'strftime')
            else str(analysis_date)[:10]
        )

        try:
            _dl_cols = ['Rank', 'Sector', 'Symbol', 'Company',
                        f'Trend ({entry_label})', f'Trend ({conf_label})',
                        f'MA Align ({entry_label})', f'MA Align ({conf_label})',
                        f'RSI ({entry_label})', f'RSI ({conf_label})',
                        f'Setup ({entry_label})', 'Divergence', 'Price Pos.',
                        'Score', 'Description']
            _dl_bull = df_bullish[_dl_cols].copy() if all(c in df_bullish.columns for c in _dl_cols) else df_bullish.copy()
            _dl_bear = df_bearish[_dl_cols].copy() if all(c in df_bearish.columns for c in _dl_cols) else df_bearish.copy()

            _excel_bytes = build_confluence_excel(
                df_bull        = _dl_bull,
                df_bear        = _dl_bear,
                timeframe_label= conf_tf_label,
                analysis_date  = _analysis_date_str,
                sector_filter  = conf_sector_filter,
            )

            _bull_pass = len(df_bullish[df_bullish['Score'] > _GATE_FAIL_SCORE])
            _bear_pass = len(df_bearish[df_bearish['Score'] > _GATE_FAIL_SCORE])
            _bull_rej  = len(df_bullish) - _bull_pass
            _bear_rej  = len(df_bearish) - _bear_pass

            col_dl1, col_dl2 = st.columns([1, 2])
            with col_dl1:
                st.download_button(
                    label     = f"⬇️ Download Excel ({conf_tf_label})",
                    data      = _excel_bytes,
                    file_name = f"confluence_{conf_tf_label.replace(' ','_')}_{_analysis_date_str}.xlsx",
                    mime      = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type      = "primary",
                    key       = "confluence_download_excel",
                )
            with col_dl2:
                st.info(
                    f"**Excel contains 4 sheets:**  \n"
                    f"① Summary (gate rules + key metrics)  \n"
                    f"② 🟢 Top Bullish — **{_bull_pass}** passed ({_bull_rej} rejected)  \n"
                    f"③ 🔴 Top Bearish — **{_bear_pass}** passed ({_bear_rej} rejected)  \n"
                    f"④ ⛔ Rejected — stocks that failed Phase 1 gates"
                )
        except Exception as _dl_err:
            st.warning(f"⚠️ Download not available: {_dl_err}")

        st.markdown("---")

        # Interpretation guide (v3.1)
        with st.expander("ℹ️ Score Interpretation Guide (v3.1)"):
            st.markdown("""
**Max score ≈ 20 pts** per side (10 factors across entry TF + 1D).

**Score Ranges:**
- **≥ 12:** 🟢 Excellent — multiple confluences aligned, high-probability setup
- **9–12:** 🟢 Good / strong — solid entry opportunity, most factors aligned
- **5–9:** 🟡 Moderate — some confirmation needed, mixed signals
- **< 5:** 🔴 Weak — high conflict, AVOID
- **≤ -5 (rejected):** ⛔ Failed Phase-1 gates — not shown in Top 8 tables; see Rejected sheet in Excel.

**Price Position:**
- **Near HL** = within 3% of last confirmed pivot LOW → ideal for **Bullish** (buy at HL support)
- **Near LH** = within 3% of last confirmed pivot HIGH → ideal for **Bearish** (short at LH resistance)
- Bearish at "Near HL" = **TOO LATE** (price at support)

**v3.1 logic:** Phase-1 hard gates for bullish (Uptrend required, RSI rising & <70 required, MA not Bearish required). Middle price position is **allowed** (+1 pt). Near HL = +3 (ideal), Middle = +1 (acceptable), Near LH = −1 (caution, not rejected unless RSI also falling). Graduated RSI zone scoring: 40–55 = +2.5 (sweet spot), 55–65 = +2, 65–70 = +1. Rejected stocks shown in ⛔ Rejected sheet of the Excel download. Confluence pertains to **top 4 sectors (bullish) and bottom 6 sectors (bearish)** per Momentum Ranking when that filter is selected.
""")

        # --- Last 30 days: individual parameter lookback per stock ---
        with st.expander("📅 Last 30 days — individual parameters (lookback)"):
            st.caption("See how confluence parameters (trend, MA, RSI, price position, scores) changed over the last 30 trading days for a selected stock.")
            symbol_options = sorted(confluence_shortlist_symbols)
            if not symbol_options:
                st.info("No confluence shortlist — run analysis above to see stocks.")
            else:
                def _company_for(s):
                    b = df_bullish[df_bullish['Symbol'] == s]
                    if len(b): return b['Company'].iloc[0]
                    be = df_bearish[df_bearish['Symbol'] == s]
                    return be['Company'].iloc[0] if len(be) else s
                sel_symbol = st.selectbox(
                    "Select stock",
                    options=symbol_options,
                    key="conf_30d_symbol",
                    format_func=lambda s: f"{s} — {_company_for(s)}"
                )
                if sel_symbol:
                    with st.spinner(f"Building 30-day parameter history for {sel_symbol}..."):
                        end_date = pd.Timestamp(analysis_date).date() if hasattr(analysis_date, 'date') else (analysis_date if hasattr(analysis_date, 'year') else pd.Timestamp(analysis_date).date())
                        dates_30 = pd.bdate_range(end=end_date, periods=30, freq='B').tolist()
                        dates_30 = list(reversed(dates_30))
                        data_1d = fetch_sector_data(sel_symbol, end_date=analysis_date, interval='1d')
                        if conf_tf_code in ('2h', '4h'):
                            data_entry_raw = fetch_sector_data(sel_symbol, end_date=analysis_date, interval='1h')
                        else:
                            data_entry_raw = data_1d
                        min_daily, min_entry = 50, (80 if conf_tf_code == '4h' else 40)
                        history_rows = []
                        for date_t in dates_30:
                            d_ts = pd.Timestamp(date_t)
                            d_date = d_ts.date() if hasattr(d_ts, 'date') else d_ts
                            if data_1d is not None and len(data_1d) >= min_daily:
                                data_1d_t = data_1d[data_1d.index.date <= d_date].tail(min_daily) if hasattr(data_1d.index, 'date') else data_1d[data_1d.index <= d_ts].tail(min_daily)
                            else:
                                data_1d_t = None
                            if data_entry_raw is not None and len(data_entry_raw) >= min_entry:
                                data_entry_t = data_entry_raw[data_entry_raw.index.date <= d_date].tail(min_entry) if hasattr(data_entry_raw.index, 'date') else data_entry_raw[data_entry_raw.index <= d_ts].tail(min_entry)
                            else:
                                data_entry_t = None
                            if data_1d_t is None or len(data_1d_t) < 30 or data_entry_t is None or len(data_entry_t) < min_entry:
                                continue
                            try:
                                from confluence_fixed import (
                                    analyze_stock_confluence,
                                    calculate_confluence_score_bullish,
                                    calculate_confluence_score_bearish,
                                )
                                ana = analyze_stock_confluence(data_entry_t, data_1d_t, entry_timeframe=conf_tf_code)
                                if ana is None:
                                    continue
                                bull_sc, _ = calculate_confluence_score_bullish(ana)
                                bear_sc, _ = calculate_confluence_score_bearish(ana)
                                rsi_e, rsi_d = ana['rsi_entry'], ana['rsi_1d']
                                rsi_ep, rsi_dp = ana.get('rsi_entry_prev', rsi_e), ana.get('rsi_1d_prev', rsi_d)
                                rsi_e_str = f"{rsi_e}" + (" ↑" if rsi_e > rsi_ep else (" ↓" if rsi_e < rsi_ep else ""))
                                rsi_d_str = f"{rsi_d}" + (" ↑" if rsi_d > rsi_dp else (" ↓" if rsi_d < rsi_dp else ""))
                                trend_ent = ana['trend_entry']
                                trend_1d = ana['trend_1d']
                                ma_ent = ana['ma_alignment_entry']
                                ma_1d = ana['ma_alignment_1d']
                                if entry_label == '1D':
                                    entry_trend, conf_trend = trend_1d, trend_ent
                                    entry_ma, conf_ma = ma_1d, ma_ent
                                    entry_rsi, conf_rsi = rsi_d_str, rsi_e_str
                                else:
                                    entry_trend, conf_trend = trend_ent, trend_1d
                                    entry_ma, conf_ma = ma_ent, ma_1d
                                    entry_rsi, conf_rsi = rsi_e_str, rsi_d_str
                                history_rows.append({
                                    'Date': d_ts.strftime('%Y-%m-%d'),
                                    'Day': d_ts.strftime('%A'),
                                    f'Trend ({entry_label})': entry_trend,
                                    f'Trend ({conf_label})': conf_trend,
                                    f'MA ({entry_label})': entry_ma,
                                    f'MA ({conf_label})': conf_ma,
                                    f'RSI ({entry_label})': entry_rsi,
                                    f'RSI ({conf_label})': conf_rsi,
                                    'Price Pos.': ana.get('price_position', ''),
                                    'Divergence': ana.get('divergence', ''),
                                    'Bull': int(round(bull_sc)),
                                    'Bear': int(round(bear_sc)),
                                })
                            except Exception:
                                continue
                        if history_rows:
                            df_hist = pd.DataFrame(history_rows)
                            df_hist = df_hist.sort_values('Date', ascending=False).reset_index(drop=True)
                            st.dataframe(df_hist, use_container_width=True, hide_index=True)
                        else:
                            st.info("No parameter history could be computed for the last 30 trading days (insufficient data).")

        # For backward compat: df_results = bullish df, df_top10 = top 10 bullish
        df_results = df_bullish.copy()
        df_top10 = df_bullish.head(10)

    # ============================================================
    # PART 4: INDIVIDUAL STOCK - FIBONACCI ANALYSIS (shortlisted only)
    # ============================================================
    st.markdown("## 📊 PART 4: Individual Stock - Fibonacci Analysis")
    st.markdown("---")

    # Build shortlist: union of Top 10 Bullish + Top 10 Bearish (MA+RSI+VWAP) + Confluence Top 8 Bull + Top 8 Bear
    fib_shortlist_symbols = set(top_bullish['Symbol'].tolist()) | set(top_bearish['Symbol'].tolist()) | confluence_shortlist_symbols
    df_fib_stocks = df_stocks[df_stocks['Symbol'].isin(fib_shortlist_symbols)]

    st.info(
        f"Analyzing Fibonacci 0.5 (golden level) for **{len(df_fib_stocks)}** shortlisted stocks "
        f"(Top 10 Bullish/Bearish from MA+RSI+VWAP + Confluence Top 8 Bullish/Bearish)."
    )
    st.caption(
        "**Note:** Fibonacci analysis is limited to shortlisted stocks from Part 2 and Part 3 "
        "to reduce processing time. Only the Fib 0.5 level is checked (within 2%)."
    )

    fib_results = []
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, (idx, row) in enumerate(df_fib_stocks.iterrows()):
        symbol = row['Symbol']
        sector = row['Sector']
        company_name = row['Company Name']

        status_text.text(f"Fibonacci for {company_name} ({i+1}/{len(df_fib_stocks)})...")
        progress_bar.progress((i + 1) / len(df_fib_stocks))

        try:
            data_15m = fetch_sector_data(symbol, end_date=analysis_date, interval='15m')
            if data_15m is None or len(data_15m) < 20:
                data_daily = fetch_sector_data(symbol, end_date=analysis_date, interval='1d')
                if data_daily is None or len(data_daily) < 20:
                    continue
                data_for_fib = data_daily
            else:
                data_for_fib = data_15m

            if data_for_fib.index.freq is None or 'D' not in str(data_for_fib.index.freq):
                data_daily_agg = data_for_fib.resample('D').agg({
                    'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
                }).dropna()
            else:
                data_daily_agg = data_for_fib

            if len(data_daily_agg) < 20:
                continue

            swing_high, swing_low, swing_high_date, swing_low_date = find_swing_high_low(data_daily_agg, lookback_days=20)
            fib_levels = calculate_fibonacci_levels(swing_high, swing_low)
            current_price = data_daily_agg['Close'].iloc[-1]
            in_zone, fib_level, distance = check_fibonacci_golden_zone(current_price, fib_levels)

            if in_zone:
                fib_50 = fib_levels[0.5]
                pct_from_fib = ((current_price - fib_50) / fib_50) * 100
                remark = f"Fib 0.5: ₹{fib_50:,.2f} | {pct_from_fib:+.2f}% from level"
                last_crossing = find_last_crossing_time(data_daily_agg, fib_50, current_price)

                data_1h = fetch_sector_data(symbol, end_date=analysis_date, interval='1h')
                rsi_1h = adx_1h = None
                if data_1h is not None and len(data_1h) >= 14:
                    rsi_s = calculate_rsi(data_1h)
                    rsi_1h = rsi_s.iloc[-1] if not rsi_s.isna().all() else None
                    adx_s, _, _, _ = calculate_adx(data_1h)
                    adx_1h = adx_s.iloc[-1] if adx_s is not None and not adx_s.isna().all() else None

                fib_results.append({
                    'Company': company_name,
                    'Stock Price': current_price,
                    'Fib Level': fib_level,
                    'Remark': remark,
                    'Last Crossing Time': last_crossing,
                    'RSI (1H)': f"{rsi_1h:.1f}" if rsi_1h else "N/A",
                    'ADX (1H)': f"{adx_1h:.1f}" if adx_1h else "N/A",
                    'Match Score': 100 - distance,
                    'Sector': sector,
                    'Symbol': symbol
                })
        except Exception:
            continue

    progress_bar.empty()
    status_text.empty()

    if fib_results:
        df_fib = pd.DataFrame(fib_results)
        df_fib = df_fib.sort_values('Match Score', ascending=False)
        st.markdown("### 🎯 Stocks near Fibonacci 0.5 (Golden Level)")
        display_cols = ['Company', 'Stock Price', 'Fib Level', 'Remark', 'Last Crossing Time', 'RSI (1H)', 'ADX (1H)']
        st.dataframe(df_fib[display_cols], use_container_width=True, hide_index=True)
        st.success(f"✅ Found {len(fib_results)} stocks near Fibonacci 0.5 level (out of {len(df_fib_stocks)} shortlisted)")
    else:
        st.warning(f"⚠️ No stocks near Fibonacci 0.5 level (checked {len(df_fib_stocks)} shortlisted stocks)")
    
    # ============================================================
    # HISTORICAL LOGGING & EXPORT
    # ============================================================
    st.markdown("---")
    st.markdown("## 📥 Export & Historical Logs")
    
    # Prepare Excel export with all data
    excel_buffer = BytesIO()
    sheets_written = 0
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        # Market Overview logs
        if historical_logs:
            df_logs = pd.DataFrame(historical_logs)
            df_logs.to_excel(writer, sheet_name='Market Overview Logs', index=False)
            sheets_written += 1
        
        # Fibonacci results
        if fib_results:
            df_fib_export = pd.DataFrame(fib_results)
            df_fib_export.to_excel(writer, sheet_name='Fibonacci Analysis', index=False)
            sheets_written += 1
        
        # Confluence results (use stock_results_bullish if available)
        if not df_results.empty:
            df_results.to_excel(writer, sheet_name='Confluence Analysis - All', index=False)
            sheets_written += 1
        if not df_top10.empty:
            df_top10.to_excel(writer, sheet_name='Confluence Analysis - Top 10', index=False)
            sheets_written += 1
        
        # Ensure at least one sheet exists
        if sheets_written == 0:
            pd.DataFrame({'Info': ['No analysis data available for this date']}).to_excel(writer, sheet_name='Summary', index=False)
    
    excel_buffer.seek(0)
    
    st.download_button(
        label="📥 Download Complete Analysis (Excel)",
        data=excel_buffer.read(),
        file_name=f'stock_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    
    st.success(f"✅ Complete analysis finished!")


def main():
    """Main Streamlit app function."""
    try:
        # Header
        st.markdown('<div class="main-header">📊 NSE Market Sector Analysis Tool</div>', 
                    unsafe_allow_html=True)
        st.markdown('<div class="sub-header">Advanced Technical Analysis with Configurable Weights</div>', 
                    unsafe_allow_html=True)
        st.caption(f"App version: **{APP_VERSION}**")
        
        # Sidebar controls
        try:
            use_etf, momentum_weights, reversal_weights, analysis_date, time_interval, reversal_thresholds, enable_color_coding = get_sidebar_controls()
        except Exception as e:
            st.error(f"❌ Error loading sidebar controls: {str(e)}")
            return
        
        # Display current weights
        with st.sidebar.expander("📋 Current Configuration"):
            st.write("**Momentum Weights:**")
            st.json(momentum_weights)
            st.write("**Reversal Weights:**")
            st.json(reversal_weights)
            st.write(f"**Data Source:** {'ETF Proxy' if use_etf else 'NSE Indices'}")
            st.write(f"**Analysis Date:** {analysis_date}")
        
        # Display symbols being used
        with st.sidebar.expander("📊 Symbols Used"):
            data_source = SECTOR_ETFS if use_etf else SECTORS
            for sector, symbol in list(data_source.items())[:5]:  # Show first 5
                st.text(f"{sector}: {symbol}")
            if len(data_source) > 5:
                st.text(f"... and {len(data_source) - 5} more")
            st.info("See SYMBOLS.txt for complete list")
        
        # Refresh button
        if st.button("🔄 Run Analysis", type="primary", use_container_width=True):
            st.cache_data.clear()
            clear_data_cache()  # Also clear data fetcher cache
        
        # Run analysis
        with st.spinner("Analyzing sectors..."):
            # Convert date to datetime for analysis
            from datetime import datetime as dt
            analysis_datetime = dt.combine(analysis_date, dt.min.time()) if analysis_date else None
            df, sector_data, market_date = analyze_sectors_with_progress(use_etf, momentum_weights, reversal_weights, analysis_datetime, time_interval, reversal_thresholds)
        
        if df is None or df.empty:
            st.error("❌ Unable to complete analysis. Please try again or check your internet connection.")
            st.info("💡 Tip: Ensure yfinance can reach Yahoo Finance servers. If the issue persists, try again in a few moments.")
            return
        
        # Display combined data source and date information with IST timezone
        data_source_type = "ETF Proxy" if use_etf else "NSE Indices"
        # Convert to IST (UTC+5:30)
        from datetime import timezone
        ist_offset = timedelta(hours=5, minutes=30)
        ist_time = datetime.now(timezone.utc) + ist_offset
        current_time_ist = ist_time.strftime('%Y-%m-%d %H:%M:%S IST')
        st.markdown(f'''
            <div class="date-info">
                <b>📊 Data Source:</b> {data_source_type} | 
                <b>📅 Analysis Date:</b> {current_time_ist} | 
                <b>📈 Market Data Date:</b> {market_date} | 
                <b>⏱️ Interval:</b> {time_interval}
            </div>
        ''', unsafe_allow_html=True)
        
        # Market Breadth block (Nifty, Advance/Total %) - always visible above tabs
        benchmark_data = sector_data.get('Nifty 50') if sector_data else None
        display_market_breadth_block(benchmark_data, analysis_date)
        
        # Create tabs (9 total: Momentum, Market breadth, Stock Analysis, Reversal, Interpretation, Company Momentum, Company Reversals, Historical, Data Sources)
        try:
            tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
                "📈 Momentum Ranking",
                "📊 Market breadth",
                "📊 Stock Screener",
                "🔄 Reversal Candidates",
                "📊 Interpretation Guide",
                "🏢 Company Momentum",
                "🏢 Company Reversals",
                "📅 Historical Rankings",
                "🔌 Data Sources",
            ])
            
            # Get benchmark data for trend analysis
            data_source = SECTOR_ETFS if use_etf else SECTORS
            benchmark_data = sector_data.get('Nifty 50') if sector_data else None
            
            with tab1:
                try:
                    display_momentum_tab(df, sector_data, benchmark_data, enable_color_coding)
                    display_tooltip_legend()
                except Exception as e:
                    st.error(f"❌ Error displaying momentum tab: {str(e)}")
                    st.text(traceback.format_exc())
            
            with tab2:
                try:
                    display_market_breadth_tab(benchmark_data, analysis_date, sector_data, momentum_weights)
                except Exception as e:
                    st.error(f"❌ Error displaying market breadth tab: {str(e)}")
                    st.text(traceback.format_exc())
            
            with tab3:
                try:
                    display_stock_screener_tab(
                        analysis_date=analysis_date,
                        benchmark_data=benchmark_data,
                        sector_data_dict=sector_data,
                        momentum_weights=momentum_weights,
                        df_momentum=df,
                    )
                except Exception as e:
                    st.error(f"❌ Error displaying stock screener tab: {str(e)}")
                    st.text(traceback.format_exc())
            
            with tab4:
                try:
                    display_reversal_tab(df, sector_data, benchmark_data, reversal_weights, reversal_thresholds, enable_color_coding)
                    display_tooltip_legend()
                except Exception as e:
                    st.error(f"❌ Error displaying reversal tab: {str(e)}")
                    st.text(traceback.format_exc())
            
            with tab5:
                try:
                    display_interpretation_tab()
                    display_tooltip_legend()
                except Exception as e:
                    st.error(f"❌ Error displaying interpretation tab: {str(e)}")
            
            with tab6:
                try:
                    # Pass top sector as default for company momentum analysis
                    # Sort by Momentum_Score first to get rank #1
                    df_sorted_momentum = df.sort_values('Momentum_Score', ascending=False)
                    top_sector = df_sorted_momentum.iloc[0]['Sector'] if not df_sorted_momentum.empty else None
                    display_company_momentum_tab(time_interval=time_interval, momentum_weights=momentum_weights, analysis_date=analysis_date, default_sector=top_sector)
                    display_tooltip_legend()
                except Exception as e:
                    st.error(f"❌ Error displaying company momentum tab: {str(e)}")
                    st.text(traceback.format_exc())
            
            with tab7:
                try:
                    # Get top reversal candidate (if any)
                    top_reversal_sector = None
                    if not df.empty:
                        reversal_candidates = df[df['Reversal_Status'] != 'No']
                        if not reversal_candidates.empty:
                            top_reversal_sector = reversal_candidates.iloc[0]['Sector']
                    display_company_reversal_tab(time_interval=time_interval, reversal_weights=reversal_weights, reversal_thresholds=reversal_thresholds, analysis_date=analysis_date, default_sector=top_reversal_sector)
                    display_tooltip_legend()
                except Exception as e:
                    st.error(f"❌ Error displaying company reversal tab: {str(e)}")
                    st.text(traceback.format_exc())
            
            with tab8:
                try:
                    display_historical_rankings_tab(sector_data, benchmark_data, momentum_weights, reversal_weights, reversal_thresholds, use_etf)
                    display_tooltip_legend()
                except Exception as e:
                    st.error(f"❌ Error displaying historical rankings tab: {str(e)}")
                    st.text(traceback.format_exc())
            
            with tab9:
                try:
                    display_data_sources_tab()
                except Exception as e:
                    st.error(f"❌ Error displaying data sources tab: {str(e)}")
                    st.text(traceback.format_exc())
            
            # Note: Sector Companies tab removed to make room for Stock Analysis tab
                    
        except Exception as e:
            st.error(f"❌ Error creating tabs: {str(e)}")
            st.text(traceback.format_exc())
    
    except Exception as e:
        st.error(f"❌ Critical error in main function: {str(e)}")
        st.text(traceback.format_exc())
        st.stop()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"❌ Application failed to start: {str(e)}")
        st.text(traceback.format_exc())
