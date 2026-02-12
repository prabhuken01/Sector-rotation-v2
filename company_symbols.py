"""
Company Symbol Mappings for NSE Sectors
Static mapping of top 8-10 companies by weight in each sector/ETF
Weights are approximate based on latest index compositions
"""

__all__ = ['SECTOR_COMPANIES', 'get_company_symbol_list', 'load_sector_companies_from_excel', 'load_sector_companies_from_csv', 'get_sector_company_table']

# Top companies by weight in each sector/ETF
SECTOR_COMPANIES = {
    'Auto': {
        'MARUTI.NS': {'weight': 28.5, 'name': 'Maruti Suzuki'},
        'HEROMOTOCO.NS': {'weight': 12.3, 'name': 'Hero MotoCorp'},
        'BAJAJ-AUTO.NS': {'weight': 8.7, 'name': 'Bajaj Auto'},
        'TATAMOTORS.NS': {'weight': 8.2, 'name': 'Tata Motors'},
        'SUNDRMFAST.NS': {'weight': 6.1, 'name': 'Sundram Fasteners'},
        'BOSCHLTD.NS': {'weight': 5.8, 'name': 'Bosch India'},
        'ASHOKLEY.NS': {'weight': 4.5, 'name': 'Ashok Leyland'},
        'FORCEMOT.NS': {'weight': 3.2, 'name': 'Force Motors'},
        'ELOETMENT.NS': {'weight': 2.8, 'name': 'Eicher Motors'},
    },
    'Commodities': {
        'HINDALCO.NS': {'weight': 25.3, 'name': 'Hindalco Industries'},
        'NMDC.NS': {'weight': 18.7, 'name': 'NMDC Limited'},
        'COALINDIA.NS': {'weight': 15.2, 'name': 'Coal India'},
        'FCL.NS': {'weight': 12.1, 'name': 'Fineotex Chemical'},
        'RATNAMANI.NS': {'weight': 8.9, 'name': 'Ratnamani Metals'},
        'JINDALSTEL.NS': {'weight': 7.8, 'name': 'Jindal Steel'},
        'VEDL.NS': {'weight': 6.4, 'name': 'Vedanta'},
        'MOIL.NS': {'weight': 5.6, 'name': 'Manganese Ore India'},
    },
    'Defence': {
        'BDL.NS': {'weight': 28.5, 'name': 'Bharat Dynamics'},
        'HAL.NS': {'weight': 25.3, 'name': 'Hindustan Aeronautics'},
        'MAZAGON.NS': {'weight': 18.7, 'name': 'Mazagon Dock'},
        'CONCOR.NS': {'weight': 12.8, 'name': 'Container Corporation'},
        'TIINDIA.NS': {'weight': 8.9, 'name': 'Thermax India'},
        'IEX.NS': {'weight': 3.2, 'name': 'Indian Energy'},
        'NTPC.NS': {'weight': 2.6, 'name': 'NTPC'},
    },
    'Energy': {
        'RELIANCE.NS': {'weight': 35.2, 'name': 'Reliance Industries'},
        'NTPC.NS': {'weight': 18.9, 'name': 'NTPC Limited'},
        'POWERGRID.NS': {'weight': 12.3, 'name': 'Power Grid'},
        'IBREALEST.NS': {'weight': 8.7, 'name': 'IB Realtime'},
        'MANAPPURAM.NS': {'weight': 6.5, 'name': 'Manappuram Finance'},
        'BEL.NS': {'weight': 5.2, 'name': 'Bharat Electronics'},
        'INDIGO.NS': {'weight': 4.1, 'name': 'IndiGo'},
        'SBIN.NS': {'weight': 3.8, 'name': 'State Bank of India'},
    },
    'FMCG': {
        'ITC.NS': {'weight': 22.3, 'name': 'ITC Limited'},
        'NESTLEIND.NS': {'weight': 18.9, 'name': 'Nestle India'},
        'HUL.NS': {'weight': 17.5, 'name': 'Hindustan Unilever'},
        'MARICO.NS': {'weight': 12.1, 'name': 'Marico'},
        'BRITANNIA.NS': {'weight': 10.8, 'name': 'Britannia Industries'},
        'GODREJIND.NS': {'weight': 8.2, 'name': 'Godrej Industries'},
        'EMAMILTD.NS': {'weight': 5.6, 'name': 'Emami Limited'},
        'COLPAL.NS': {'weight': 4.6, 'name': 'Colgate-Palmolive'},
    },
    'IT': {
        'TCS.NS': {'weight': 20.5, 'name': 'Tata Consultancy Services'},
        'INFY.NS': {'weight': 18.2, 'name': 'Infosys'},
        'WIPRO.NS': {'weight': 12.1, 'name': 'Wipro'},
        'TECHM.NS': {'weight': 9.8, 'name': 'Tech Mahindra'},
        'LT.NS': {'weight': 8.5, 'name': 'Larsen & Toubro'},
        'HCL.NS': {'weight': 7.3, 'name': 'HCL Technologies'},
        'MPHASIS.NS': {'weight': 5.2, 'name': 'Mphasis'},
        'LTTS.NS': {'weight': 4.1, 'name': 'LT Technologies'},
    },
    'Infra': {
        'LT.NS': {'weight': 24.3, 'name': 'Larsen & Toubro'},
        'IRFC.NS': {'weight': 15.8, 'name': 'Indian Railway Finance'},
        'NHPC.NS': {'weight': 12.5, 'name': 'NHPC Limited'},
        'POWERGRID.NS': {'weight': 11.2, 'name': 'Power Grid'},
        'BPCL.NS': {'weight': 9.7, 'name': 'Bharat Petroleum'},
        'ICCBANK.NS': {'weight': 8.1, 'name': 'ICC Bank'},
        'REC.NS': {'weight': 6.4, 'name': 'REC Limited'},
        'SCCL.NS': {'weight': 5.0, 'name': 'South Coast Commerce'},
    },
    'Media': {
        'INDIGO.NS': {'weight': 22.1, 'name': 'IndiGo'},
        'SONYLTV.NS': {'weight': 18.5, 'name': 'Sony TV'},
        'STARTECH.NS': {'weight': 14.3, 'name': 'Star Tech'},
        'ZEEL.NS': {'weight': 12.8, 'name': 'Zee Entertainment'},
        'TVTODAY.NS': {'weight': 10.2, 'name': 'TV Today'},
        'NETWORK18.NS': {'weight': 8.9, 'name': 'Network 18'},
        'ICIBANK.NS': {'weight': 6.5, 'name': 'ICICI Bank'},
        'HDFCBANK.NS': {'weight': 4.7, 'name': 'HDFC Bank'},
    },
    'Metal': {
        'TATASTEEL.NS': {'weight': 28.9, 'name': 'Tata Steel'},
        'HINDALCO.NS': {'weight': 24.5, 'name': 'Hindalco Industries'},
        'JSWSTEEL.NS': {'weight': 18.7, 'name': 'JSW Steel'},
        'NMDC.NS': {'weight': 12.3, 'name': 'NMDC Limited'},
        'VEDL.NS': {'weight': 8.6, 'name': 'Vedanta'},
        'JINDALSTEL.NS': {'weight': 3.2, 'name': 'Jindal Steel'},
        'MOIL.NS': {'weight': 2.1, 'name': 'Manganese Ore India'},
    },
    'Fin Services': {
        # FINIETF = Financial Services Ex-Bank ETF - NBFC, Insurance, Capital Markets
        # Excludes banks, which are tracked separately in 'PSU Bank' and 'Pvt Bank' sectors
        'BAJFINANCE.NS': {'weight': 15.40, 'name': 'Bajaj Finance Ltd.'},
        'SHRIRAMFIN.NS': {'weight': 8.20, 'name': 'Shriram Finance Ltd.'},
        'BAJAJFINSV.NS': {'weight': 6.85, 'name': 'Bajaj Finserv Ltd.'},
        'BSE.NS': {'weight': 6.32, 'name': 'BSE Ltd.'},
        'JIOFIN.NS': {'weight': 5.68, 'name': 'Jio Financial Services Ltd.'},
        'SBILIFE.NS': {'weight': 5.37, 'name': 'SBI Life Insurance Company'},
        'HDFCLIFE.NS': {'weight': 4.74, 'name': 'HDFC Life Insurance Company'},
        'CHOLAFIN.NS': {'weight': 4.23, 'name': 'Cholamandalam Inv. & Fin.'},
        'POLICYBZR.NS': {'weight': 3.66, 'name': 'PB Fintech (Policybazaar)'},
        'MCX.NS': {'weight': 3.34, 'name': 'MCX India Ltd.'},
    },
    'Pharma': {
        'SUNPHARMA.NS': {'weight': 18.5, 'name': 'Sun Pharmaceutical'},
        'LUPIN.NS': {'weight': 14.2, 'name': 'Lupin Limited'},
        'CIPLA.NS': {'weight': 12.8, 'name': 'Cipla'},
        'DRREDDY.NS': {'weight': 11.5, 'name': 'Dr. Reddy\'s Labs'},
        'AUROPHARMA.NS': {'weight': 9.7, 'name': 'Aurobindo Pharma'},
        'DIVISLAB.NS': {'weight': 8.3, 'name': 'Divi\'s Laboratories'},
        'IPCALAB.NS': {'weight': 6.9, 'name': 'IPCA Laboratories'},
        'ALEMBICPHARM.NS': {'weight': 5.8, 'name': 'Alembic Pharma'},
    },
    'PSU Bank': {
        'SBIN.NS': {'weight': 38.2, 'name': 'State Bank of India'},
        'CENTRALBANK.NS': {'weight': 18.5, 'name': 'Central Bank'},
        'BANKBARODA.NS': {'weight': 15.3, 'name': 'Bank of Baroda'},
        'INDIANBANK.NS': {'weight': 12.1, 'name': 'Indian Bank'},
        'CANBANK.NS': {'weight': 9.8, 'name': 'Canara Bank'},
        'UNIONBANK.NS': {'weight': 4.2, 'name': 'Union Bank'},
        'PNBHOUSING.NS': {'weight': 1.9, 'name': 'PNB Housing'},
    },
    'Pvt Bank': {
        'HDFCBANK.NS': {'weight': 28.5, 'name': 'HDFC Bank'},
        'ICICIBANK.NS': {'weight': 24.3, 'name': 'ICICI Bank'},
        'AXISBANK.NS': {'weight': 18.7, 'name': 'Axis Bank'},
        'KOTAKBANK.NS': {'weight': 15.2, 'name': 'Kotak Mahindra Bank'},
        'IDFCBANK.NS': {'weight': 7.8, 'name': 'IDFC Bank'},
        'INDUSIND.NS': {'weight': 4.2, 'name': 'IndusInd Bank'},
        'HDFCAMC.NS': {'weight': 1.3, 'name': 'HDFC Asset Management'},
    },
    'Realty': {
        'DLF.NS': {'weight': 22.8, 'name': 'DLF Limited'},
        'SUNTECK.NS': {'weight': 18.5, 'name': 'Sunteck Realty'},
        'OBEROYREALTY.NS': {'weight': 14.2, 'name': 'Oberoi Realty'},
        'PRESTIGE.NS': {'weight': 11.9, 'name': 'Prestige Estates'},
        'LODHA.NS': {'weight': 10.3, 'name': 'Lodha Group'},
        'BRIGADE.NS': {'weight': 8.1, 'name': 'Brigade Enterprises'},
        'GODREJPROP.NS': {'weight': 6.8, 'name': 'Godrej Properties'},
        'MAHINDRALOG.NS': {'weight': 5.2, 'name': 'Mahindra Logistics'},
    },
    'Oil & Gas': {
        'RELIANCE.NS': {'weight': 45.2, 'name': 'Reliance Industries'},
        'BPCL.NS': {'weight': 22.3, 'name': 'Bharat Petroleum'},
        'IOCL.NS': {'weight': 18.5, 'name': 'Indian Oil Corporation'},
        'ONGC.NS': {'weight': 10.2, 'name': 'Oil and Natural Gas'},
        'GAIL.NS': {'weight': 3.8, 'name': 'Gas Authority of India'},
    },
    'Nifty 50': {
        'RELIANCE.NS': {'weight': 12.5, 'name': 'Reliance Industries'},
        'TCS.NS': {'weight': 9.8, 'name': 'Tata Consultancy Services'},
        'HDFCBANK.NS': {'weight': 8.2, 'name': 'HDFC Bank'},
        'INFY.NS': {'weight': 7.5, 'name': 'Infosys'},
        'ICICIBANK.NS': {'weight': 6.3, 'name': 'ICICI Bank'},
        'SBIN.NS': {'weight': 5.1, 'name': 'State Bank of India'},
        'WIPRO.NS': {'weight': 4.2, 'name': 'Wipro'},
        'LT.NS': {'weight': 3.8, 'name': 'Larsen & Toubro'},
    },
}

def get_sector_companies(sector_name):
    """Get companies for a sector."""
    return SECTOR_COMPANIES.get(sector_name, {})

def get_all_sectors():
    """Get all sector names."""
    return list(SECTOR_COMPANIES.keys())

def get_company_symbol_list(sector_name):
    """Get list of company symbols for a sector."""
    companies = SECTOR_COMPANIES.get(sector_name, {})
    return list(companies.keys())


def get_sector_company_table():
    """
    Return sector/company data as a list of dicts for display.
    Keys: Sector, Company Name, Symbol, Weight (%).
    """
    rows = []
    for sector in sorted(SECTOR_COMPANIES.keys()):
        for symbol, info in SECTOR_COMPANIES[sector].items():
            rows.append({
                'Sector': sector,
                'Company Name': info.get('name', symbol),
                'Symbol': symbol,
                'Weight (%)': info.get('weight', 0),
            })
    return rows


def _build_sector_companies_from_df(df):
    """
    Build SECTOR_COMPANIES-style dict from a DataFrame with columns:
    Sector, Company Name, Symbol, Weight (%).
    Skips rows with blank Symbol. Uses 0 for blank Weight.
    Ensures no company (Symbol) appears in two sectors; first occurrence wins.
    """
    import pandas as pd
    result = {}
    seen_symbols = {}  # symbol -> (sector, name) for duplicate check
    for _, row in df.iterrows():
        sector = row.get('Sector')
        name = row.get('Company Name', '')
        symbol = row.get('Symbol')
        weight = row.get('Weight (%)', 0)
        if pd.isna(symbol) or (isinstance(symbol, str) and not str(symbol).strip()):
            continue
        symbol = str(symbol).strip()
        if sector not in result:
            result[sector] = {}
        if symbol in seen_symbols:
            prev_sector, prev_name = seen_symbols[symbol]
            print(f"[WARN] Symbol {symbol} appears in both '{prev_sector}' and '{sector}'; keeping first only.")
            continue
        seen_symbols[symbol] = (sector, name)
        try:
            w = float(weight) if not (pd.isna(weight) or (isinstance(weight, str) and not str(weight).strip())) else 0.0
        except (TypeError, ValueError):
            w = 0.0
        result[sector][symbol] = {'name': str(name) if not pd.isna(name) else symbol, 'weight': w}
    return result if result else None


def load_sector_companies_from_csv(csv_file='sector_company.csv'):
    """
    Load sector-company mappings from CSV.
    Columns: Sector, Company Name, Symbol, Weight (%).
    Returns dict matching SECTOR_COMPANIES format, or None if file doesn't exist.
    """
    try:
        import pandas as pd
        import os
        if not os.path.exists(csv_file):
            return None
        df = pd.read_csv(csv_file)
        for col in ['Sector', 'Company Name', 'Symbol', 'Weight (%)']:
            if col not in df.columns:
                print(f"[WARN] CSV missing column '{col}'; skipping load.")
                return None
        return _build_sector_companies_from_df(df)
    except Exception as e:
        print(f"Could not load CSV file {csv_file}: {e}")
        return None


def load_sector_companies_from_excel(excel_file='Sector-Company.xlsx'):
    """
    Load sector-company mappings from Excel file.
    Excel format: Sector | Company Name | Symbol | Weight(%)
    Blank Symbol rows are skipped; blank Weight treated as 0.
    Returns dict matching SECTOR_COMPANIES format, or None if file doesn't exist.
    """
    try:
        import pandas as pd
        import os
        if not os.path.exists(excel_file):
            return None
        df = pd.read_excel(excel_file)
        for col in ['Sector', 'Company Name', 'Symbol', 'Weight (%)']:
            if col not in df.columns:
                print(f"[WARN] Excel missing column '{col}'; skipping load.")
                return None
        return _build_sector_companies_from_df(df)
    except Exception as e:
        print(f"Could not load Excel file: {e}")
        return None


# Load order: sector_company.csv first (canonical 135-stock from Sector-company-v2; always in repo),
# then Sector-Company.xlsx if present, then the built-in defaults.
_loaded_source = None
_csv_data = load_sector_companies_from_csv('sector_company.csv')
if _csv_data is not None:
    SECTOR_COMPANIES = _csv_data
    _loaded_source = 'sector_company.csv'
    print("[OK] Loaded sector-company data from sector_company.csv")
else:
    _excel_data = load_sector_companies_from_excel('Sector-Company.xlsx')
    if _excel_data is not None:
        SECTOR_COMPANIES = _excel_data
        _loaded_source = 'Sector-Company.xlsx'
        print("[OK] Loaded sector-company data from Sector-Company.xlsx")


# ---------------------------------------------------------------------------
# F&O LIST INTEGRATION (NON-DESTRUCTIVE)
# ---------------------------------------------------------------------------
# If the user updates the F&O TradingView list, we only ADD new companies
# into existing sectors based on FO_GROUP_TO_SECTOR mapping. We never
# remove or overwrite existing mappings.
try:
    from fo_watchlist import FO_GROUPS, FO_GROUP_TO_SECTOR

    for group_name, symbols in FO_GROUPS.items():
        sector_name = FO_GROUP_TO_SECTOR.get(group_name)
        if not sector_name:
            continue

        # Ensure sector exists; if not, skip (we do NOT create new sectors here)
        sector_dict = SECTOR_COMPANIES.get(sector_name)
        if sector_dict is None:
            continue

        for fo_symbol in symbols:
            yf_symbol = fo_symbol.yf_symbol
            if yf_symbol not in sector_dict:
                # Add with minimal metadata; user can refine weights via Excel later
                clean_name = yf_symbol.replace(".NS", "")
                sector_dict[yf_symbol] = {
                    'weight': 0.0,
                    'name': clean_name,
                }
except Exception:
    # F&O integration is best-effort only; never block app startup
    pass
