# NSE Market Sector Analysis Tool 📊

A comprehensive Python-based tool for analyzing NSE (National Stock Exchange) sector performance using advanced technical indicators and momentum/reversal scoring strategies. Powered by Streamlit with real-time data from Yahoo Finance.

**📚 Documentation:**
- [Implementation Guide](implementation_guide.md) - Technical details & troubleshooting
- [Scoring Methodology](UNIFIED_SCORING_LOGIC.md) - Complete scoring logic explanation

## 🎯 Overview

This tool analyzes **16 major NSE sectors** (plus Nifty 50 benchmark) to identify:
- **Momentum Opportunities**: Sectors outperforming Nifty 50 with strong trend signals
- **Reversal Candidates**: Oversold sectors with institutional buying signals and recovery potential

Perfect for traders, analysts, and investment professionals seeking data-driven sector insights.

## ✨ Key Features

- **Real-time Sector Ranking**: Momentum and reversal analysis with composite scoring (1-10 scale)
- **8 Interactive Tabs**: Momentum, Reversals, Company Analysis, Historical Rankings, Interpretation Guide, Data Sources, Sector Companies
- **Technical Indicators**: RSI, ADX, DI Spread, CMF, Z-Score ADX, Mansfield RS
- **Company-Level Analysis**: Drill down into individual stocks within each sector
- **Historical Rankings**: View top 2 sectors from T-7 to T with consistency metrics
- **Configurable Weights**: Customize indicator weights for momentum and reversal scoring
- **Multiple Intervals**: Daily, Weekly, or Hourly analysis
- **Data Caching**: 5-minute TTL for faster loading (~2-3x performance improvement)
- **CSV Download**: Export analysis results and historical performance reports

## 📊 Technical Indicators

| Indicator | Purpose | Interpretation |
|-----------|---------|-----------------|
| **RSI (14-period)** | Momentum & overbought/oversold | >65 = Overbought, <35 = Oversold |
| **ADX** | Trend strength (0-100) | >25 = Strong trend, <20 = Weak trend |
| **DI Spread** | Bullish vs bearish pressure | Positive = Bullish, Negative = Bearish |
| **CMF (20-period)** | Institutional buying/selling | >0 = Inflow, <0 = Outflow |
| **Z-Score ADX** | Normalized trend strength | >0 = Above average, <0 = Below average |
| **Mansfield RS** | Relative strength vs Nifty 50 | >0 = Outperforming, <0 = Underperforming |

## 🔄 Scoring Logic

### Momentum Scoring (Scale 1-10)
- **Rank 1 (Best)**: Highest ADX_Z, RS Rating, RSI, DI Spread
- **Weights**: RS Rating (40%), RSI (30%), ADX Z-Score (20%), DI Spread (10%)
- **Score 10 = Best momentum** | **Score 1 = Worst momentum**

### Reversal Scoring (Scale 1-10)
- **Eligibility**: RSI < threshold AND ADX_Z < threshold AND CMF > threshold
- **BUY_DIV Status**: RSI < 30 AND ADX_Z < -1 AND CMF > 0.1 (highest confidence)
- **Watch Status**: Meets filter criteria but not BUY_DIV threshold
- **Weights**: RS Rating (40%), CMF (40%), RSI (10%), ADX Z-Score (10%)
- **Score 10 = Best reversal candidate** | **Score 1 = Worst reversal candidate**

## 📈 Sectors Covered

| # | Sector | Primary ETF |
|----|--------|------------|
| 1 | Auto | AUTOBEES.NS |
| 2 | Commodities | ^CNXCOMMODITIES |
| 3 | Defence | DEFENCE.NS |
| 4 | Energy | MOENERGY.NS |
| 5 | FMCG | ICICIFMCG.NS |
| 6 | IT | ITBEES.NS |
| 7 | Infra | INFRABEES.NS |
| 8 | Media | ^CNXMEDIA |
| 9 | Metal | METALIETF.NS |
| 10 | Fin Services | FINIETF.NS (NBFC, Insurance, Capital Markets) |
| 11 | Pharma | PHARMABEES.NS |
| 12 | PSU Bank | PSUBNKBEES.NS |
| 13 | Pvt Bank | PVTBANKBEES.NS |
| 14 | Realty | MOREALTY.NS |
| 15 | Oil & Gas | OILIETF.NS |
| 16 | Nifty 50 | NIFTYBEES.NS (Benchmark) |

## 🚀 Quick Start

### Installation
```bash
git clone https://github.com/prabhuken01/Sector-rotation-v2.git
cd Sector-rotation-v2
pip install -r requirements.txt
```

### Run Application
```bash
python -m streamlit run streamlit_app.py
```
Opens at: `http://localhost:8501`

## 📱 UI Tabs Overview

| Tab | Purpose |
|-----|---------|
| **📈 Momentum Ranking** | Top sectors by momentum score with trend analysis |
| **🔄 Reversal Candidates** | Oversold sectors with recovery signals |
| **📊 Interpretation Guide** | Detailed explanation of all indicators |
| **🏢 Company Momentum** | Individual company performance within sectors |
| **🏢 Company Reversals** | Oversold companies showing recovery signals |
| **📅 Historical Rankings** | Track top 2 sectors from T-7 to T |
| **🔌 Data Sources** | Live connectivity status for all data feeds |
| **🏢 Sector Companies** | Company mappings with weights, downloadable as CSV |

## ⚙️ Configuration

### Momentum Weights (Sidebar)
- RS Rating: 40% (relative performance vs Nifty 50)
- RSI: 30% (momentum strength)
- ADX Z-Score: 20% (trend reliability)
- DI Spread: 10% (bullish/bearish pressure)

### Reversal Filters (Sidebar)
- RSI Threshold: 20-60 (default 40)
- ADX Z-Score Threshold: -2 to 2 (default -0.5)
- CMF Threshold: -0.5 to 0.5 (default 0)

### Analysis Date & Interval
- Select any historical date for backtesting
- Interval: Daily, Weekly, or Hourly

## 📥 Export Features

- **Momentum Data**: Download sector rankings as CSV
- **Historical Rankings**: T-7 to T sector rankings (consistency analysis)
- **Sector Companies**: All company mappings with weights
- **Historical Performance**: 6-month backtest with forward returns

## ⚠️ Important Notes

1. **Historical Backtests**: Point-in-time calculations may differ slightly from live analysis due to data updates
2. **Data Latency**: Market data from Yahoo Finance (typically 15-20 min delay for NSE)
3. **Fin Services ETF**: FINIETF is NBFC/Insurance/Capital Markets only (excludes banks)
4. **Company Analysis**: Tracks 8-10 top-weighted companies per sector

## 🛠️ Files Overview

| File | Purpose |
|------|---------|
| **streamlit_app.py** | Main UI and analysis orchestration |
| **company_analysis.py** | Company-level momentum/reversal analysis |
| **analysis.py** | Sector-level analysis and scoring |
| **indicators.py** | Technical indicator calculations |
| **data_fetcher.py** | Yahoo Finance data fetching with caching |
| **config.py** | Configuration (sectors, ETFs, default weights) |
| **company_symbols.py** | Company-to-sector mappings with weights |

## 📝 Recent Updates (Jan 2026)

- ✅ Fixed company reversal tab error (uninitialized variable)
- ✅ Updated FINIETF composition (NBFC/Insurance/Capital Markets)
- ✅ Added "Indicators" label to company trend analysis
- ✅ Added CSV download for sector companies
- ✅ Added Historical Rankings tab (T-7 to T)
- ✅ Performance optimization with 5-min caching
- ✅ Fixed momentum/reversal scoring logic
- ✅ Added IST timezone support
- ✅ Improved point-in-time historical calculations

## 🔗 Quick Links

- **GitHub**: https://github.com/prabhuken01/Sector-rotation-v2
- **Data Source**: Yahoo Finance (via yfinance)
- **Framework**: Streamlit (Python web framework)

## 📧 Support

For issues or suggestions, please check the implementation_guide.md for detailed methodology and troubleshooting.
