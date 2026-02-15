# Confluence Analysis – Where Everything Lives

Single reference so you don’t have to search the repo for confluence-related code.

---

## 1. Confluence options (1D+2H vs 4H+1H)

- **Part 3 (live Confluence Analysis):** `streamlit_app.py`  
  - Radio: `["1D + 2H (default)", "4H + 1H"]`  
  - Search: `conf_tf = st.radio` or `"1D + 2H (default)"`  
  - Default = first option (1D+2H). Code uses `conf_tf_code = '2h'` or `'4h'`.

- **Historical Rankings:** same options, same file  
  - Search: `hist_conf_tf = st.radio` or `"1D + 2H (default)"`  
  - Cache key includes timeframe: `historical_rankings_cache_v9_2h.csv` / `_v9_4h.csv`.

---

## 2. Confluence scoring table (V2 / confluence_summary_v2)

- **Location:** `streamlit_app.py`, Part 3 section  
  - Search: `How Confluence Scoring works` or `entry_tf_short` or `10 factors`.

- **Content:** 10 factors, max ~20 pts, including:
  - Trend (entry TF + 1D), MA Align (entry + 1D), **Price Position**, RSI (entry + 1D), MA Crossover, RSI Divergence, **Volume**.
  - Text: “**≥ 12** = excellent, **≥ 9** = good/strong, **5–9** = moderate, **< 5** = weak/avoid.”

---

## 3. Confluence logic (scoring implementation)

- **File:** `confluence_fixed.py`  
- **Functions:**  
  - `analyze_stock_confluence(..., entry_timeframe='2h'|'4h'|'1d')`  
  - `calculate_confluence_score_bullish(analysis_data)`  
  - `calculate_confluence_score_bearish(analysis_data)`  
  - `generate_entry_description(...)`  
- **Entry timeframes:** `'2h'` (1H data resampled to 2H), `'4h'` (1H resampled to 4H), `'1d'` (daily as entry).

---

## 4. Historical Rankings – Confluence

- **Dates:** Last **15** trading days (was 10). Search: `lookback_days = min(15, ...)`.
- **Confluence columns:** Advance/Total %, Stocks % above 10 DMA, Conf Bull/Bear #1/#2, **CMP** (no decimal), **Score** (integer), 1D/2D/3D % (one decimal).
- **Formatting:** In `streamlit_app.py`, search: `cmp_cols_b` or `pct_cols_b` or `fmt = {c: '{:.0f}'`.

---

## 5. Streamlit deployment

- Live app: https://sector-rotation-v2.streamlit.app/
- It deploys from the **main** branch. To see latest confluence (V2 + 1D+2H/4H+1H), ensure these changes are merged/pushed to **main**.

---

*Last updated: Feb 2025 – confluence_summary_v2, 1D+2H / 4H+1H, 15-day historical, CMP/return formatting.*
