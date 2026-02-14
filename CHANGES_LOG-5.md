# Changelog (version history)

This file records version and changes for deploy verification. The existing **CHANGES_SUMMARY-6.md** is unchanged.

---

## Version 2.3.0 (Feb 2026)

- **App version:** Set to `2.3.0` on main page.
- **Sector-company universe:** Project uses **Sector-company-v2.xlsx** content: 135 rows in `Sector-Company.xlsx` (sheet **Main**). **Single source: Excel only**; app loads sheet Main (or Sheet2 fallback). One symbol duplicated across sectors yields 134 unique symbols in app.
- **Dynamic stock count:** All references to a fixed "97-stock universe" removed. Market breadth caption, Stock Screener title, and Data Sources use the live count from `SECTOR_COMPANIES` (e.g. 134/135).
- **Momentum score – Trending mode:** When sidebar "Trending" is selected, sector momentum score is **50% Z(RSI) + 50% Z(CMF)** (cross-sectional Z-scores), scaled to 1–10. Applied in main Momentum Ranking (`analysis.py`) and in Historical Rankings secondary block (`streamlit_app.py`). Historical mode unchanged (rank-based, CMF = 0%).
- **Historical Rankings:** Caption added that the table includes the most recent dates (T, T-1) when available; Next 1D % / Next 2D % may be blank for those rows. Date logic unchanged (last 10 trading days including T and T-1).
- **Stock Screener Part 3 fix:** `df_stocks` NameError resolved by defining `df_stocks` from the screener results DataFrame with a `Company Name` column for Part 3 (Fibonacci) and confluence loops. No change to scoring or data logic.
- **Excel:** Single sheet **Main**; Grok_Sector and Sheet1 removed via `consolidate_sector_company_to_sheet2.py`. Option A: one folder for app + Excel (e.g. E: drive).
- **No other core logic changes:** Reversal, data fetch, cache, and remaining scoring logic unchanged.

---

## Version 2.1.0 (Feb 2026)

- **Visible version:** App version `2.1.0` is shown on the main page (below the sub-header) so you can confirm the deployed build.
- **Stock count on main page:** Stock Screener tab title now shows the actual number of stocks from the data source (e.g. "Stock Screener (97 Stocks)" or higher if `Sector-Company.xlsx` has more rows). No logic change; the app always used all rows from the data source.
- **No logic changes in this release:** Only display (version caption and dynamic stock count).

---

## Earlier changes (already in repo)

- **Historical Rankings** uses same scoring as Stock Screener for Bullish #1/#2 and Bearish #1/#2 (RSI direction 1W/1D/1H, price vs 8/20/50 SMA, VWAP 1H, RSI divergence 2H). Scoring caption added below the table.
- **Date dropdown** in Stock Screener: dates in descending order (today/latest first).
- **Data Sources tab:** Sector–company table built from `SECTOR_COMPANIES` (no import of `get_sector_company_table`).
- **Sector-company data:** Single source `Sector-Company.xlsx` sheet **Main**; run consolidate script to remove other sheets.
- **Historical cache:** `data_cache/historical_rankings_cache_v2.csv` (screener-based scoring).
- **Nifty display:** Uses ^NSEI for header and Market breadth tab; RSI integers in Stock Screener; percentage formatting one decimal.
