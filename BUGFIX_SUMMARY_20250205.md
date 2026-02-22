# Bug Fix Summary (2026-02-05)

## Problem vs Fix Effectiveness

| # | Problem | Root Cause | Fix Applied | Effectively Addressed? |
|---|---------|------------|-------------|------------------------|
| 1 | Historical Rankings tab shows `NameError: hist_conf_sector_code is not defined` | `hist_conf_sector_code` was only set in an `if` block; alternate UI options (e.g. "Sector universe from Gates") bypass that block, so variable undefined before `cache_path` use | Define `hist_conf_sector_code` early, right after sector filter radio, so it's always set before `cache_path` | Yes |
| 2 | Stock Screener "Previous day" / "Next day" triggers `session_state cannot be modified after widget instantiated` | Button handlers updated the same session key used by the date widget after the widget ran | Use `on_click` callbacks that only update `_stock_screener_date_idx`; selectbox uses separate key `stock_screener_date_select`; no write to widget key after render | Yes |
| 3 | Market price in Stock Screener not based on chosen time (10:15 AM vs EOD) | Price/indicators used EOD or last bar; no time-of-day selection | Added "Price / indicators as of:" dropdown (9:15 AM, 10:15 AM, ..., 3:15 PM EOD); slice hourly to `<= end_dt`; use last hourly Close for price when non-EOD time selected | Yes |

## Files Changed

- `streamlit_app.py`: All three fixes
- Backup: `streamlit_app_backup_20250205.py` (local restore point)
