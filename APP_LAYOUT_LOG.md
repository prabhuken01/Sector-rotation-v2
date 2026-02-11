## App Layout & Tab Structure

This file documents the current Streamlit app layout so future changes don’t accidentally break tab order or behaviour.

### Top-level tabs (in order)

1. **📈 Momentum Ranking**
   - **Scope**: Sector-level (indices/ETFs).
   - **Content**:
     - Main momentum table with RS Rating, ADX Z, RSI, DI Spread, CMF, Mansfield RS, Momentum Score.
     - Color coding for momentum, RS, CMF, etc.
     - Summary metrics (Top Momentum Sectors, Positive Mansfield RS, CMF Sum).
     - Sector trend mini-view (T‑7 … T) for selected sector.

2. **📊 Market breadth**
   - **Universe**: 97-stock list from `Sector-Company.xlsx` / `SECTOR_COMPANIES`.
   - **Primary table** (last 20 trading days, most recent day at top):
     - `Date` (latest row labelled “(Current day)”).
     - `Day` (weekday name).
     - `Advances`, `Declines` (count over 97-stock universe).
     - `Advance/Total %` (advances ÷ (advances+declines), 1 decimal).
     - `% Above 8 DMA`, `% Above 20 DMA`, `% Above 50 DMA` (daily closes vs 8/20/50‑day SMAs on the same 97-stock universe, 1 decimal).
     - `Nifty` (benchmark index close, **no decimals**).
     - `Nifty Chg %` (day‑on‑day % change, 1 decimal).
   - **Color coding**:
     - `Advance/Total %`, `% Above 8/20/50 DMA`:
       - **<25%**: red (weak).
       - **25–50%**: yellow (neutral).
       - **>50%**: green (positive).
     - `Nifty Chg %` (based on absolute move):
       - \|chg\| < **0.3%**: no color.
       - **0.3–0.8%**: yellow.
       - > **0.8%**: green if positive, red if negative.
   - **Summary row**:
     - Last row labelled `20-day avg` with averages for `% Above 8 DMA`, `% Above 20 DMA`, `% Above 50 DMA`, `Nifty Chg %`.

3. **📊 Stock Screener**
   - **Universe**: Same 97 stocks as above.
   - **Date control**: Dropdown of past ~10 trading days (by benchmark index date).
   - **Per-stock metrics**:
     - `Sector`, `Symbol`, `Company`.
     - `Price` (latest close on chosen date).
     - `RSI (1W)`, `RSI (1D)`, `RSI (1H)` **values + direction** columns (`Up` / `Down` / `Flat`).
     - `Price > 8 SMA`, `Price > 20 SMA`, `Price > 50 SMA` (daily SMAs, Yes/No).
     - `Price vs VWAP (1H)` for latest day: `Above` / `Approaching` / `Below`.
     - `RSI divergence (2H)` (simple bullish/bearish divergence flag on resampled 2‑hour bars, Yes/No).
     - `Final score` (float).
   - **Scoring (simplified)**:
     - User‑tunable sliders for:
       - RSI directions (all three up).
       - Price above 8/20/50 SMA.
       - Price above / approaching VWAP.
       - RSI divergence (2H).
     - Higher score when:
       - All three RSIs trend up.
       - Price is above more SMAs.
       - Price above / near VWAP.
       - RSI divergence present.
   - **Tables**:
     - **Top 15 Bullish** (highest Final score) with `Sentiment` column:
       - `<1.5` → 🔴 Weak, `<3.0` → 🟡 Moderate, else 🔵/🟢 Strong.
     - **Top 15 Bearish** (lowest scores, reversed order) with same sentiment scale.

4. **🔄 Reversal Candidates**
   - Sector-level reversal view using Reversal Score and thresholds (RSI / ADX / DI rules).
   - Shows eligible reversal candidates, statuses, and color coding.

5. **📊 Interpretation Guide**
   - Static explanation of all indicators, tooltips, and how to interpret Momentum/Reversal tables.

6. **🏢 Company Momentum**
   - Company-level momentum tab:
     - For selected sector (default: top momentum sector).
     - Uses same momentum scoring logic as sector tab.
     - Company trend mini‑view (T‑7 … T).

7. **🏢 Company Reversals**
   - Company-level reversal scoring for selected sector (default: top reversal candidate).

8. **📅 Historical Rankings**
   - **Lookback**: **10** days (T‑9 … T) for performance (user requested 7–10 days).
   - **Primary table** (per day):
     - `Date`.
     - `Advance/Total %` and `Stocks % above 10 DMA` (Nifty‑50 based).
     - `Momentum #1 Sector` (and other sector + stock ranking columns from existing logic).
   - **Secondary section**:
     - Sector momentum & reversal evolution (T‑7 … T) for selected sectors.

9. **🔌 Data Sources**
   - Tab explaining which symbols, indices, ETFs, and caches are used for data.

---

### Change Log (high level)

- **2026‑02‑11** – Added:
  - Dedicated **Market breadth** tab using 97-stock universe and 20‑day table.
  - Detailed **Stock Screener** tab (RSI 1W/1D/1H, SMAs, VWAP, divergence, Final score).
  - Reduced **Historical Rankings** main table lookback from 20 to **10** days for faster loading.

