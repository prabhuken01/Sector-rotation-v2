"""
Configuration constants for NSE Market Sector Analysis Tool
"""

# Technical Indicator Periods
RSI_PERIOD = 14
ADX_PERIOD = 14
CMF_PERIOD = 20
MANSFIELD_RS_PERIOD = 250  # ~52 weeks for daily data

# Decimal Formatting (as per user preference)
DECIMAL_PLACES = {
    'RSI': 1,
    'ADX': 1,
    'ADX_Z': 1,
    'DI_Spread': 1,
    'CMF': 2,
    'RS_Rating': 1,
    'Mansfield_RS': 1,
    'Momentum_Score': 1,
    'Reversal_Score': 1
}

# NSE Sector Symbols (Indices)
SECTORS = {
    'Nifty 50': '^NSEI',
    'PSU Bank': '^NIFTYPSUBANK',
    'Pvt Bank': '^NIFTYBANK',
    'IT': '^CNXIT',
    'Pharma': '^CNXPHARMA',
    'FMCG': '^CNXFMCG',
    'Auto': '^CNXAUTO',
    'Metal': '^CNXMETAL',
    'Realty': '^CNXREALTY',
    'Media': '^CNXMEDIA',
    'Energy': '^CNXENERGY',
    'Infra': '^CNXINFRA',
    'Commodities': '^CNXCOMMODITIES',
    'Defence': '^CNXDEFENCE',
    'Oil & Gas': '^CNXOILGAS',
    'Nifty Oil & Gas': '^NIFTIT_OIL_AND_GAS',
    'Nifty India Defence': '^NIFTY_INFRA',  # Using Infra as proxy - Defence data limited
    'Nifty Fin Services Ex-Bank': '^NIFTYFINSERV'
}

# ETF Proxy Symbols (alternative to indices)
SECTOR_ETFS = {
    'Nifty 50': '^NSEI',  # No ETF for benchmark
    'PSU Bank': 'PSUBNKBEES.NS',
    'Pvt Bank': 'PVTBANIETF.NS',
    'IT': 'ITBEES.NS',
    'Pharma': 'PHARMABEES.NS',
    'FMCG': 'ICICIFMCG.NS',
    'Auto': 'AUTOBEES.NS',
    'Metal': 'METALIETF.NS',
    'Realty': 'MOREALTY.NS',
    'Media': '^CNXMEDIA',  # No ETF available
    'Energy': 'MOENERGY.NS',
    'Infra': 'INFRAIETF.NS',
    'Commodities': '^CNXCOMMODITIES',  # No ETF available
    'Defence': 'DEFENCEBEES.NS',
    'Oil & Gas': 'OILETF.NS',
    'Nifty Oil & Gas': '^NIFTY_OIL_AND_GAS',  # Limited data
    'Nifty India Defence': '^NIFTY_INFRA',  # Using Infra proxy
    'Nifty Fin Services Ex-Bank': '^NIFTYFINSERV'
}

# Analysis Thresholds
MIN_DATA_POINTS = 50
# For ranking-based momentum score, super bullish means top ~30% of sectors
# With ~15 sectors, this means top 4-5 sectors
# Threshold is calculated dynamically based on sector count
MOMENTUM_SCORE_PERCENTILE_THRESHOLD = 70  # Top 30% of sectors

# Default Scoring Weights (user-configurable)
# Momentum weights are percentages that sum to 100%
DEFAULT_MOMENTUM_WEIGHTS = {
    'ADX_Z': 20.0,
    'RS_Rating': 40.0,
    'RSI': 30.0,
    'DI_Spread': 10.0
}

DEFAULT_REVERSAL_WEIGHTS = {
    'RS_Rating': 40.0,
    'CMF': 40.0,
    'RSI': 10.0,
    'ADX_Z': 10.0
}

# Reversal Filter Thresholds
REVERSAL_BUY_DIV = {
    'RSI': 40,
    'ADX_Z': -0.5,
    'CMF': 0.1
}

REVERSAL_WATCH = {
    'RSI': 50,
    'ADX_Z': 0.5,
    'CMF': 0
}
