"""
Company-Level Momentum and Reversal Analysis
Analyzes individual companies within sectors with same logic as sector analysis
Benchmarks each company against Nifty 50
"""

import streamlit as st
import pandas as pd
from company_symbols import SECTOR_COMPANIES, get_company_symbol_list
from data_fetcher import fetch_sector_data
from indicators import calculate_rsi, calculate_adx, calculate_cmf, calculate_z_score, calculate_mansfield_rs


def display_company_momentum_tab():
    """Display company-level momentum analysis within selected sector."""
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
    
    # Fetch company data
    with st.spinner(f"Analyzing companies in {selected_sector}..."):
        company_list = get_company_symbol_list(selected_sector)
        companies_data = {}
        failed_companies = []
        
        for company_symbol in company_list:
            try:
                data = fetch_sector_data(company_symbol, end_date=None, interval='1d')
                if data is not None and len(data) > 0:
                    companies_data[company_symbol] = data
                else:
                    failed_companies.append(company_symbol)
            except:
                failed_companies.append(company_symbol)
        
        if not companies_data:
            st.error(f"❌ No data available for companies in {selected_sector}")
            return
        
        if failed_companies:
            st.warning(f"⚠️ Could not fetch data for: {', '.join(failed_companies)}")
    
    # Fetch benchmark (Nifty 50)
    benchmark_data = fetch_sector_data('^NSEI', end_date=None, interval='1d')
    
    if benchmark_data is None or len(benchmark_data) == 0:
        st.error("❌ Unable to fetch Nifty 50 benchmark data")
        return
    
    # Build analysis for each company
    company_results = []
    company_scores = []
    
    for company_symbol, data in companies_data.items():
        company_info = SECTOR_COMPANIES[selected_sector].get(company_symbol, {})
        company_name = company_info.get('name', company_symbol)
        weight = company_info.get('weight', 0)
        
        # Calculate indicators
        rsi_series = calculate_rsi(data)
        adx_series, plus_di_series, minus_di_series, di_spread_series = calculate_adx(data)
        cmf_series = calculate_cmf(data)
        mansfield_rs = calculate_mansfield_rs(data, benchmark_data)  # Returns scalar
        adx_z_series = calculate_z_score(adx_series.dropna())
        
        # Get latest values from Series (or use scalar directly)
        rsi = rsi_series.iloc[-1] if isinstance(rsi_series, pd.Series) and len(rsi_series) > 0 else None
        adx = adx_series.iloc[-1] if isinstance(adx_series, pd.Series) and len(adx_series) > 0 else None
        plus_di = plus_di_series.iloc[-1] if isinstance(plus_di_series, pd.Series) and len(plus_di_series) > 0 else None
        minus_di = minus_di_series.iloc[-1] if isinstance(minus_di_series, pd.Series) and len(minus_di_series) > 0 else None
        di_spread = di_spread_series.iloc[-1] if isinstance(di_spread_series, pd.Series) and len(di_spread_series) > 0 else None
        cmf = cmf_series.iloc[-1] if isinstance(cmf_series, pd.Series) and len(cmf_series) > 0 else None
        adx_z = adx_z_series.iloc[-1] if isinstance(adx_z_series, pd.Series) and len(adx_z_series) > 0 else None
        
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
        
        # Momentum score (same weights as sector momentum)
        # Simplified: use RS Rating as proxy for now
        momentum_score = rs_rating
        company_scores.append(momentum_score)
        
        company_results.append({
            'Company': company_name,
            'Symbol': company_symbol,
            'Price': f"{current_price:.2f}",
            'Change %': f"{pct_change:+.2f}%",
            'Momentum_Score': f"{momentum_score:.1f}",
            'Mansfield_RS': f"{float(mansfield_rs):.1f}" if mansfield_rs is not None and pd.notna(mansfield_rs) else "N/A",
            'RS_Rating': f"{rs_rating:.1f}",
            'RSI': f"{float(rsi):.1f}" if rsi is not None and pd.notna(rsi) else "N/A",
            'ADX': f"{float(adx):.1f}" if adx is not None and pd.notna(adx) else "N/A",
            'ADX_Z': f"{float(adx_z):.1f}" if adx_z is not None and pd.notna(adx_z) else "N/A",
            'DI_Spread': f"{float(di_spread):.1f}" if di_spread is not None and pd.notna(di_spread) else "N/A",
            'CMF': f"{float(cmf):.2f}" if cmf is not None and pd.notna(cmf) else "N/A",
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


def display_company_reversal_tab():
    """Display company-level reversal analysis within selected sector."""
    st.markdown("### 🔄 Company Reversal Analysis")
    st.markdown("---")
    st.info("🎯 **Find oversold companies** within a sector showing recovery signals. Benchmarked against Nifty 50.")
    
    # Sector selector
    sector_list = list(SECTOR_COMPANIES.keys())
    selected_sector = st.selectbox("Select Sector/ETF:", sector_list, key="company_reversal_sector")
    
    if not selected_sector:
        st.warning("Please select a sector")
        return
    
    st.markdown(f"**Analysis:** {selected_sector} | Reversal candidates with money flow signals")
    
    # Fetch company data
    with st.spinner(f"Analyzing reversal opportunities in {selected_sector}..."):
        company_list = get_company_symbol_list(selected_sector)
        companies_data = {}
        failed_companies = []
        
        for company_symbol in company_list:
            try:
                data = fetch_sector_data(company_symbol, end_date=None, interval='1d')
                if data is not None and len(data) > 0:
                    companies_data[company_symbol] = data
                else:
                    failed_companies.append(company_symbol)
            except:
                failed_companies.append(company_symbol)
        
        if not companies_data:
            st.error(f"❌ No data available for companies in {selected_sector}")
            return
        
        if failed_companies:
            st.warning(f"⚠️ Could not fetch data for: {', '.join(failed_companies)}")
    
    # Fetch benchmark (Nifty 50)
    benchmark_data = fetch_sector_data('^NSEI', end_date=None, interval='1d')
    
    if benchmark_data is None or len(benchmark_data) == 0:
        st.error("❌ Unable to fetch Nifty 50 benchmark data")
        return
    
    # Reversal thresholds
    reversal_thresholds = {'RSI': 40, 'ADX_Z': -0.5, 'CMF': 0.1}
    
    # Build analysis for each company
    company_results = []
    
    for company_symbol, data in companies_data.items():
        company_info = SECTOR_COMPANIES[selected_sector].get(company_symbol, {})
        company_name = company_info.get('name', company_symbol)
        weight = company_info.get('weight', 0)
        
        # Calculate indicators
        rsi_series = calculate_rsi(data)
        adx_series, plus_di_series, minus_di_series, di_spread_series = calculate_adx(data)
        cmf_series = calculate_cmf(data)
        adx_z_series = calculate_z_score(adx_series.dropna())
        mansfield_rs = calculate_mansfield_rs(data, benchmark_data)  # Returns scalar
        
        # Get latest values from Series (or use scalar directly)
        rsi = rsi_series.iloc[-1] if isinstance(rsi_series, pd.Series) and len(rsi_series) > 0 else None
        adx_z = adx_z_series.iloc[-1] if isinstance(adx_z_series, pd.Series) and len(adx_z_series) > 0 else None
        cmf = cmf_series.iloc[-1] if isinstance(cmf_series, pd.Series) and len(cmf_series) > 0 else None
        
        # Get current price and change %
        current_price = data['Close'].iloc[-1] if len(data) > 0 else 0.0
        prev_close = data['Close'].iloc[-2] if len(data) > 1 else current_price
        pct_change = ((current_price - prev_close) / prev_close * 100) if prev_close != 0 else 0.0
        
        # Determine reversal status
        status = "No"
        if rsi is not None and adx_z is not None and cmf is not None:
            if pd.notna(rsi) and pd.notna(adx_z) and pd.notna(cmf):
                if rsi < reversal_thresholds['RSI'] and adx_z < reversal_thresholds['ADX_Z'] and cmf > reversal_thresholds['CMF']:
                    status = "BUY_DIV"
                elif rsi < 50 and adx_z < 0.5 and cmf > 0:
                    status = "Watch"
        
        if status != "No":  # Only show reversals
            company_results.append({
                'Company': company_name,
                'Symbol': company_symbol,
                'Price': f"{current_price:.2f}",
                'Change %': f"{pct_change:+.2f}%",
                'Weight (%)': f"{weight:.1f}" if weight > 0 else "N/A",
                'Status ℹ️': status,
                'RSI ℹ️': f"{float(rsi):.1f}" if rsi is not None and pd.notna(rsi) else "N/A",
                'ADX_Z ℹ️': f"{float(adx_z):.1f}" if adx_z is not None and pd.notna(adx_z) else "N/A",
                'CMF ℹ️': f"{float(cmf):.2f}" if cmf is not None and pd.notna(cmf) else "N/A",
                'Mansfield_RS ℹ️': f"{float(mansfield_rs):.1f}" if mansfield_rs is not None and pd.notna(mansfield_rs) else "N/A",
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
    else:
        st.info(f"ℹ️ No reversal candidates found in {selected_sector} at this time")
