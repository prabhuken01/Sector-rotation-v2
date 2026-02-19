## Confluence Logic – Version 2.3.5

This document summarizes the **core logic** used for confluence scoring and sector selection in v2.3.5 (and v2.3.1–2.3.4).

---

### Confluence flow (confluence_2_3_1) — step-by-step

Use this flow to verify behaviour when debugging or changing code.

1. **Pivot points (HH/HL/LH/LL source)**  
   - Implemented in `confluence_fixed.py`: `_pivot_highs_lows()` and `detect_swing_structure()`.  
   - **Aligned with TradingView:** Same logic as Pine script *Pivot Points High Low*: `ta.pivothigh(10, 10)` and `ta.pivotlow(10, 10)`.  
   - **Parameters:** `left=10`, `right=10` (not 3/3). A bar is a **pivot high** if its High is the unique maximum in the window `[i-10 … i+10]`; **pivot low** if its Low is the unique minimum in that window.  
   - **Window:** Last 100 bars of entry TF and last 100 bars of 1D are used for pivot detection (`pivot_window` / `pivot_window_d`).

2. **Swing structure (trend label)**  
   - From the list of pivot highs (ph) and pivot lows (pl):  
     - Count **HH** = consecutive pivot highs where each high > previous; **LH** = each high < previous.  
     - Count **HL** = consecutive pivot lows where each low > previous; **LL** = each low < previous.  
   - **Trend:**  
     - `Uptrend (HH/HL)` if ≥55% of pivot-high pairs are HH and ≥55% of pivot-low pairs are HL.  
     - `Downtrend (LL/LH)` if ≥55% are LL and LH.  
     - Else `Sideways`.  
   - **Outputs:** `last_hl_price` = most recent pivot low (HL candidate); `last_lh_price` = most recent pivot high (LH candidate).

3. **Price position (vs pivots)**  
   - **Near HL:** Current price within 3% of `last_hl_price` → ideal **bullish** entry (buy at support).  
   - **Near LH:** Current price within 3% of `last_lh_price` → at resistance / **at HH** → ideal **bearish** entry; **not** ideal for bullish.  
   - **Middle:** Neither.  
   - If within 3% of both, choose the closer pivot.

4. **Bullish gates (all must pass)**  
   - RSI rising on confirmation TF; and on entry TF when entry ≠ 4H.  
   - MA alignment Bullish on **both** entry and confirmation TFs.  
   - Entry TF trend = **Uptrend (HH/HL)** (when entry ≠ 1H; 1H trend not used).  
   - **Price must NOT be at LH/HH:** If `price_position == "Near LH"` → **fail** (score -5). So stocks at HH are never picked as Confluence Bullish.  
   - (Price near HL is not required to pass the gate; it only adds +3 in scoring.)

5. **Bullish scoring (after gates)**  
   - Trend Uptrend (HH/HL): +4. MA entry: +3, MA conf: +2.  
   - Near HL: +3; Near LH: −1 (but Near LH already failed gate); Middle: +0.5.  
   - RSI entry (when used): rising 40–70 +2, rising else +1, falling −1; RSI > 70 −1; RSI < 30 rising +0.5.  
   - RSI conf: rising 40–70 +1.5, rising else +0.5, falling −0.5; RSI > 70 −0.5.  
   - MA crossover, divergence, volume as in §2.2 below.

6. **Bearish**  
   - Same pivot/swing logic. Gates require RSI falling, MA Bearish, trend Downtrend (LL/LH) when applicable.  
   - Ideal entry: **Near LH** (short at resistance). Price at **Near HL** = “TOO LATE” for short (at support).

---

### 0. Sector–company mapping (Stock Screener & Confluence)

- **Primary source:** `Sector-Company.xlsx` (sheet **Main**). Path is configurable; app loads it at startup and shows the path in the UI. Use **Sector Companies** tab → **Reload from Excel** after editing the file.
- **Fallback:** If the Excel file is missing or fails to load, the app uses the static mapping in `company_symbols.py`. In the fallback:
  - **Energy** contains only energy/oil & gas names (e.g. Reliance, NTPC, Power Grid, ONGC, GAIL, Indian Oil, Petronet). Manappuram Finance and Bharat Electronics are **not** under Energy.
  - **Manappuram Finance** (`MANAPPURAM.NS`) is under **Fin Services** (NBFC).
  - **Bharat Electronics** (`BEL.NS`) is under **Defence**.

### 1. Sector universe for Confluence (Stock Screener & Historical Rankings)

1. **Momentum Ranking source**
   - Sector momentum comes from the **Momentum tab** (`Momentum_Score`), using the same weights and mode as the sidebar:
     - **Trending mode**: `Momentum_Score` is based on cross‑sectional **Z(RSI) + Z(CMF)** (50/50).
     - **Historical / Mixed mode**: `Momentum_Score` is rank‑based on **ADX_Z, RS_Rating, RSI, DI_Spread (and CMF if weighted)**.

2. **Stock Screener (current day)**
   - When `df_momentum` is available (the main analysis result):
     - **Top 4 (bullish):** first 4 sectors by `Momentum_Score` (descending).
     - **Bottom 6 (bearish):** last 6 sectors by `Momentum_Score` (descending).
   - **Sector filter option:** **"Top 4 + Bottom 6 (per Momentum Ranking)"** or **"Universal (All Sectors)"**.
   - When **Top 4 + Bottom 6** is selected:
     - The **screener universe** is stocks from those 10 sectors (top 4 ∪ bottom 6).
     - **Top 10 Bullish** = top 10 by MA+RSI+VWAP score from **top 4 sectors only**.
     - **Top 10 Bearish** = bottom 10 by score from **bottom 6 sectors only** (same logic as Historical Rankings).
   - Confluence in the Screener tab uses the same top 4 (bullish) and bottom 6 (bearish) sector lists.
   - If `df_momentum` is not available, the Screener falls back to **RSI+CMF Z‑score** per sector to derive top 4 and bottom 6.
   - **Confluence fallback (v2.3.5):** If the Stock Screener returns **no rows** for the selected date (e.g. no data, all fetches failed), Part 3 Confluence builds its stock universe from **SECTOR_COMPANIES** using the same sector filter (Top 4 + Bottom 6 or Universal). So Confluence can still run and show Top 8 Bullish/Bearish; a caption notes *"Screener had no rows for this date; using sector–company universe for confluence."*

3. **Historical Rankings (per date)**
   - For **each date** in the 30‑day table:
     1. Build a per‑sector snapshot up to that date.
     2. Compute momentum using the **same mode as the sidebar**:
        - **Trending mode**: cross‑sectional Z‑scores of **RSI** and **CMF**, `Score = 0.5·Z(RSI) + 0.5·Z(CMF)`, higher is better.
        - **Historical / Mixed mode**: rank‑based weighted average of **ADX_Z, RS_Rating, RSI, DI_Spread (and CMF if weighted)**; lower weighted rank is better.
     3. Sort sectors by this `Score` to obtain:
        - `Momentum #1 Sector`, `Momentum #2 Sector` for that date.
        - **Top 4** and **Bottom 6** sectors for that date:
          - **Top 4 (bullish):** best 4 by `Score` for that date.
          - **Bottom 6 (bearish):** worst 6 by `Score` for that date.
   - The **Historical Confluence** filter uses these date‑specific Top 4 / Bottom 6 lists so that:
     - Bullish confluence only considers stocks from that date’s **Top 4** sectors.
     - Bearish confluence only considers stocks from that date’s **Bottom 6** sectors.

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
   - Pivots use **left=10, right=10** (Pine “Pivot Points High Low” default).

4. **Price must NOT be at LH/HH (resistance)**
   - If `price_position == "Near LH"` (price within ~3% of last pivot high) → **fail**. Stocks at HH are not ideal for bullish entry and are excluded.

5. **Price near HL** is scoring-only (not a gate); some stocks pass without it.

If **any** of the above gates fail, the function returns:

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
Only stocks satisfying the **core gates** (RSI up where required, MA Bullish on both, Uptrend HH/HL, and price **not** at Near LH/HH) can receive a positive confluence score.

---

### Changelog

**v2.3.9 (confluence_2_3_1 flow)**
- **Pivot lengths:** Pivot high/low detection now uses **left=10, right=10** to match TradingView Pine script “Pivot Points High Low” (`ta.pivothigh(10,10)`, `ta.pivotlow(10,10)`). Previously 3/3, which produced noisier pivots and could misclassify HH/HL.
- **Bullish gate:** If **price position = Near LH** (price within 3% of last pivot high = at HH/resistance), the setup **fails** (score -5). Confluence Bullish no longer picks stocks that are at HH on the chart.
- **Flow doc:** Added “Confluence flow (confluence_2_3_1)” section above for step-by-step verification.

**v2.3.5**
- Version set to **2.3.5**.
- **Confluence when screener has no rows:** If the Stock Screener returns zero rows for the selected date, Part 3 Confluence builds `df_stocks` from **SECTOR_COMPANIES** (Top 4 + Bottom 6 or Universal) so confluence analysis still runs and Top 8 Bullish/Bearish can show. A caption indicates when this fallback is used.
- **Market breadth tab:** When the sector–company universe has more than 80 symbols, the breadth tab uses **Nifty 50** for the fetch so the table reliably returns Advance/Total % and % above 10 DMA (avoids timeout / empty data on large universes or Cloud).
- **Historical Rankings confluence:** When 4H or 2H is selected but hourly data is missing or too thin for a symbol/date, confluence falls back to **1D** for that row so the Confluence Bear #1/#2 (and Bull) columns still show results instead of mostly None.

**v2.3.2**
- Version set to **2.3.2**.
- **Confluence section (Part 3)** already uses **top 4 sectors for bullish** and **bottom 6 sectors for bearish**: only stocks in `top_conf_sectors` are appended to Top 8 Bullish, and only stocks in `bot_conf_sectors` to Top 8 Bearish (with gate filter score > -5). No code change needed there.
- **Stock Screener MA+RSI+VWAP tables:** **Top 10 Bullish** = top 10 by score from **top 4 sectors** only; **Top 10 Bearish** = bottom 10 from **bottom 6 sectors** only (in sync with Confluence and Historical Rankings).

**v2.3.1**
- **Sector–company mapping:** Primary source is **Sector-Company.xlsx**. Static fallback in `company_symbols.py` corrected: **Energy** no longer contains Manappuram Finance or Bharat Electronics; Manappuram is in **Fin Services**, BEL in **Defence**. Energy fallback uses only energy/oil & gas names (e.g. Reliance, NTPC, Power Grid, ONGC, GAIL, IOC, Petronet).
- **Confluence & Historical Rankings:** Sector options are **"Top 4 + Bottom 6 (per Momentum Ranking)"** and **"Universal (All Sectors)"**; no separate "top 4 only" / "bottom 4 only" radios. Bottom count is **6** (bearish), not 4.

