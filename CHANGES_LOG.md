# Changelog (version history)

This file records version and changes for deploy verification. The existing **CHANGES_SUMMARY.md** is unchanged.

---

## Version 2.1.0 (Feb 2026)

- **Visible version:** App version `2.1.0` is shown on the main page (below the sub-header) so you can confirm the deployed build.
- **Stock count on main page:** Stock Screener tab title now shows the actual number of stocks from the data source (e.g. "Stock Screener (97 Stocks)" or higher if `sector_company.csv` / `Sector-Company.xlsx` has more rows). No logic change; the app always used all rows from the data source.
- **No logic changes in this release:** Only display (version caption and dynamic stock count).

---

## Earlier changes (already in repo)

- **Historical Rankings** uses same scoring as Stock Screener for Bullish #1/#2 and Bearish #1/#2 (RSI direction 1W/1D/1H, price vs 8/20/50 SMA, VWAP 1H, RSI divergence 2H). Scoring caption added below the table.
- **Date dropdown** in Stock Screener: dates in descending order (today/latest first).
- **Data Sources tab:** Sector–company table built from `SECTOR_COMPANIES` (no import of `get_sector_company_table`).
- **Sector-company data:** Single source `sector_company.csv` (or `Sector-Company.xlsx`); removed unused `sector_companies_20260204.csv` and `sector_companies_cleaned.csv`.
- **Historical cache:** `data_cache/historical_rankings_cache_v2.csv` (screener-based scoring).
- **Nifty display:** Uses ^NSEI for header and Market breadth tab; RSI integers in Stock Screener; percentage formatting one decimal.
