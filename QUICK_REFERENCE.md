# Quick Reference: Scoring Logic

## Momentum Score Calculation (Sectors & Companies)

```
STEP 1: Rank Indicators
┌─────────────────────────────────┐
│ Company    RSI   RSI_Rank        │
├─────────────────────────────────┤
│ A          75.0  1.0 (best)      │
│ B          70.0  2.0             │
│ C          65.0  3.0             │
│ D          60.0  4.0             │
│ E          55.0  5.0 (worst)     │
└─────────────────────────────────┘

STEP 2: Calculate Weighted Average Rank
Weighted_Avg_Rank = (RSI_Rank × 30% + ADX_Z_Rank × 20% + 
                     RS_Rating_Rank × 40% + DI_Spread_Rank × 10%)

Example: Company A
= (1.0 × 0.30) + (1.0 × 0.20) + (1.0 × 0.40) + (1.5 × 0.10)
= 0.30 + 0.20 + 0.40 + 0.15
= 1.05

STEP 3: Scale to 1-10
min_rank = 1.05 (best)
max_rank = 5.00 (worst)

For Company A:
Score = 10 - ((1.05 - 1.05) / (5.00 - 1.05)) × 9
      = 10 - 0
      = 10.0 ✓ Best

For Company E:
Score = 10 - ((5.00 - 1.05) / (5.00 - 1.05)) × 9
      = 10 - 9.0
      = 1.0 ✓ Worst
```

---

## Reversal Score Calculation (After Filtering)

```
STEP 0: Filter (ALL must be true)
┌──────────────────────────────────┐
│ Criteria Met?                    │
├──────────────────────────────────┤
│ A: RSI 35 < 40? YES              │
│    ADX_Z -0.8 < -0.5? YES        │
│    CMF 0.15 > 0.0? YES           │
│    → ELIGIBLE ✓                  │
├──────────────────────────────────┤
│ B: RSI 45 < 40? NO               │
│    → NOT ELIGIBLE ✗              │
└──────────────────────────────────┘

STEP 1: Rank Eligible Companies
Lower RSI = better for reversal

┌─────────────────────────────────────┐
│ Company    RSI   RSI_Rank           │
├─────────────────────────────────────┤
│ X          30.0  1.0 (most oversold)│
│ Y          35.0  2.0                │
│ Z          38.0  3.0                │
└─────────────────────────────────────┘

STEP 2: Calculate Weighted Average Rank
Weighted_Avg_Rank = (RSI_Rank × 10% + ADX_Z_Rank × 10% + 
                     RS_Rating_Rank × 40% + CMF_Rank × 40%)

STEP 3: Scale to 1-10
Best reversal candidate (min_rank) → 10
Worst reversal candidate (max_rank) → 1
```

---

## Key Differences at a Glance

### Momentum = Best Positioned to CONTINUE
- ✓ High RSI (strong momentum)
- ✓ High ADX_Z (strong trend)
- ✓ High RS_Rating (outperforming market)
- ✓ High DI_Spread (bullish)

### Reversal = Best Positioned to RECOVER
- ✓ Low RSI (oversold - room to bounce)
- ✓ Low ADX_Z (weak trend - can reverse)
- ✓ Low RS_Rating (underperforming - catching up)
- ✓ High CMF (money starting to flow in)

---

## Configuration (Sidebar)

### Momentum Weights
```
┌─────────────────────────────────┐
│ RS_Rating:     40% (default)    │
│ RSI:           30% (default)    │
│ ADX_Z:         20% (default)    │
│ DI_Spread:     10% (default)    │
│ ─────────────────────────────   │
│ Total:        100%              │
└─────────────────────────────────┘
```

### Reversal Weights
```
┌─────────────────────────────────┐
│ RS_Rating:     40% (default)    │
│ CMF:           40% (default)    │
│ RSI:           10% (default)    │
│ ADX_Z:         10% (default)    │
│ ─────────────────────────────   │
│ Total:        100%              │
└─────────────────────────────────┘
```

### Reversal Filters
```
┌─────────────────────────────────┐
│ RSI below:        40 (default)  │
│ ADX_Z below:     -0.5 (default) │
│ CMF above:        0.0 (default) │
└─────────────────────────────────┘

Only companies meeting ALL three show in reversal tab.
```

---

## Ranking Methods

### method='min' (Sectors)
Ties get the same rank:
```
Values:  [10, 10, 10, 9, 8]
Ranks:   [1,  1,  1,  4, 5]  ← All tied values = 1
```

### method='average' (Companies)
Ties split the ranks:
```
Values:  [10, 10, 10, 9, 8]
Ranks:   [2,  2,  2,  4, 5]  ← Average of 1,2,3 = 2
```

**Why 'average' for companies?**
- Smaller groups (5-8 companies) have more ties
- Spreads identical scores across fractional ranks
- Prevents bunching at same score

---

## Example: Before & After

### Before (Hardcoded, method='min')
```
Metal Sector Companies:
Company    RS_Rating  Score
Tata       10.0       10.0 ← Bunched!
Hindalco   10.0       10.0 ← Bunched!
JSW Steel  10.0       10.0 ← Bunched!
Vedanta    10.0       10.0 ← Bunched!
Jindal     8.0        5.0  ✓ Different
```

### After (Configurable, method='average')
```
Metal Sector Companies:
Company      Weighted_Rank  Score
Tata         1.0            10.0
Hindalco     1.5            9.3
JSW Steel    2.0            8.5
Vedanta      2.5            7.8
Jindal       5.0            1.0
```

---

## Flow Diagram: Company Analysis

```
User Selects Sector
        ↓
User Chooses Interval (Daily/Weekly/Hourly)
        ↓
Fetch Company Data (respects interval)
        ↓
┌─ MOMENTUM TAB ─────────────────────────────────────┐
│                                                    │
│  Calculate Indicators (RSI, ADX_Z, RS, DI_Spread) │
│  ↓                                                 │
│  Rank Each (method='average')                      │
│  ↓                                                 │
│  Apply Momentum Weights (from sidebar)             │
│  ↓                                                 │
│  Calculate Weighted Average Rank                   │
│  ↓                                                 │
│  Scale to 1-10 Momentum Score                      │
│  ↓                                                 │
│  Display Sorted by Score (high to low)             │
└─────────────────────────────────────────────────────┘

┌─ REVERSAL TAB ─────────────────────────────────────────┐
│                                                        │
│  Calculate Indicators (RSI, ADX_Z, RS, CMF)           │
│  ↓                                                     │
│  FILTER: RSI < 40 AND ADX_Z < -0.5 AND CMF > 0.0    │
│  ↓                                                     │
│  Rank Eligible Only (method='average')                │
│  ├─ RSI: ascending=True (lower = better)              │
│  ├─ ADX_Z: ascending=True (lower = better)            │
│  ├─ RS_Rating: ascending=True (lower = better)        │
│  └─ CMF: ascending=False (higher = better)            │
│  ↓                                                     │
│  Apply Reversal Weights (from sidebar)                │
│  ↓                                                     │
│  Calculate Weighted Average Rank                      │
│  ↓                                                     │
│  Scale to 1-10 Reversal Score                         │
│  ↓                                                     │
│  Display Sorted by Score (high to low)                │
└────────────────────────────────────────────────────────┘
```

---

## Code Locations

| Functionality | Sector | Company |
|---|---|---|
| Momentum ranking | analysis.py:251-268 | company_analysis.py:247-275 |
| Momentum scaling | analysis.py:270-277 | company_analysis.py:276-285 |
| Reversal filtering | analysis.py:282 | company_analysis.py:506-512 |
| Reversal ranking | analysis.py:286-289 | company_analysis.py:541-544 |
| Reversal scaling | analysis.py:302-313 | company_analysis.py:557-564 |

