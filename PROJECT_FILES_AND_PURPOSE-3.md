# Project Files and Purpose

This document lists the main files and folders in the Sector Rotation / Advanced Technical Analysis project and their purpose. Keep this for reference and backup.

---

## Data and configuration (keep these safe)

| File / Folder | Purpose |
|---------------|---------|
| **Sector-Company.xlsx** | **Single source** for sector–stock list. The app reads the sheet named **Main** only (columns: Sector, Company Name, Symbol, Weight (%)). Run `consolidate_sector_company_to_sheet2.py` once to keep only former Sheet2, rename to Main, and remove Grok_Sector/Sheet1. |
| **.streamlit/config.toml** | Streamlit UI settings (theme, layout). |
| **.gitignore** | Tells Git which files/folders not to track (e.g. venv, secrets, cache). |
| **requirements.txt** | Python package list for install (e.g. streamlit, pandas, yfinance, openpyxl). |

---

## Core application code (do not change unless intended)

| File | Purpose |
|------|---------|
| **streamlit_app.py** | Main Streamlit app: sidebar, tabs (Momentum, Market breadth, Stock Screener, Reversal, Historical Rankings, Data Sources, etc.), and UI logic. |
| **company_symbols.py** | Loads sector–company data from Excel (sheet Main or Sheet2), builds SECTOR_COMPANIES. |
| **analysis.py** | Sector analysis: momentum and reversal scoring, rank-based and Trending (50% Z(RSI) + 50% Z(CMF)) logic. |
| **indicators.py** | Technical indicators: RSI, ADX, CMF, Z-score, Mansfield RS, etc. |
| **config.py** | App constants: default momentum/reversal weights, decimal places, Mansfield period. Optional SECTOR_COMPANY_EXCEL_PATH for non–Option A. |
| **data_fetcher.py** | Fetches market data (e.g. yfinance) for symbols and intervals. |
| **local_cache.py** | Local caching of fetched data. |
| **cache_scheduler.py** | Cache refresh scheduling; uses SECTOR_COMPANIES for symbol list. |
| **company_analysis.py** | Company-level momentum and reversal tabs (per sector). |
| **market_analysis.py** | Market-level analysis helpers. |

---

## Supporting and test scripts

| File | Purpose |
|------|---------|
| **consolidate_sector_company_to_sheet2.py** | One-time: read Sheet2, keep only that sheet, rename to **Main**, remove other sheets. Usage: `python consolidate_sector_company_to_sheet2.py [path]`. |
| **gen_fo_watchlist.py** | Generates F&O watchlist data (optional; fo_watchlist integration in company_symbols). |
| **test_excel_load.py** | Quick test that Sector-Company.xlsx can be read. |
| **verify_deployment.py** | Checks deployment (e.g. SECTOR_COMPANIES load, connectivity). |
| **_indicator_tv_compare.py** | Indicator comparison / TradingView-style logic (reference or optional use). |
| **google_apps_script_market_breadth.js** | Google Apps Script for market breadth (external to main app). |

---

## Cached / generated (can be recreated)

| File / Folder | Purpose |
|---------------|---------|
| **data_cache/** | Folder for cache files (e.g. market_data.db, historical_rankings_cache_v2.csv). Safe to clear for a fresh start; app will rebuild. |

---

## Documentation (read in order 1 → 2 → 3 …)

| File | Purpose |
|------|---------|
| **readme-1.md** | Project overview, Option A, quick start. |
| **EXCEL_ONE_PLACE_STEPS-2.md** | Excel: one folder, sheet Main, consolidate script. |
| **PROJECT_FILES_AND_PURPOSE-3.md** | This file: list of files and purpose. |
| **DEPLOYMENT-4.md** | Deployment guide (Streamlit Cloud, Railway, Render). |
| **CHANGES_LOG-5.md** | Version history (e.g. v2.3.0). |
| **CHANGES_SUMMARY-6.md** | Summary of major feature changes. |
| **CACHE_SETUP_GUIDE-7.md** | How to set up and use the cache. |
| **UNIFIED_SCORING_LOGIC-8.md** | Scoring logic (momentum, reversal, screener). |
| **implementation_guide-9.md** | Implementation and design notes. |
| **APP_LAYOUT_LOG-10.md** | Notes on app layout and structure. |

---

## Quick Start and reference

| File | Purpose |
|------|---------|
| **Quick_Start/README-1.md** | Quick start guide. |
| **Quick_Start/REFERENCE_MANUAL-2.md** | Reference for using the app. |
| **SYMBOLS.txt** | Symbol list or notes (reference). |

---

## Other

| File / Folder | Purpose |
|---------------|---------|
| **.devcontainer/devcontainer.json** | Dev container setup for consistent dev environment. |
| **.git** | Git repository data (version history). |

---

**Keeping files safe:** Commit and push regularly so the repo (e.g. on GitHub) is the backup. For Option A, keep **Sector-Company.xlsx** (sheet **Main**) in your project folder (e.g. E: drive) and ensure that folder has the latest code.

*Last updated: Feb 2026 (v2.3.0).*
