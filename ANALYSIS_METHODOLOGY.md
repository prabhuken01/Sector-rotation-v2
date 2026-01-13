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

**Rank-Based System with 1-10 Scaling:**
- Each sector is ranked on each indicator independently
- **Higher indicator values = better for momentum = Rank 1** (ascending=False)
- Ranks are weighted and averaged, then scaled to a **1-10 score**
- **Score 10 = Best momentum, Score 1 = Worst momentum**

**Default Weights:**
- RS Rating: 40%
- RSI: 30%
- ADX Z-Score: 20%
- DI Spread: 10%

**Step-by-Step Calculation:**

**Step 1: Rank Each Indicator (Higher Raw Value = Rank 1)**
```
Sector       RS_Rating  RSI   ADX_Z  DI_Spread
IT           8.2        68    1.5    15
Pharma       6.5        55    0.8    8
Metal        4.1        42   -0.5    -2
```
→ Ranks (1=best, 3=worst):
```
Sector       RS_Rank  RSI_Rank  ADX_Z_Rank  DI_Rank
IT           1        1         1           1
Pharma       2        2         2           2
Metal        3        3         3           3
```

**Step 2: Calculate Weighted Average Rank**
```
IT:     (1×0.40) + (1×0.30) + (1×0.20) + (1×0.10) = 1.0
Pharma: (2×0.40) + (2×0.30) + (2×0.20) + (2×0.10) = 2.0
Metal:  (3×0.40) + (3×0.30) + (3×0.20) + (3×0.10) = 3.0
```

**Step 3: Scale to 1-10 (Lower Weighted Rank = Higher Score)**
```
Formula: Score = 10 - ((weighted_rank - min_rank) / (max_rank - min_rank)) × 9

IT:     10 - ((1.0 - 1.0) / (3.0 - 1.0)) × 9 = 10.0
Pharma: 10 - ((2.0 - 1.0) / (3.0 - 1.0)) × 9 = 5.5
Metal:  10 - ((3.0 - 1.0) / (3.0 - 1.0)) × 9 = 1.0
```

**Final Result:**
| Sector | Momentum Score | Rank |
|--------|---------------|------|
| IT     | 10.0          | 1    |
| Pharma | 5.5           | 2    |
| Metal  | 1.0           | 3    |

**Interpretation:** IT has the strongest momentum (score 10), Metal has weakest (score 1).

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

**Rank-Based System with 1-10 Scaling (Eligible Sectors Only):**
- Only sectors meeting BOTH eligibility criteria (RSI < threshold AND ADX_Z < threshold) are ranked
- For reversals, **lower indicator values are better** (except CMF where higher is better)
- Ranks are weighted and averaged, then scaled to a **1-10 score**
- **Score 10 = Best reversal candidate, Score 1 = Worst among eligible**

**Default Weights:**
- RS Rating: 40% (lower = more beaten down = better)
- CMF: 40% (higher = money inflow = better)
- RSI: 10% (lower = more oversold = better)
- ADX Z-Score: 10% (lower = weaker trend = better for reversal)

**Step-by-Step Calculation Example:**

**Step 1: Filter to Eligible Sectors Only**
Only sectors with RSI < 40 AND ADX_Z < -0.5 qualify:
```
Sector      RSI   ADX_Z  CMF    RS_Rating  Eligible?
Pharma      35    -0.8   0.15   3.5        ✅ Yes
Realty      38    -1.2   0.08   2.8        ✅ Yes
Metal       32    -0.3   0.20   4.2        ❌ No (ADX_Z > -0.5)
IT          55     1.2   0.05   7.5        ❌ No (RSI > 40)
```

**Step 2: Rank Each Indicator Among Eligible Only**
- RS_Rating: Lower is better → ascending=True (lowest gets Rank 1)
- CMF: Higher is better → ascending=False (highest gets Rank 1)
- RSI: Lower is better → ascending=True
- ADX_Z: Lower is better → ascending=True

```
Sector      RS_Rank  CMF_Rank  RSI_Rank  ADX_Z_Rank
Realty      1        2         2         1          (RS=2.8 lowest, ADX_Z=-1.2 lowest)
Pharma      2        1         1         2          (CMF=0.15 highest, RSI=35 highest)
```

**Step 3: Calculate Weighted Average Rank**
```
Realty: (1×0.40) + (2×0.40) + (2×0.10) + (1×0.10) = 1.5
Pharma: (2×0.40) + (1×0.40) + (1×0.10) + (2×0.10) = 1.5
```

**Step 4: Scale to 1-10**
When weighted ranks are equal, both get score 5.0 (midpoint).

If they differed:
```
Formula: Score = 10 - ((weighted_rank - min_rank) / (max_rank - min_rank)) × 9
```

**Final Result:**
| Sector | Reversal Score | Rank | Status |
|--------|---------------|------|--------|
| Realty | 5.0           | 1    | Watch  |
| Pharma | 5.0           | 2    | BUY_DIV (if RSI<30, ADX_Z<-1, CMF>0.1) |

**Interpretation:** Both are equally good reversal candidates. Pharma gets BUY_DIV status if it meets the stricter thresholds.

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
