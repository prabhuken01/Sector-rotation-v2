# NSE Market Sector Analysis Tool 📊

A comprehensive Python-based tool for analyzing NSE (National Stock Exchange) sector performance using advanced technical indicators and momentum/reversal scoring strategies. Powered by Streamlit with real-time data from Yahoo Finance.

## 🎯 Overview

This tool analyzes **16 major NSE sectors** (plus Nifty 50 benchmark) to identify:
- **Momentum Opportunities**: Sectors outperforming Nifty 50 with strong trend signals
- **Reversal Candidates**: Oversold sectors with institutional buying signals and recovery potential

Perfect for traders, analysts, and investment professionals seeking data-driven sector insights.

## ✨ Key Features

### 🔴 **Recent Updates (Jan 2026)**

| Date | Update | Impact |
|------|--------|--------|
| Jan 13 | **Performance Optimization** | Added data caching (5-min TTL), parallel fetching, ~2-3x faster loading |
| Jan 13 | Fixed Momentum/Reversal scoring logic | Scores now properly scaled 1-10 (10=best, 1=worst) |
| Jan 13 | Fixed ranking direction for indicators | Higher values correctly ranked as better for momentum |
| Jan 13 | Fixed company reversal filter logic | Only shows companies meeting ALL filter criteria |
| Jan 13 | Added user-configurable company reversal thresholds | RSI, ADX_Z, CMF thresholds in sidebar |
| Jan 13 | Updated ANALYSIS_METHODOLOGY.md | Clear step-by-step scoring examples added |
| Jan 12 | Fixed Market Data Date logic by interval (Hourly/Daily/Weekly) | Correct date display based on analysis interval |
| Jan 12 | Added IST (Indian Standard Time) display for Analysis Date | Time shown as 9:15 AM IST, 10:15 AM IST, etc. |
| Jan 12 | Added actual dates in brackets for T-7 to T trend analysis | Shows T-6 (05-Jan), T-5 (06-Jan), etc. |
| Jan 12 | Added CMF Sum Total metric for sector rotation detection | Value near 1 indicates clear sector rotation |
| Jan 12 | Fixed Reversal Candidates filter logic | Sectors meeting user criteria now properly shown |
| Jan 12 | Added Price & Change% to Company analysis tabs | Same format as sector analysis |
| Jan 12 | Fixed company symbol mappings (e.g., Sun Pharma not in Auto) | Correct sector-company associations |
| Jan 12 | Improved Company Momentum/Reversal tab format | Ranking, consistent layout with sector tabs |
| Jan 11 | Added Data Sources tab with real-time connectivity status | Full transparency on data availability |
| Jan 11 | Corrected all sector symbols (16 sectors) and ETF tickers | Accurate data fetching for all sectors |
| Jan 11 | Added alternate ETF fallback logic | Automatic retry if primary ETF fails |
| Jan 11 | Fixed Metal ETF (METALIETF.NS) and added Realty ETF (MOREALTY.NS) | Complete coverage for all sectors |
| Jan 10 | Fixed reversal filtering logic with proper RSI/ADX thresholds | Accurate reversal status determination |

### Technical Indicators
- **RSI (Relative Strength Index)**: Momentum and overbought/oversold conditions (Wilder's smoothing, 14-period)
- **ADX (Average Directional Index)**: Trend strength measurement with +DI/-DI components
- **DI Spread (Directional Movement)**: Bullish vs bearish pressure differential
- **CMF (Chaikin Money Flow)**: Institutional buying/selling pressure (20-period)
- **Z-Score ADX**: Normalized trend strength for comparative analysis across sectors
- **Mansfield RS**: Relative strength vs Nifty 50 (52-week moving average)

### Dual Analysis Approach
1. **Momentum Scoring** (Trend Following)
   - **Rank-based composite score scaled to 1-10** where:
     - **Score 10 = Best momentum** (highest indicator values)
     - **Score 1 = Worst momentum** (lowest indicator values)
   - Indicators ranked: RS Rating (40%), RSI (30%), ADX Z-Score (20%), DI Spread (10%)
   - Higher raw indicator values → Rank 1 → Higher final score
   - See [Scoring Methodology](ANALYSIS_METHODOLOGY.md) for detailed example

2. **Reversal Detection** (Bottom Fishing)
   - Strict dual-filter approach ensuring reliability:
     - **Eligibility**: RSI < threshold AND ADX_Z < threshold
     - **BUY_DIV** (Best): RSI < 30 AND ADX_Z < -1 AND CMF > 0.1
     - **Watch**: Meets filter thresholds but not BUY_DIV
     - **No**: Does not meet filter criteria
   - **Reversal score scaled to 1-10** where:
     - **Score 10 = Best reversal candidate** (lowest RS/RSI/ADX_Z, highest CMF)
     - **Score 1 = Weakest reversal candidate**
   - Only eligible sectors receive scores and rankings

### Sectors Analyzed (16 Total)
| # | Sector | Index | Primary ETF | Alternate ETF |
|----|--------|-------|------------|---------------|
| 0 | Nifty 50 | ^NSEI | NIFTYBEES.NS | - |
| 1 | Auto | ^CNXAUTO | AUTOBEES.NS | - |
| 2 | Commodities | ^CNXCOMMODITIES | N/A | - |
| 3 | Defence | ^NSEDEFENCE.NS | DEFENCE.NS | - |
| 4 | Energy | ^CNXENERGY | MOENERGY.NS | CPSEETF.NS |
| 5 | FMCG | ^CNXFMCG | ICIFMCG.NS | - |
| 6 | IT | ^CNXIT | ITBEES.NS | - |
| 7 | Infra | ^CNXINFRA | INFRABEES.NS | INFRAIETF.NS |
| 8 | Media | ^CNXMEDIA | N/A | - |
| 9 | Metal | ^CNXMETAL | METALIETF.NS | METALBEES.NS |
| 10 | Fin Services | ^NIFTYFINSERV | FINIETF.NS | - |
| 11 | Pharma | ^CNXPHARMA | PHARMABEES.NS | - |
| 12 | PSU Bank | ^NIFTYPSUBANK | PSUBNKBEES.NS | - |
| 13 | Pvt Bank | ^CNXPVTBANK | PVTBANKBEES.NS | PVTBANIETF.NS |
| 14 | Realty | ^CNXREALTY | MOREALTY.NS | - |
| 15 | Oil & Gas | ^CNXOILGAS | OILIETF.NS | - |

## 📋 Requirements

- Python 3.8+
- pip (Python package manager)
- Internet connection (for live market data via Yahoo Finance)

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/prabhuken01/Sector-rotation-v2.git
cd Sector-rotation-v2
```

### 2. Set Up Virtual Environment (Recommended)
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

**Dependencies:**
- streamlit >= 1.28.0
- yfinance >= 0.2.32
- pandas >= 2.0.0
- numpy >= 1.24.0

### 4. Run the Web Application
```bash
streamlit run streamlit_app.py
```

The application will open at `http://localhost:8501` in your default browser.

## ⚡ Performance Optimizations

The application includes several performance optimizations for faster loading and smoother transitions:

| Optimization | Description | Benefit |
|--------------|-------------|---------|
| **Data Caching** | 5-minute TTL cache for fetched data | Instant reloads when switching tabs |
| **Streamlit Cache** | `@st.cache_data` for expensive computations | Avoids redundant calculations |
| **Efficient Fetching** | Smart caching by symbol/date/interval | Reduces API calls by ~80% |
| **Optimized Indicators** | Vectorized NumPy operations | Faster RSI/ADX/CMF calculations |

**Cache Behavior:**
- First load: ~15-30 seconds (fetching all sectors)
- Subsequent loads (same parameters): ~1-3 seconds (cached)
- Tab switching: Instant (shared cache)
- Click "🔄 Run Analysis": Clears cache for fresh data

### 5. Using the Application

**Sidebar Controls:**
- 📅 **Analysis Date**: Select any historical date with ⬅️ ➡️ navigation arrows
- ⏱️ **Analysis Interval**: Choose Daily, Weekly, or Hourly data frequency
- 🔄 **Data Source**: Toggle between NSE Indices (raw) or ETF Proxy (more traded)
- ⚖️ **Momentum Score Weights**: Customize all 4 indicator weights (sum = 100%)
- 📊 **Reversal Score Weights**: Customize reversal ranking weights
- 🎯 **Reversal Filters**: Adjust RSI and ADX Z-Score thresholds
- 🎨 **Color Coding**: Enable/disable Bullish (Green) vs Bearish (Red) highlighting

**Four Main Tabs:**

| Tab | Name | Purpose |
|-----|------|---------|
| 1 | **📈 Momentum Ranking** | Top performing sectors with trend analysis, historical 6-month performance download |
| 2 | **🔄 Reversal Candidates** | Oversold sectors meeting criteria, trend analysis with status history |
| 3 | **📊 Interpretation Guide** | Detailed explanations of all indicators, formulas, and scoring methodology |
| 4 | **🔌 Data Sources** | Real-time connectivity status for all 16 sectors with index/ETF availability |

## 📚 Documentation

### Quick Start Guide
- 📖 [Installation & Setup](Quick_Start/README.md)
- 🔧 [Troubleshooting](Quick_Start/README.md#troubleshooting)
- 📋 [Common Tasks](Quick_Start/README.md#common-tasks)

### Technical Reference
- 🎓 [Technical Indicators Explained](Quick_Start/REFERENCE_MANUAL.md)
- 📊 [Scoring Methodology](Quick_Start/REFERENCE_MANUAL.md#scoring)
- 🏗️ [System Architecture](Quick_Start/REFERENCE_MANUAL.md#architecture)
- 📝 [API Reference](Quick_Start/REFERENCE_MANUAL.md#api-reference)

## 📂 Project Structure

```
Sector-rotation-v2/
├── streamlit_app.py             # Main Streamlit web app (1900+ lines)
│   ├── get_sidebar_controls()   # Sidebar UI and configuration
│   ├── display_momentum_tab()   # Momentum ranking display
│   ├── display_reversal_tab()   # Reversal candidates display
│   ├── display_interpretation_tab()  # Indicator explanations
│   ├── display_data_sources_tab()    # Connectivity status
│   └── analyze_sectors_with_progress()  # Data fetching with progress
├── analysis.py                   # Core analysis logic (315 lines)
│   ├── analyze_all_sectors()    # Main orchestration
│   ├── determine_reversal_status()  # BUY_DIV/Watch/No determination
│   └── analyze_sector()         # Per-sector calculations
├── data_fetcher.py               # Yahoo Finance integration (94+ lines)
│   ├── fetch_sector_data()      # Single symbol fetching
│   └── fetch_sector_data_with_alternate()  # Fallback to alternate ETF
├── indicators.py                 # Technical calculations (200+ lines)
│   ├── calculate_rsi()          # RSI (Wilder's)
│   ├── calculate_adx()          # ADX with DI
│   ├── calculate_cmf()          # Chaikin Money Flow
│   ├── calculate_z_score()      # Normalization
│   └── calculate_mansfield_rs() # Relative strength
├── market_analysis.py            # Standalone CLI (for batch analysis)
├── config.py                     # Configuration (107 lines)
│   ├── SECTORS                  # Index symbols
│   ├── SECTOR_ETFS              # Primary ETF choices
│   └── SECTOR_ETFS_ALTERNATE    # Fallback ETFs
├── requirements.txt              # Python dependencies
├── README.md                     # This file (Main documentation)
├── ANALYSIS_METHODOLOGY.md       # Detailed methodology documentation
├── SYMBOLS.txt                   # Complete list of all symbols used
├── Quick_Start/
│   ├── README.md                 # Installation & getting started guide
│   └── REFERENCE_MANUAL.md       # Technical deep-dive documentation
└── .gitignore                    # Git ignore rules
```

## 🔧 Configuration

All parameters can be adjusted directly in the Streamlit web interface sidebar. Changes apply immediately without code modifications.

### Momentum Score Weights (Configurable)
Default allocations (must sum to 100%):
- **RS Rating Weight**: 40% - Relative strength vs Nifty 50 ranking
- **ADX Z-Score Weight**: 20% - Normalized trend strength ranking
- **RSI Weight**: 30% - Momentum and overbought/oversold ranking
- **DI Spread Weight**: 10% - Directional movement ranking

### Reversal Detection Weights (Configurable)
Default allocations (must sum to 100%):
- **RS Rating Weight**: 40% - Sector underperformance signal
- **CMF Weight**: 40% - Institutional money flow accumulation
- **RSI Weight**: 10% - Oversold condition severity
- **ADX Z-Score Weight**: 10% - Weak trend indicator strength

### Reversal Filters (Configurable)
- **RSI Threshold for BUY_DIV**: Default 40 (can range 30-50)
- **ADX Z-Score Threshold for BUY_DIV**: Default -0.5 (negative = weak trend)
- **CMF Threshold for BUY_DIV**: Default 0.1 (positive = money flowing in)
- **ADX Z-Score Threshold**: Maximum ADX Z for weak trend detection (default -0.5)

All weights sum to 100% and are validated in real-time in the interface.

## 📈 Understanding the Output

### TAB 1: Momentum Ranking
Shows sectors sorted by momentum score (highest first) with:
- **Momentum Score**: Rank-based composite score of all indicators
- **Mansfield RS**: Relative strength vs Nifty 50 (green = outperforming, orange = underperforming)
- **Technical Indicators**: RSI, ADX, ADX Z-Score, DI Spread, CMF
- **CMF Sum Total**: Sum of all sector CMFs indicating overall market rotation (positive = money flowing in)
- **Trend Analysis**: Historical momentum evolution with actual dates in brackets (e.g., T-6 (05-Jan))
- **Historical Performance**: Top 2 momentum sectors' 7-day and 14-day forward returns over 6 months

**Momentum Score Interpretation:**
- Calculated using ranking method across all indicators
- 🟢 **Top 3-5 sectors**: Strongest momentum signals
- 🟡 **Middle sectors**: Mixed signals
- 🔴 **Bottom sectors**: Weak or negative momentum

### TAB 2: Reversal Candidates
Shows oversold sectors with recovery potential:
- **Reversal Status**: 
  - 🟢 **BUY_DIV**: Strong buy signal (RSI<40, ADX_Z<-0.5, CMF>0.1)
  - � **Watch**: Meets user-defined filter thresholds (potential reversal)
- **Reversal Score**: Rank-based score for reversal potential among eligible sectors
- **Technical Indicators**: RS Rating, CMF, RSI, ADX Z-Score
- **Trend Analysis**: Historical reversal metrics with actual dates (e.g., T-6 (05-Jan))
- **All Sectors View**: Complete reversal scores for comparison

**Reversal Filter Logic:**
- Sectors must meet BOTH user-defined RSI AND ADX_Z thresholds to be eligible
- Eligible sectors that pass thresholds are shown as "Watch" or "BUY_DIV"
- Only eligible sectors receive reversal scores and rankings

**Reversal Score Factors:**
- **Low RS Rating**: Indicates underperformance (recovery potential)
- **Positive CMF**: Money accumulation at the bottom
- **Low RSI**: Oversold conditions
- **Negative ADX Z**: Weak trend (favorable for reversal)

### TAB 3: Interpretation Guide
Complete explanation of all indicators and scoring methodologies.

## 📊 Features

### Momentum Tab Features
- ✅ Sector trend analysis (last 8 periods)
- ✅ Historical top 2 momentum performance (6 months)
- ✅ Download momentum data as CSV
- ✅ Download trend analysis as CSV
- ✅ Download historical performance report as CSV

### Reversal Tab Features
- ✅ All sectors reversal scoring
- ✅ Sector reversal trend analysis (last 8 periods)
- ✅ Download reversal candidates as CSV
- ✅ Download reversal trend analysis as CSV
- ✅ Historical top 2 reversal performance (6 months) - *Coming Soon*

### General Features
- ✅ Real-time analysis with configurable weights
- ✅ Multiple timeframes (Daily, Weekly, Hourly)
- ✅ Date navigation for historical analysis
- ✅ ETF and Index data sources
- ✅ Export all analysis to CSV
- ✅ Responsive web interface

## 💡 Usage Examples

### Basic Analysis
1. Open `http://localhost:8501`
2. Select analysis date (default: today)
3. Choose timeframe (Daily/Weekly/Hourly)
4. Click "Run Analysis" button
5. Review tabs: Momentum, Reversals, and Interpretation

### Customize Analysis Parameters
In the sidebar:
1. Adjust momentum score weights to emphasize different indicators
2. Adjust reversal filter thresholds for stricter/looser criteria
3. Switch between ETF Proxy and NSE Indices data
4. Go back to any historical date for backtesting

### Download Analysis Results
- Each tab has download buttons for CSV export
- Download individual trend analyses for specific sectors
- Download historical performance reports for backtesting

### Historical Performance Backtesting
1. Generate historical top 2 momentum/reversal performance report
2. Review 7-day and 14-day forward returns
3. Analyze how sectors performed after being ranked
4. Use insights to validate strategy parameters

## ⚠️ Disclaimer

This tool is for educational and analytical purposes only. Not financial advice. Always conduct your own research and consult with financial advisors before making investment decisions.

## 🔄 Data Sources

- **Data Provider**: Yahoo Finance (yfinance)
- **Update Frequency**: Real-time market data
- **Historical Period**: Up to 1 year (configurable)
- **Timezone**: IST (Indian Standard Time)

## � Upcoming Features (Q1 2026)

### Company-Level Analysis (In Development)
Drill down from sector momentum/reversal into individual companies:

**📈 Tab 5: Company Momentum**
- Sector/ETF dropdown selector
- Auto-fetch constituent companies with index weights
- Same technical analysis as sector level: RSI, ADX, CMF, RS Rating
- Rank companies by momentum score within selected sector
- Identify which companies are gaining momentum within their sector
- Trend analysis showing historical company performance vs sector

**🔄 Tab 6: Company Reversals**
- Same selector and constituent display as momentum tab
- Reversal status (BUY_DIV/Watch/No) at company level
- Trend analysis showing historical reversals
- Find oversold companies with recovery potential within sector

**Implementation Roadmap:**
1. Create company symbol mappings for each ETF (e.g., ITBEES.NS → [TCS.NS, INFY.NS, ...])
2. Fetch constituent weights from index/ETF data
3. Extend analysis.py to support company-level scoring
4. Add company selector dropdown in streamlit_app.py
5. Create display functions for company tabs
6. Test and validate with major sectors (IT, Banking, FMCG)

## �🐛 Troubleshooting

### Issue: Streamlit app won't start
```bash
# Ensure streamlit is installed
pip install --upgrade streamlit

# Run the app again
streamlit run streamlit_app.py
```

### Issue: "No module named" error
```bash
# Install/upgrade all dependencies
pip install -r requirements.txt --upgrade
```

### Issue: No data available or connection timeout
- Check your internet connection
- Yahoo Finance may be temporarily unavailable
- Try running analysis again after a few minutes
- For hourly data, limited to recent 60 days

### Issue: Analysis takes too long
- Hourly analysis takes longer due to more data points
- Try Daily or Weekly intervals
- Check internet speed
- Historical analysis with custom weights may take 30-60 seconds

For more help, see [Quick Start Troubleshooting](Quick_Start/README.md#troubleshooting)

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.

## 👤 Author

**prabhuken01**
- GitHub: [@prabhuken01](https://github.com/prabhuken01)

## 📞 Support

- 📖 Check [Documentation](Quick_Start/README.md)
- 🐛 Report issues via [GitHub Issues](https://github.com/prabhuken01/market-sector-analysis/issues)
- 💬 Start a [Discussion](https://github.com/prabhuken01/market-sector-analysis/discussions)

## 🎓 Learning Resources

### Technical Analysis
- [RSI Indicator Guide](https://www.investopedia.com/terms/r/rsi.asp)
- [ADX Indicator Explained](https://www.investopedia.com/terms/a/adx.asp)
- [Money Flow Analysis](https://www.investopedia.com/terms/c/chaikinmoneyflow.asp)

### NSE Indices
- [Nifty 50 Index](https://www.nseindia.com/)
- [NSE Sectoral Indices](https://www.nseindia.com/products/content/indices/index_market_watch.htm)

## 🗺️ Roadmap

- [ ] Dashboard visualization (Plotly/Dash)
- [ ] Email alerts for momentum/reversal signals
- [ ] Historical backtesting module
- [ ] Multi-sector correlation analysis
- [ ] Machine learning predictions
- [ ] Mobile app integration

## ⭐ Show Your Support

If this project helped you, please give it a star! ⭐

---

**Last Updated**: 2026-01-12  
**Version**: 2.1.0 (Enhanced Date/Time & Filtering Logic)  
**Status**: Active & Maintained ✅
