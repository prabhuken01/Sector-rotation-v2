## Confluence Logic – Version 2.3.1

This document summarizes the **core logic** used for confluence scoring and sector selection in v2.3.1.

### 1. Sector universe for Confluence (Stock Screener & Historical Rankings)

1. **Momentum Ranking source**
   - Sector momentum comes from the **Momentum tab** (`Momentum_Score`), using the same weights and mode as the sidebar:
     - **Trending mode**: `Momentum_Score` is based on cross‑sectional **Z(RSI) + Z(CMF)** (50/50).
     - **Historical / Mixed mode**: `Momentum_Score` is rank‑based on **ADX_Z, RS_Rating, RSI, DI_Spread (and CMF if weighted)**.

2. **Stock Screener (current day)**
   - When `df_momentum` is available (the main analysis result):
     - **Top 4 Bullish**: first 4 sectors by `Momentum_Score` (descending).
     - **Bottom 4 Bearish**: last 4 sectors by `Momentum_Score` (descending).
   - These lists drive:
     - The **Screener sector universe** (which sectors to scan).
     - The **Confluence sector universe** in the Screener tab.
   - If `df_momentum` is not available, the Screener falls back to **RSI+CMF Z‑score** per sector.

3. **Historical Rankings (per date)**
   - For **each date** in the 30‑day table:
     1. Build a per‑sector snapshot up to that date.
     2. Compute momentum using the **same mode as the sidebar**:
        - **Trending mode**: cross‑sectional Z‑scores of **RSI** and **CMF**, `Score = 0.5·Z(RSI) + 0.5·Z(CMF)`, higher is better.
        - **Historical / Mixed mode**: rank‑based weighted average of **ADX_Z, RS_Rating, RSI, DI_Spread (and CMF if weighted)**; lower weighted rank is better.
     3. Sort sectors by this `Score` to obtain:
        - `Momentum #1 Sector`, `Momentum #2 Sector` for that date.
        - **Top 4** and **Bottom 4** sectors for that date:
          - **Top 4 Bullish sectors**: best 4 by `Score` for that date.
          - **Bottom 4 Bearish sectors**: worst 4 by `Score` for that date.
   - The **Historical Confluence** filter uses these date‑specific Top 4 / Bottom 4 lists so that:
     - Bullish confluence only considers stocks from that date’s Top 4 sectors (when Top 4 filter is selected).
     - Bearish confluence only considers stocks from that date’s Bottom 4 sectors (when Bottom 4 filter is selected).

### 2. Bullish Confluence Scoring (v2.3.1)

The function `calculate_confluence_score_bullish(analysis)` now enforces **hard gates** before detailed scoring:

#### 2.1. Core gates (must all be satisfied)

For a bullish setup to be considered valid:

1. **RSI direction (both timeframes)**
   - Entry timeframe RSI: `rsi_entry > rsi_entry_prev + 0.5` → **rising**.
   - Confirmation timeframe RSI: `rsi_1d > rsi_1d_prev + 0.5` → **rising**.

2. **MA alignment (both timeframes)**
   - Entry MA alignment: `ma_alignment_entry == "Bullish"`.
   - Confirmation MA alignment: `ma_alignment_1d == "Bullish"`.

3. **Trend on higher timeframe (entry TF)**
   - Entry‑timeframe trend from `detect_swing_structure` must be:
     - `trend_entry == "Uptrend (HH/HL)"`.
   - This requires a consistent HH/HL pattern in the pivot structure.

4. **Recent pivot = Higher Low (HL) and price near HL**
   - From the same pivot structure:
     - `price_position == "Near HL"` (price within ~3% of last HL pivot).

If **any** of the above fail, the function returns:

```text
score  = -5.0
reasons = ["-5  Core bullish conditions failed: ..."]
```

These setups are treated as **failed bullish confluences** and will not rank in the top bullish list.

#### 2.2. Detailed scoring (only if gates pass)

For setups passing all gates, additional points are added as follows:

1. **Trend (entry TF)**  
   - `+4` for `Uptrend (HH/HL)` (already ensured by gate, acts as base credit).

2. **MA alignment**
   - `+3` for Bullish on entry TF.  
   - `+2` for Bullish on confirmation TF.

3. **Price position vs pivots**
   - `+3` if `price_position == "Near HL"` (ideal buy zone at HL support).  
   - `−1` if `price_position == "Near LH"` (near resistance).  
   - `+0.5` otherwise (“Middle” range).

4. **RSI (entry TF)**
   - `+2` if RSI is rising and in the **40–70** zone.  
   - `+1` if RSI is rising outside 40–70.  
   - `−1` if RSI is falling.  
   - Additional adjustments:
     - `−1` if RSI > 70 (overbought).  
     - `+0.5` if RSI < 30 but turning up (oversold bounce).

5. **RSI (confirmation TF)**
   - `+1.5` if RSI rising and within 40–70.  
   - `+0.5` if RSI rising but outside 40–70.  
   - `−0.5` if RSI falling.  
   - `−0.5` if RSI > 70 (overbought).

6. **MA crossover (entry TF)**
   - `+1.5` for a **Bullish Crossover** (DMA20 > DMA50 within ~1.5% band).  
   - `−1` for a **Bearish Crossover**.

7. **RSI divergence**
   - `+1.5` for Bullish divergence (price making lower lows, RSI making higher lows).  
   - `−1` for Bearish divergence.

8. **Volume**
   - `+1` if recent volume is significantly above the recent average (`volume_status == "High"`).

The final score is rounded to 2 decimals and used to rank bullish confluence candidates.  
Only stocks satisfying the **core gates** (RSI up on both TFs, MA Bullish on both, Uptrend HH/HL with price near HL) can receive a positive confluence score.

