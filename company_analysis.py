"""
Company-Level Momentum and Reversal Analysis
Analyzes individual companies within sectors with same logic as sector analysis
Benchmarks each company against Nifty 50
Optimized with caching for faster loading
"""

import streamlit as st
import pandas as pd
from company_symbols import SECTOR_COMPANIES, get_company_symbol_list
from data_fetcher import fetch_sector_data
from indicators import calculate_rsi, calculate_adx, calculate_cmf, calculate_z_score, calculate_mansfield_rs
from config import DEFAULT_MOMENTUM_WEIGHTS, DEFAULT_REVERSAL_WEIGHTS


def format_value(val, decimals=1):
    """Format numerical value with specified decimal places."""
    try:
        return f"{float(val):.{decimals}f}"
    except:
        return val


@st.cache_data(ttl=300, show_spinner=False)
def fetch_company_data_cached(selected_sector, interval='1d'):
    """
    Fetch and cache company data for a sector.
    Returns tuple of (companies_data dict, failed_companies list, benchmark_data)
    
    Args:
        selected_sector: Sector name
        interval: Data interval ('1d', '1wk', '1h')
    """
    company_list = get_company_symbol_list(selected_sector)
    companies_data = {}
    failed_companies = []
    
    for company_symbol in company_list:
        try:
            data = fetch_sector_data(company_symbol, end_date=None, interval=interval)
            if data is not None and len(data) > 0:
                companies_data[company_symbol] = data
            else:
                failed_companies.append(company_symbol)
        except:
            failed_companies.append(company_symbol)
    
    # Also fetch benchmark
    benchmark_data = fetch_sector_data('^NSEI', end_date=None, interval=interval)
    
    return companies_data, failed_companies, benchmark_data


def calculate_company_trend(company_symbol, company_data, benchmark_data, all_companies_data_dict, selected_sector, periods=7):
    """
    Calculate trend for a company over the last N periods.
    Similar to sector trend analysis but for individual companies.
    
    Args:
        company_symbol: Symbol of the company to analyze
        company_data: Price data for the selected company
        benchmark_data: Benchmark (Nifty 50) data
        all_companies_data_dict: Dictionary of all company data for the sector
        selected_sector: Name of the sector
        periods: Number of periods to look back
    
    Returns:
        DataFrame with historical indicators
    """
    try:
        if company_data is None or len(company_data) < periods:
            return None
        
        trend_data = []
        
        for i in range(periods, 0, -1):
            try:
                # Get the actual date for this period from the data index
                period_index = -i if i > 0 else -1
                if abs(period_index) <= len(company_data):
                    period_date = company_data.index[period_index]
                    date_str = period_date.strftime('%d-%b')
                else:
                    date_str = ""
                
                period_label = f'T-{i-1} ({date_str})' if i > 1 else f'T ({date_str})'
                
                # Get data up to that historical point
                subset_data = company_data.iloc[:-i+1] if i > 1 else company_data
                bench_subset = benchmark_data.iloc[:-i+1] if i > 1 else benchmark_data
                
                if len(subset_data) < 14:  # Minimum for most indicators
                    continue
                
                # Calculate all indicators for this company at this point in time
                rsi = calculate_rsi(subset_data)
                adx, plus_di, minus_di, di_spread = calculate_adx(subset_data)
                cmf = calculate_cmf(subset_data)
                mansfield_rs = calculate_mansfield_rs(subset_data, bench_subset)
                adx_z = calculate_z_score(adx.dropna())
                
                # Calculate RS Rating
                if bench_subset is not None and len(bench_subset) > 0:
                    company_returns = subset_data['Close'].pct_change().dropna()
                    benchmark_returns = bench_subset['Close'].pct_change().dropna()
                    
                    common_index = company_returns.index.intersection(benchmark_returns.index)
                    if len(common_index) > 1:
                        company_returns_aligned = company_returns.loc[common_index]
                        benchmark_returns_aligned = benchmark_returns.loc[common_index]
                        
                        company_cumret = (1 + company_returns_aligned).prod() - 1
                        benchmark_cumret = (1 + benchmark_returns_aligned).prod() - 1
                        
                        if not pd.isna(company_cumret) and not pd.isna(benchmark_cumret):
                            relative_perf = company_cumret - benchmark_cumret
                            rs_rating = 5 + (relative_perf * 25)
                            rs_rating = max(0, min(10, rs_rating))
                        else:
                            rs_rating = 5.0
                    else:
                        rs_rating = 5.0
                else:
                    rs_rating = 5.0
                
                trend_data.append({
                    'Period': period_label,
                    'Mansfield_RS': format_value(mansfield_rs, 1),
                    'RS_Rating': format_value(rs_rating, 1),
                    'ADX': format_value(adx.iloc[-1] if not adx.isna().all() else 0, 1),
                    'ADX_Z': format_value(adx_z if not pd.isna(adx_z) else 0, 1),
                    'DI_Spread': format_value(di_spread.iloc[-1] if not di_spread.isna().all() else 0, 1),
                    'RSI': format_value(rsi.iloc[-1] if not rsi.isna().all() else 50, 1),
                    'CMF': format_value(cmf.iloc[-1] if not cmf.isna().all() else 0, 2),
                })
            except Exception as e:
                continue
        
        if not trend_data:
            return None
        
        df = pd.DataFrame(trend_data)
        return df
        
    except Exception as e:
        st.warning(f"⚠️ Error calculating company trend: {str(e)}")
        return None



def display_company_momentum_tab(time_interval='Daily', momentum_weights=None):
    """
    Display company-level momentum analysis within selected sector.
    Uses same ranking-based logic as sector momentum scoring.
    
    Args:
        time_interval: 'Daily', 'Weekly', or 'Hourly' - matches sidebar selection
        momentum_weights: Dict with weights for RSI, ADX_Z, RS_Rating, DI_Spread
    """
    if momentum_weights is None:
        momentum_weights = DEFAULT_MOMENTUM_WEIGHTS
    
    # Convert to yfinance interval format
    interval_map = {'Daily': '1d', 'Weekly': '1wk', 'Hourly': '1h'}
    yf_interval = interval_map.get(time_interval, '1d')
    
    st.markdown("### 📈 Company Momentum Analysis")
    st.markdown("---")
    st.info("🔍 **Drill down into individual companies** within a sector. Same momentum scoring as sectors, benchmarked against Nifty 50.")
    
    # Sector selector
    sector_list = list(SECTOR_COMPANIES.keys())
    selected_sector = st.selectbox("Select Sector/ETF:", sector_list, key="company_momentum_sector")
    
    if not selected_sector:
        st.warning("Please select a sector")
        return
    
    st.markdown(f"**Analysis:** {selected_sector} | Top companies by index weight")
    
    # Fetch company data using cached function with correct interval
    with st.spinner(f"Analyzing companies in {selected_sector}..."):
        companies_data, failed_companies, benchmark_data = fetch_company_data_cached(selected_sector, interval=yf_interval)
        
        if not companies_data:
            st.error(f"❌ No data available for companies in {selected_sector}")
            return
        
        if failed_companies:
            st.warning(f"⚠️ Could not fetch data for: {', '.join(failed_companies)}")
    
    if benchmark_data is None or len(benchmark_data) == 0:
        st.error("❌ Unable to fetch Nifty 50 benchmark data")
        return
    
    # Build analysis for each company - first collect all raw indicator values
    company_results = []
    raw_data_for_ranking = []
    
    for company_symbol, data in companies_data.items():
        company_info = SECTOR_COMPANIES[selected_sector].get(company_symbol, {})
        company_name = company_info.get('name', company_symbol)
        weight = company_info.get('weight', 0)
        
        # Calculate indicators
        rsi_series = calculate_rsi(data)
        adx_series, plus_di_series, minus_di_series, di_spread_series = calculate_adx(data)
        cmf_series = calculate_cmf(data)
        mansfield_rs = calculate_mansfield_rs(data, benchmark_data)  # Returns scalar
        adx_z = calculate_z_score(adx_series.dropna())  # Returns scalar
        
        # Get latest values from Series (or use scalar directly)
        rsi = rsi_series.iloc[-1] if isinstance(rsi_series, pd.Series) and len(rsi_series) > 0 else None
        adx = adx_series.iloc[-1] if isinstance(adx_series, pd.Series) and len(adx_series) > 0 else None
        plus_di = plus_di_series.iloc[-1] if isinstance(plus_di_series, pd.Series) and len(plus_di_series) > 0 else None
        minus_di = minus_di_series.iloc[-1] if isinstance(minus_di_series, pd.Series) and len(minus_di_series) > 0 else None
        di_spread = di_spread_series.iloc[-1] if isinstance(di_spread_series, pd.Series) and len(di_spread_series) > 0 else None
        cmf = cmf_series.iloc[-1] if isinstance(cmf_series, pd.Series) and len(cmf_series) > 0 else None
        
        # Get current price and change %
        current_price = data['Close'].iloc[-1] if len(data) > 0 else 0.0
        prev_close = data['Close'].iloc[-2] if len(data) > 1 else current_price
        pct_change = ((current_price - prev_close) / prev_close * 100) if prev_close != 0 else 0.0
        
        # RS Rating vs Nifty 50
        sector_returns = data['Close'].pct_change().dropna()
        benchmark_returns = benchmark_data['Close'].pct_change().dropna()
        
        common_index = sector_returns.index.intersection(benchmark_returns.index)
        if len(common_index) > 1:
            sector_ret = sector_returns.loc[common_index]
            bench_ret = benchmark_returns.loc[common_index]
            sector_cumret = (1 + sector_ret).prod() - 1
            bench_cumret = (1 + bench_ret).prod() - 1
            relative_perf = sector_cumret - bench_cumret
            rs_rating = 5 + (relative_perf * 25)
            rs_rating = max(0, min(10, rs_rating))
        else:
            rs_rating = 5.0
        
        # Store raw data for ranking calculation
        raw_data_for_ranking.append({
            'Company': company_name,
            'Symbol': company_symbol,
            'Price': current_price,
            'Change_pct': pct_change,
            'RSI': rsi if rsi is not None and pd.notna(rsi) else 50.0,
            'ADX': adx if adx is not None and pd.notna(adx) else 0.0,
            'ADX_Z': adx_z if adx_z is not None and pd.notna(adx_z) else 0.0,
            'DI_Spread': di_spread if di_spread is not None and pd.notna(di_spread) else 0.0,
            'CMF': cmf if cmf is not None and pd.notna(cmf) else 0.0,
            'Mansfield_RS': mansfield_rs if mansfield_rs is not None and pd.notna(mansfield_rs) else 0.0,
            'RS_Rating': rs_rating,
        })
    
    # Create DataFrame for proper ranking
    df_raw = pd.DataFrame(raw_data_for_ranking)
    num_companies = len(df_raw)
    
    if num_companies > 0:
        # Calculate ranks: Higher values = better = rank 1 (ascending=False)
        # Using method='average' to differentiate ties properly
        df_raw['ADX_Z_Rank'] = df_raw['ADX_Z'].rank(ascending=False, method='average')
        df_raw['RS_Rating_Rank'] = df_raw['RS_Rating'].rank(ascending=False, method='average')
        df_raw['RSI_Rank'] = df_raw['RSI'].rank(ascending=False, method='average')
        df_raw['DI_Spread_Rank'] = df_raw['DI_Spread'].rank(ascending=False, method='average')
        
        # Calculate weighted average rank using configurable weights (same logic as sectors)
        total_weight = sum(momentum_weights.values())
        df_raw['Weighted_Avg_Rank'] = (
            (df_raw['ADX_Z_Rank'] * momentum_weights.get('ADX_Z', 20.0) / total_weight) +
            (df_raw['RS_Rating_Rank'] * momentum_weights.get('RS_Rating', 40.0) / total_weight) +
            (df_raw['RSI_Rank'] * momentum_weights.get('RSI', 30.0) / total_weight) +
            (df_raw['DI_Spread_Rank'] * momentum_weights.get('DI_Spread', 10.0) / total_weight)
        )
        
        # Scale to 1-10 where 10 = best momentum, 1 = worst
        if num_companies > 1:
            min_rank = df_raw['Weighted_Avg_Rank'].min()
            max_rank = df_raw['Weighted_Avg_Rank'].max()
            if max_rank > min_rank:
                df_raw['Momentum_Score'] = 10 - ((df_raw['Weighted_Avg_Rank'] - min_rank) / (max_rank - min_rank)) * 9
            else:
                df_raw['Momentum_Score'] = 5.0
        else:
            df_raw['Momentum_Score'] = 5.0
        
        company_scores = df_raw['Momentum_Score'].tolist()
        
        # Build display results
        for _, row in df_raw.iterrows():
            company_results.append({
                'Company': row['Company'],
                'Symbol': row['Symbol'],
                'Price': f"{row['Price']:.2f}",
                'Change %': f"{row['Change_pct']:+.2f}%",
                'Momentum_Score': f"{row['Momentum_Score']:.1f}",
                'Mansfield_RS': f"{row['Mansfield_RS']:.1f}",
                'RS_Rating': f"{row['RS_Rating']:.1f}",
                'RSI': f"{row['RSI']:.1f}",
                'ADX': f"{row['ADX']:.1f}",
                'ADX_Z': f"{row['ADX_Z']:.1f}",
                'DI_Spread': f"{row['DI_Spread']:.1f}",
                'CMF': f"{row['CMF']:.2f}",
            })
    
    # Display results - sort by Momentum Score and add ranking
    df_companies = pd.DataFrame(company_results)
    
    # Convert Momentum_Score to float for sorting and ranking
    df_companies['_score_float'] = df_companies['Momentum_Score'].astype(float)
    df_companies = df_companies.sort_values('_score_float', ascending=False)
    df_companies['Rank'] = range(1, len(df_companies) + 1)
    df_companies = df_companies.drop('_score_float', axis=1)
    
    # Reorder columns to put Rank near the front
    cols = ['Rank', 'Company', 'Symbol', 'Price', 'Change %', 'Momentum_Score', 'Mansfield_RS', 
            'RS_Rating', 'RSI', 'ADX', 'ADX_Z', 'DI_Spread', 'CMF']
    df_companies = df_companies[[c for c in cols if c in df_companies.columns]]
    
    st.dataframe(df_companies, use_container_width=True, height=400)
    
    st.success(f"✅ Analysis complete for {len(companies_data)} companies in {selected_sector}")
    
    # Summary stats with CMF sum
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Companies Analyzed", len(companies_data))
    with col2:
        avg_momentum = sum(company_scores) / len(company_scores) if company_scores else 0
        st.metric("Avg Momentum Score", f"{avg_momentum:.1f}")
    with col3:
        top_momentum = max(company_scores) if company_scores else 0
        st.metric("Highest Momentum", f"{top_momentum:.1f}")
    with col4:
        # Calculate CMF sum for the sector
        cmf_values = [float(r['CMF']) for r in company_results if r['CMF'] != 'N/A']
        cmf_sum = sum(cmf_values) if cmf_values else 0
        cmf_delta = "↑ Inflow" if cmf_sum > 0 else "↓ Outflow"
        st.metric("CMF Sum (Sector)", f"{cmf_sum:.2f}", delta=cmf_delta,
                  help="Sum of all company CMF values in this sector")
    
    # Company Trend Analysis
    st.markdown("---")
    st.markdown("### 📊 Company Trend Analysis (T-7 to T)")
    
    company_symbols_list = list(companies_data.keys())
    selected_company_symbol = st.selectbox("Select a company for trend view:", company_symbols_list, key="momentum_company_trend")
    
    if selected_company_symbol and selected_company_symbol in companies_data:
        with st.spinner(f"Calculating trend for {selected_company_symbol}..."):
            trend_df = calculate_company_trend(selected_company_symbol, companies_data[selected_company_symbol], 
                                             benchmark_data, companies_data, selected_sector, periods=8)
        
        if trend_df is not None:
            company_name = SECTOR_COMPANIES[selected_sector].get(selected_company_symbol, {}).get('name', selected_company_symbol)
            st.markdown(f"#### Trend for **{company_name}** ({selected_company_symbol})")
            
            # Transpose trend data: periods as columns, indicators as rows
            trend_display = trend_df.set_index('Period').T
            
            # Apply color styling
            def style_company_trend(val):
                """Apply mild green/red colors based on indicator values."""
                try:
                    num_val = float(val)
                    # Mansfield_RS: positive = green, negative = red
                    if 'Mansfield' in str(val):
                        if num_val > 0:
                            return 'background-color: #d4edda; color: #000'
                        elif num_val < 0:
                            return 'background-color: #f8d7da; color: #000'
                    # RSI: >65 = green, <35 = red
                    elif 'RSI' in str(val):
                        if num_val > 65:
                            return 'background-color: #d4edda; color: #000'
                        elif num_val < 35:
                            return 'background-color: #f8d7da; color: #000'
                    # ADX: >25 = green, <20 = red
                    elif 'ADX' in str(val) and 'ADX_Z' not in str(val):
                        if num_val > 25:
                            return 'background-color: #d4edda; color: #000'
                        elif num_val < 20:
                            return 'background-color: #f8d7da; color: #000'
                    # ADX_Z: >0 = green, <0 = red
                    elif 'ADX_Z' in str(val):
                        if num_val > 0:
                            return 'background-color: #d4edda; color: #000'
                        elif num_val < 0:
                            return 'background-color: #f8d7da; color: #000'
                    # DI_Spread: >0 = green, <0 = red
                    elif 'DI_Spread' in str(val):
                        if num_val > 0:
                            return 'background-color: #d4edda; color: #000'
                        elif num_val < 0:
                            return 'background-color: #f8d7da; color: #000'
                    # CMF: >0 = green, <0 = red
                    elif 'CMF' in str(val):
                        if num_val > 0:
                            return 'background-color: #d4edda; color: #000'
                        elif num_val < 0:
                            return 'background-color: #f8d7da; color: #000'
                except:
                    pass
                return ''
            
            trend_styled = trend_display.style.applymap(style_company_trend)
            st.dataframe(trend_styled, use_container_width=True, hide_index=True)
            st.caption("📈 **Note:** Dates as columns (T-7 to T), Indicators as rows. Green/Red shows bullish/bearish signals.")


def display_company_reversal_tab(time_interval='Daily', reversal_weights=None):
    """
    Display company-level reversal analysis within selected sector.
    Uses same ranking-based logic as sector reversal scoring.
    
    Args:
        time_interval: 'Daily', 'Weekly', or 'Hourly' - matches sidebar selection
        reversal_weights: Dict with weights for RSI, ADX_Z, RS_Rating, CMF
    """
    if reversal_weights is None:
        reversal_weights = DEFAULT_REVERSAL_WEIGHTS
    
    # Convert to yfinance interval format
    interval_map = {'Daily': '1d', 'Weekly': '1wk', 'Hourly': '1h'}
    yf_interval = interval_map.get(time_interval, '1d')
    
    st.markdown("### 🔄 Company Reversal Analysis")
    st.markdown("---")
    st.info("🎯 **Find oversold companies** within a sector showing recovery signals. Benchmarked against Nifty 50.")
    
    # Sector selector
    sector_list = list(SECTOR_COMPANIES.keys())
    selected_sector = st.selectbox("Select Sector/ETF:", sector_list, key="company_reversal_sector")
    
    if not selected_sector:
        st.warning("Please select a sector")
        return
    
    # Reversal filter thresholds - user-configurable
    st.sidebar.markdown("---")
    st.sidebar.subheader("Company Reversal Filters")
    rsi_threshold = st.sidebar.slider("RSI must be below", 20.0, 60.0, 40.0, 1.0,
                                      help="Only show companies with RSI below this value",
                                      key="company_rsi_threshold")
    adx_z_threshold = st.sidebar.slider("ADX Z-Score must be below", -2.0, 2.0, -0.5, 0.1,
                                        help="Only show companies with ADX Z below this value",
                                        key="company_adx_z_threshold")
    cmf_threshold = st.sidebar.slider("CMF must be above", -0.5, 0.5, 0.0, 0.05,
                                      help="Only show companies with CMF above this value (money inflow)",
                                      key="company_cmf_threshold")
    
    reversal_thresholds = {'RSI': rsi_threshold, 'ADX_Z': adx_z_threshold, 'CMF': cmf_threshold}
    
    st.markdown(f"**Analysis:** {selected_sector} | Reversal candidates with money flow signals")
    
    # Fetch company data using cached function with correct interval
    with st.spinner(f"Analyzing reversal opportunities in {selected_sector}..."):
        companies_data, failed_companies, benchmark_data = fetch_company_data_cached(selected_sector, interval=yf_interval)
        
        if not companies_data:
            st.error(f"❌ No data available for companies in {selected_sector}")
            return
        
        if failed_companies:
            st.warning(f"⚠️ Could not fetch data for: {', '.join(failed_companies)}")
    
    if benchmark_data is None or len(benchmark_data) == 0:
        st.error("❌ Unable to fetch Nifty 50 benchmark data")
        return
    
    # Build analysis for each company - collect all data first for ranking
    all_company_data = []
    
    for company_symbol, data in companies_data.items():
        company_info = SECTOR_COMPANIES[selected_sector].get(company_symbol, {})
        company_name = company_info.get('name', company_symbol)
        weight = company_info.get('weight', 0)
        
        # Calculate indicators
        rsi_series = calculate_rsi(data)
        adx_series, plus_di_series, minus_di_series, di_spread_series = calculate_adx(data)
        cmf_series = calculate_cmf(data)
        adx_z = calculate_z_score(adx_series.dropna())  # Returns scalar
        mansfield_rs = calculate_mansfield_rs(data, benchmark_data)  # Returns scalar
        
        # Get latest values from Series (or use scalar directly)
        rsi = rsi_series.iloc[-1] if isinstance(rsi_series, pd.Series) and len(rsi_series) > 0 else None
        cmf = cmf_series.iloc[-1] if isinstance(cmf_series, pd.Series) and len(cmf_series) > 0 else None
        
        # RS Rating calculation
        sector_returns = data['Close'].pct_change().dropna()
        benchmark_returns = benchmark_data['Close'].pct_change().dropna()
        common_index = sector_returns.index.intersection(benchmark_returns.index)
        if len(common_index) > 1:
            sector_ret = sector_returns.loc[common_index]
            bench_ret = benchmark_returns.loc[common_index]
            sector_cumret = (1 + sector_ret).prod() - 1
            bench_cumret = (1 + bench_ret).prod() - 1
            relative_perf = sector_cumret - bench_cumret
            rs_rating = 5 + (relative_perf * 25)
            rs_rating = max(0, min(10, rs_rating))
        else:
            rs_rating = 5.0
        
        # Get current price and change %
        current_price = data['Close'].iloc[-1] if len(data) > 0 else 0.0
        prev_close = data['Close'].iloc[-2] if len(data) > 1 else current_price
        pct_change = ((current_price - prev_close) / prev_close * 100) if prev_close != 0 else 0.0
        
        # Check if company meets ALL reversal filter criteria
        meets_criteria = False
        if rsi is not None and adx_z is not None and cmf is not None:
            if pd.notna(rsi) and pd.notna(adx_z) and pd.notna(cmf):
                meets_criteria = (rsi < reversal_thresholds['RSI'] and 
                                 adx_z < reversal_thresholds['ADX_Z'] and 
                                 cmf > reversal_thresholds['CMF'])
        
        all_company_data.append({
            'Company': company_name,
            'Symbol': company_symbol,
            'Price': current_price,
            'Change_pct': pct_change,
            'Weight': weight,
            'RSI': rsi if rsi is not None and pd.notna(rsi) else 50.0,
            'ADX_Z': adx_z if adx_z is not None and pd.notna(adx_z) else 0.0,
            'CMF': cmf if cmf is not None and pd.notna(cmf) else 0.0,
            'RS_Rating': rs_rating,
            'Mansfield_RS': mansfield_rs if mansfield_rs is not None and pd.notna(mansfield_rs) else 0.0,
            'Meets_Criteria': meets_criteria
        })
    
    # Create DataFrame and filter to eligible companies only
    df_all = pd.DataFrame(all_company_data)
    df_eligible = df_all[df_all['Meets_Criteria']].copy()
    
    if len(df_eligible) > 0:
        num_eligible = len(df_eligible)
        
        # Calculate ranks within eligible companies only
        # For reversals: Lower RSI/RS_Rating/ADX_Z = better = rank 1 (ascending=True for lower-is-better)
        # Higher CMF = better = rank 1 (ascending=False for higher-is-better)
        # Using method='average' for better differentiation in small company groups
        df_eligible['RS_Rating_Rank'] = df_eligible['RS_Rating'].rank(ascending=True, method='average')
        df_eligible['CMF_Rank'] = df_eligible['CMF'].rank(ascending=False, method='average')
        df_eligible['RSI_Rank'] = df_eligible['RSI'].rank(ascending=True, method='average')
        df_eligible['ADX_Z_Rank'] = df_eligible['ADX_Z'].rank(ascending=True, method='average')
        
        # Calculate weighted average rank using configurable weights (same logic as sectors)
        total_weight = sum(reversal_weights.values())
        df_eligible['Weighted_Avg_Rank'] = (
            (df_eligible['RS_Rating_Rank'] * reversal_weights.get('RS_Rating', 40.0) / total_weight) +
            (df_eligible['CMF_Rank'] * reversal_weights.get('CMF', 40.0) / total_weight) +
            (df_eligible['RSI_Rank'] * reversal_weights.get('RSI', 10.0) / total_weight) +
            (df_eligible['ADX_Z_Rank'] * reversal_weights.get('ADX_Z', 10.0) / total_weight)
        )
        
        # Scale to 1-10 where 10 = best reversal candidate (lowest weighted rank), 1 = worst
        if num_eligible > 1:
            min_rank = df_eligible['Weighted_Avg_Rank'].min()
            max_rank = df_eligible['Weighted_Avg_Rank'].max()
            if max_rank > min_rank:
                df_eligible['Reversal_Score'] = 10 - ((df_eligible['Weighted_Avg_Rank'] - min_rank) / (max_rank - min_rank)) * 9
            else:
                df_eligible['Reversal_Score'] = 5.0  # All eligible companies tied
        else:
            df_eligible['Reversal_Score'] = 10.0  # Single eligible company gets max score
        
        # Sort by Reversal Score descending and add Rank
        df_eligible = df_eligible.sort_values('Reversal_Score', ascending=False)
        df_eligible['Rank'] = range(1, len(df_eligible) + 1)
        
        # Determine status based on stricter BUY_DIV criteria
        def get_status(row):
            # BUY_DIV: Extra strict - RSI < 30, ADX_Z < -1, CMF > 0.1
            if row['RSI'] < 30 and row['ADX_Z'] < -1.0 and row['CMF'] > 0.1:
                return "BUY_DIV"
            return "Watch"  # All eligible companies are at least Watch
        
        df_eligible['Status'] = df_eligible.apply(get_status, axis=1)
        
        # Build display results
        company_results = []
        for _, row in df_eligible.iterrows():
            company_results.append({
                'Rank': row['Rank'],
                'Company': row['Company'],
                'Symbol': row['Symbol'],
                'Price': f"{row['Price']:.2f}",
                'Change %': f"{row['Change_pct']:+.2f}%",
                'Weight (%)': f"{row['Weight']:.1f}" if row['Weight'] > 0 else "N/A",
                'Status ℹ️': row['Status'],
                'Reversal_Score': f"{row['Reversal_Score']:.1f}",
                'RSI ℹ️': f"{row['RSI']:.1f}",
                'ADX_Z ℹ️': f"{row['ADX_Z']:.1f}",
                'CMF ℹ️': f"{row['CMF']:.2f}",
                'Mansfield_RS ℹ️': f"{row['Mansfield_RS']:.1f}",
            })
    
    if company_results:
        df_reversals = pd.DataFrame(company_results)
        st.dataframe(df_reversals, use_container_width=True, height=400)
        
        # Count by status
        buy_div_count = sum(1 for r in company_results if r['Status ℹ️'] == 'BUY_DIV')
        watch_count = sum(1 for r in company_results if r['Status ℹ️'] == 'Watch')
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Reversals", len(company_results))
        with col2:
            st.metric("🟢 BUY_DIV", buy_div_count)
        with col3:
            st.metric("🟡 Watch", watch_count)
        
        st.success(f"✅ Found {len(company_results)} reversal candidates in {selected_sector}")
        
        # Company Trend Analysis for Reversals
        st.markdown("---")
        st.markdown("### 📊 Company Trend Analysis (T-7 to T)")
        
        reversal_symbols = [r['Symbol'] for r in company_results]
        selected_reversal_symbol = st.selectbox("Select a reversal candidate for trend view:", reversal_symbols, key="reversal_company_trend")
        
        if selected_reversal_symbol and selected_reversal_symbol in companies_data:
            with st.spinner(f"Calculating trend for {selected_reversal_symbol}..."):
                trend_df = calculate_company_trend(selected_reversal_symbol, companies_data[selected_reversal_symbol], 
                                                 benchmark_data, companies_data, selected_sector, periods=8)
            
            if trend_df is not None:
                company_name = SECTOR_COMPANIES[selected_sector].get(selected_reversal_symbol, {}).get('name', selected_reversal_symbol)
                st.markdown(f"#### Trend for **{company_name}** ({selected_reversal_symbol})")
                
                # Transpose trend data: periods as columns, indicators as rows
                trend_display = trend_df.set_index('Period').T
                
                # Apply color styling for reversal
                def style_reversal_company_trend(val):
                    """Apply mild green/red colors based on indicator values."""
                    try:
                        num_val = float(val)
                        # Mansfield_RS: positive = green, negative = red
                        if 'Mansfield' in str(val):
                            if num_val > 0:
                                return 'background-color: #d4edda; color: #000'
                            elif num_val < 0:
                                return 'background-color: #f8d7da; color: #000'
                        # RSI: <40 is good for reversal (green)
                        elif 'RSI' in str(val):
                            if num_val < 40:
                                return 'background-color: #d4edda; color: #000'
                            elif num_val > 50:
                                return 'background-color: #f8d7da; color: #000'
                        # ADX: >20 = green
                        elif 'ADX' in str(val) and 'ADX_Z' not in str(val):
                            if num_val > 20:
                                return 'background-color: #d4edda; color: #000'
                            elif num_val < 15:
                                return 'background-color: #f8d7da; color: #000'
                        # ADX_Z: >-0.5 = better for reversal
                        elif 'ADX_Z' in str(val):
                            if num_val > -0.5:
                                return 'background-color: #d4edda; color: #000'
                            elif num_val < -1.0:
                                return 'background-color: #f8d7da; color: #000'
                        # CMF: >0.1 = green
                        elif 'CMF' in str(val):
                            if num_val > 0.1:
                                return 'background-color: #d4edda; color: #000'
                            elif num_val < 0:
                                return 'background-color: #f8d7da; color: #000'
                    except:
                        pass
                    return ''
                
                trend_styled = trend_display.style.applymap(style_reversal_company_trend)
                st.dataframe(trend_styled, use_container_width=True, hide_index=True)
                st.caption("📈 **Note:** Dates as columns (T-7 to T), Indicators as rows. Green/Red shows improving/deteriorating signals.")
    else:
        st.info(f"ℹ️ No reversal candidates found in {selected_sector} at this time")
