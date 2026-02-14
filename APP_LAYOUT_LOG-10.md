## App Layout & Tab Structure

This file documents the current Streamlit app layout so future changes don't accidentally break tab order or behaviour.

### Top-level tabs (in order)

1. **📈 Momentum Ranking**
   - **Scope**: Sector-level (indices/ETFs).
   - **Content**:
     - Main momentum table with RS Rating, ADX Z, RSI, DI Spread, CMF, Mansfield RS, Momentum Score.
     - Color coding for momentum, RS, CMF, etc.
     - Summary metrics (Top Momentum Sectors, Positive Mansfield RS, CMF Sum).
     - Sector trend mini-view (T‑7 … T) for selected sector.

2. **📊 Market breadth**
   - **Universe**: Stocks from `Sector-Company.xlsx` / `SECTOR_COMPANIES` (dynamic count).
   - **Primary table** (last 20 trading days, most recent day at top):
     - `Date` (latest row labelled "(Current day)").
     - `Day` (weekday name).
     - `Advances`, `Declines` (count over universe).
     - `Advance/Total %`, `% Above 8 DMA`, `% Above 20 DMA`, `% Above 50 DMA`, `Nifty`, `Nifty Chg %`.
   - **Color coding**: &lt;25% red, 25–50% yellow, &gt;50% green; Nifty chg by magnitude.
   - **Summary row**: 20-day avg.

3. **📊 Stock Screener**
   - **Universe**: Same as Market breadth.
   - **Date control**: Dropdown of past ~10 trading days.
   - **Per-stock metrics**: Sector, Symbol, Company, Price, RSI (1W/1D/1H), SMAs, VWAP (1H), RSI divergence (2H), Final score.
   - **Top 15 Bullish** / **Top 15 Bearish** with Sentiment.

4. **🔄 Reversal Candidates** – Sector-level reversal view.

5. **📊 Interpretation Guide** – Static explanation of indicators.

6. **🏢 Company Momentum** – Company-level momentum for selected sector.

7. **🏢 Company Reversals** – Company-level reversal for selected sector.

8. **📅 Historical Rankings** – 10 days (T‑9 … T), primary table + sector momentum/reversal evolution.

9. **🔌 Data Sources** – Symbols, indices, ETFs, caches.

---

### Change Log (high level)

- **2026‑02** – Market breadth tab, Stock Screener, Historical Rankings 10-day lookback; single source Excel (Main); Option A; doc numbering (readme-1, … -10).
