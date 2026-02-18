# Tab-by-Tab Code Nuances (Streamlit App)

This file documents implementation details and code-change rules for each main tab so future edits do not break behaviour.

---

## 1. Momentum Ranking (Tab 1)

- **Function**: `display_momentum_tab()` (streamlit_app.py).
- **Sort order**: Sort by `Momentum_Score` **before** formatting numeric columns to strings; otherwise display order will not match score order.
- **Columns**: `Sector`, `Symbol`, `Price`, `Change_%`, `Momentum_Score`, `Mansfield_RS`, `RS_Rating`, `ADX`, `ADX_Z`, `RSI`, `DI_Spread`, `CMF`. Do not drop `Momentum_Score` before sorting.
- **Color coding**: Applied per row for Mansfield_RS and CMF (green positive, red negative). Format decimals **after** sorting so styling uses correct values.

---

## 2. Market breadth (Tab 2)

- **Function**: `display_market_breadth_tab()` (streamlit_app.py).
- **Universe**: Uses full universe from `SECTOR_COMPANIES` (Excel / Sector-Company.xlsx); fallback to Nifty 50 only when that list is empty. Do **not** cap the universe at 80 stocks (e.g. do not force Nifty 50 when `len(universe_symbols) > 80`); the table is designed for 130+ stocks from the sheet.
- **Include current date (T) always**: The 20-day table must always include the current/latest trading day (T). Build dates with `t_date = pd.Timestamp(benchmark_data.index[-1]).normalize().date()` and `pd.bdate_range(end=t_date, periods=20, freq='B')`. After reversing, if the last element of `dates_20` is not `t_date`, replace it: `if dates_20[-1].date() != t_date: dates_20 = dates_20[:-1] + [pd.Timestamp(t_date)]`.
- **Date/index matching**: Stock and Nifty series indices may be timezone-aware or have different types than `pd.bdate_range` dates. To avoid advances/declines and Nifty columns staying 0 or None:
  - Normalize series index: `series_dates = series.index.tz_localize(None).normalize() if series.index.tz is not None else series.index.normalize()`.
  - Use `date_ts = pd.Timestamp(date_t).normalize()` and `series_dates.get_indexer([date_ts], method='ffill')[0]`. Same idea for `nifty_index_data`: normalize its index and use `pd.Timestamp(date_t).normalize()` in `get_indexer`. Do **not** pass raw `date_t` (e.g. from `bdate_range().tolist()`) into `get_indexer` without converting to `pd.Timestamp` and normalizing, or matches can fail and all rows show zeros.
- **Min bars**: Only include a stock in `nifty_closes` if it has at least `_min_bars_breadth` (25) rows.
- **Display**: Table sorted by date descending so newest (T) is at top; last row in the source list is labelled "(Current day)".

---

## 3. Stock Screener (Tab 3)

- **Function**: `display_stock_screener_tab()` (streamlit_app.py).
- **Initialization**: At the start of the function, initialize `historical_logs`, `fib_results`, `stock_results`, `df_results`, `df_top10`, and `total_market_stocks` (e.g. to `[]`, `[]`, `[]`, empty DataFrame, empty DataFrame, `0`) so that later Excel export and other branches never see `NameError` if an earlier path is skipped.
- **Excel export**: When writing the workbook, ensure at least one sheet is visible. If no data-driven sheets are written (e.g. no results), write a default "Summary" (or similar) sheet with a short message so openpyxl does not raise `IndexError: At least one sheet must be visible`.
- **Confluence**: Logic must stay in sync with Historical Rankings’ Confluence Bullish (same gates and scoring for a given date). See also CONFLUENCE_* docs.

---

## 4. Reversal Candidates (Tab 4)

- **Function**: `display_reversal_tab()` (streamlit_app.py).
- **Weights/thresholds**: Uses `reversal_weights` and `reversal_thresholds` from sidebar; ensure these are passed from `main()` and not hardcoded in the tab.

---

## 5. Interpretation Guide (Tab 5)

- **Function**: `display_interpretation_tab()` (streamlit_app.py).
- **Content**: Static/markdown; no data-dependent logic. Safe to change copy or structure without touching other tabs.

---

## 6. Company Momentum (Tab 6)

- **Function**: Rendered under the same tab structure; company-level momentum from same sector/company data. Keep column set and sort logic consistent with main Momentum Ranking where they are intended to align.

---

## 7. Company Reversals (Tab 7)

- **Function**: Company-level reversal view; should use same reversal definitions and weights as Reversal Candidates tab.

---

## 8. Historical Rankings (Tab 8)

- **Function**: `display_historical_rankings_tab()` (streamlit_app.py).
- **Confluence sync**: For a given date, Confluence Bullish #1 and #2 must match the Stock Screener’s logic (same universe, same gates, same timeframe rules). When entry timeframe is 2H/4H, skip stocks with insufficient hourly bars (e.g. min bars 40 for 2H, 80 for 4H) instead of falling back to 1D, so that Historical and Stock Screener agree.
- **Win-ratio table**: Bullish #1 and Bullish #2 win ratios (e.g. % achieving ≥1%, ≥1.5%, ≥2% in the next week) must be computed **separately** per pick, not combined or sampled.

---

## 9. Data Sources (Tab 9)

- **Function**: Describes data sources and any ETF vs index choice. No critical logic; document any new sources here when adding providers.

---

## General

- **Tabs order**: Main tabs are created in `main()` as: Momentum Ranking, Market breadth, Stock Screener, Reversal Candidates, Interpretation Guide, Company Momentum, Company Reversals, Historical Rankings, Data Sources. Changing order or names here affects navigation and any tab-index assumptions.
- **Benchmark data**: Market breadth and several tabs depend on `benchmark_data` (e.g. Nifty 50). Ensure `benchmark_data` has at least 22 trading days when calling `display_market_breadth_tab()`.
- **Version**: Bump `APP_VERSION` and any “App version” display when making user-facing behaviour or tab logic changes.
