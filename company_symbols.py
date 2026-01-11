"""
Company Symbol Mappings for NSE Sectors
Static mapping of top 8-10 companies by weight in each sector/ETF
Weights are approximate based on latest index compositions
"""

# Top companies by weight in each sector/ETF
SECTOR_COMPANIES = {
    'Auto': {
        'MARUTI.NS': {'weight': 28.5, 'name': 'Maruti Suzuki'},
        'HEROMOTOCO.NS': {'weight': 12.3, 'name': 'Hero MotoCorp'},
        'BAJAJMOTO.NS': {'weight': 8.7, 'name': 'Bajaj Auto'},
        'TATAMOTORS.NS': {'weight': 8.2, 'name': 'Tata Motors'},
        'SUNPHARMA.NS': {'weight': 6.1, 'name': 'Sundram Fasteners'},
        'BOSCHIND.NS': {'weight': 5.8, 'name': 'Bosch India'},
        'ASHOKLEY.NS': {'weight': 4.5, 'name': 'Ashok Leyland'},
        'FORCEMOTORS.NS': {'weight': 3.2, 'name': 'Force Motors'},
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
        'HDFCBANK.NS': {'weight': 32.5, 'name': 'HDFC Bank'},
        'HDFC.NS': {'weight': 28.1, 'name': 'Housing Development'},
        'SBIN.NS': {'weight': 15.3, 'name': 'State Bank of India'},
        'ICICIBANK.NS': {'weight': 12.8, 'name': 'ICICI Bank'},
        'AXISBANK.NS': {'weight': 6.2, 'name': 'Axis Bank'},
        'KOTAKBANK.NS': {'weight': 3.1, 'name': 'Kotak Mahindra Bank'},
        'LT.NS': {'weight': 1.5, 'name': 'Larsen & Toubro'},
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
