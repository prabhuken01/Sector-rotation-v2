#!/usr/bin/env python3
"""
NSE Market Sector Analysis Tool - Streamlit Web Interface
Enhanced with configurable weights, ETF proxy, and improved aesthetics
Version: 2.0.0 - Fixed reversal ranking logic (Jan 2026)
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import warnings
import traceback
warnings.filterwarnings('ignore')

try:
    from config import (SECTORS, SECTOR_ETFS, SECTOR_ETFS_ALTERNATE, MOMENTUM_SCORE_PERCENTILE_THRESHOLD, 
                        DEFAULT_MOMENTUM_WEIGHTS, DEFAULT_REVERSAL_WEIGHTS, DECIMAL_PLACES)
    from data_fetcher import fetch_sector_data, fetch_sector_data_with_alternate, fetch_all_sectors_parallel, clear_data_cache
    from analysis import analyze_all_sectors, format_results_dataframe, analyze_sector
    from indicators import calculate_rsi, calculate_adx, calculate_cmf, calculate_z_score, calculate_mansfield_rs
    from company_analysis import display_company_momentum_tab, display_company_reversal_tab
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
    
    # Momentum weights (percentages that sum to 100%)
    st.sidebar.subheader("Momentum Score Weights (%)")
    st.sidebar.caption("Weights should sum to 100%")
    
    rs_weight = st.sidebar.slider("RS Rating Weight (%)", 0.0, 100.0, 
                                   DEFAULT_MOMENTUM_WEIGHTS['RS_Rating'], 1.0)
    adx_weight = st.sidebar.slider("ADX Z-Score Weight (%)", 0.0, 100.0, 
                                    DEFAULT_MOMENTUM_WEIGHTS['ADX_Z'], 1.0)
    rsi_momentum_weight = st.sidebar.slider("RSI Weight (%)", 0.0, 100.0, 
                                             DEFAULT_MOMENTUM_WEIGHTS['RSI'], 1.0)
    di_spread_weight = st.sidebar.slider("DI Spread Weight (%)", 0.0, 100.0, 
                                          DEFAULT_MOMENTUM_WEIGHTS['DI_Spread'], 1.0)
    
    # Calculate and display total
    total_momentum_weight = adx_weight + rs_weight + rsi_momentum_weight + di_spread_weight
    if abs(total_momentum_weight - 100.0) > 0.1:
        st.sidebar.warning(f"⚠️ Weights sum to {total_momentum_weight:.1f}% (should be 100%)")
    else:
        st.sidebar.success(f"✅ Weights sum to {total_momentum_weight:.1f}%")
    
    momentum_weights = {
        'ADX_Z': adx_weight,
        'RS_Rating': rs_weight,
        'RSI': rsi_momentum_weight,
        'DI_Spread': di_spread_weight
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
        try:
            alternate_symbol = alternates.get(sector_name) if alternates else None
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
    Display historical rankings showing how top 2 sectors evolved over past 7 trading days.
    Shows current top sectors with their historical indicator trends.
    
    Args:
        sector_data_dict: Dictionary of sector name to data DataFrame
        benchmark_data: Benchmark data DataFrame  
        momentum_weights: Dict with momentum score weights
        reversal_weights: Dict with reversal score weights
        reversal_thresholds: Dict with reversal thresholds
        use_etf: Whether using ETF or Index data
    """
    st.markdown("### 📅 Historical Rankings (T-7 to T)")
    st.markdown("---")
    
    st.info("📊 **Track how current top-ranked sectors evolved over the past 7 trading days.**")
    
    if sector_data_dict is None or benchmark_data is None:
        st.error("❌ No data available for historical analysis")
        return
    
    from indicators import calculate_rsi, calculate_adx, calculate_z_score, calculate_cmf, calculate_mansfield_rs
    
    # Get current top 2 momentum sectors
    current_results = []
    for sect_name, sect_data in sector_data_dict.items():
        if sect_name == 'Nifty 50':
            continue
        
        if len(sect_data) < 50:
            continue
        
        # Calculate current indicators
        rsi = calculate_rsi(sect_data)
        adx, _, _, di_spread = calculate_adx(sect_data)
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
            'ADX_Z': adx_z if not pd.isna(adx_z) else 0,
            'RS_Rating': rs_rating,
            'DI_Spread': di_spread.iloc[-1] if not di_spread.isna().all() else 0,
        })
    
    if not current_results:
        st.error("❌ Unable to calculate rankings")
        return
    
    # Rank and get top 2
    df_current = pd.DataFrame(current_results)
    df_current['ADX_Z_Rank'] = df_current['ADX_Z'].rank(ascending=False)
    df_current['RS_Rating_Rank'] = df_current['RS_Rating'].rank(ascending=False)
    df_current['RSI_Rank'] = df_current['RSI'].rank(ascending=False)
    df_current['DI_Spread_Rank'] = df_current['DI_Spread'].rank(ascending=False)
    
    total_weight = sum(momentum_weights.values())
    df_current['Momentum_Score'] = (
        (df_current['ADX_Z_Rank'] * momentum_weights.get('ADX_Z', 20) / total_weight) +
        (df_current['RS_Rating_Rank'] * momentum_weights.get('RS_Rating', 40) / total_weight) +
        (df_current['RSI_Rank'] * momentum_weights.get('RSI', 30) / total_weight) +
        (df_current['DI_Spread_Rank'] * momentum_weights.get('DI_Spread', 10) / total_weight)
    )
    
    # Scale 1-10
    num_sectors = len(df_current)
    if num_sectors > 1:
        min_rank = df_current['Momentum_Score'].min()
        max_rank = df_current['Momentum_Score'].max()
        if max_rank > min_rank:
            df_current['Momentum_Score'] = 10 - ((df_current['Momentum_Score'] - min_rank) / (max_rank - min_rank)) * 9
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
    
    from company_symbols import SECTOR_COMPANIES, load_sector_companies_from_excel
    
    # Try to load from Excel if available
    excel_data = load_sector_companies_from_excel('Sector-Company.xlsx')
    
    # Use Excel data if available, otherwise use default
    display_data = excel_data if excel_data is not None else SECTOR_COMPANIES
    
    if excel_data is not None:
        st.success("✅ **Data loaded from Sector-Company.xlsx**")
    
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
        if excel_data is not None:
            st.caption("✅ Using Sector-Company.xlsx")
        else:
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
    Check if price is in Fibonacci golden zone (0.5 to 0.618).
    
    Returns:
        Tuple of (is_in_zone, fib_level, distance_pct)
        fib_level: '0.5', '0.618', or None
        distance_pct: % distance from fib level
    """
    fib_50 = fib_levels[0.5]
    fib_618 = fib_levels[0.618]
    
    # Check if price is between 0.5 and 0.618
    if fib_618 <= price <= fib_50:
        # Calculate which level is closer
        dist_to_50 = abs(price - fib_50) / fib_50 * 100
        dist_to_618 = abs(price - fib_618) / fib_618 * 100
        
        if dist_to_50 < dist_to_618:
            return True, '0.5', dist_to_50
        else:
            return True, '0.618', dist_to_618
    
    # Check if price is near 0.5 (within 2%)
    if abs(price - fib_50) / fib_50 * 100 < 2.0:
        return True, '0.5', abs(price - fib_50) / fib_50 * 100
    
    # Check if price is near 0.618 (within 2%)
    if abs(price - fib_618) / fib_618 * 100 < 2.0:
        return True, '0.618', abs(price - fib_618) / fib_618 * 100
    
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


def display_stock_analysis_tab(analysis_date=None):
    """
    Display comprehensive stock analysis with 4-part structure.
    
    PART 1: Market Overview (NSE/NIFTY)
    - Sentiment: India VIX, Advance/Decline (with totals and 7-day trend)
    - Breadth: % above 20 DMA and 50 DMA (with 7-day trend)
    - Total market stocks count
    
    PART 2: Nifty - Fibonacci Analysis
    - Swing high/low from daily high/low (last 20 days)
    - Fibonacci levels (0.5-0.618 golden zone)
    
    PART 3: Individual Stock - Fibonacci
    - Fibonacci analysis for stocks from CSV
    - 15-minute timeframe, day-end data after 4 PM
    - Display: Co name, Stock price, Fib level, Remark, Last crossing time, RSI (1H), ADX (1H)
    - Ranked in descending order of best match
    
    PART 4: Individual Stock Ranking - Confluence Analysis
    - Trend, Direction, RSI, Setup, Divergence
    - Confluence Score ranking
    
    Args:
        analysis_date: Date for analysis
    """
    import os
    import numpy as np
    from io import BytesIO
    from data_fetcher import fetch_sector_data
    
    st.markdown("### 📊 Stock Analysis Dashboard")
    st.markdown("---")
    
    # Load stock list from CSV
    csv_path = 'sector_companies_20260204.csv'
    if not os.path.exists(csv_path):
        st.error(f"❌ CSV file not found: {csv_path}")
        st.info("Please ensure sector_companies_20260204.csv is in the project directory")
        return
    
    try:
        df_stocks = pd.read_csv(csv_path)
        # Remove duplicates if any
        df_stocks = df_stocks.drop_duplicates(subset=['Symbol'], keep='first')
        total_market_stocks = len(df_stocks)
        st.success(f"✅ Loaded {total_market_stocks} unique stocks from CSV")
    except Exception as e:
        st.error(f"❌ Error loading CSV: {str(e)}")
        return
    
    # Historical data storage for logging
    historical_logs = []
    
    # ============================================================
    # PART 1: MARKET OVERVIEW (ENHANCED)
    # ============================================================
    st.markdown("## 📈 PART 1: Market Overview (NSE/NIFTY)")
    st.markdown("---")
    
    with st.spinner("Fetching market data and calculating 7-day trends..."):
        # Fetch Nifty 50 data (need at least 7 days for trends)
        nifty_data = fetch_sector_data('^NSEI', end_date=analysis_date, interval='1d')
        
        # Fetch India VIX (try multiple symbols)
        vix_symbols = ['^INDIAVIX', 'INDIAVIX.NS', 'INDIAVIX']
        vix_value = None
        for vix_sym in vix_symbols:
            try:
                vix_data = fetch_sector_data(vix_sym, end_date=analysis_date, interval='1d')
                if vix_data is not None and len(vix_data) > 0:
                    vix_value = vix_data['Close'].iloc[-1]
                    break
            except:
                continue
        
        if nifty_data is None or len(nifty_data) == 0:
            st.error("❌ Unable to fetch Nifty 50 data")
            return
        
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
    # PART 2: NIFTY - FIBONACCI ANALYSIS
    # ============================================================
    st.markdown("## 🔢 PART 2: Nifty - Fibonacci Analysis")
    st.markdown("---")
    
    with st.spinner("Calculating Nifty Fibonacci levels..."):
        try:
            # Fetch daily Nifty data for last 20 days
            nifty_daily = fetch_sector_data('^NSEI', end_date=analysis_date, interval='1d')
            
            if nifty_daily is not None and len(nifty_daily) >= 20:
                # Find swing high and swing low based on day's HIGH and LOW
                swing_high, swing_low, swing_high_date, swing_low_date = find_swing_high_low(nifty_daily, lookback_days=20)
                
                # Calculate Fibonacci levels
                fib_levels = calculate_fibonacci_levels(swing_high, swing_low)
                
                # Current Nifty price
                current_nifty_price = nifty_daily['Close'].iloc[-1]
                
                # Check if current price is in golden zone
                in_zone, fib_level, distance = check_fibonacci_golden_zone(current_nifty_price, fib_levels)
                
                # Display Fibonacci analysis
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
                    st.write(f"**0.500:** ₹{fib_levels[0.5]:,.2f} ⭐")
                    st.write(f"**0.618:** ₹{fib_levels[0.618]:,.2f} ⭐")
                    st.write(f"**0.786:** ₹{fib_levels[0.786]:,.2f}")
                
                if in_zone:
                    st.success(f"✅ Nifty is in Golden Zone (Fib {fib_level}) - Distance: {distance:.2f}%")
                else:
                    st.info(f"ℹ️ Nifty is not in Golden Zone. Nearest level: {fib_level if fib_level else 'N/A'}")
            else:
                st.warning("⚠️ Insufficient Nifty data for Fibonacci analysis")
        except Exception as e:
            st.error(f"❌ Error in Nifty Fibonacci analysis: {str(e)}")
    
    # ============================================================
    # PART 3: INDIVIDUAL STOCK - FIBONACCI ANALYSIS
    # ============================================================
    st.markdown("## 📊 PART 3: Individual Stock - Fibonacci Analysis")
    st.markdown("---")
    st.info("Analyzing stocks for Fibonacci golden zone (0.5-0.618). This may take a few minutes...")
    
    fib_results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, row in df_stocks.iterrows():
        symbol = row['Symbol']
        sector = row['Sector']
        company_name = row['Company Name']
        
        status_text.text(f"Analyzing Fibonacci for {company_name} ({idx+1}/{len(df_stocks)})...")
        progress_bar.progress((idx + 1) / len(df_stocks))
        
        try:
            # Fetch 15-minute data (preferred timeframe)
            # For day-end data after 4 PM, we'll use daily data and resample if needed
            data_15m = fetch_sector_data(symbol, end_date=analysis_date, interval='15m')
            
            # If 15m not available, try daily and use it
            if data_15m is None or len(data_15m) < 20:
                data_daily = fetch_sector_data(symbol, end_date=analysis_date, interval='1d')
                if data_daily is None or len(data_daily) < 20:
                    continue
                data_for_fib = data_daily
            else:
                data_for_fib = data_15m
            
            # Find swing high and swing low based on day's HIGH and LOW (last 20 days)
            # For intraday data, we need to aggregate to daily first
            if data_for_fib.index.freq is None or 'D' not in str(data_for_fib.index.freq):
                # Resample to daily using HIGH and LOW
                data_daily_agg = data_for_fib.resample('D').agg({
                    'Open': 'first',
                    'High': 'max',  # Day's high
                    'Low': 'min',   # Day's low
                    'Close': 'last',
                    'Volume': 'sum'
                }).dropna()
            else:
                data_daily_agg = data_for_fib
            
            if len(data_daily_agg) < 20:
                continue
            
            # Find swing points
            swing_high, swing_low, swing_high_date, swing_low_date = find_swing_high_low(data_daily_agg, lookback_days=20)
            
            # Calculate Fibonacci levels
            fib_levels = calculate_fibonacci_levels(swing_high, swing_low)
            
            # Current stock price
            current_price = data_daily_agg['Close'].iloc[-1]
            
            # Check if in golden zone (0.5-0.618)
            in_zone, fib_level, distance = check_fibonacci_golden_zone(current_price, fib_levels)
            
            if in_zone:
                # Calculate price range
                fib_50 = fib_levels[0.5]
                fib_618 = fib_levels[0.618]
                price_range = f"₹{fib_618:,.2f} - ₹{fib_50:,.2f}"
                
                # Calculate % up from Fib 0.5 or % down from Fib 0.618
                if fib_level == '0.5':
                    pct_from_fib = ((current_price - fib_50) / fib_50) * 100
                    remark = f"{price_range} | {pct_from_fib:+.2f}% from Fib 0.5"
                else:
                    pct_from_fib = ((current_price - fib_618) / fib_618) * 100
                    remark = f"{price_range} | {pct_from_fib:+.2f}% from Fib 0.618"
                
                # Find last crossing time
                last_crossing = find_last_crossing_time(data_daily_agg, fib_levels[0.5] if fib_level == '0.5' else fib_levels[0.618], current_price)
                
                # Fetch 1H data for RSI and ADX
                data_1h = fetch_sector_data(symbol, end_date=analysis_date, interval='1h')
                rsi_1h = None
                adx_1h = None
                
                if data_1h is not None and len(data_1h) >= 14:
                    rsi_series = calculate_rsi(data_1h)
                    rsi_1h = rsi_series.iloc[-1] if not rsi_series.isna().all() else None
                    
                    adx_series, _, _, _ = calculate_adx(data_1h)
                    adx_1h = adx_series.iloc[-1] if adx_series is not None and not adx_series.isna().all() else None
                
                # Calculate match score (lower distance = better match)
                match_score = 100 - distance  # Invert distance so higher = better
                
                fib_results.append({
                    'Company': company_name,
                    'Stock Price': current_price,
                    'Fib Level': fib_level,
                    'Remark': remark,
                    'Last Crossing Time': last_crossing,
                    'RSI (1H)': f"{rsi_1h:.1f}" if rsi_1h else "N/A",
                    'ADX (1H)': f"{adx_1h:.1f}" if adx_1h else "N/A",
                    'Match Score': match_score,
                    'Sector': sector,
                    'Symbol': symbol
                })
        
        except Exception as e:
            continue
    
    progress_bar.empty()
    status_text.empty()
    
    if fib_results:
        # Sort by match score (descending order of best match)
        df_fib = pd.DataFrame(fib_results)
        df_fib = df_fib.sort_values('Match Score', ascending=False)
        
        # Display results
        st.markdown("### 🎯 Stocks in Fibonacci Golden Zone (0.5-0.618)")
        display_cols = ['Company', 'Stock Price', 'Fib Level', 'Remark', 'Last Crossing Time', 'RSI (1H)', 'ADX (1H)']
        st.dataframe(df_fib[display_cols], use_container_width=True, hide_index=True)
        
        st.success(f"✅ Found {len(fib_results)} stocks in Fibonacci golden zone")
    else:
        st.warning("⚠️ No stocks found in Fibonacci golden zone")
    
    # ============================================================
    # PART 4: INDIVIDUAL STOCK RANKING - CONFLUENCE ANALYSIS
    # ============================================================
    st.markdown("## 🏆 PART 4: Individual Stock Ranking - Confluence Analysis")
    st.markdown("---")
    st.info("Analyzing stocks for confluence factors. This may take a few minutes...")
    
    stock_results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, row in df_stocks.iterrows():
        symbol = row['Symbol']
        sector = row['Sector']
        company_name = row['Company Name']
        
        status_text.text(f"Analyzing confluence for {company_name} ({idx+1}/{len(df_stocks)})...")
        progress_bar.progress((idx + 1) / len(df_stocks))
        
        try:
            # Fetch 1H data and resample to 4H
            data_1h = fetch_sector_data(symbol, end_date=analysis_date, interval='1h')
            if data_1h is None or len(data_1h) < 50:
                continue
            
            # Resample to 4H
            data_4h = data_1h.resample('4H').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()
            
            if len(data_4h) < 20:
                continue
            
            # Calculate DMAs
            data_4h['DMA_20'] = data_4h['Close'].rolling(20).mean()
            data_4h['DMA_50'] = data_4h['Close'].rolling(50).mean()
            
            # Get latest values
            current_price = data_4h['Close'].iloc[-1]
            dma_20 = data_4h['DMA_20'].iloc[-1]
            dma_50 = data_4h['DMA_50'].iloc[-1]
            
            # 1. TREND: Detect HH/HL (Uptrend) or LL/LH (Downtrend)
            recent_highs = data_4h['High'].tail(10).values
            recent_lows = data_4h['Low'].tail(10).values
            
            # Check for Higher Highs and Higher Lows (Uptrend)
            if len(recent_highs) >= 4:
                hh_pattern = recent_highs[-1] > recent_highs[-3] > recent_highs[-5] if len(recent_highs) >= 5 else False
                hl_pattern = recent_lows[-1] > recent_lows[-3] > recent_lows[-5] if len(recent_lows) >= 5 else False
                uptrend = hh_pattern and hl_pattern
            else:
                uptrend = False
            
            # Check for Lower Lows and Lower Highs (Downtrend)
            if len(recent_lows) >= 4:
                ll_pattern = recent_lows[-1] < recent_lows[-3] < recent_lows[-5] if len(recent_lows) >= 5 else False
                lh_pattern = recent_highs[-1] < recent_highs[-3] < recent_highs[-5] if len(recent_highs) >= 5 else False
                downtrend = ll_pattern and lh_pattern
            else:
                downtrend = False
            
            if uptrend:
                trend = "HH/HL (Uptrend)"
            elif downtrend:
                trend = "LL/LH (Downtrend)"
            else:
                trend = "Sideways"
            
            # 2. DIRECTION: Price > 20 DMA > 50 DMA (Bullish) or Price < 20 DMA < 50 DMA (Bearish)
            if pd.notna(dma_20) and pd.notna(dma_50):
                if current_price > dma_20 > dma_50:
                    direction = "Bullish"
                elif current_price < dma_20 < dma_50:
                    direction = "Bearish"
                else:
                    direction = "Mixed"
            else:
                direction = "N/A"
            
            # 3. MOMENTUM: RSI (14)
            rsi_series = calculate_rsi(data_4h)
            rsi_current = rsi_series.iloc[-1] if not rsi_series.isna().all() else 50.0
            rsi_prev = rsi_series.iloc[-2] if len(rsi_series) > 1 and not pd.isna(rsi_series.iloc[-2]) else rsi_current
            
            rsi_rising = rsi_current > rsi_prev
            rsi_falling = rsi_current < rsi_prev
            rsi_in_zone = 40 <= rsi_current <= 60
            
            rsi_status = []
            if rsi_rising:
                rsi_status.append("Rising")
            if rsi_falling:
                rsi_status.append("Falling")
            if rsi_in_zone:
                rsi_status.append("40-60 Zone")
            
            rsi_display = f"{rsi_current:.1f} ({', '.join(rsi_status)})" if rsi_status else f"{rsi_current:.1f}"
            
            # 4. CHART SETUP: DMA crossover detection
            if pd.notna(dma_20) and pd.notna(dma_50):
                dma_diff_pct = abs((dma_20 - dma_50) / dma_50 * 100)
                if dma_diff_pct < 2.0:  # Within 2% = approaching crossover
                    setup = "Crossover Setup"
                elif dma_20 > dma_50:
                    setup = "20 DMA > 50 DMA"
                else:
                    setup = "20 DMA < 50 DMA"
            else:
                setup = "N/A"
            
            # 5. RSI DIVERGENCE: At 50% formation mark (2-hour mark of 4H candle)
            current_4h_start = data_4h.index[-1] - pd.Timedelta(hours=4)
            current_1h_data = data_1h[data_1h.index >= current_4h_start]
            
            divergence = "None"
            if len(current_1h_data) >= 2:
                mid_point_idx = len(current_1h_data) // 2
                if mid_point_idx > 0 and mid_point_idx < len(current_1h_data):
                    rsi_1h_series = calculate_rsi(current_1h_data)
                    if len(rsi_1h_series) > mid_point_idx:
                        rsi_at_50pct = rsi_1h_series.iloc[mid_point_idx] if not pd.isna(rsi_1h_series.iloc[mid_point_idx]) else rsi_current
                        
                        price_at_start = current_1h_data['Close'].iloc[0]
                        price_at_50pct = current_1h_data['Close'].iloc[mid_point_idx]
                        price_at_end = current_1h_data['Close'].iloc[-1]
                        
                        if price_at_50pct < price_at_start and rsi_at_50pct > rsi_current:
                            divergence = "Bullish"
                        elif price_at_50pct > price_at_start and rsi_at_50pct < rsi_current:
                            divergence = "Bearish"
            
            # Calculate Confluence Score
            score = 0
            if trend == "HH/HL (Uptrend)":
                score += 3
            elif trend == "LL/LH (Downtrend)":
                score += 0
            else:
                score += 1
            
            if direction == "Bullish":
                score += 3
            elif direction == "Bearish":
                score += 0
            else:
                score += 1
            
            if rsi_rising and rsi_in_zone:
                score += 2
            elif rsi_rising:
                score += 1
            
            if setup == "Crossover Setup" and direction == "Bullish":
                score += 2
            
            if divergence == "Bullish":
                score += 2
            elif divergence == "Bearish":
                score -= 1
            
            stock_results.append({
                'Sector': sector,
                'Symbol': symbol,
                'Company': company_name,
                'Trend': trend,
                'Direction': direction,
                'RSI': rsi_display,
                'Setup': setup,
                'Divergence': divergence,
                'Score': score
            })
            
        except Exception as e:
            continue
    
    progress_bar.empty()
    status_text.empty()
    
    if not stock_results:
        st.warning("⚠️ No stock data available for confluence analysis")
    else:
        # Create DataFrame and rank
        df_results = pd.DataFrame(stock_results)
        df_results = df_results.sort_values('Score', ascending=False)
        df_results['Rank'] = range(1, len(df_results) + 1)
        
        # Display top 10
        st.markdown("### 🥇 Top 10 Stocks by Confluence Score")
        df_top10 = df_results.head(10)[['Rank', 'Sector', 'Symbol', 'Company', 'Trend', 'Direction', 'RSI', 'Setup', 'Divergence', 'Score']]
        st.dataframe(df_top10, use_container_width=True, hide_index=True)
        
        st.success(f"✅ Confluence analysis complete! Analyzed {len(stock_results)} stocks.")
    
    # ============================================================
    # HISTORICAL LOGGING & EXPORT
    # ============================================================
    st.markdown("---")
    st.markdown("## 📥 Export & Historical Logs")
    
    # Prepare Excel export with all data
    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        # Market Overview logs
        if historical_logs:
            df_logs = pd.DataFrame(historical_logs)
            df_logs.to_excel(writer, sheet_name='Market Overview Logs', index=False)
        
        # Fibonacci results
        if fib_results:
            df_fib_export = pd.DataFrame(fib_results)
            df_fib_export.to_excel(writer, sheet_name='Fibonacci Analysis', index=False)
        
        # Confluence results
        if stock_results:
            df_results.to_excel(writer, sheet_name='Confluence Analysis - All', index=False)
            df_top10.to_excel(writer, sheet_name='Confluence Analysis - Top 10', index=False)
    
    excel_buffer.seek(0)
    
    st.download_button(
        label="📥 Download Complete Analysis (Excel)",
        data=excel_buffer.read(),
        file_name=f'stock_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    
    st.success(f"✅ Complete analysis finished! Total stocks analyzed: {total_market_stocks}")


def main():
    """Main Streamlit app function."""
    try:
        # Header
        st.markdown('<div class="main-header">📊 NSE Market Sector Analysis Tool</div>', 
                    unsafe_allow_html=True)
        st.markdown('<div class="sub-header">Advanced Technical Analysis with Configurable Weights</div>', 
                    unsafe_allow_html=True)
        
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
        
        # Create tabs (8 total: 4 sector-level + 2 company-level + 1 historical + 1 sector companies + 1 data sources + 1 stock analysis)
        try:
            tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
                "📈 Momentum Ranking",
                "📊 Stock Analysis",
                "🔄 Reversal Candidates",
                "📊 Interpretation Guide",
                "🏢 Company Momentum",
                "🏢 Company Reversals",
                "📅 Historical Rankings",
                "🔌 Data Sources"
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
                    display_stock_analysis_tab(analysis_date=analysis_date)
                except Exception as e:
                    st.error(f"❌ Error displaying stock analysis tab: {str(e)}")
                    st.text(traceback.format_exc())
            
            with tab3:
                try:
                    display_reversal_tab(df, sector_data, benchmark_data, reversal_weights, reversal_thresholds, enable_color_coding)
                    display_tooltip_legend()
                except Exception as e:
                    st.error(f"❌ Error displaying reversal tab: {str(e)}")
                    st.text(traceback.format_exc())
            
            with tab4:
                try:
                    display_interpretation_tab()
                    display_tooltip_legend()
                except Exception as e:
                    st.error(f"❌ Error displaying interpretation tab: {str(e)}")
            
            with tab5:
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
            
            with tab6:
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
            
            with tab7:
                try:
                    display_historical_rankings_tab(sector_data, benchmark_data, momentum_weights, reversal_weights, reversal_thresholds, use_etf)
                    display_tooltip_legend()
                except Exception as e:
                    st.error(f"❌ Error displaying historical rankings tab: {str(e)}")
                    st.text(traceback.format_exc())
            
            with tab8:
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
