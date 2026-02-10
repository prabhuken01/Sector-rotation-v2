/**
 * =======================================================================
 * Google Apps Script — Market Breadth Automation
 * =======================================================================
 *
 * HOW TO SET UP
 * ─────────────
 * 1. Open your Google Sheet (the one with your Market Breadth data).
 *
 * 2. Create THREE sheets (tabs) in the workbook:
 *
 *    ┌──────────┬──────────────────────────────────────────────────────────────┐
 *    │  Tickers  │ Column A = Symbol (NSE symbol, e.g. RELIANCE, TCS, INFY)   │
 *    │           │ Paste ALL symbols you want to track (1 per row, from row 2).│
 *    │           │ Row 1 = header "Symbol".                                    │
 *    │           │ You can have 500, 1000, 1500+ rows.                         │
 *    └──────────┴──────────────────────────────────────────────────────────────┘
 *    ┌──────────┬──────────────────────────────────────────────────────────────┐
 *    │   Live   │ This sheet is auto-populated by the script.                 │
 *    │           │ E1 = Advances count, E2 = Declines count                   │
 *    │           │ Also: DMA counts, Up/Down 4% counts, etc.                  │
 *    └──────────┴──────────────────────────────────────────────────────────────┘
 *    ┌──────────┬──────────────────────────────────────────────────────────────┐
 *    │ History  │ One row per trading day (appended automatically at 4 PM).   │
 *    │           │ Columns: Date, Day, Advances, Declines, Advance/Total(%),  │
 *    │           │ Up4%Daily, Down4%Daily, %Above10DMA, %Above20DMA,          │
 *    │           │ %Above40DMA, %Above50DMA, Nifty, NiftyChg%, VIX           │
 *    └──────────┴──────────────────────────────────────────────────────────────┘
 *
 * 3. Extensions → Apps Script → paste this entire file → Save.
 *
 * 4. Run  setupDailyTrigger()  once (from the Run menu).
 *    This creates a time-driven trigger that runs every weekday at 4 PM IST.
 *
 * 5. You can also run  refreshLive()  manually at any time to update the Live sheet.
 *
 * NOTE: GOOGLEFINANCE is a *spreadsheet* function — it cannot be called from
 * Apps Script directly. So this script uses the Yahoo Finance v8 JSON API
 * (free, no key) for price data.  Each symbol takes ~0.2 s, so 1500 symbols
 * ≈ 5 minutes — well within the 6-minute Apps Script limit.
 * =======================================================================
 */

// ── Configuration ────────────────────────────────────────────────────────
var TICKERS_SHEET  = 'Tickers';
var LIVE_SHEET     = 'Live';
var HISTORY_SHEET  = 'History';

// ── Yahoo Finance helper ─────────────────────────────────────────────────

/**
 * Fetch current and recent closing prices for a single NSE symbol from Yahoo Finance.
 * Returns { price, prevClose, close21dAgo, dma10, dma20, dma40, dma50 } or null on error.
 */
function fetchStockData_(symbol) {
  var ySymbol = symbol.indexOf('.') === -1 ? symbol + '.NS' : symbol;
  // 3-month daily data (enough for 50 DMA)
  var url = 'https://query1.finance.yahoo.com/v8/finance/chart/' + encodeURIComponent(ySymbol)
          + '?range=3mo&interval=1d&includePrePost=false';
  try {
    var resp = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
    if (resp.getResponseCode() !== 200) return null;
    var json = JSON.parse(resp.getContentText());
    var result = json.chart.result;
    if (!result || result.length === 0) return null;
    var closes = result[0].indicators.quote[0].close;
    if (!closes || closes.length < 2) return null;

    // Remove trailing nulls
    while (closes.length > 0 && closes[closes.length - 1] == null) closes.pop();
    var n = closes.length;
    if (n < 2) return null;

    var price     = closes[n - 1];
    var prevClose = closes[n - 2];

    // 21-day ago price (for monthly return)
    var close21dAgo = n > 21 ? closes[n - 22] : null;

    // Simple moving averages
    function sma(arr, period) {
      if (arr.length < period) return null;
      var sum = 0;
      for (var i = arr.length - period; i < arr.length; i++) {
        if (arr[i] == null) return null;
        sum += arr[i];
      }
      return sum / period;
    }

    return {
      price:       price,
      prevClose:   prevClose,
      close21dAgo: close21dAgo,
      dma10:       sma(closes, 10),
      dma20:       sma(closes, 20),
      dma40:       sma(closes, 40),
      dma50:       sma(closes, 50)
    };
  } catch (e) {
    return null;
  }
}

/**
 * Fetch Nifty 50 close and previous close.
 * Returns { close, prevClose } or null.
 */
function fetchNifty_() {
  return fetchStockData_('^NSEI');
}

/**
 * Fetch India VIX close.
 * Returns number or null.
 */
function fetchVIX_() {
  var d = fetchStockData_('^INDIAVIX');
  return d ? d.price : null;
}

// ── Core logic ───────────────────────────────────────────────────────────

/**
 * Refresh the "Live" sheet with latest breadth data from all tickers.
 * Can be run manually or called by the daily trigger.
 */
function refreshLive() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var tickerSheet = ss.getSheetByName(TICKERS_SHEET);
  if (!tickerSheet) { Logger.log('Missing sheet: ' + TICKERS_SHEET); return; }

  // Read all symbols from column A (skip header)
  var symbols = tickerSheet.getRange('A2:A' + tickerSheet.getLastRow()).getValues()
    .map(function(r) { return String(r[0]).trim(); })
    .filter(function(s) { return s.length > 0; });

  var advances = 0, declines = 0;
  var up4 = 0, down4 = 0;
  var above10 = 0, above20 = 0, above40 = 0, above50 = 0;
  var total = 0;

  for (var i = 0; i < symbols.length; i++) {
    var d = fetchStockData_(symbols[i]);
    if (!d || d.price == null || d.prevClose == null) continue;
    total++;

    // Advance / Decline
    if (d.price > d.prevClose) advances++;
    else if (d.price < d.prevClose) declines++;

    // Daily % move
    var dailyPct = (d.price - d.prevClose) / d.prevClose * 100;
    if (dailyPct >= 4)  up4++;
    if (dailyPct <= -4) down4++;

    // % above DMA
    if (d.dma10 != null && d.price > d.dma10) above10++;
    if (d.dma20 != null && d.price > d.dma20) above20++;
    if (d.dma40 != null && d.price > d.dma40) above40++;
    if (d.dma50 != null && d.price > d.dma50) above50++;
  }

  // Nifty & VIX
  var nifty = fetchNifty_();
  var niftyClose   = nifty ? nifty.price     : '';
  var niftyPrev    = nifty ? nifty.prevClose  : null;
  var niftyChgPct  = (nifty && niftyPrev) ? ((nifty.price - niftyPrev) / niftyPrev * 100) : '';
  var vix = fetchVIX_();

  var advTotalPct = (advances + declines > 0) ? (advances / (advances + declines) * 100) : 0;
  var pct = function(num) { return total > 0 ? (num / total * 100) : 0; };

  // Write to Live sheet
  var liveSheet = ss.getSheetByName(LIVE_SHEET);
  if (!liveSheet) { liveSheet = ss.insertSheet(LIVE_SHEET); }
  liveSheet.clear();

  // Labels in column A–D, values in column E
  var labels = [
    ['Metric',           'Value'],
    ['Advances',          advances],
    ['Declines',          declines],
    ['Total Stocks',      total],
    ['Advance/Total (%)', round2(advTotalPct)],
    ['Up 4% (Daily)',     up4],
    ['Down 4% (Daily)',   down4],
    ['% Above 10 DMA',   round2(pct(above10))],
    ['% Above 20 DMA',   round2(pct(above20))],
    ['% Above 40 DMA',   round2(pct(above40))],
    ['% Above 50 DMA',   round2(pct(above50))],
    ['Nifty',             typeof niftyClose === 'number' ? Math.round(niftyClose) : ''],
    ['Nifty Chg %',       typeof niftyChgPct === 'number' ? round2(niftyChgPct) : ''],
    ['VIX',               vix != null ? round2(vix) : ''],
    ['Last Updated',      new Date().toLocaleString('en-IN', {timeZone: 'Asia/Kolkata'})]
  ];
  liveSheet.getRange(1, 1, labels.length, 2).setValues(labels);

  // Also put Advances in E1 and Declines in E2 (as requested)
  liveSheet.getRange('E1').setValue(advances);
  liveSheet.getRange('E2').setValue(declines);

  Logger.log('Live refreshed: ' + total + ' stocks, ' + advances + ' advances, ' + declines + ' declines');
}

function round2(v) { return Math.round(v * 100) / 100; }

// ── Append to History ────────────────────────────────────────────────────

/**
 * Read current values from Live sheet and append one row to History.
 * Called by the daily trigger after refreshLive().
 */
function appendToHistory() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var liveSheet = ss.getSheetByName(LIVE_SHEET);
  if (!liveSheet) { Logger.log('No Live sheet'); return; }

  // Read values from Live (column B, rows 2-14 = Advances … VIX)
  var vals = liveSheet.getRange('B2:B14').getValues().map(function(r) { return r[0]; });

  var today    = new Date();
  var dayNames = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
  var dayName  = dayNames[today.getDay()];
  var dateStr  = Utilities.formatDate(today, 'Asia/Kolkata', 'yyyy-MM-dd');

  // Row: Date, Day, Advances, Declines, Advance/Total(%), Up4%, Down4%,
  //      %Above10DMA, %Above20DMA, %Above40DMA, %Above50DMA, Nifty, NiftyChg%, VIX
  var row = [
    dateStr, dayName,
    vals[0],  // Advances
    vals[1],  // Declines
    vals[3],  // Advance/Total (%)
    vals[4],  // Up 4%
    vals[5],  // Down 4%
    vals[6],  // % Above 10 DMA
    vals[7],  // % Above 20 DMA
    vals[8],  // % Above 40 DMA
    vals[9],  // % Above 50 DMA
    vals[10], // Nifty
    vals[11], // Nifty Chg %
    vals[12]  // VIX
  ];

  var histSheet = ss.getSheetByName(HISTORY_SHEET);
  if (!histSheet) {
    histSheet = ss.insertSheet(HISTORY_SHEET);
    // Add header
    histSheet.getRange(1, 1, 1, 14).setValues([[
      'Date', 'Day', 'Advances', 'Declines', 'Advance/Total (%)',
      'Up 4% (Daily)', 'Down 4% (Daily)',
      '% Above 10 DMA', '% Above 20 DMA', '% Above 40 DMA', '% Above 50 DMA',
      'Nifty', 'Nifty Chg %', 'VIX'
    ]]);
  }

  // Prevent duplicate: check if today's date already exists
  var lastRow = histSheet.getLastRow();
  if (lastRow >= 2) {
    var lastDate = histSheet.getRange(lastRow, 1).getValue();
    if (String(lastDate) === dateStr) {
      // Overwrite last row (update, don't duplicate)
      histSheet.getRange(lastRow, 1, 1, 14).setValues([row]);
      Logger.log('History updated (overwrite) for ' + dateStr);
      return;
    }
  }

  histSheet.appendRow(row);
  Logger.log('History appended for ' + dateStr);
}

// ── Daily combined function ──────────────────────────────────────────────

/**
 * This is what the trigger calls every weekday at 4 PM IST.
 * 1) Refreshes Live sheet (fetches all stock data)
 * 2) Appends a row to History
 */
function dailyBreadthSnapshot() {
  refreshLive();
  appendToHistory();
}

// ── Trigger setup (run once) ─────────────────────────────────────────────

/**
 * Run this function ONCE from the Apps Script editor (Run menu).
 * It creates a time-based trigger: every weekday at 4 PM IST (10:30 UTC).
 *
 * To remove: Triggers → delete "dailyBreadthSnapshot".
 */
function setupDailyTrigger() {
  // Remove existing triggers for this function
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === 'dailyBreadthSnapshot') {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }

  // 4:00 PM IST = 10:30 UTC  (IST is UTC+5:30)
  // ScriptApp uses the script's timezone (set in appsscript.json or project settings).
  // We use atHour(16) which means 4 PM in the project timezone.
  // Make sure project timezone is "Asia/Kolkata" (File → Project Settings → Timezone).
  ScriptApp.newTrigger('dailyBreadthSnapshot')
    .timeBased()
    .onWeekDay(ScriptApp.WeekDay.MONDAY).atHour(16).create();
  ScriptApp.newTrigger('dailyBreadthSnapshot')
    .timeBased()
    .onWeekDay(ScriptApp.WeekDay.TUESDAY).atHour(16).create();
  ScriptApp.newTrigger('dailyBreadthSnapshot')
    .timeBased()
    .onWeekDay(ScriptApp.WeekDay.WEDNESDAY).atHour(16).create();
  ScriptApp.newTrigger('dailyBreadthSnapshot')
    .timeBased()
    .onWeekDay(ScriptApp.WeekDay.THURSDAY).atHour(16).create();
  ScriptApp.newTrigger('dailyBreadthSnapshot')
    .timeBased()
    .onWeekDay(ScriptApp.WeekDay.FRIDAY).atHour(16).create();

  Logger.log('Daily triggers set for weekdays at 4 PM (project timezone).');
}
