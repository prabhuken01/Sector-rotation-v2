# Momentum Score Calculation Methodology

## Overview
The momentum score uses a **rank-based normalization approach** that scales indicator rankings to a 1-10 scale. This ensures fair comparison across sectors/companies with different absolute indicator values.

---

## Sector Momentum Scoring Logic (from `analysis.py`)

### Step 1: Calculate Technical Indicators
For each sector, calculate:
- **RSI** (Relative Strength Index): Momentum oscillator (0-100), higher = stronger momentum
- **ADX_Z** (ADX Z-Score): Normalized trend strength, higher = stronger trend
- **RS_Rating** (Relative Strength vs Nifty 50): Outperformance vs benchmark (0-10 scale)
  - Formula: `RS_Rating = 5 + (relative_performance * 25)`
  - Clamped: `max(0, min(10, rs_rating))`
  - Ranges from 0 (worst underperformance) to 10 (best outperformance)
- **DI_Spread** (Directional Index Spread): Difference between +DI and -DI, indicates trend direction strength

### Step 2: Rank Each Indicator
Rank all sectors for each indicator using `method='min'` (ties get same rank):
```python
df['ADX_Z_Rank'] = df['ADX_Z'].rank(ascending=False, method='min')
df['RS_Rating_Rank'] = df['RS_Rating'].rank(ascending=False, method='min')
df['RSI_Rank'] = df['RSI'].rank(ascending=False, method='min')
df['DI_Spread_Rank'] = df['DI_Spread'].rank(ascending=False, method='min')
```

**Key:** `ascending=False` means higher values get rank 1 (better)

Example with 5 sectors:
```
Sector    RS_Rating    RS_Rating_Rank
--------  ----------   ---------------
A         10.0         1
B         9.5          2
C         8.0          3
D         7.0          4
E         6.0          5
```

### Step 3: Calculate Weighted Average Rank
Using configurable weights (default: RS_Rating 40%, ADX_Z 20%, RSI 30%, DI_Spread 10%):

```python
total_weight = sum(momentum_weights.values())
df['Weighted_Avg_Rank'] = (
    (df['ADX_Z_Rank'] * 20.0 / total_weight) +
    (df['RS_Rating_Rank'] * 40.0 / total_weight) +
    (df['RSI_Rank'] * 30.0 / total_weight) +
    (df['DI_Spread_Rank'] * 10.0 / total_weight)
)
```

This produces a weighted average rank value. Lower values = better momentum.

### Step 4: Scale to 1-10 Momentum Score
Convert weighted rank to 1-10 scale:

```python
num_sectors = len(df)
min_rank = df['Weighted_Avg_Rank'].min()  # Best (lowest) weighted rank
max_rank = df['Weighted_Avg_Rank'].max()  # Worst (highest) weighted rank

if max_rank > min_rank:
    df['Momentum_Score'] = 10 - ((df['Weighted_Avg_Rank'] - min_rank) / (max_rank - min_rank)) * 9
else:
    df['Momentum_Score'] = 5.0  # All sectors tied
```

**Translation:**
- Sector with min_rank → Momentum_Score = 10 (best)
- Sector with max_rank → Momentum_Score = 1 (worst)
- Linearly scaled between: `Score = 10 - (relative_position_in_range * 9)`

---

## Why Sector Logic Differs from Company Logic

### The Key Issue: Different Denominators
- **Sectors:** ~13 sectors being ranked, so ranks range from 1-13
- **Companies:** Only 5-8 companies per sector, so ranks range from 1-5 or 1-8

When all companies have **tied RS_Rating = 10.0** (common because multiple companies outperform equally):
- All get `RS_Rating_Rank = 1` with `method='min'`
- With 40% weight on RS_Rating, this dominates the calculation
- Many companies end up with identical weighted average ranks
- When `max_rank == min_rank`, all get `Momentum_Score = 5.0` (neutral)
- But if there's tiny variation, the scaling produces bunched scores

### The Problem with Using `method='min'`
```
Company    RS_Rating    RS_Rating_Rank (method='min')
---------  ----------   ---------------------------
Tata       10.0         1
Hindalco   10.0         1  ← TIED! Both get rank 1
JSWSTEEL   10.0         1  ← TIED! 
Vedanta    10.0         1  ← TIED!
```

When multiple indicators are tied with `method='min'`, they don't differentiate. For companies with 5-8 data points and many tied values, this creates bunching.

---

## Fixed Approach for Company Momentum Scoring

### Changes Made:
1. **Use `method='average'` instead of `method='min'`**
   - Ties are split fractionally among tied positions
   - Provides better differentiation

Example with `method='average'`:
```
Company    RS_Rating    RS_Rating_Rank (method='average')
---------  ----------   --------------------------------
Tata       10.0         2.5  ← Ranks 1-4 are tied, average = (1+2+3+4)/4 = 2.5
Hindalco   10.0         2.5
JSWSTEEL   10.0         2.5
Vedanta    10.0         2.5
Jindal     8.0          5    ← Distinct value gets unique rank
```

2. **Pass Interval Parameter**
   - Company analysis was hardcoded to `interval='1d'` regardless of user selection
   - Now correctly respects user's interval choice (Daily/Weekly/Hourly)
   - Ensures data consistency with what's being displayed

3. **Improved Reversal Filter Logic**
   - Also changed reversal ranking to `method='average'`
   - Ensures companies that don't meet filter criteria are properly excluded

---

## Applied Logic Summary

| Aspect | Sector | Company (Now Fixed) |
|--------|--------|-------------------|
| **Indicators** | RSI, ADX_Z, RS_Rating, DI_Spread | RSI, ADX_Z, RS_Rating, DI_Spread (same) |
| **Ranking Method** | `method='min'` | `method='average'` (better for small groups) |
| **Weights** | Configurable (default: RS 40%, ADX_Z 20%, RSI 30%, DI_Spread 10%) | Same as sectors |
| **Interval** | User-selected | User-selected (now fixed) |
| **Scale** | 1-10 (best to worst) | 1-10 (best to worst) |
| **When Applied** | All 13 sectors | Top N companies per sector |

---

## How Momentum Score Reflects Market Position

**High Momentum Score (8-10):**
- Outperforming vs Nifty 50 (high RS_Rating)
- Strong trend (high ADX_Z)
- Strong momentum (high RSI, high DI_Spread)
- Best positioned for continuation

**Mid Momentum Score (4-7):**
- Mixed signals
- Moderate indicators
- Transition/consolidation phase

**Low Momentum Score (1-3):**
- Underperforming vs Nifty 50
- Weak trend or no trend
- Weak momentum
- Potential for reversal/rotation

---

## Code Files Affected

1. **[company_analysis.py](company_analysis.py)**
   - `fetch_company_data_cached()`: Now accepts `interval` parameter
   - `display_company_momentum_tab()`: Now accepts and passes `time_interval`
   - `display_company_reversal_tab()`: Now accepts and passes `time_interval`
   - Ranking: Changed from `method='min'` to `method='average'`

2. **[streamlit_app.py](streamlit_app.py)**
   - Updated calls to pass `time_interval` to company analysis tabs

3. **[analysis.py](analysis.py)**
   - Existing sector logic (unchanged, reference implementation)
   - Uses `method='min'` due to larger dataset (~13 sectors)
