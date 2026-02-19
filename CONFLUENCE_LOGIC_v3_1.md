# Confluence Logic — Version 3.1

This document defines the **Confluence v3.1** logic: gates, filter for scoring, and per-factor weights. Pivot points follow the reference in **HH-HL.txt** (TradingView Pine script «Pivot Points High Low»).

---

## Pivot reference (HH-HL)

Pivot highs and lows are computed to match the **Pine script** in `HH-HL.txt`:

- **Pivot High:** `ta.pivothigh(leftLenH, rightLenH)` with default **left=10, right=10**. A bar is a pivot high if its High is the **unique maximum** in the window of 10 bars to the left and 10 bars to the right.
- **Pivot Low:** `ta.pivotlow(leftLenL, rightLenL)` with default **left=10, right=10**. A bar is a pivot low if its Low is the **unique minimum** in that same window.

In Python (`confluence_fixed.py`): `_pivot_highs_lows(data, left=10, right=10)` and `detect_swing_structure(..., left=10, right=10)`. Last 100 bars of the entry TF (and 1D) are used for pivot detection.

From pivot lists we derive **HH/HL/LH/LL** and trend: **Uptrend (HH/HL)**, **Downtrend (LL/LH)**, or **Sideways**. Price position: **Near HL** (within 3% of last pivot low), **Near LH** (within 3% of last pivot high), or **Middle**.

---

## (a) Gates (Phase-1 — must all pass)

Stocks that **fail any gate** get score **−5** and are **excluded** from Top 8 tables (and from scoring).

### Bullish gates

1. **RSI direction**  
   - When entry TF ≠ 4H: RSI must be **rising** on **both** entry and confirmation TFs (`rsi > rsi_prev + 0.5`).  
   - When entry TF = 4H: only confirmation TF RSI must be **rising**.

2. **MA alignment**  
   - **Both** entry and confirmation TFs: `ma_alignment == "Bullish"` (price > 20 DMA > 50 DMA).

3. **Trend (entry TF)**  
   - When entry TF ≠ 1H: `trend_entry == "Uptrend (HH/HL)"`.  
   - 1H trend is **not** used.

4. **Price must NOT be at LH/HH**  
   - `price_position != "Near LH"`. If price is within 3% of last pivot high (at resistance/HH), the setup **fails** and is not shown in Top 8 Bullish.

### Bearish gates

- No single “fail all” score; bearish uses the same pivot/trend logic.  
- Stocks with score **> −5** (above gate-fail threshold) are included in Top 8 Bearish.  
- Ideal: RSI falling, MA Bearish, Downtrend (LL/LH), Price **Near LH**. Price at **Near HL** is penalised (−2) and “TOO LATE” for short.

---

## (b) Filter for scoring

- **Universe:** Stocks from **Top 4 sectors (bullish)** and **Bottom 6 sectors (bearish)** per Momentum Ranking when “Top 4 + Bottom 6” is selected; or **Universal (All Sectors)**.
- **Included in tables:** Only stocks with **score > −5** (i.e. passed Phase-1 gates for that side).  
- **Ranking:** Sorted by **Score** (descending). Top 8 Bullish and Top 8 Bearish are shown.

---

## (c) Per-factor weights (what drives the score)

Each factor adds or subtracts points. The **reasons** list returned by `calculate_confluence_score_bullish` / `calculate_confluence_score_bearish` gives the exact breakdown per stock (e.g. "+4 Uptrend (HH/HL)", "+3 Price near HL", "−1 RSI FALLING"). Below is the nominal weight layout.

### Bullish (after gates)

| # | Factor | +Pts | −Pts | Note |
|---|--------|------|------|------|
| 1 | Trend (entry TF) | +4 Uptrend (HH/HL) | — | Not used when entry = 1H |
| 2 | MA entry | +3 Bullish | — | Gate |
| 3 | MA conf | +2 Bullish | — | Gate |
| 4 | Price position | +3 Near HL | −1 Near LH | Near LH already failed gate |
| 5 | Price middle | +0.5 | — | |
| 6 | RSI entry | +2 rising 40–70, +1 rising else | −1 falling, −1 if >70 | Not used when entry = 4H |
| 7 | RSI conf | +1.5 rising 40–70, +0.5 rising else | −0.5 falling, −0.5 if >70 | |
| 8 | MA crossover | +1.5 Bullish | −1 Bearish | |
| 9 | RSI divergence | +1.5 Bullish | −1 Bearish | |
| 10 | Volume | +1 High | — | |

**Max ≈ 20 pts.** Score **≥ 12** = excellent, **≥ 9** = good, **< 5** = weak. **≤ −5** = failed gates (excluded).

### Bearish

| # | Factor | +Pts | −Pts |
|---|--------|------|------|
| 1 | Trend entry | +4 LL/LH, +0.5 Sideways | −3 HH/HL |
| 2 | MA entry | +3 Bearish | −2 Bullish |
| 3 | MA conf | +2 Bearish | −1 Bullish |
| 4 | Price | +3 Near LH, +0.5 Middle | −2 Near HL |
| 5 | RSI entry (e.g. at LH) | +2.5 / +1.5 / +1 by zone | −1 rising, −1.5 oversold at LH |
| 6 | RSI conf | +1.5 / +0.5 falling | −0.5 rising, −0.5 oversold |
| 7 | MA crossover | +1.5 Bearish | −1 Bullish |
| 8 | Divergence | +1.5 Bearish | −1 Bullish |
| 9 | Volume | +1.5 at LH, +0.5 else | — |

Same threshold: score **> −5** to appear in Top 8 Bearish.

---

## Summary

- **Pivot:** 10/10 as in HH-HL.txt (Pine).  
- **Gates:** RSI direction, MA Bullish both TFs, Uptrend (HH/HL) when not 1H, and for bullish **not** at Near LH.  
- **Filter:** Score > −5 to be included; Top 4 + Bottom 6 or Universal.  
- **Score breakdown:** Shown per stock in the app (reasons list = per-weight contribution).
