# NSE Sector Rotation App — Logic Guide (v2.4.9)

> **Purpose:** This document explains the complete pipeline of how sectors are identified, how stocks are selected, what filtering and rejection criteria apply, and how the two main tabs (Stock Screener and Historical Rankings) work — including their similarities and differences.

---

## 1. App Overview

The app has five tabs:

| Tab | Purpose |
|-----|---------|
| 📊 Momentum | Sector-level momentum ranking (RSI, ADX, CMF, RS-Rating, DI-Spread) |
| 📅 Historical Rankings | Date-wise table of top bullish + bearish stock picks for the last 30 days |
| 🔍 Stock Screener | Current-date stock scoring for the selected analysis date |
| 🔀 Confluence_Future | Enable/disable confluence analysis + entry strategy guide |
| 🔌 Data Sources | Data fetch status per sector ETF/index |

---

## 2. Sector Identification Pipeline

Both the Stock Screener and Historical Rankings use the **same Momentum Ranking** to identify which sectors are bullish/bearish. The ranking is computed from live sector data.

### 2A. Sector Momentum Scoring

For each sector (ETF or index), the following indicators are computed from daily OHLCV data:

| Indicator | Metric | Weight (sidebar-configurable) |
|-----------|--------|-------------------------------|
| RSI (14-period) | 14-day RSI of sector | Configurable (default 30%) |
| ADX Z-score | Z-score of 14-day ADX | Configurable |
| CMF (Chaikin Money Flow) | 20-day CMF | Configurable |
| RS Rating | Sector return vs Nifty 50 over lookback | Configurable |
| DI Spread | (+DI − −DI) from ADX calculation | Configurable |

**Composite score** = weighted average rank across the above (each indicator ranked 1–N across sectors).

> Lower composite score = stronger sector (rank 1 = best).

### 2B. Sector Selection

| Direction | Rule |
|-----------|------|
| **Bullish** | Top N sectors by Momentum Ranking (N = slider in "Bullish gate" sidebar, default 1) |
| **Bearish** | Bottom N sectors by Momentum Ranking (N = slider in "Bearish gate" sidebar, default 2) |

The **N sliders** are located in the sidebar under:
- *Bullish MA+RSI+VWAP gate* → "Top N bullish sectors (Momentum Ranking)" (range: 1–4)
- *Bearish MA+RSI+VWAP gate* → "Bottom N bearish sectors (Momentum Ranking)" (range: 1–6)

> **Historical Rankings** computes this per date (point-in-time momentum scores for each historical date).
> **Stock Screener** computes this for the selected analysis date only.

---

## 3. Stock Selection Within Sectors

After sectors are identified, all stocks belonging to those sectors (from `Sector-Company.xlsx`) are scored.

### 3A. Scoring System (MA+RSI+VWAP)

Each stock receives a **Bullish Score** and a **Bearish Score** on a 0–7.5 scale:

| Criterion | Bullish points | Bearish points |
|-----------|---------------|----------------|
| RSI(1W) trending Up | +1 | +1 if NOT Up |
| RSI(1D) trending Up | +1 | +1 if NOT Up |
| RSI(1H) trending Up | +1 | +1 if NOT Up |
| Price > MA8 (daily) | +1 | +1 if NOT above |
| Price > MA20 (daily) | +1 | +1 if NOT above |
| Price > MA50 (daily) | +1 | +1 if NOT above |
| Price vs VWAP (1H) — Above | +1.0 | 0 |
| Price vs VWAP (1H) — Approaching | +0.5 | +0.5 |
| Price vs VWAP (1H) — Below | 0 | +1.0 |

- **Bullish Score** = sum of bullish criteria met (max ≈ 7.5). Higher = stronger bullish setup.
- **Bearish Score** = sum of bearish criteria met (max ≈ 7.5). Higher = stronger bearish setup.

RSI direction (Up/Down/Neutral) is determined from the slope of the last 3 RSI values.

VWAP weights (0.5/1.0 split above) are adjustable via the "Scoring weights" expander in the Stock Screener.

---

### 3B. Rejection Criteria

These filters are applied **before** final ranking and are **not toggleable** (always active):

| Filter | Applied to | Condition |
|--------|-----------|-----------|
| RSI(1D) overbought | Bullish candidates | Excluded if RSI(1D) > 75 *(sidebar checkbox, default OFF)* |
| RSI(1H) overbought | Bullish candidates | Excluded if RSI(1H) > 75 *(sidebar checkbox, default OFF)* |
| RSI(1D) oversold | Bearish candidates | Excluded if RSI(1D) < 30 *(hardcoded, always active)* |

> Note: The RSI overbought exclusion checkboxes (Bullish gate sidebar) are *off by default in v2.4.8+*. Turn them on to apply stricter filtering.

---

### 3C. Gate Filters (Sidebar-Controlled)

These are **optional** filters applied **after** the base scoring, gated by sidebar toggles:

| Filter | Bullish condition | Bearish condition | Toggle location |
|--------|-------------------|-------------------|-----------------|
| Sector gate | Stock's sector in top N bullish sectors | Stock's sector in bottom N bearish sectors | Gate enabled checkbox |
| Price > MA8(1H) | Required | — | "Price above MA8(1H)" checkbox |
| Price < MA8(1H) | — | Required | "Price below MA8(1H)" checkbox |
| Price > VWAP(1H) | Required | — | "Price above VWAP(1H)" checkbox |
| Price < or ≈ VWAP(1H) | — | Required ("Below" or "Approaching ↓") | "Price below VWAP(1H)" checkbox |
| RSI(1H) ≥ threshold | Required (when use_rsi ON) | — | "Apply RSI(1H) min threshold" + slider |
| RSI(1H) ≤ threshold | — | Required (when use_rsi ON) | "Apply RSI(1H) max threshold" + slider |

**Default state (v2.4.8+):**
- Both Bullish and Bearish master gates: **ON**
- Sector gate: **active** (uses N from slider)
- All sub-filters (MA8, VWAP, RSI threshold): **OFF**

---

## 4. Data Sources & Timeframes

| Data | Timeframe | Used for |
|------|-----------|---------|
| Sector OHLCV | Daily (1D), 1 year | Momentum Ranking, RSI 1W, RSI 1D, SMA8/20/50, forward returns |
| Company OHLCV | Daily (1D), 1 year | RSI 1W, RSI 1D, Price vs SMA |
| Company intraday | Hourly (1H), last 60 days | RSI 1H, VWAP, MA8(1H) |
| Nifty 50 stocks | Daily (1D) | Market breadth (Advance/Total %, above 10 DMA %) |

**1H Snapshot time** (selectable in Stock Screener):
- `2:15 PM IST (pre-close)` — default; captures the full-day RSI/VWAP picture
- `10:15 AM IST (post-open)` — captures early-day momentum

**Data fetch hierarchy:**
1. Local SQLite cache (last 6 months of daily data)
2. In-memory cache (5-minute TTL)
3. yfinance live fetch (fallback)

---

## 5. Stock Screener Tab — Detailed Flow

```
User selects analysis date (last 30 trading days)
    ↓
Sector Momentum Ranking computed for that date
    ↓
Top N bullish sectors / Bottom N bearish sectors identified
    ↓
Universe = all stocks from selected sectors (Sector-Company.xlsx)
    ↓
For each stock:
    1. Fetch daily data (full 1-year history, no end-date cap)
    2. Strip timezone; locate analysis date index via searchsorted
    3. Slice daily data to analysis date (for indicators)
    4. Fetch 1H data (end_date = analysis date)
    5. Slice 1H data to selected snapshot time
    6. Compute MA8/20/50, RSI(1W/1D/1H), VWAP(1H)
    7. Compute Bullish Score + Bearish Score
    8. Compute forward returns: 1D%, 2D%, 3D%, 1W% (from full daily data beyond analysis date)
    ↓
Apply rejection filters (RSI overbought/oversold)
Apply gate filters (MA8/VWAP/RSI threshold — if enabled)
    ↓
Sort by Bullish Score (descending) → Top 10 Bullish
Sort by Bearish Score (descending) → Top 10 Bearish
    ↓
Display tables with 1D%/2D%/3D%/1W% forward return columns
```

**Forward return columns:**
- `1D%` = (Close[T+1] / Close[T] − 1) × 100
- `2D%` = (Close[T+2] / Close[T] − 1) × 100
- `3D%` = (Close[T+3] / Close[T] − 1) × 100
- `1W%` = (Close[T+5] / Close[T] − 1) × 100

Blank (`—`) if future bars are not yet available (e.g., analysis date is within last 5 trading days).

---

## 6. Historical Rankings Tab — Detailed Flow

```
For each of the last 30 trading dates (point-in-time):
    ↓
    1. Compute Nifty 50 market breadth:
       - Advance/Total % (stocks advancing vs declining)
       - Stocks % above 10 DMA
    ↓
    2. Compute sector momentum scores for THIS date (using data up to that date only)
       → Identify top N bullish sectors + bottom N bearish sectors
    ↓
    3. Fetch 1H company data (end_date = this date)
       Slice to snapshot time (synced from Stock Screener setting)
    ↓
    4. Score all companies using _compute_screener_score(daily_up_to_date, hourly)
       → Bullish Score + Bearish Score + score_details (RSI values, VWAP)
    ↓
    5. Apply rejection + gate filters (same as Stock Screener)
       → Sector filter: per-DATE top N / bottom N sectors
    ↓
    6. Pick top 2 bullish + top 2 bearish stocks
    ↓
    7. Compute forward returns (1D/2D/3D/1W) from daily data beyond that date
    ↓
    Append one row to date-wise table
    ↓
Display table: Date | Breadth | Momentum#1 | Bullish#1/#2 + returns | Bearish#1/#2 + returns
```

---

## 7. Comparison: Stock Screener vs Historical Rankings

| Aspect | Stock Screener | Historical Rankings |
|--------|---------------|---------------------|
| Dates covered | 1 selected date (past 30 days) | All 30 trading days simultaneously |
| Sector selection | Current Momentum Ranking for selected date | **Per-date** Momentum Ranking (point-in-time) |
| N sectors | From gate slider | Same gate slider (synced via `mrvg_options`) |
| Scoring function | `_compute_screener_score()` | Same `_compute_screener_score()` |
| 1H data | Fetched with `end_date=analysis_date` | Fetched with `end_date=each_date` |
| Daily data | Full history (no end cap) — tz-stripped for date lookup | Pre-fetched, get_indexer for point-in-time |
| Forward returns | 1D/2D/3D/1W per stock (10 shown) | 1D/2D/3D/1W for top 2 picks only |
| Output format | Top 10 bull + Top 10 bear (flat list) | 1 row per date (date-wise summary) |
| Win rate | Not applicable | Computed over all 30 dates (1W-available rows only) |
| Composite win rate | Not applicable | Green-day bullish + Red-day bearish (1W horizon) |

---

## 8. Win Rate Calculation (Historical Rankings)

**Definition:** Percentage of days where the top pick achieved the return threshold.

| Win rate type | Denominator | Numerator |
|--------------|------------|-----------|
| Bullish (all days) | Dates with 1W return available | Dates where Bullish #1 Next 1W% ≥ threshold |
| Bullish (green days) | Green days with 1W return available | Green days where Bullish #1 Next 1W% ≥ threshold |
| Bearish (all days) | Dates with 1W return available | Dates where Bearish #1 Next 1W% ≤ −threshold |
| Bearish (red days) | Red days with 1W return available | Red days where Bearish #1 Next 1W% ≤ −threshold |
| **Composite** | Green days (1W available) + Red days (1W available) | Green day bull wins + Red day bear wins |

**Green day** = Advance/Total % > 50% AND Stocks above 10 DMA > 50%

**Red day** = Advance/Total % < 50% AND Stocks above 10 DMA < 50%

**1W return available** = analysis date is more than 5 trading days in the past (last 5 days have no 1W data yet).

**Thresholds tested:** ≥1.0%, ≥1.5%, ≥2.0% (for bullish); ≤−1.0%, ≤−1.5%, ≤−2.0% (for bearish).

---

## 9. Confluence Analysis (when enabled)

Confluence Analysis is enabled/disabled from the **Confluence_Future** tab.

When enabled, it appears in:
- **Historical Rankings** — additional columns in the date-wise table showing confluence-filtered picks
- **Stock Screener (PART 3)** — separate section below the MA+RSI+VWAP results

**Confluence scoring** uses a separate `_compute_confluence_score()` function that evaluates:
- Trend structure (HH/HL for bullish; LL/LH for bearish)
- RSI alignment across timeframes
- MA alignment across timeframes
- Gate options (sidebar Confluence gates v3.1)

**Timeframes:**
- `1D + 2H` — uses daily chart as higher timeframe, 2-hour as entry timeframe
- `4H + 1H (default)` — uses 4-hour as higher timeframe, 1-hour as entry timeframe

Stocks below the gate-fail score threshold are shown in the "Rejected" section.

---

## 10. Sidebar Gate Reference

| Control | Location | Effect |
|---------|----------|--------|
| Enable Bullish gate | Bullish MA+RSI+VWAP expander | Master switch for ALL bullish gate logic |
| Top N bullish sectors | Bullish expander (1st item) | How many top Momentum sectors qualify for bullish picks |
| Price above MA8(1H) | Bullish expander | Exclude stocks where price is below 8-bar SMA on 1H chart |
| Price above VWAP(1H) | Bullish expander | Exclude stocks where price is below VWAP on 1H chart |
| Apply RSI(1H) min | Bullish expander | Enable RSI(1H) ≥ threshold filter |
| RSI(1H) ≥ (min) slider | Bullish expander | Threshold value (30–80, default 50) |
| Exclude RSI(1D) > 75 | Bullish expander | Remove overbought stocks (RSI 1D) |
| Exclude RSI(1H) > 75 | Bullish expander | Remove overbought stocks (RSI 1H) |
| Enable Bearish gate | Bearish MA+RSI+VWAP expander | Master switch for ALL bearish gate logic |
| Bottom N bearish sectors | Bearish expander (1st item) | How many bottom Momentum sectors qualify for bearish picks |
| Price below MA8(1H) | Bearish expander | Exclude stocks where price is above 8-bar SMA on 1H chart |
| Price below VWAP(1H) | Bearish expander | Exclude stocks where price is above VWAP on 1H chart |
| Apply RSI(1H) max | Bearish expander | Enable RSI(1H) ≤ threshold filter |
| RSI(1H) ≤ (max) slider | Bearish expander | Threshold value (20–70, default 50) |

---

*Document version: v2.4.9 — generated 2026-02-22*
