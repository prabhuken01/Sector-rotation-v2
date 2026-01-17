# Implementation Guide

Complete technical documentation for the NSE Sector Analysis Tool.

## Table of Contents

1. [Scoring Methodology](#scoring-methodology)
2. [Technical Implementation](#technical-implementation)
3. [Data Flow](#data-flow)
4. [Configuration Details](#configuration-details)
5. [Troubleshooting](#troubleshooting)

## Scoring Methodology

### Momentum Score (1-10 Scale)

**Purpose**: Identify sectors with strong uptrend and positive momentum signals.

**Calculation Steps**:

1. **Fetch Data**: Get 50-day price history for each sector
2. **Calculate Indicators**:
   - RSI(14): Relative Strength Index (Wilder's smoothing)
   - ADX(14): Average Directional Index with +DI/-DI
   - CMF(20): Chaikin Money Flow
   - Z-Score(ADX): Normalize ADX for cross-sector comparison
   - Mansfield RS: 52-week moving average performance vs Nifty 50

3. **Generate Ranks** (for all N sectors):
   - ADX_Z_Rank: Higher values = Rank 1 (ascending=False)
   - RS_Rating_Rank: Higher values = Rank 1
   - RSI_Rank: Higher values = Rank 1 (overbought = momentum)
   - DI_Spread_Rank: Higher values = Rank 1 (bullish)

4. **Weighted Average Rank**:
   ```
   WAR = (ADX_Z_Rank × 0.20 + RS_Rating_Rank × 0.40 + RSI_Rank × 0.30 + DI_Spread_Rank × 0.10) / 4
   ```

5. **Scale to 1-10**:
   ```
   Momentum_Score = 10 - ((WAR - min_WAR) / (max_WAR - min_WAR)) × 9
   ```
   - Score 10: Rank 1 overall (best momentum)
   - Score 5.5: Median sector
   - Score 1: Worst momentum

**Example**:
- Sector A: ADX_Z=+1.2, RS=8.5, RSI=72, DI_Spread=+2.1 → All rank 1 → Score 10 ✅
- Sector B: ADX_Z=+0.5, RS=6.2, RSI=45, DI_Spread=+0.8 → Mixed ranks → Score 5.5 ⚖️
- Sector C: ADX_Z=-0.8, RS=3.1, RSI=25, DI_Spread=-0.5 → All low ranks → Score 1 ❌

### Reversal Score (1-10 Scale)

**Purpose**: Find oversold sectors with institutional buying signals.

**Filtering Logic**:

1. **Eligibility Filter** (ALL must be true):
   - RSI < user_threshold (default 40)
   - ADX_Z < user_threshold (default -0.5)
   - CMF > user_threshold (default 0)

2. **Status Determination**:
   - **BUY_DIV**: RSI < 30 AND ADX_Z < -1.0 AND CMF > 0.1 (high confidence)
   - **Watch**: Meets eligibility but not BUY_DIV (medium confidence)
   - **No**: Does not meet eligibility (excluded from rankings)

3. **Ranking** (only eligible sectors):
   - RS_Rating_Rank: Lower values = Rank 1 (ascending=True)
   - CMF_Rank: Higher values = Rank 1 (ascending=False)
   - RSI_Rank: Lower values = Rank 1 (ascending=True)
   - ADX_Z_Rank: Lower values = Rank 1 (ascending=True)

4. **Weighted Average Rank**:
   ```
   WAR = (RS_Rating_Rank × 0.40 + CMF_Rank × 0.40 + RSI_Rank × 0.10 + ADX_Z_Rank × 0.10) / 4
   ```

5. **Scale to 1-10**:
   ```
   Reversal_Score = 10 - ((WAR - min_WAR) / (max_WAR - min_WAR)) × 9
   ```

**Key Differences from Momentum**:
- Only includes sectors meeting strict filters (reduces false positives)
- Lower RSI/ADX_Z values are better (opposite of momentum)
- Higher CMF values are better (institutional buying)
- Confidence indicator: BUY_DIV vs Watch status

## Technical Implementation

### Directory Structure

```
/workspaces/Sector-rotation-v2/
├── streamlit_app.py          # Main UI (8 tabs, 2500+ lines)
├── company_analysis.py       # Company momentum/reversal (680+ lines)
├── analysis.py              # Sector analysis engine
├── indicators.py            # All indicator calculations
├── data_fetcher.py          # Yahoo Finance data + caching
├── config.py                # Configuration constants
├── company_symbols.py       # Company mappings (120+ companies)
├── requirements.txt         # Python dependencies
├── readme.md               # Quick start & overview
└── implementation_guide.md  # This file
```

### Key Classes & Functions

#### `streamlit_app.py`
- `main()`: Entry point, manages UI flow
- `analyze_sectors_with_progress()`: Parallel sector analysis
- `display_momentum_tab()`: Sector momentum rankings
- `display_reversal_tab()`: Sector reversal candidates
- `display_company_momentum_tab()`: Company-level momentum
- `display_company_reversal_tab()`: Company-level reversals
- `display_historical_rankings_tab()`: T-7 to T trends
- `calculate_historical_momentum_performance()`: 6-month backtest
- `display_sector_companies_tab()`: Company mappings (downloadable)

#### `company_analysis.py`
- `display_company_momentum_tab()`: Company momentum analysis within sector
- `display_company_reversal_tab()`: Company reversal analysis within sector
- `calculate_company_trend()`: Historical trend calculation (8 periods)
- `fetch_company_data_cached()`: Cached company data fetching

#### `analysis.py`
- `analyze_all_sectors()`: Parallel analysis of all 16 sectors
- `analyze_sector()`: Single sector analysis with indicators
- `calculate_sector_momentum()`: Momentum scoring logic
- `calculate_sector_reversal()`: Reversal scoring logic

#### `indicators.py`
- `calculate_rsi()`: Relative Strength Index (14-period)
- `calculate_adx()`: Average Directional Index with DI components
- `calculate_cmf()`: Chaikin Money Flow (20-period)
- `calculate_z_score()`: Z-score normalization
- `calculate_mansfield_rs()`: Relative strength vs benchmark

#### `data_fetcher.py`
- `fetch_sector_data()`: Fetch sector data with caching (5-min TTL)
- `fetch_all_sectors_parallel()`: Parallel fetching for 16 sectors
- `clear_data_cache()`: Manual cache clearing

### Data Flow

```
User Input (Streamlit UI)
    ↓
[Date, Interval, Momentum Weights, Reversal Weights, Reversal Filters]
    ↓
analyze_sectors_with_progress()
    ├─→ Parallel fetch for 16 sectors + Nifty 50
    │   └─→ fetch_sector_data() with caching
    │
    └─→ For each sector:
        ├─→ Calculate indicators
        │   ├─→ RSI, ADX, DI_Spread, CMF
        │   ├─→ Z-Score(ADX)
        │   └─→ Mansfield RS
        │
        ├─→ Calculate momentum score
        │   └─→ Rank-based composite
        │
        └─→ Calculate reversal score
            └─→ Filter + rank-based composite
    ↓
DataFrame with all sectors + scores + indicators
    ↓
Display in 8 Tabs (UI)
    ├─→ Momentum Ranking
    ├─→ Reversal Candidates
    ├─→ Company Momentum (drills into sector companies)
    ├─→ Company Reversals
    ├─→ Historical Rankings (T-7 to T)
    ├─→ Interpretation Guide
    ├─→ Data Sources
    └─→ Sector Companies
```

## Configuration Details

### `config.py`

**SECTORS** (16 NSE Indices):
```python
{
    'Auto': '^CNXAUTO',
    'Commodities': '^CNXCOMMODITIES',
    'Defence': '^NSEDEFENCE.NS',
    'Energy': '^CNXENERGY',
    'FMCG': '^CNXFMCG',
    'IT': '^CNXIT',
    'Infra': '^CNXINFRA',
    'Media': '^CNXMEDIA',
    'Metal': '^CNXMETAL',
    'Fin Services': '^NIFTYFINSERV',
    'Pharma': '^CNXPHARMA',
    'PSU Bank': '^NIFTYPSUBANK',
    'Pvt Bank': '^CNXPVTBANK',
    'Realty': '^CNXREALTY',
    'Oil & Gas': '^CNXOILGAS',
}
```

**SECTOR_ETFS** (Primary ETF tickers):
```python
{
    'Auto': 'AUTOBEES.NS',
    'Energy': 'MOENERGY.NS',
    'IT': 'ITBEES.NS',
    'Fin Services': 'FINIETF.NS',  # NBFC, Insurance, Capital Markets
    ...
}
```

**DEFAULT_MOMENTUM_WEIGHTS**:
```python
{
    'RS_Rating': 40,     # Relative strength vs Nifty 50
    'RSI': 30,          # Momentum strength
    'ADX_Z': 20,        # Trend reliability
    'DI_Spread': 10,    # Bullish/bearish pressure
}
```

**DEFAULT_REVERSAL_WEIGHTS**:
```python
{
    'RS_Rating': 40,     # Relative weakness
    'CMF': 40,          # Money flow signals
    'RSI': 10,          # Oversold condition
    'ADX_Z': 10,        # Trend weakness
}
```

### `company_symbols.py`

Maps 120+ companies to 16 sectors with weights:
```python
'Fin Services': {
    'BAJFINANCE.NS': {'weight': 15.40, 'name': 'Bajaj Finance Ltd.'},
    'SHRIRAMFIN.NS': {'weight': 8.20, 'name': 'Shriram Finance Ltd.'},
    ...
}
```

**Note**: FINIETF (Fin Services) contains:
- **NBFC**: Bajaj Finance, Shriram Finance, Jio Financial
- **Insurance**: SBI Life, HDFC Life, Cholamandalam
- **Capital Markets**: BSE, MCX
- **FinTech**: PB Fintech (Policybazaar)

**Excludes Banks** (tracked separately in PSU Bank & Pvt Bank sectors)

## Troubleshooting

### Issue: "Could not fetch data for TATAMOTORS.NS"

**Cause**: Yahoo Finance outage or network issue
**Solution**:
1. Check internet connection
2. Manual clear cache: Button in sidebar
3. Wait 5-10 minutes and retry
4. Check Data Sources tab for connectivity status

### Issue: Company trend showing blank/partial data

**Cause**: Insufficient historical data for company
**Solution**:
1. Select different company in dropdown
2. Ensure interval has sufficient history
3. Check if company added recently

### Issue: Historical rankings showing different sectors than live analysis

**Cause**: Point-in-time calculation differences due to:
- Data revisions by Yahoo Finance
- Different historical snapshot timing
- Market data updates
**Solution**: This is expected behavior. Use Historical Rankings tab to compare consistency over T-7 to T.

### Issue: "Error displaying reversal tab"

**Cause**: No companies meet reversal filter criteria
**Solution**:
1. Adjust reversal thresholds in sidebar (lower RSI, higher CMF)
2. Try different sector
3. Check if historical data available

### Issue: Streamlit app slow to load

**Cause**: Network latency or many sector requests
**Solution**:
1. Data is cached for 5 minutes (check cache status in Data Sources tab)
2. Reload page if stuck
3. Use ETF proxy mode (often faster than indices)

## Advanced Usage

### Backtesting Strategy
1. Select historical date using date picker
2. Review momentum and reversal rankings
3. View historical performance report (6-month forward returns)
4. Compare consistency in Historical Rankings tab

### Custom Weights
1. Adjust momentum weights in sidebar (RS Rating, RSI, ADX_Z, DI_Spread)
2. System recalculates rankings automatically
3. Download results for comparison

### Company Drill-Down
1. Select sector in Company Momentum/Reversal tabs
2. View individual company scores and ranks
3. Compare trend analysis T-7 to T for selected company

## Performance Metrics

- **Load Time**: 3-5 seconds (with caching)
- **Data Age**: 15-20 minutes (Yahoo Finance delay)
- **Cache TTL**: 5 minutes
- **Parallel Fetching**: 16 sectors + 1 benchmark simultaneously
- **Supported Intervals**: Daily (50 days), Weekly (100 weeks), Hourly (limited)

## Version History

**v2.1.0 (Jan 15, 2026)**
- Fixed company reversal variable error
- Updated FINIETF composition
- Added Indicators label to trends
- Added historical rankings tab
- Added CSV download for companies

**v2.0.0 (Jan 13, 2026)**
- Complete scoring logic overhaul
- Performance optimization with caching
- Fixed momentum/reversal ranking direction
- Added data sources connectivity tab

**v1.0.0 (Jan 10, 2026)**
- Initial release
- 16 sectors analysis
- Company-level analysis
