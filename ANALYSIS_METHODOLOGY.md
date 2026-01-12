# NSE Market Sector Analysis - Methodology

## Overview
This tool analyzes NSE market sectors using technical indicators to identify momentum opportunities and potential reversal candidates. The analysis uses a rank-based scoring system to compare sectors relative to each other.

## Data Sources
- **Index Data**: NSE sector indices (default)
- **ETF Proxy**: Alternative ETF-based data
- **Benchmark**: Nifty 50 (for relative performance calculations)
- **Intervals**: Daily (1d), Weekly (1wk), Hourly (1h)

---

## Momentum Analysis

### Purpose
Identify sectors with strong relative momentum for potential investment opportunities.

### Key Indicators

1. **RS Rating (Relative Strength Rating)** - 0-10 scale
   - Measures sector performance relative to Nifty 50 benchmark
   - Calculation: `RS_Rating = 5 + (relative_performance × 25)`
   - Clamped between 0 (worst) and 10 (best)
   - Higher values indicate outperformance

2. **ADX Z-Score (Average Directional Index Z-Score)**
   - Normalized ADX showing trend strength relative to other sectors
   - Positive values indicate stronger trends
   - Used to identify sectors with strengthening momentum

3. **RSI (Relative Strength Index)** - 14-period
   - Traditional momentum oscillator
   - Higher values (50-70) indicate stronger momentum
   - Values >70 may indicate overbought conditions

4. **DI Spread (Directional Indicator Spread)**
   - Difference between +DI and -DI
   - Positive values indicate bullish momentum
   - Negative values indicate bearish momentum

### Scoring Methodology

**Rank-Based System:**
- Each sector is ranked on each indicator (1 = worst, N = best)
- Ranks are combined using configurable percentage weights
- Default weights:
  - RS Rating: 40%
  - ADX Z-Score: 20%
  - RSI: 30%
  - DI Spread: 10%

**Momentum Score Formula:**
```
Momentum_Score = (RS_Rating_Rank × 0.40) + 
                 (ADX_Z_Rank × 0.20) + 
                 (RSI_Rank × 0.30) + 
                 (DI_Spread_Rank × 0.10)
```

**Result:** Higher momentum scores indicate sectors with stronger relative momentum.

### Historical Performance Report
- Tracks top 2 momentum-ranked sectors over past 6 months
- Calculates forward returns (7-day and 14-day)
- Helps evaluate momentum strategy effectiveness
- Downloadable CSV format

---

## Reversal Analysis

### Purpose
Identify oversold sectors with potential for mean reversion or trend reversal.

### Pre-Filtering (Eligibility Criteria)

Sectors must meet **BOTH** user-defined conditions to be considered reversal candidates:

1. **RSI < threshold** (default: 40)
   - Indicates oversold condition
   - Configurable threshold (20-60 range in sidebar)

2. **ADX Z-Score < threshold** (default: -0.5)
   - Indicates weak trend relative to other sectors
   - Configurable threshold (-2.0 to 2.0 range in sidebar)

### Reversal Status Determination

| Status | Condition |
|--------|-----------|
| **BUY_DIV** | Meets strict BUY_DIV thresholds: RSI < 40, ADX_Z < -0.5, CMF > 0.1 |
| **Watch** | Passes user-defined filters but doesn't meet strict BUY_DIV criteria |
| **No** | Does not meet user-defined filter thresholds |

**Important:** Sectors that pass the user's RSI and ADX_Z filter thresholds are automatically at least "Watch" status. This ensures all qualifying sectors appear in the Reversal Candidates list.

### Key Indicators for Reversal Scoring

1. **RS Rating** - Lower values preferred
   - Identifies sectors underperforming the benchmark
   - Used inversely in ranking (lower = better for reversal)

2. **CMF (Chaikin Money Flow)** - 20-period
   - Measures accumulation/distribution
   - Positive values indicate buying pressure
   - Higher CMF preferred for reversals (indicates potential accumulation)

3. **RSI** - Lower values preferred
   - More oversold = higher reversal potential
   - Used inversely in ranking

4. **ADX Z-Score** - Lower values preferred
   - Weaker trends more likely to reverse
   - Used inversely in ranking

### Scoring Methodology

**Rank-Based System (Eligible Sectors Only):**
- Only sectors meeting eligibility criteria are ranked
- Lower RS Rating, RSI, and ADX Z receive higher ranks
- Higher CMF receives higher rank
- Default weights:
  - RS Rating: 40%
  - CMF: 40%
  - RSI: 10%
  - ADX Z-Score: 10%

**Reversal Score Formula:**
```
Reversal_Score = (RS_Rating_Rank × 0.40) + 
                 (CMF_Rank × 0.40) + 
                 (RSI_Rank × 0.10) + 
                 (ADX_Z_Rank × 0.10)
```

**Result:** Higher reversal scores indicate better reversal candidates among eligible sectors.

---

## Trend Analysis

### Momentum Trend (T-7 to T)
- Shows how momentum indicators evolved over past 8 periods
- Recalculates momentum scores at each historical point
- Maintains rank-based scoring consistency
- Format: Periods as rows, indicators as columns

### Reversal Trend (T-7 to T)
- Shows how reversal indicators evolved over past 8 periods
- Recalculates reversal scores ONLY for eligible sectors at each period
- If sector doesn't meet eligibility criteria at a period, shows "N/A"
- Format: Periods as columns, indicators as rows (transposed)

**Note:** Reversal scores are contextual - a sector may be eligible at some periods but not others based on RSI and ADX Z thresholds.

---

## Additional Metrics

### Mansfield Relative Strength
- Long-term (250-day MA) relative strength vs benchmark
- Positive = outperforming, Negative = underperforming
- Used for context, not in scoring

### ADX (Average Directional Index)
- Absolute trend strength measurement
- Values >25 indicate strong trends
- Values <20 indicate weak/no trend

### Price Change %
- Current period price change
- Used for context, not in scoring

---

## Configuration

### Adjustable Parameters

**Momentum Weights:**
- All weights must sum to 100%
- Allows customization based on personal preference

**Reversal Filters:**
- RSI threshold (20-60)
- ADX Z threshold (-2.0 to 2.0)
- Stricter thresholds = fewer but stronger candidates

**Reversal Weights:**
- All weights must sum to 100%
- Allows customization based on mean reversion strategy

**Analysis Date:**
- Historical analysis capability
- Useful for backtesting strategies

---

## Best Practices

1. **Momentum Trading:**
   - Focus on top 2-3 momentum ranked sectors
   - Monitor RS Rating and ADX Z for strength continuation
   - Use historical performance to validate strategy

2. **Reversal Trading:**
   - Only consider sectors meeting both eligibility criteria
   - Higher reversal scores indicate better setups
   - Monitor CMF for accumulation signals
   - Review trend analysis to understand recent behavior

3. **Risk Management:**
   - Diversify across multiple sectors
   - Use stop losses based on volatility
   - Monitor benchmark (Nifty 50) for market direction

4. **Timeframe Selection:**
   - Daily: Short-term trading (days to weeks)
   - Weekly: Medium-term trading (weeks to months)
   - Hourly: Intraday trading (limited historical data)

---

## Market Data Date Logic

The "Market Data Date" shown in the header depends on the selected interval:

| Interval | Market Data Date Display |
|----------|--------------------------|
| **Hourly** | Same as Analysis Date with latest hourly timestamp |
| **Daily** | The actual date of the last trading session data |
| **Weekly** | Shows "Week of YYYY-MM-DD" with Monday's date |

**Note:** Analysis Date is shown in IST (Indian Standard Time) for Indian market alignment.

---

## CMF Sum Total (Sector Rotation Indicator)

The **CMF Sum** metric aggregates all sector CMF values to indicate overall market rotation:

| CMF Sum Value | Interpretation |
|---------------|----------------|
| **> 0.5** | Strong net inflow - bullish sector rotation |
| **0 to 0.5** | Mild inflow - neutral to slightly bullish |
| **-0.5 to 0** | Mild outflow - neutral to slightly bearish |
| **< -0.5** | Strong net outflow - bearish sector rotation |

A value approaching 1.0 indicates clear sector rotation with money flowing into sectors.

---

## Trend Analysis Period Labels

Historical trend analysis now shows actual dates alongside period labels:

- **T (12-Jan)**: Current period (latest data)
- **T-1 (11-Jan)**: One period prior
- **T-2 (10-Jan)**: Two periods prior
- ... continuing to **T-7**

For **Weekly** interval, dates show the week's Monday.
For **Hourly** interval, dates show the trading session date.

---

## Technical Notes

- **Rank-based scoring** provides relative comparison, not absolute values
- Scores are recalculated with each analysis run
- Historical trend analysis uses point-in-time calculations
- All indicators use standard technical analysis formulas
- Data fetched from Yahoo Finance API
- All times displayed in IST (Indian Standard Time, UTC+5:30)
