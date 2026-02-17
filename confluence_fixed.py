"""
confluence_fixed.py  — v3.0
============================
Fixes applied in this version
-------------------------------
(a) Historical Rankings sync:
    The sector-filter and timeframe choice is now purely caller-controlled.
    Both Historical Rankings and Part-3 Stock Screener receive the same
    top/bottom sector list from the same helper functions here, so a given
    date/TF/filter combination always produces identical stock selections.

(b) Bearish sector selection:
    get_bottom_n_sectors_by_momentum() returns the BOTTOM-N sectors
    (lowest RSI + CMF) for bearish picks.  The existing
    get_top_n_sectors_by_momentum() (in streamlit_app.py) is for bullish.

(c) RSI direction enforced:
    Bullish  → RSI *rising* earns positive pts; RSI *falling* is penalised.
    Bearish  → RSI *falling* earns positive pts; RSI *rising* is penalised.

(d) Pivot-based price position (ENTRY TF only):
    For 4H+1H → use 4H pivot structure.
    For 1D+2H → use 1D pivot structure.
    2H / 1H conf-TF trend is kept as a display placeholder (weight = 0).
    Entry ideal:  Bullish at HL (Higher Low),  Bearish at LH (Lower High).

(e) HH / HL / LH / LL reconstruction via detect_swing_structure()
    (Python port of the Pine-Script "Pivot Points High Low" indicator).
"""

from __future__ import annotations
import pandas as pd
import numpy as np


# ─────────────────────────────────────────────────────────────────────────────
# RSI helper
# ─────────────────────────────────────────────────────────────────────────────

def _calculate_rsi_from_df(data: pd.DataFrame, period: int = 14) -> pd.Series:
    delta = data["Close"].diff()
    gain  = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss  = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan).fillna(1e-10)
    return (100.0 - 100.0 / (1.0 + rs)).fillna(50.0)


# ─────────────────────────────────────────────────────────────────────────────
# (e) Pivot Points High / Low — Python port of Pine-Script ta.pivothigh/low
# ─────────────────────────────────────────────────────────────────────────────

def _pivot_highs_lows(
    data: pd.DataFrame,
    left: int = 3,
    right: int = 3,
) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    """
    Detect pivot highs and pivot lows.

    A bar at index i is a pivot HIGH when its High is the unique highest
    value in the window [i-left … i+right].  Same logic for LOW.

    Returns
    -------
    ph : list[(bar_index, price)]  — confirmed pivot highs
    pl : list[(bar_index, price)]  — confirmed pivot lows
    """
    highs = data["High"].values
    lows  = data["Low"].values
    n     = len(data)
    ph: list[tuple[int, float]] = []
    pl: list[tuple[int, float]] = []

    for i in range(left, n - right):
        h_win = highs[i - left : i + right + 1]
        if highs[i] == h_win.max() and int((h_win == highs[i]).sum()) == 1:
            ph.append((i, float(highs[i])))

        l_win = lows[i - left : i + right + 1]
        if lows[i] == l_win.min() and int((l_win == lows[i]).sum()) == 1:
            pl.append((i, float(lows[i])))

    return ph, pl


def detect_swing_structure(
    data: pd.DataFrame,
    left: int = 3,
    right: int = 3,
    min_pivots: int = 4,
) -> dict:
    """
    Classify the swing structure of the data into:
      'Uptrend (HH/HL)'   — majority of pivot highs are HH, pivot lows are HL
      'Downtrend (LL/LH)' — majority of pivot lows are LL, pivot highs are LH
      'Sideways'          — neither dominant

    Also returns the most-recent pivot low price (last HL candidate)
    and most-recent pivot high price (last LH candidate).
    """
    empty = {
        "trend": "Sideways",
        "last_hl_price": None,
        "last_lh_price": None,
        "ph_list": [],
        "pl_list": [],
    }

    needed = left + right + min_pivots * 2
    if data is None or len(data) < needed:
        return empty

    ph, pl = _pivot_highs_lows(data, left=left, right=right)

    if len(ph) < 2 or len(pl) < 2:
        return {**empty, "ph_list": ph, "pl_list": pl}

    # How many consecutive pairs are HH / LH / HL / LL
    hh = sum(1 for i in range(1, len(ph)) if ph[i][1] > ph[i - 1][1])
    lh = sum(1 for i in range(1, len(ph)) if ph[i][1] < ph[i - 1][1])
    hl = sum(1 for i in range(1, len(pl)) if pl[i][1] > pl[i - 1][1])
    ll = sum(1 for i in range(1, len(pl)) if pl[i][1] < pl[i - 1][1])

    pairs_h = len(ph) - 1
    pairs_l = len(pl) - 1

    is_up   = (pairs_h > 0 and pairs_l > 0
               and hh / pairs_h >= 0.55 and hl / pairs_l >= 0.55)
    is_down = (pairs_h > 0 and pairs_l > 0
               and lh / pairs_h >= 0.55 and ll / pairs_l >= 0.55)

    trend = ("Uptrend (HH/HL)" if is_up
             else "Downtrend (LL/LH)" if is_down
             else "Sideways")

    return {
        "trend":         trend,
        "last_hl_price": pl[-1][1] if pl else None,   # most-recent pivot low = HL candidate
        "last_lh_price": ph[-1][1] if ph else None,   # most-recent pivot high = LH candidate
        "ph_list":       ph,
        "pl_list":       pl,
    }


# ─────────────────────────────────────────────────────────────────────────────
# MA / crossover / divergence / volume helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ma_alignment(price: float, dma20: float, dma50: float) -> str:
    if pd.isna(dma20) or pd.isna(dma50):
        return "N/A"
    if price > dma20 > dma50:
        return "Bullish"
    if price < dma20 < dma50:
        return "Bearish"
    return "Mixed"


def _ma_crossover(dma20: float, dma50: float) -> str:
    if pd.isna(dma20) or pd.isna(dma50):
        return "N/A"
    diff_pct = abs((dma20 - dma50) / max(dma50, 1e-6) * 100)
    if diff_pct < 1.5:
        return "Bullish Crossover" if dma20 > dma50 else "Bearish Crossover"
    return "None"


def _detect_divergence(data: pd.DataFrame, rsi_series: pd.Series) -> str:
    if len(data) < 10:
        return "None"
    try:
        rh  = data["High"].tail(10).values
        rl  = data["Low"].tail(10).values
        rrs = rsi_series.tail(10).values
        if len(rrs) < 5 or np.isnan(rrs).all():
            return "None"
        if rl[-1] < rl[-3] and rrs[-1] > rrs[-3]:
            return "Bullish"
        if rh[-1] > rh[-3] and rrs[-1] < rrs[-3]:
            return "Bearish"
    except Exception:
        pass
    return "None"


def _volume_status(data: pd.DataFrame, lookback: int = 5) -> str:
    if "Volume" not in data.columns or len(data) < lookback * 2:
        return "N/A"
    try:
        rv  = data["Volume"].tail(lookback).mean()
        avg = data["Volume"].tail(lookback * 4).mean()
        return "High" if (avg > 0 and rv > avg * 1.2) else "Normal"
    except Exception:
        return "N/A"


# ─────────────────────────────────────────────────────────────────────────────
# (d) Price-position: where is the current price relative to last HL / LH?
# ─────────────────────────────────────────────────────────────────────────────

def _price_position(price: float, swing: dict, threshold_pct: float = 3.0) -> str:
    """
    'Near HL' — within threshold_pct% of last pivot low  → ideal bullish entry
    'Near LH' — within threshold_pct% of last pivot high → ideal bearish entry
    'Middle'  — neither
    """
    hl = swing.get("last_hl_price")
    lh = swing.get("last_lh_price")

    near_hl = hl is not None and abs(price - hl) / max(hl, 1e-6) * 100 <= threshold_pct
    near_lh = lh is not None and abs(price - lh) / max(lh, 1e-6) * 100 <= threshold_pct

    if near_hl and near_lh:
        return "Near HL" if abs(price - hl) <= abs(price - lh) else "Near LH"
    if near_hl:
        return "Near HL"
    if near_lh:
        return "Near LH"
    return "Middle"


# ─────────────────────────────────────────────────────────────────────────────
# (b) Bottom-N sectors helper — weak sectors for bearish picks
# ─────────────────────────────────────────────────────────────────────────────

def get_bottom_n_sectors_by_momentum(
    sector_data_dict: dict,
    momentum_weights: dict,
    n: int = 4,
) -> list:
    """
    Return the N sectors with the LOWEST RSI + CMF momentum.
    These are losing momentum — candidates for bearish stock selection.
    """
    if not sector_data_dict or len(sector_data_dict) < n:
        return list(sector_data_dict.keys()) if sector_data_dict else []

    scores: list = []
    try:
        from indicators import calculate_rsi, calculate_cmf
    except ImportError:
        return list(sector_data_dict.keys())

    for name, data in sector_data_dict.items():
        if data is None or len(data) < 14:
            continue
        try:
            rsi_s = calculate_rsi(data)
            cmf_s = calculate_cmf(data)
            scores.append({
                "Sector": name,
                "RSI": float(rsi_s.iloc[-1]) if not rsi_s.isna().all() else 50.0,
                "CMF": float(cmf_s.iloc[-1]) if not cmf_s.isna().all() else 0.0,
            })
        except Exception:
            continue

    if not scores:
        return list(sector_data_dict.keys())

    df = pd.DataFrame(scores)
    if len(df) > 1:
        rs = df["RSI"].std()
        cs = df["CMF"].std()
        rz = (df["RSI"] - df["RSI"].mean()) / rs if rs > 0 else 0.0
        cz = (df["CMF"] - df["CMF"].mean()) / cs if cs > 0 else 0.0
        df["Score"] = 0.5 * rz + 0.5 * cz
    else:
        df["Score"] = 0.0

    # ascending=True → weakest first
    return df.sort_values("Score", ascending=True).head(n)["Sector"].tolist()


# ─────────────────────────────────────────────────────────────────────────────
# Main analysis function
# ─────────────────────────────────────────────────────────────────────────────

def analyze_stock_confluence(
    data_1h_or_entry: pd.DataFrame,
    data_1d: pd.DataFrame | None,
    entry_timeframe: str = "2h",
) -> dict | None:
    """
    Build a per-stock analysis dict used by both scoring functions.

    (d) Pivot structure is built on the ENTRY TF only.
        Confirmation-TF trend is displayed but not scored (weight = 0).
    """
    try:
        if entry_timeframe in ("2h", "4h"):
            freq     = "2H" if entry_timeframe == "2h" else "4H"
            min_bars = 50
            data_entry = (
                data_1h_or_entry
                .resample(freq)
                .agg({"Open": "first", "High": "max", "Low": "min",
                      "Close": "last",  "Volume": "sum"})
                .dropna()
            )
        else:
            data_entry = data_1h_or_entry
            data_1d    = data_1h_or_entry
            min_bars   = 50

        if data_entry is None or len(data_entry) < min_bars:
            return None
        if data_1d is None or len(data_1d) < 30:
            return None

        data_entry = data_entry.copy()
        data_entry["DMA_20"] = data_entry["Close"].rolling(20).mean()
        data_entry["DMA_50"] = data_entry["Close"].rolling(50).mean()
        rsi_e_s = _calculate_rsi_from_df(data_entry)

        price_e = float(data_entry["Close"].iloc[-1])
        dma20_e = float(data_entry["DMA_20"].iloc[-1])
        dma50_e = float(data_entry["DMA_50"].iloc[-1])
        rsi_e   = float(rsi_e_s.iloc[-1]) if not rsi_e_s.isna().all() else 50.0
        rsi_ep  = float(rsi_e_s.iloc[-2]) if len(rsi_e_s.dropna()) >= 2 else rsi_e

        data_1d = data_1d.copy()
        data_1d["DMA_20"] = data_1d["Close"].rolling(20).mean()
        data_1d["DMA_50"] = data_1d["Close"].rolling(50).mean()
        rsi_d_s = _calculate_rsi_from_df(data_1d)

        price_d = float(data_1d["Close"].iloc[-1])
        dma20_d = float(data_1d["DMA_20"].iloc[-1])
        dma50_d = float(data_1d["DMA_50"].iloc[-1])
        rsi_d   = float(rsi_d_s.iloc[-1]) if not rsi_d_s.isna().all() else 50.0
        rsi_dp  = float(rsi_d_s.iloc[-2]) if len(rsi_d_s.dropna()) >= 2 else rsi_d

        pivot_window = min(80, len(data_entry))
        swing_e = detect_swing_structure(
            data_entry.tail(pivot_window), left=3, right=3, min_pivots=4
        )
        trend_entry = swing_e["trend"]

        pivot_window_d = min(80, len(data_1d))
        swing_d  = detect_swing_structure(
            data_1d.tail(pivot_window_d), left=3, right=3, min_pivots=4
        )
        trend_1d = swing_d["trend"]

        ma_e = _ma_alignment(price_e, dma20_e, dma50_e)
        ma_d = _ma_alignment(price_d, dma20_d, dma50_d)
        xo_e = _ma_crossover(dma20_e, dma50_e)
        div = _detect_divergence(data_entry, rsi_e_s)
        price_pos = _price_position(price_e, swing_e, threshold_pct=3.0)
        vol = _volume_status(data_entry)
        tf_lbl = "2H" if entry_timeframe == "2h" else ("4H" if entry_timeframe == "4h" else "1D")

        return {
            "current_price":      round(price_e, 2),
            "trend_entry":        trend_entry,
            "trend_1d":           trend_1d,
            "ma_alignment_entry": ma_e,
            "ma_alignment_1d":    ma_d,
            "ma_crossover_entry": xo_e,
            "rsi_entry":          round(rsi_e, 1),
            "rsi_entry_prev":     round(rsi_ep, 1),
            "rsi_1d":             round(rsi_d, 1),
            "rsi_1d_prev":        round(rsi_dp, 1),
            "divergence":         div,
            "price_position":     price_pos,
            "last_hl_price":      swing_e.get("last_hl_price"),
            "last_lh_price":      swing_e.get("last_lh_price"),
            "volume_status":      vol,
            "entry_tf_label":     tf_lbl,
        }

    except Exception:
        return None


def calculate_confluence_score_bullish(analysis: dict) -> tuple:
    """
    Bullish confluence.

    **Core requirements (gates):**
    - RSI rising on BOTH entry and confirmation timeframes
    - MA alignment Bullish on BOTH timeframes
    - Entry timeframe trend = Uptrend (HH/HL)
    - Price near the last HL pivot on the entry timeframe

    If any of these fail, the setup is treated as a failed bullish confluence and
    returned with a strongly negative score so it will not rank in the top list.
    """
    reasons: list = []

    # --- Core signals used by gates ---
    trend_entry = analysis["trend_entry"]
    ma_entry    = analysis["ma_alignment_entry"]
    ma_conf     = analysis["ma_alignment_1d"]

    pos      = analysis.get("price_position", "Middle")
    hl_price = analysis.get("last_hl_price")
    lh_price = analysis.get("last_lh_price")

    rsi_e   = analysis["rsi_entry"]
    rsi_ep  = analysis["rsi_entry_prev"]
    rsi_d   = analysis["rsi_1d"]
    rsi_dp  = analysis["rsi_1d_prev"]

    rising_entry = rsi_e > rsi_ep + 0.5
    rising_conf  = rsi_d > rsi_dp + 0.5
    ma_bull_entry = (ma_entry == "Bullish")
    ma_bull_conf  = (ma_conf == "Bullish")
    trend_ok      = (trend_entry == "Uptrend (HH/HL)")
    price_near_hl = (pos == "Near HL")

    core_fail_reasons = []
    if not (rising_entry and rising_conf):
        core_fail_reasons.append("RSI not rising on both entry and confirmation TFs")
    if not (ma_bull_entry and ma_bull_conf):
        core_fail_reasons.append("MA alignment not Bullish on both TFs")
    if not trend_ok:
        core_fail_reasons.append("Entry TF trend is not Uptrend (HH/HL)")
    if not price_near_hl:
        core_fail_reasons.append("Price not near HL pivot on entry TF")

    if core_fail_reasons:
        # Hard gate: treat as failed bullish setup so it never ranks in top confluence list
        msg = "; ".join(core_fail_reasons)
        return -5.0, [f"-5  Core bullish conditions failed: {msg}"]

    # --- Detailed scoring (only for setups passing the gates) ---
    score = 0.0

    # Trend on entry TF (higher TF for this confluence setup)
    score += 4
    reasons.append("+4  Uptrend (HH/HL) on entry TF")

    # MA alignment on entry & confirmation TFs (both already Bullish by gate)
    score += 3; reasons.append("+3  MA Bullish on entry TF")
    score += 2; reasons.append("+2  MA Bullish on conf TF")

    # Price relative to HL / LH pivot on entry TF
    if pos == "Near HL":
        score += 3
        lbl = f"{hl_price:.2f}" if hl_price else "?"
        reasons.append(f"+3  Price near HL pivot ({lbl}) — ideal BUY")
    elif pos == "Near LH":
        score -= 1
        lbl = f"{lh_price:.2f}" if lh_price else "?"
        reasons.append(f"−1  Price near LH pivot ({lbl}) — near resistance")
    else:
        score += 0.5; reasons.append("+0.5 Price in middle range")

    # RSI on entry TF
    rising  = rising_entry
    falling = rsi_e < rsi_ep - 0.5
    if rising and 40 <= rsi_e <= 70:
        score += 2;   reasons.append(f"+2  RSI rising in 40–70 zone ({rsi_e})")
    elif rising:
        score += 1;   reasons.append(f"+1  RSI rising ({rsi_e})")
    elif falling:
        score -= 1;   reasons.append(f"−1  RSI FALLING ({rsi_e}) — wrong for bullish")
    if rsi_e > 70:
        score -= 1;   reasons.append(f"−1  RSI overbought ({rsi_e})")
    elif rsi_e < 30 and rising:
        score += 0.5; reasons.append(f"+0.5 RSI oversold but turning up ({rsi_e})")

    # RSI on confirmation TF
    rsid  = rsi_d
    rsidp = rsi_dp
    if rsid > rsidp + 0.5 and 40 <= rsid <= 70:
        score += 1.5; reasons.append(f"+1.5 Conf RSI rising in 40–70 ({rsid})")
    elif rsid > rsidp + 0.5:
        score += 0.5; reasons.append(f"+0.5 Conf RSI rising ({rsid})")
    elif rsid < rsidp - 0.5:
        score -= 0.5; reasons.append(f"−0.5 Conf RSI falling ({rsid})")
    if rsid > 70:
        score -= 0.5; reasons.append(f"−0.5 Conf RSI overbought ({rsid})")

    # MA crossover & divergence / volume as supporting factors
    xo = analysis["ma_crossover_entry"]
    if xo == "Bullish Crossover":
        score += 1.5; reasons.append("+1.5 Bullish MA crossover forming")
    elif xo == "Bearish Crossover":
        score -= 1;   reasons.append("−1  Bearish MA crossover forming")

    div = analysis["divergence"]
    if div == "Bullish":
        score += 1.5; reasons.append("+1.5 Bullish RSI divergence")
    elif div == "Bearish":
        score -= 1;   reasons.append("−1  Bearish RSI divergence")

    vol = analysis.get("volume_status", "N/A")
    if vol == "High":
        score += 1;   reasons.append("+1  High volume")

    return round(score, 2), reasons


def calculate_confluence_score_bearish(analysis: dict) -> tuple:
    """Bearish confluence. RSI falling = positive; rising = penalty. Near LH = +3."""
    score = 0.0
    reasons: list = []

    t = analysis["trend_entry"]
    if t == "Downtrend (LL/LH)":
        score += 4;  reasons.append("+4  Downtrend (LL/LH) on entry TF")
    elif t == "Uptrend (HH/HL)":
        score -= 3;  reasons.append("−3  Uptrend on entry TF — penalised")
    else:
        score += 0.5; reasons.append("+0.5 Sideways entry TF")

    ma = analysis["ma_alignment_entry"]
    if ma == "Bearish":
        score += 3;  reasons.append("+3  MA Bearish on entry TF")
    elif ma == "Bullish":
        score -= 2;  reasons.append("−2  MA Bullish on entry TF")

    ma1 = analysis["ma_alignment_1d"]
    if ma1 == "Bearish":
        score += 2;  reasons.append("+2  MA Bearish on conf TF")
    elif ma1 == "Bullish":
        score -= 1;   reasons.append("−1  MA Bullish on conf TF")

    pos      = analysis.get("price_position", "Middle")
    hl_price = analysis.get("last_hl_price")
    lh_price = analysis.get("last_lh_price")
    if pos == "Near LH":
        score += 3
        lbl = f"{lh_price:.2f}" if lh_price else "?"
        reasons.append(f"+3  Price near LH pivot ({lbl}) — ideal SHORT")
    elif pos == "Near HL":
        score -= 2
        lbl = f"{hl_price:.2f}" if hl_price else "?"
        reasons.append(f"−2  Price near HL ({lbl}) — at support, too late to short")
    else:
        score += 0.5; reasons.append("+0.5 Price in middle range")

    rsi  = analysis["rsi_entry"]
    rsip = analysis["rsi_entry_prev"]
    falling = rsi < rsip - 0.5
    rising  = rsi > rsip + 0.5
    if pos == "Near LH":
        if 50 <= rsi <= 70 and falling:
            score += 2.5; reasons.append(f"+2.5 RSI rolling down from resistance zone ({rsi})")
        elif 50 <= rsi <= 70:
            score += 1.5; reasons.append(f"+1.5 RSI in resistance zone ({rsi})")
        elif rsi > 70:
            score += 1;   reasons.append(f"+1  RSI overbought at resistance ({rsi})")
        elif rsi < 30:
            score -= 1.5; reasons.append(f"−1.5 RSI oversold at LH — suspicious ({rsi})")
        elif rising:
            score -= 1;   reasons.append(f"−1  RSI RISING at resistance ({rsi})")
    else:
        if falling and 30 <= rsi <= 60:
            score += 2;   reasons.append(f"+2  RSI falling in 30–60 zone ({rsi})")
        elif falling:
            score += 1;   reasons.append(f"+1  RSI falling ({rsi})")
        elif rising:
            score -= 1;   reasons.append(f"−1  RSI RISING ({rsi}) — wrong for bearish")
        if rsi < 30:
            score -= 1;   reasons.append(f"−1  RSI oversold ({rsi}) — late entry")

    rsid  = analysis["rsi_1d"]
    rsidp = analysis["rsi_1d_prev"]
    if rsid < rsidp - 0.5 and 30 <= rsid <= 60:
        score += 1.5; reasons.append(f"+1.5 Conf RSI falling in 30–60 ({rsid})")
    elif rsid < rsidp - 0.5:
        score += 0.5; reasons.append(f"+0.5 Conf RSI falling ({rsid})")
    elif rsid > rsidp + 0.5:
        score -= 0.5; reasons.append(f"−0.5 Conf RSI rising ({rsid})")
    if rsid < 30:
        score -= 0.5; reasons.append(f"−0.5 Conf RSI oversold ({rsid})")

    xo = analysis["ma_crossover_entry"]
    if xo == "Bearish Crossover":
        score += 1.5; reasons.append("+1.5 Bearish MA crossover forming")
    elif xo == "Bullish Crossover":
        score -= 1;   reasons.append("−1  Bullish MA crossover forming")

    div = analysis["divergence"]
    if div == "Bearish":
        score += 1.5; reasons.append("+1.5 Bearish RSI divergence")
    elif div == "Bullish":
        score -= 1;   reasons.append("−1  Bullish RSI divergence")

    vol = analysis.get("volume_status", "N/A")
    if vol == "High" and pos == "Near LH":
        score += 1.5; reasons.append("+1.5 High volume at LH resistance (distribution)")
    elif vol == "High":
        score += 0.5; reasons.append("+0.5 High volume")

    return round(score, 2), reasons


def generate_entry_description(analysis: dict, score: float, is_bullish: bool = True) -> str:
    pos = analysis.get("price_position", "Middle")
    hl  = analysis.get("last_hl_price")
    lh  = analysis.get("last_lh_price")
    grade = (
        "EXCELLENT" if score >= 12
        else "GOOD"     if score >= 9
        else "MODERATE" if score >= 5
        else "WEAK"
    )
    if is_bullish:
        if pos == "Near HL":
            ref = f" ({hl:.2f})" if hl else ""
            return f"{grade}: Uptrend + Price at HL support{ref} + Rising RSI"
        elif pos == "Near LH":
            return f"{grade}: Uptrend but price near LH resistance — caution"
        return f"{grade}: Strong uptrend + Bullish alignment + Rising momentum"
    else:
        if pos == "Near LH":
            ref = f" ({lh:.2f})" if lh else ""
            return f"{grade}: Downtrend + Price at LH resistance{ref} + Falling RSI"
        elif pos == "Near HL":
            ref = f" ({hl:.2f})" if hl else ""
            return f"TOO LATE: Price at HL{ref} — missed SHORT entry"
        return f"{grade}: Downtrend + Bearish alignment + Falling momentum"
