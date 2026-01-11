# Market Sector Analysis Tool 📊

A comprehensive Python-based tool for analyzing NSE (National Stock Exchange) sector performance using advanced technical indicators and momentum/reversal scoring strategies.

## 🎯 Overview

This tool analyzes 13 major NSE sectors to identify:
- **Momentum Opportunities**: Sectors outperforming Nifty 50
- **Reversal Candidates**: Oversold sectors with institutional buying signals

Perfect for traders, analysts, and investment professionals seeking data-driven sector insights.

## ✨ Key Features

### Technical Indicators
- **RSI (Relative Strength Index)**: Momentum and overbought/oversold conditions
- **ADX (Average Directional Index)**: Trend strength measurement
- **DI Spread (Directional Movement)**: Bullish vs bearish pressure
- **CMF (Chaikin Money Flow)**: Institutional buying/selling pressure
- **Z-Score ADX**: Normalized trend strength for comparative analysis

### Dual Analysis Approach
1. **Momentum Scoring** (Trend Following)
   - **Rank-based composite score** combining:
     - ADX Z-Score Rank (20% weight)
     - RS Rating Rank (40% weight)
     - RSI Rank (30% weight)
     - DI Spread Rank (10% weight)
   - Each sector ranked independently on each indicator, then combined with configurable weights
   - Identifies strongest performing sectors

2. **Reversal Detection** (Bottom Fishing)
   - Strict filtering for beaten-down sectors with recovery signals
   - **Watch**: RSI < 50 AND ADX_Z < 0.5 AND CMF > 0
   - **BUY_DIV**: RSI < 40 AND ADX_Z < -0.5 AND CMF > 0.1
   - Reversal score calculated only for eligible sectors using RS Rating, CMF, RSI, and ADX Z rankings

### Sectors Analyzed
- ✅ Nifty 50 (Benchmark)
- ✅ PSU Bank
- ✅ Private Bank
- ✅ IT
- ✅ Pharma
- ✅ FMCG
- ✅ Auto
- ✅ Metal
- ✅ Realty
- ✅ Media
- ✅ Energy
- ✅ Infrastructure
- ✅ Commodities

## 📋 Requirements

- Python 3.8+
- pip (Python package manager)
- Internet connection (for live market data)

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/prabhuken01/market-sector-analysis.git
cd market-sector-analysis
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

### 4. Run the Web Application
```bash
streamlit run streamlit_app.py
```

The application will open at `http://localhost:8501` in your default browser.

### 5. Using the Application

**Sidebar Controls:**
- 📅 **Analysis Date**: Select any date for historical analysis
- ⏱️ **Analysis Interval**: Choose Daily, Weekly, or Hourly data
- 🔄 **Data Source**: Toggle between NSE Indices and ETF Proxy
- ⚖️ **Momentum Score Weights**: Customize how momentum is calculated
- 📊 **Reversal Score Weights**: Customize reversal candidate ranking
- 🎯 **Reversal Filters**: Set RSI and ADX Z-Score thresholds

**Three Main Tabs:**
1. **📈 Momentum Ranking**: Top performing sectors with trend analysis
2. **🔄 Reversal Candidates**: Oversold sectors with recovery potential
3. **📊 Interpretation Guide**: Understanding the indicators and scores

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
├── streamlit_app.py             # Main Streamlit web application
├── analysis.py                   # Core analysis logic
├── data_fetcher.py               # Yahoo Finance data fetching
├── indicators.py                 # Technical indicator calculations
├── market_analysis.py            # Standalone CLI analysis script
├── config.py                     # Configuration and sector symbols
├── requirements.txt              # Python dependencies
├── README.md                     # This file
├── ANALYSIS_METHODOLOGY.md       # Detailed methodology documentation
├── SYMBOLS.txt                   # Complete list of symbols used
├── Quick_Start/
│   ├── README.md                 # Installation & getting started
│   └── REFERENCE_MANUAL.md       # Technical documentation
└── .gitignore
```

## 🔧 Configuration

All parameters can be adjusted directly in the web interface:

### Momentum Score Weights (Configurable in Sidebar)
- **RS Rating Weight**: How much relative strength ranking contributes (default 40%)
- **ADX Z-Score Weight**: Trend strength comparison (default 20%)
- **RSI Weight**: Momentum indicator (default 30%)
- **DI Spread Weight**: Directional movement (default 10%)

### Reversal Detection Weights (Configurable in Sidebar)
- **RS Rating Weight**: Underperformance signal (default 40%)
- **CMF Weight**: Money flow accumulation (default 40%)
- **RSI Weight**: Oversold condition (default 10%)
- **ADX Z-Score Weight**: Weak trend indicator (default 10%)

### Reversal Filters (Configurable in Sidebar)
- **RSI Threshold**: Minimum RSI for reversal candidates (default 40)
- **ADX Z-Score Threshold**: Maximum ADX Z for weak trend detection (default -0.5)

All weights sum to 100% and are validated in real-time in the interface.

## 📈 Understanding the Output

### TAB 1: Momentum Ranking
Shows sectors sorted by momentum score (highest first) with:
- **Momentum Score**: Rank-based composite score of all indicators
- **Mansfield RS**: Relative strength vs Nifty 50 (green = outperforming, orange = underperforming)
- **Technical Indicators**: RSI, ADX, ADX Z-Score, DI Spread, CMF
- **Trend Analysis**: Historical momentum evolution for any selected sector (last 8 periods)
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
  - 🔵 **Watch**: Potential reversal (RSI<50, ADX_Z<0.5, CMF>0)
- **Reversal Score**: Rank-based score for reversal potential among eligible sectors
- **Technical Indicators**: RS Rating, CMF, RSI, ADX Z-Score
- **Trend Analysis**: Historical reversal metrics for any selected sector
- **All Sectors View**: Complete reversal scores for comparison

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

## 🐛 Troubleshooting

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

**Last Updated**: 2026-01-11  
**Version**: 2.0.0 (Streamlit Web Interface)  
**Status**: Active & Maintained ✅
