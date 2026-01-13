# Unified Momentum & Reversal Scoring Logic

## Overview
Both **sectors and companies** now use identical ranking-based scoring logic:
1. **Calculate technical indicators**
2. **Rank indicators** (relative to peers)
3. **Apply configurable weights**
4. **Scale to 1-10 score**

This ensures consistent methodology across different analysis levels.

---

## Momentum Scoring Logic (Sectors & Companies)

### Step 1: Calculate Indicators
For each entity (sector or company):
```
RSI                - Momentum oscillator (0-100, higher = stronger)
ADX_Z              - Trend strength Z-score (higher = stronger trend)  
RS_Rating          - Outperformance vs Nifty 50 (0-10 scale)
DI_Spread          - Bullish/bearish bias (higher = bullish)
```

### Step 2: Rank Each Indicator Within Group
Rank all peers on each indicator using `ascending=False` (higher = rank 1):

**Example with 5 companies:**
```
Company    RSI      RSI_Rank (method='average')
--------   -------  ---------------------------
A          75.0     1.0  (highest RSI = best momentum)
B          70.0     2.0
C          65.0     3.0
D          60.0     4.0
E          55.0     5.0  (lowest RSI = worst momentum)
```

**Why method='average'?**
- Ties are split fractionally among tied positions
- Better differentiation in small groups (5-8 companies)
- Prevents multiple entities with identical scores

Example with ties:
```
Company    RS_Rating    RS_Rating_Rank (method='average')
--------   ----------   --------------------------------
A          10.0         2.5  (ranks 1-4 averaged = 2.5)
B          10.0         2.5
C          10.0         2.5
D          10.0         2.5
E          8.0          5.0  (distinct rank)
```

### Step 3: Calculate Weighted Average Rank
Apply configurable weights from sidebar:

```python
total_weight = sum(momentum_weights.values())
weighted_rank = (
    (RSI_Rank * RSI_Weight / total_weight) +
    (ADX_Z_Rank * ADX_Z_Weight / total_weight) +
    (RS_Rating_Rank * RS_Rating_Weight / total_weight) +
    (DI_Spread_Rank * DI_Spread_Weight / total_weight)
)
```

**Default weights:**
- RS_Rating: 40%
- RSI: 30%
- ADX_Z: 20%
- DI_Spread: 10%

**Result:** Lower weighted_rank = better momentum

### Step 4: Scale to 1-10 Momentum Score

```python
if (max_rank > min_rank):
    momentum_score = 10 - ((weighted_rank - min_rank) / (max_rank - min_rank)) * 9
else:
    momentum_score = 5.0  # All tied
```

**Translation:**
- Best (min_rank) → Score = 10
- Worst (max_rank) → Score = 1
- Linear scale in between

**Example:**
```
Company    Weighted_Rank    Momentum_Score
--------   ---------------  ---------------
A          1.0              10.0 (best)
B          1.8              8.2
C          2.5              6.4
D          3.2              4.6
E          4.0              2.8
F          5.0              1.0 (worst)
```

---

## Reversal Scoring Logic (Sectors & Companies)

### Step 1: Apply Filter Criteria

Only rank companies/sectors meeting **ALL** conditions:
```
AND RSI < RSI_Threshold           (default: 40, user-adjustable)
AND ADX_Z < ADX_Z_Threshold       (default: -0.5, user-adjustable)
AND CMF > CMF_Threshold           (default: 0.0, user-adjustable)
```

**Why filter first?**
- Only candidates showing weakness are ranked
- Avoids ranking companies that don't meet oversold criteria
- Cleaner interpretation: "Ranked among oversold companies"

### Step 2: Rank Eligible Entities

Within filtered group, rank using:
- **Lower is better:** RSI, RS_Rating, ADX_Z (ascending=True)
- **Higher is better:** CMF (ascending=False)

**Example: 3 eligible companies after filtering**
```
Company    RSI      RSI_Rank    CMF     CMF_Rank
--------   -------  ---------   ------  ---------
A          35.0     2.0 (higher RSI)     0.15     2.0
B          30.0     1.0 (lower RSI)      0.20     1.0 (higher CMF)
C          38.0     3.0 (highest RSI)    0.05     3.0 (lower CMF)
```

**Logic:**
- Lower RSI (more oversold) = gets lower rank number (better for reversal)
- Higher CMF (money inflow) = gets lower rank number (better for reversal)

### Step 3: Calculate Weighted Average Rank

Apply configurable reversal weights:

```python
weighted_rank = (
    (RS_Rating_Rank * RS_Rating_Weight / total_weight) +
    (CMF_Rank * CMF_Weight / total_weight) +
    (RSI_Rank * RSI_Weight / total_weight) +
    (ADX_Z_Rank * ADX_Z_Weight / total_weight)
)
```

**Default weights:**
- RS_Rating: 40% (how beaten down)
- CMF: 40% (money inflow signal)
- RSI: 10% (oversold level)
- ADX_Z: 10% (trend weakness)

### Step 4: Scale to 1-10 Reversal Score

Same scaling as momentum:
```python
if (max_rank > min_rank):
    reversal_score = 10 - ((weighted_rank - min_rank) / (max_rank - min_rank)) * 9
else:
    reversal_score = 5.0
```

**Translation:**
- Best reversal candidate (min_rank) → Score = 10
- Weakest reversal candidate (max_rank) → Score = 1

**Example: 3 eligible companies**
```
Company    Weighted_Rank    Reversal_Score
--------   ---------------  ---------------
A          1.0              10.0 (most oversold)
B          2.0              5.5
C          3.0              1.0 (least oversold)
```

---

## Key Differences: Momentum vs Reversal

| Aspect | Momentum | Reversal |
|--------|----------|----------|
| **Filter** | None - rank all | Required - RSI, ADX_Z, CMF criteria |
| **RSI ranking** | Higher RSI = rank 1 (ascending=False) | Lower RSI = rank 1 (ascending=True) |
| **ADX_Z ranking** | Higher = rank 1 (strong trend) | Lower = rank 1 (weak trend) |
| **RS_Rating ranking** | Higher = rank 1 (outperforming) | Lower = rank 1 (underperforming) |
| **CMF ranking** | N/A | Higher = rank 1 (money inflow) |
| **Interpretation** | Best positioned to continue | Best positioned to recover |

---

## Code Implementation

### Momentum (Sectors & Companies)

**Location:** `analysis.py` lines 246-277 (sectors), `company_analysis.py` lines 247-275 (companies)

```python
# 1. Rank each indicator
df['ADX_Z_Rank'] = df['ADX_Z'].rank(ascending=False, method='average')
df['RS_Rating_Rank'] = df['RS_Rating'].rank(ascending=False, method='average')
df['RSI_Rank'] = df['RSI'].rank(ascending=False, method='average')
df['DI_Spread_Rank'] = df['DI_Spread'].rank(ascending=False, method='average')

# 2. Calculate weighted average rank
total_weight = sum(momentum_weights.values())
df['Weighted_Avg_Rank'] = (
    (df['ADX_Z_Rank'] * momentum_weights.get('ADX_Z', 20.0) / total_weight) +
    (df['RS_Rating_Rank'] * momentum_weights.get('RS_Rating', 40.0) / total_weight) +
    (df['RSI_Rank'] * momentum_weights.get('RSI', 30.0) / total_weight) +
    (df['DI_Spread_Rank'] * momentum_weights.get('DI_Spread', 10.0) / total_weight)
)

# 3. Scale to 1-10
if num_entities > 1:
    min_rank = df['Weighted_Avg_Rank'].min()
    max_rank = df['Weighted_Avg_Rank'].max()
    if max_rank > min_rank:
        df['Momentum_Score'] = 10 - ((df['Weighted_Avg_Rank'] - min_rank) / (max_rank - min_rank)) * 9
```

### Reversal (Sectors & Companies)

**Location:** `analysis.py` lines 284-313 (sectors), `company_analysis.py` lines 540-564 (companies)

```python
# 0. Filter eligible entities
eligible = df[df['Meets_Criteria']].copy()

# 1. Rank within eligible (lower values = better)
eligible['RSI_Rank'] = eligible['RSI'].rank(ascending=True, method='average')
eligible['ADX_Z_Rank'] = eligible['ADX_Z'].rank(ascending=True, method='average')
eligible['RS_Rating_Rank'] = eligible['RS_Rating'].rank(ascending=True, method='average')
eligible['CMF_Rank'] = eligible['CMF'].rank(ascending=False, method='average')

# 2. Calculate weighted average rank
total_weight = sum(reversal_weights.values())
eligible['Weighted_Avg_Rank'] = (
    (eligible['RS_Rating_Rank'] * reversal_weights.get('RS_Rating', 40.0) / total_weight) +
    (eligible['CMF_Rank'] * reversal_weights.get('CMF', 40.0) / total_weight) +
    (eligible['RSI_Rank'] * reversal_weights.get('RSI', 10.0) / total_weight) +
    (eligible['ADX_Z_Rank'] * reversal_weights.get('ADX_Z', 10.0) / total_weight)
)

# 3. Scale to 1-10
if num_eligible > 1:
    min_rank = eligible['Weighted_Avg_Rank'].min()
    max_rank = eligible['Weighted_Avg_Rank'].max()
    if max_rank > min_rank:
        eligible['Reversal_Score'] = 10 - ((eligible['Weighted_Avg_Rank'] - min_rank) / (max_rank - min_rank)) * 9
```

---

## Benefits of Unified Logic

✅ **Consistency** - Same methodology at sector and company levels
✅ **Fairness** - Relative ranking ensures no artificial clustering
✅ **Configurability** - User can adjust weights for both momentum and reversal
✅ **Interpretability** - Clear ranking order (1 = best in group)
✅ **Differentiation** - method='average' prevents score bunching
✅ **Transparency** - Weighted rank → 1-10 score is mathematically clear

---

## User Configuration (Sidebar)

Users can adjust in the sidebar:

**Momentum Weights (must sum to 100%):**
- RS_Rating Weight (%): 40 default
- ADX Z-Score Weight (%): 20 default
- RSI Weight (%): 30 default
- DI Spread Weight (%): 10 default

**Reversal Weights (must sum to 100%):**
- RS_Rating Weight (%): 40 default
- CMF Weight (%): 40 default
- RSI Weight (%): 10 default
- ADX Z-Score Weight (%): 10 default

**Reversal Filters:**
- RSI must be below: 40 default
- ADX Z-Score must be below: -0.5 default
- CMF must be above: 0.0 default

These weights apply **identically** to both sector and company analysis tabs.
