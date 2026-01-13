"""
Data fetching module for NSE Market Sector Analysis Tool
Handles data retrieval from Yahoo Finance
"""

import yfinance as yf
import warnings
warnings.filterwarnings('ignore')

from config import MIN_DATA_POINTS


def fetch_sector_data(symbol, period='1y', min_data_points=MIN_DATA_POINTS, end_date=None, interval='1d'):
    """
    Fetch historical data for a sector using yfinance.
    
    Args:
        symbol: Yahoo Finance symbol
        period: Time period for historical data (default '1y')
        min_data_points: Minimum required data points (default 50)
        end_date: End date for historical analysis (datetime object)
        interval: Data interval - '1h' (hourly), '1d' (daily), '1wk' (weekly)
        
    Returns:
        DataFrame with OHLCV data or None if error/insufficient data
    """
    try:
        ticker = yf.Ticker(symbol)
        
        if end_date:
            # Calculate start date based on period, interval, and end date
            from datetime import timedelta
            
            # Yahoo Finance's history() returns data up to but NOT including end_date
            # So we add 1 day to ensure we get data for the requested date
            actual_end_date = end_date + timedelta(days=1)
            
            # Adjust period based on interval
            if interval == '1h':
                # Hourly data: max 730 days (2 years) on Yahoo Finance
                start_date = end_date - timedelta(days=60)  # 60 days for hourly
            elif interval == '1wk':
                # Weekly data: longer history
                if period == '1y':
                    start_date = end_date - timedelta(days=400)
                else:
                    start_date = end_date - timedelta(days=800)
            else:  # Daily
                if period == '1y':
                    start_date = end_date - timedelta(days=400)
                elif period == '2y':
                    start_date = end_date - timedelta(days=800)
                else:
                    start_date = end_date - timedelta(days=400)
            
            data = ticker.history(start=start_date, end=actual_end_date, interval=interval)
        else:
            # Adjust period for hourly data
            if interval == '1h':
                period = '60d'  # Max ~60 days for hourly data
            data = ticker.history(period=period, interval=interval)
        
        if data.empty:
            return None
            
        # Clean data
        data = data.dropna()
        
        if len(data) < min_data_points:
            return None
            
        return data
        
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None


def fetch_sector_data_with_alternate(symbol, alternate_symbol=None, period='1y', min_data_points=MIN_DATA_POINTS, end_date=None, interval='1d'):
    """
    Fetch historical data for a sector, trying primary symbol first, then alternate if available.
    
    Args:
        symbol: Primary Yahoo Finance symbol
        alternate_symbol: Alternate symbol to try if primary fails (optional)
        period: Time period for historical data (default '1y')
        min_data_points: Minimum required data points (default 50)
        end_date: End date for historical analysis (datetime object)
        interval: Data interval - '1h' (hourly), '1d' (daily), '1wk' (weekly)
        
    Returns:
        Tuple of (DataFrame with OHLCV data or None, symbol used)
    """
    # Try primary symbol
    data = fetch_sector_data(symbol, period, min_data_points, end_date, interval)
    if data is not None:
        return data, symbol
    
    # If primary failed and alternate is available, try alternate
    if alternate_symbol and alternate_symbol != 'N/A':
        data = fetch_sector_data(alternate_symbol, period, min_data_points, end_date, interval)
        if data is not None:
            return data, alternate_symbol
    
    return None, None


def fetch_all_sectors(sectors_dict, period='1y'):
    """
    Fetch data for all sectors.
    
    Args:
        sectors_dict: Dictionary of sector names to symbols
        period: Time period for historical data
        
    Returns:
        Dictionary mapping sector names to their data DataFrames
    """
    sector_data = {}
    
    for sector_name, symbol in sectors_dict.items():
        data = fetch_sector_data(symbol, period)
        if data is not None:
            sector_data[sector_name] = data
            
    return sector_data
