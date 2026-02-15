"""
ENHANCED CONFLUENCE ANALYSIS V2
================================

Key Improvements over V1:
1. Fixed BEARISH logic — Entry at LH (resistance), NOT at LL (too late)
2. Price position detection: Near High / Near Low / Middle
3. Volume confirmation for breakdown/breakout signals
4. RSI interpretation fixed for bearish (50-70 at LH, not <30)
5. Two-timeframe analysis (entry TF + 1D confirmation)
6. Negative scoring for opposing conditions
7. Position-aware entry descriptions

Scoring (max ~20 pts each side):
  Trend (entry TF):  +4 aligned / -3 opposing / +0.5 sideways
  Trend (1D):        +3 aligned / -2 opposing / +0.5 sideways
  MA Align (entry):  +3 aligned / -2 opposing
  MA Align (1D):     +2 aligned / -1 opposing
  Price Position:    Bullish: Near Low +2 / Bearish: Near High +3
  RSI (entry TF):    up to +2.5 (context-dependent)
  RSI (1D):          up to +1.5
  Crossover (entry): +1.5 aligned / -1 opposing
  Divergence:        +1.5 aligned / -1 opposing
  Volume:            +1 to +1.5 (context-dependent)
"""

import pandas as pd
import numpy as np

# Use the project's own RSI calculation if available; fallback to local impl.
try:
    from indicators import calculate_rsi as _calc_rsi_series
    def _calculate_rsi_from_df(df, period=14):
        """Wrapper: indicators.calculate_rsi expects a DataFrame with 'Close'."""
        return _calc_rsi_series(df, period=period)
except ImportError:
    def _calculate_rsi_from_df(df, period=14):
        try:
            delta = df['Close'].diff()
            gain = delta.where(delta > 0, 0).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            return 100 - (100 / (1 + rs))
        except Exception:
            return pd.Series([50.0] * len(df), index=df.index)


# ---------------------------------------------------------------------------
# Trend detection
# ---------------------------------------------------------------------------
def detect_trend(highs, lows, lookback=10):
    """
    Detect trend using swing highs and lows.
    Returns: 'Uptrend (HH/HL)', 'Downtrend (LL/LH)', or 'Sideways'
    """
    if len(highs) < lookback or len(lows) < lookback:
        return 'Sideways'

    recent_highs = highs[-lookback:]
    recent_lows = lows[-lookback:]

    hh_count = sum(1 for i in range(2, len(recent_highs)) if recent_highs[i] > recent_highs[i - 2])
    hl_count = sum(1 for i in range(2, len(recent_lows)) if recent_lows[i] > recent_lows[i - 2])

    ll_count = sum(1 for i in range(2, len(recent_lows)) if recent_lows[i] < recent_lows[i - 2])
    lh_count = sum(1 for i in range(2, len(recent_highs)) if recent_highs[i] < recent_highs[i - 2])

    if hh_count >= 3 and hl_count >= 3:
        return 'Uptrend (HH/HL)'
    elif ll_count >= 3 and lh_count >= 3:
        return 'Downtrend (LL/LH)'
    else:
        return 'Sideways'


# ---------------------------------------------------------------------------
# MA alignment helper
# ---------------------------------------------------------------------------
def _ma_alignment(price, dma20, dma50):
    if pd.isna(dma20) or pd.isna(dma50):
        return 'N/A'
    if price > dma20 > dma50:
        return 'Bullish'
    elif price < dma20 < dma50:
        return 'Bearish'
    else:
        return 'Mixed'


# ---------------------------------------------------------------------------
# MA crossover detection
# ---------------------------------------------------------------------------
def _ma_crossover(dma20, dma50):
    if pd.isna(dma20) or pd.isna(dma50):
        return 'N/A'
    diff_pct = abs((dma20 - dma50) / dma50 * 100)
    if diff_pct < 1.5:
        return 'Bullish Crossover' if dma20 > dma50 else 'Bearish Crossover'
    return 'None'


# ---------------------------------------------------------------------------
# Divergence detection
# ---------------------------------------------------------------------------
def _detect_divergence(data_tf, rsi_series):
    """Check last 10 bars for price-RSI divergence."""
    if len(data_tf) < 10 or len(rsi_series) < 10:
        return 'None'
    try:
        recent = data_tf.tail(10)
        highs = recent['High'].values
        lows = recent['Low'].values
        rsi_vals = rsi_series.tail(10).values
        if len(highs) >= 5:
            if lows[-1] < lows[-3] and rsi_vals[-1] > rsi_vals[-3]:
                return 'Bullish'
            if highs[-1] > highs[-3] and rsi_vals[-1] < rsi_vals[-3]:
                return 'Bearish'
    except Exception:
        pass
    return 'None'


# ---------------------------------------------------------------------------
# NEW: Price position detection (Near High / Near Low / Middle)
# ---------------------------------------------------------------------------
def _find_recent_swing_points(data, lookback=20):
    """
    Find recent swing high/low and determine where current price sits.

    Returns: (recent_high, recent_low, position)
      position: 'Near High' | 'Near Low' | 'Middle' | 'Unknown'
    """
    if len(data) < lookback:
        return None, None, 'Unknown'

    recent_data = data.tail(lookback)
    recent_high = recent_data['High'].max()
    recent_low = recent_data['Low'].min()
    current_price = data['Close'].iloc[-1]

    total_range = recent_high - recent_low
    if total_range == 0:
        return recent_high, recent_low, 'Unknown'

    dist_from_high = abs(current_price - recent_high) / recent_high * 100
    dist_from_low = abs(current_price - recent_low) / recent_low * 100

    if dist_from_high < 2.0:
        return recent_high, recent_low, 'Near High'
    elif dist_from_low < 2.0:
        return recent_high, recent_low, 'Near Low'
    else:
        return recent_high, recent_low, 'Middle'


# ---------------------------------------------------------------------------
# NEW: Volume confirmation
# ---------------------------------------------------------------------------
def _check_volume_confirmation(data, lookback=5):
    """
    Check if recent volume is higher than average (20-bar).
    Returns: 'High' if recent vol > avg * 1.2, else 'Normal', or 'N/A'.
    """
    if 'Volume' not in data.columns or len(data) < lookback * 4:
        return 'N/A'
    try:
        recent_vol = data['Volume'].tail(lookback).mean()
        avg_vol = data['Volume'].tail(lookback * 4).mean()
        return 'High' if recent_vol > avg_vol * 1.2 else 'Normal'
    except Exception:
        return 'N/A'


# ---------------------------------------------------------------------------
# Analyze a single stock across two timeframes (V2)
# ---------------------------------------------------------------------------
def analyze_stock_confluence(data_1h_or_entry, data_1d, entry_timeframe='2h'):
    """
    Enhanced multi-timeframe confluence analysis.

    Parameters
    ----------
    data_1h_or_entry : DataFrame
        If entry_timeframe='2h': 1H data (resampled to 2H internally).
        If entry_timeframe='1d': daily data (used directly as entry TF).
    data_1d : DataFrame
        Daily data for the confirmation timeframe.
    entry_timeframe : str
        '2h', '4h', or '1d'. For '2h'/'4h', 1H data is resampled; for '1d', daily is used as entry.

    Returns
    -------
    dict with all analysis fields including price_position and volume_status,
    or None on failure.
    """
    try:
        # --- Build entry-TF data ---
        if entry_timeframe == '2h':
            if data_1h_or_entry is None or len(data_1h_or_entry) < 40:
                return None
            data_entry = data_1h_or_entry.resample('2h').agg({
                'Open': 'first', 'High': 'max', 'Low': 'min',
                'Close': 'last', 'Volume': 'sum'
            }).dropna()
            if len(data_entry) < 20:
                return None
        elif entry_timeframe == '4h':
            if data_1h_or_entry is None or len(data_1h_or_entry) < 80:
                return None
            data_entry = data_1h_or_entry.resample('4h').agg({
                'Open': 'first', 'High': 'max', 'Low': 'min',
                'Close': 'last', 'Volume': 'sum'
            }).dropna()
            if len(data_entry) < 20:
                return None
        else:
            data_entry = data_1h_or_entry
            if data_entry is None or len(data_entry) < 50:
                return None

        if data_1d is None or len(data_1d) < 50:
            return None

        # --- Indicators on entry TF ---
        data_entry = data_entry.copy()
        data_entry['DMA_20'] = data_entry['Close'].rolling(20).mean()
        data_entry['DMA_50'] = data_entry['Close'].rolling(50).mean()
        rsi_entry = _calculate_rsi_from_df(data_entry)

        price_entry = data_entry['Close'].iloc[-1]
        dma20_entry = data_entry['DMA_20'].iloc[-1]
        dma50_entry = data_entry['DMA_50'].iloc[-1]
        rsi_e = rsi_entry.iloc[-1] if not rsi_entry.isna().all() else 50.0
        rsi_e_prev = rsi_entry.iloc[-2] if len(rsi_entry) > 1 and not pd.isna(rsi_entry.iloc[-2]) else rsi_e

        # --- Indicators on 1D ---
        data_1d = data_1d.copy()
        data_1d['DMA_20'] = data_1d['Close'].rolling(20).mean()
        data_1d['DMA_50'] = data_1d['Close'].rolling(50).mean()
        rsi_1d = _calculate_rsi_from_df(data_1d)

        price_1d = data_1d['Close'].iloc[-1]
        dma20_1d = data_1d['DMA_20'].iloc[-1]
        dma50_1d = data_1d['DMA_50'].iloc[-1]
        rsi_d = rsi_1d.iloc[-1] if not rsi_1d.isna().all() else 50.0
        rsi_d_prev = rsi_1d.iloc[-2] if len(rsi_1d) > 1 and not pd.isna(rsi_1d.iloc[-2]) else rsi_d

        # --- Trend ---
        trend_entry = detect_trend(
            data_entry['High'].tail(20).values,
            data_entry['Low'].tail(20).values,
            lookback=15
        )
        trend_1d = detect_trend(
            data_1d['High'].tail(30).values,
            data_1d['Low'].tail(30).values,
            lookback=20
        )

        # --- MA alignment ---
        ma_align_entry = _ma_alignment(price_entry, dma20_entry, dma50_entry)
        ma_align_1d = _ma_alignment(price_1d, dma20_1d, dma50_1d)

        # --- Crossover (entry TF) ---
        crossover_entry = _ma_crossover(dma20_entry, dma50_entry)

        # --- Divergence (entry TF) ---
        divergence = _detect_divergence(data_entry, rsi_entry)

        # --- NEW: Price position ---
        recent_high, recent_low, price_position = _find_recent_swing_points(data_entry, lookback=20)

        # --- NEW: Volume confirmation ---
        volume_status = _check_volume_confirmation(data_entry, lookback=5)

        tf_label = '2H' if entry_timeframe == '2h' else ('4H' if entry_timeframe == '4h' else '1D')

        # Confirmation TF (not always 1D: in 4H+1H mode it is 1H conceptually; data_1d is still used)
        return {
            'current_price': round(float(price_entry), 2),
            'trend_entry': trend_entry,
            'trend_1d': trend_1d,
            'trend_conf': trend_1d,
            'ma_alignment_entry': ma_align_entry,
            'ma_alignment_1d': ma_align_1d,
            'ma_alignment_conf': ma_align_1d,
            'ma_crossover_entry': crossover_entry,
            'rsi_entry': round(float(rsi_e), 1),
            'rsi_entry_prev': round(float(rsi_e_prev), 1),
            'rsi_1d': round(float(rsi_d), 1),
            'rsi_1d_prev': round(float(rsi_d_prev), 1),
            'rsi_conf': round(float(rsi_d), 1),
            'rsi_conf_prev': round(float(rsi_d_prev), 1),
            'divergence': divergence,
            'price_position': price_position,
            'recent_high': round(float(recent_high), 2) if recent_high else None,
            'recent_low': round(float(recent_low), 2) if recent_low else None,
            'volume_status': volume_status,
            'entry_tf_label': tf_label,
        }
    except Exception:
        return None


# ---------------------------------------------------------------------------
# BULLISH scoring (V2 — with price position + volume)
# ---------------------------------------------------------------------------
def calculate_confluence_score_bullish(analysis_data):
    """
    Enhanced bullish confluence score.
    For bullish: want price Near Low (buying at HL support).
    Max ~20 pts.
    """
    score = 0.0
    reasons = []

    # 1. TREND (entry TF) — 4 pts
    t = analysis_data['trend_entry']
    if t == 'Uptrend (HH/HL)':
        score += 4; reasons.append("+4: Uptrend on entry TF")
    elif t == 'Downtrend (LL/LH)':
        score -= 3; reasons.append("-3: Downtrend on entry TF (against)")
    else:
        score += 0.5; reasons.append("+0.5: Sideways on entry TF")

    # 2. TREND (1D) — 3 pts
    t1 = analysis_data['trend_1d']
    if t1 == 'Uptrend (HH/HL)':
        score += 3; reasons.append("+3: Uptrend on 1D")
    elif t1 == 'Downtrend (LL/LH)':
        score -= 2; reasons.append("-2: Downtrend on 1D (against)")
    else:
        score += 0.5; reasons.append("+0.5: Sideways on 1D")

    # 3. MA ALIGNMENT (entry TF) — 3 pts
    ma = analysis_data['ma_alignment_entry']
    if ma == 'Bullish':
        score += 3; reasons.append("+3: Bullish MA alignment (entry TF)")
    elif ma == 'Bearish':
        score -= 2; reasons.append("-2: Bearish MA alignment (entry TF)")

    # 4. MA ALIGNMENT (1D) — 2 pts
    ma1 = analysis_data['ma_alignment_1d']
    if ma1 == 'Bullish':
        score += 2; reasons.append("+2: Bullish MA alignment (1D)")
    elif ma1 == 'Bearish':
        score -= 1; reasons.append("-1: Bearish MA alignment (1D)")

    # 5. PRICE POSITION — 2 pts (bullish wants Near Low = buying dip/HL)
    pos = analysis_data.get('price_position', 'Unknown')
    if pos == 'Near Low':
        score += 2; reasons.append("+2: Price near recent low (good entry at HL)")
    elif pos == 'Near High':
        score -= 1; reasons.append("-1: Price near recent high (late entry)")
    else:
        score += 0.5; reasons.append("+0.5: Price in middle range")

    # 6. RSI (entry TF) — 2 pts
    rsi = analysis_data['rsi_entry']
    rsi_p = analysis_data['rsi_entry_prev']
    if rsi > rsi_p and 40 <= rsi <= 70:
        score += 2; reasons.append(f"+2: RSI rising in 40-70 zone (entry: {rsi})")
    elif rsi > 70:
        score -= 1; reasons.append(f"-1: RSI overbought (entry: {rsi})")
    elif rsi < 30 and rsi > rsi_p:
        score += 1.5; reasons.append(f"+1.5: RSI oversold but rising (entry: {rsi})")
    elif rsi > rsi_p:
        score += 1; reasons.append(f"+1: RSI rising (entry: {rsi})")
    elif rsi < rsi_p:
        score -= 0.5; reasons.append(f"-0.5: RSI falling (entry: {rsi})")

    # 7. RSI (1D) — 1.5 pts
    rsi_d = analysis_data['rsi_1d']
    rsi_dp = analysis_data['rsi_1d_prev']
    if rsi_d > rsi_dp and 40 <= rsi_d <= 70:
        score += 1.5; reasons.append(f"+1.5: RSI rising in 40-70 zone (1D: {rsi_d})")
    elif rsi_d > 70:
        score -= 0.5; reasons.append(f"-0.5: RSI overbought (1D: {rsi_d})")
    elif rsi_d > rsi_dp:
        score += 0.5; reasons.append(f"+0.5: RSI rising (1D: {rsi_d})")

    # 8. CROSSOVER (entry TF) — 1.5 pts
    xo = analysis_data['ma_crossover_entry']
    if xo == 'Bullish Crossover':
        score += 1.5; reasons.append("+1.5: Bullish MA crossover forming")
    elif xo == 'Bearish Crossover':
        score -= 1; reasons.append("-1: Bearish MA crossover forming")

    # 9. DIVERGENCE — 1.5 pts
    div = analysis_data['divergence']
    if div == 'Bullish':
        score += 1.5; reasons.append("+1.5: Bullish RSI divergence")
    elif div == 'Bearish':
        score -= 1; reasons.append("-1: Bearish RSI divergence (against)")

    # 10. VOLUME — 1 pt
    vol = analysis_data.get('volume_status', 'N/A')
    if vol == 'High':
        score += 1; reasons.append("+1: High volume confirmation")

    return round(score, 2), reasons


# ---------------------------------------------------------------------------
# BEARISH scoring (V2 — CRITICAL FIX: entry at LH, not LL)
# ---------------------------------------------------------------------------
def calculate_confluence_score_bearish(analysis_data):
    """
    Enhanced bearish confluence score.

    CRITICAL FIX: For SHORT entry we want price Near High (at LH resistance),
    NOT at LL (too late — price already fell).
    RSI at LH should be 50-70 turning down (not oversold).
    Max ~20 pts.
    """
    score = 0.0
    reasons = []

    # 1. TREND (entry TF) — 4 pts
    t = analysis_data['trend_entry']
    if t == 'Downtrend (LL/LH)':
        score += 4; reasons.append("+4: Downtrend on entry TF")
    elif t == 'Uptrend (HH/HL)':
        score -= 3; reasons.append("-3: Uptrend on entry TF (against)")
    else:
        score += 0.5; reasons.append("+0.5: Sideways on entry TF")

    # 2. TREND (1D) — 3 pts
    t1 = analysis_data['trend_1d']
    if t1 == 'Downtrend (LL/LH)':
        score += 3; reasons.append("+3: Downtrend on 1D")
    elif t1 == 'Uptrend (HH/HL)':
        score -= 2; reasons.append("-2: Uptrend on 1D (against)")
    else:
        score += 0.5; reasons.append("+0.5: Sideways on 1D")

    # 3. MA ALIGNMENT (entry TF) — 3 pts
    ma = analysis_data['ma_alignment_entry']
    if ma == 'Bearish':
        score += 3; reasons.append("+3: Bearish MA alignment (entry TF)")
    elif ma == 'Bullish':
        score -= 2; reasons.append("-2: Bullish MA alignment (entry TF)")

    # 4. MA ALIGNMENT (1D) — 2 pts
    ma1 = analysis_data['ma_alignment_1d']
    if ma1 == 'Bearish':
        score += 2; reasons.append("+2: Bearish MA alignment (1D)")
    elif ma1 == 'Bullish':
        score -= 1; reasons.append("-1: Bullish MA alignment (1D)")

    # 5. PRICE POSITION (CRITICAL) — 3 pts for Near High
    # For BEARISH: Near High = at LH resistance = IDEAL SHORT entry
    #              Near Low  = at LL = TOO LATE, price already fell
    pos = analysis_data.get('price_position', 'Unknown')
    if pos == 'Near High':
        score += 3; reasons.append("+3: Price near recent high (SHORT entry at LH)")
    elif pos == 'Near Low':
        score -= 2; reasons.append("-2: Price near recent low (too late, already at LL)")
    else:
        score += 0.5; reasons.append("+0.5: Price in middle range")

    # 6. RSI (entry TF) — up to 2.5 pts (context-dependent on position)
    rsi = analysis_data['rsi_entry']
    rsi_p = analysis_data['rsi_entry_prev']

    if pos == 'Near High':
        # At LH resistance: want RSI 50-70 turning down (perfect SHORT setup)
        if 50 <= rsi <= 70 and rsi < rsi_p:
            score += 2.5; reasons.append(f"+2.5: RSI turning down from resistance zone (entry: {rsi})")
        elif 50 <= rsi <= 70:
            score += 1.5; reasons.append(f"+1.5: RSI in resistance zone (entry: {rsi})")
        elif rsi > 70:
            score += 1; reasons.append(f"+1: RSI overbought at resistance (entry: {rsi})")
        elif rsi < 30:
            score -= 1.5; reasons.append(f"-1.5: RSI already oversold at 'high' (entry: {rsi})")
    else:
        # Not at ideal position
        if rsi < rsi_p and 30 <= rsi <= 60:
            score += 1.5; reasons.append(f"+1.5: RSI falling (entry: {rsi})")
        elif rsi < 30:
            score -= 1; reasons.append(f"-1: RSI oversold (late entry: {rsi})")
        elif rsi < rsi_p:
            score += 1; reasons.append(f"+1: RSI falling (entry: {rsi})")
        elif rsi > rsi_p:
            score -= 0.5; reasons.append(f"-0.5: RSI rising (against: {rsi})")

    # 7. RSI (1D) — 1.5 pts
    rsi_d = analysis_data['rsi_1d']
    rsi_dp = analysis_data['rsi_1d_prev']
    if rsi_d < rsi_dp and 30 <= rsi_d <= 60:
        score += 1.5; reasons.append(f"+1.5: RSI falling in 30-60 zone (1D: {rsi_d})")
    elif rsi_d < 30:
        score -= 0.5; reasons.append(f"-0.5: RSI oversold (1D: {rsi_d})")
    elif rsi_d < rsi_dp:
        score += 0.5; reasons.append(f"+0.5: RSI falling (1D: {rsi_d})")

    # 8. CROSSOVER (entry TF) — 1.5 pts
    xo = analysis_data['ma_crossover_entry']
    if xo == 'Bearish Crossover':
        score += 1.5; reasons.append("+1.5: Bearish MA crossover forming")
    elif xo == 'Bullish Crossover':
        score -= 1; reasons.append("-1: Bullish MA crossover forming")

    # 9. DIVERGENCE — 1.5 pts
    div = analysis_data['divergence']
    if div == 'Bearish':
        score += 1.5; reasons.append("+1.5: Bearish RSI divergence")
    elif div == 'Bullish':
        score -= 1; reasons.append("-1: Bullish RSI divergence (against)")

    # 10. VOLUME — 1.5 pts at resistance, 0.5 otherwise
    vol = analysis_data.get('volume_status', 'N/A')
    if vol == 'High' and pos == 'Near High':
        score += 1.5; reasons.append("+1.5: High volume at resistance (distribution)")
    elif vol == 'High':
        score += 0.5; reasons.append("+0.5: High volume")

    return round(score, 2), reasons


# ---------------------------------------------------------------------------
# Entry description generator (V2 — position-aware)
# ---------------------------------------------------------------------------
def generate_entry_description(analysis_data, score=None, is_bullish=True):
    """Position-aware entry description."""
    pos = analysis_data.get('price_position', 'Unknown')

    # If score not passed, compute a rough one
    if score is None:
        score = 0

    if is_bullish:
        if score >= 12:
            if pos == 'Near Low':
                return "EXCELLENT: Uptrend + Price at support (HL forming) + Rising RSI"
            return "EXCELLENT: Strong uptrend + Bullish alignment + Rising momentum"
        elif score >= 9:
            if pos == 'Near Low':
                return "GOOD: Uptrend + Price near support (good entry for HL)"
            return "GOOD: Uptrend with bullish structure developing"
        elif score >= 5:
            return "MODERATE: Some bullish signals, needs confirmation"
        else:
            return "WEAK: Insufficient bullish alignment, avoid or wait"
    else:
        if score >= 12:
            if pos == 'Near High':
                return "EXCELLENT: Downtrend + Price at resistance (LH forming) + Bearish RSI"
            return "EXCELLENT: Strong downtrend + Bearish alignment + Falling momentum"
        elif score >= 9:
            if pos == 'Near High':
                return "GOOD: Downtrend + Price near resistance (good SHORT at LH)"
            return "GOOD: Downtrend with bearish structure developing"
        elif score >= 5:
            if pos == 'Near Low':
                return "TOO LATE: Price already fell to LL, missed SHORT entry"
            return "MODERATE: Some bearish signals, needs confirmation"
        else:
            return "WEAK: Insufficient bearish alignment, avoid or wait"


# ---------------------------------------------------------------------------
# Convenience: compute both scores from raw data (for Historical Rankings)
# ---------------------------------------------------------------------------
def compute_confluence_scores(data_1h_or_entry, data_1d, entry_timeframe='2h'):
    """
    All-in-one: analyse + score both sides.
    Returns (bullish_score, bearish_score, analysis_data) or (None, None, None).
    """
    analysis = analyze_stock_confluence(data_1h_or_entry, data_1d, entry_timeframe=entry_timeframe)
    if analysis is None:
        return None, None, None
    b_score, _ = calculate_confluence_score_bullish(analysis)
    s_score, _ = calculate_confluence_score_bearish(analysis)
    return b_score, s_score, analysis
