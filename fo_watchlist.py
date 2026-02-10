"""
F&O Market watchlist configuration.

This is derived from the user's TradingView export:
    "_F&O (Sector_Wise) (1).txt"

We keep this module self‑contained so the app does NOT depend on
any files outside the project directory.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


# Raw text copied from the user's TradingView export
FO_RAW_TEXT = (
    "NSE:NIFTY,TVC:GOLD,NSE:BANKNIFTY,NSEIX:NIFTY1!,"
    "###SECTOR ETFS,"
    "NSE:METALIETF,NSE:BANKBEES,NSE:PVTBANIETF,NSE:FINIETF,NSE:ITBEES,"
    "NSE:AUTOBEES,NSE:OILIETF,NSE:MOENERGY,NSE:FMCGIETF,NSE:MOREALTY,"
    "###METALS (PARABOLIC MOVE - STOCHASTIC),"
    "NSE:CNXMETAL,NSE:TATASTEEL,NSE:JSWSTEEL,NSE:HINDALCO,NSE:NATIONALUM,"
    "NSE:HINDZINC,NSE:ADANIENT,NSE:JINDALSTEL,NSE:SAIL,NSE:NMDC,"
    "###PSUBNK,"
    "NSE:SBIN,NSE:UNIONBANK,NSE:BANKBARODA,NSE:PNB,NSE:CANBK,NSE:INDIANB,"
    "###PVTBNK,"
    "NSE:HDFCBANK,NSE:ICICIBANK,NSE:INDUSINDBK,NSE:IDFCFIRSTB,NSE:KOTAKBANK,"
    "NSE:AXISBANK,"
    "###CNXFINANCE (RESPECTS DIVERGENCE FOR MANY INDICATORS),"
    "NSE:CNXFINANCE,NSE:BAJFINANCE,NSE:CHOLAFIN,NSE:LTF,NSE:SHRIRAMFIN,"
    "NSE:ABCAPITAL,NSE:MUTHOOTFIN,NSE:MANAPPURAM,NSE:PNBHOUSING,"
    "###CONSUMER_DURABLE,"
    "NSE:TITAN,NSE:DIXON,NSE:HAVELLS,NSE:VOLTAS,NSE:BLUESTARCO,"
    "NSE:KAJARIACER,NSE:THANGAMAYL,NSE:PNGJL,NSE:KALYANKJIL,"
    "###IT (ADX +EMA),"
    "NSE:CNXIT,NSE:TCS,NSE:INFY,NSE:HCLTECH,NSE:WIPRO,NSE:PERSISTENT,"
    "NSE:COFORGE,NSE:LTTS,NSE:TECHM,"
    "###AUTO,"
    "NSE:CNXAUTO,NSE:ASHOKLEY,NSE:M&M,NSE:MARUTI,NSE:TMPV,NSE:BAJAJ_AUTO,"
    "NSE:EICHERMOT,NSE:TVSMOTOR,NSE:HEROMOTOCO,NSE:MOTHERSON,NSE:TIINDIA,"
    "NSE:BOSCHLTD,NSE:MRF,NSE:APOLLOTYRE,NSE:EXIDEIND,NSE:BALKRISIND,"
    "###FMCG,"
    "NSE:CNXFMCG,NSE:HINDUNILVR,NSE:DABUR,NSE:ITC,NSE:VBL,NSE:BRITANNIA,"
    "NSE:GODREJCP,NSE:TATACONSUM,NSE:MARICO,NSE:COLPAL,NSE:NESTLEIND,"
    "###ENERGY,"
    "NSE:CNXENERGY,NSE:RELIANCE,NSE:NTPC,NSE:POWERGRID,NSE:ONGC,"
    "NSE:TATAPOWER,NSE:ADANIGREEN,NSE:BPCL,NSE:IOC,NSE:GAIL,"
    "###INFRASTRUCTURE,"
    "NSE:CNXINFRA,NSE:BHARTIARTL,NSE:ADANIPORTS,NSE:INDIGO,NSE:LT,"
    "NSE:GRASIM,NSE:JSWENERGY,NSE:SIEMENS,NSE:CUMMINSIND,NSE:SHREECEM,"
    "NSE:CNXMNC,"
    "###MEDIA,"
    "NSE:CNXMEDIA,NSE:SUNTV,NSE:PVRINOX,"
    "###DEFENCE,"
    "NSE:NIFTY_IND_DEFENCE,NSE:MODEFENCE,NSE:HAL,NSE:BEL,NSE:MAZDOCK,"
    "NSE:SOLARINDS,NSE:BDL,"
    "###REALTY,"
    "NSE:CNXREALTY,NSE:DLF,NSE:OBEROIRLTY,NSE:PRESTIGE,NSE:BSE,"
    "NSE:DRREDDY,NSE:MCX,NSE:EMAMILTD,NSE:ASIANPAINT,NSE:HDFCLIFE"
)


@dataclass(frozen=True)
class FoSymbol:
    """Represents a single F&O symbol."""

    group: str           # TradingView group name (e.g. 'AUTO')
    tv_symbol: str       # Raw TradingView symbol, e.g. 'NSE:ASHOKLEY'
    yf_symbol: str       # yfinance / app symbol, e.g. 'ASHOKLEY.NS'


def _parse_raw_text(text: str) -> Dict[str, List[str]]:
    """Parse the TradingView export into {group_name: [raw_tokens...]}."""
    tokens = [t for t in text.split(",") if t]
    groups: Dict[str, List[str]] = {}
    current_group = "ROOT"

    for tok in tokens:
        tok = tok.strip()
        if tok.startswith("###"):
            current_group = tok.lstrip("#").strip()
            groups.setdefault(current_group, [])
        else:
            groups.setdefault(current_group, []).append(tok)

    return groups


def _tv_to_yf_symbol(tv_symbol: str) -> str | None:
    """
    Convert a TradingView 'NSE:XXXX' style symbol to our app/yfinance symbol.

    Rules:
    - Ignore non-NSE symbols.
    - Skip obvious indices / ETFs (CNX..., NIFTY..., ...IETF, ...BEES, etc.)
    - Replace '_' with '-' (e.g. BAJAJ_AUTO -> BAJAJ-AUTO).
    - Append '.NS' for NSE equities.
    """
    tv_symbol = tv_symbol.strip()
    if not tv_symbol.startswith("NSE:"):
        return None

    code = tv_symbol.split(":", 1)[1].strip()

    # Filter out indices / ETFs
    if (
        code.startswith("CNX")
        or code.startswith("NIFTY")
        or code.endswith("IETF")
        or code.endswith("BEES")
        or code in {"NIFTY1!", "BANKNIFTY", "METALIETF", "FINIETF", "ITBEES",
                    "AUTOBEES", "OILIETF", "MOENERGY", "FMCGIETF", "MOREALTY",
                    "MODEFENCE"}
    ):
        return None

    # Convert TradingView convention to NSE/yfinance
    code = code.replace("_", "-")
    return f"{code}.NS"


def build_fo_symbols() -> Tuple[Dict[str, List[FoSymbol]], List[FoSymbol]]:
    """
    Build F&O symbol structures.

    Returns:
        - groups: {group_name: [FoSymbol, ...]}
        - flat_list: [FoSymbol, ...] across all groups (deduplicated by yf_symbol)
    """
    raw_groups = _parse_raw_text(FO_RAW_TEXT)

    groups: Dict[str, List[FoSymbol]] = {}
    flat_by_yf: Dict[str, FoSymbol] = {}

    for group_name, tokens in raw_groups.items():
        # Skip non-stock groups
        if group_name in {"ROOT", "SECTOR ETFS"}:
            continue

        for tok in tokens:
            yf_symbol = _tv_to_yf_symbol(tok)
            if not yf_symbol:
                continue

            sym = FoSymbol(group=group_name, tv_symbol=tok, yf_symbol=yf_symbol)
            groups.setdefault(group_name, []).append(sym)

            # Deduplicate by yf symbol across groups
            if yf_symbol not in flat_by_yf:
                flat_by_yf[yf_symbol] = sym

    flat_list = list(flat_by_yf.values())
    return groups, flat_list


# Public, ready-to-use structures
FO_GROUPS, FO_SYMBOLS = build_fo_symbols()


# Optional helper: map TradingView group -> existing sector name
FO_GROUP_TO_SECTOR: Dict[str, str] = {
    "METALS (PARABOLIC MOVE - STOCHASTIC)": "Metal",
    "PSUBNK": "PSU Bank",
    "PVTBNK": "Pvt Bank",
    "CNXFINANCE (RESPECTS DIVERGENCE FOR MANY INDICATORS)": "Fin Services",
    "CONSUMER_DURABLE": "FMCG",            # Best approximate fit in current sectors
    "IT (ADX +EMA)": "IT",
    "AUTO": "Auto",
    "FMCG": "FMCG",
    "ENERGY": "Energy",
    "INFRASTRUCTURE": "Infra",
    "MEDIA": "Media",
    "DEFENCE": "Defence",
    "REALTY": "Realty",
}

