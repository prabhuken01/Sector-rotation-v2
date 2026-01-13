"""
Data fetching module for NSE Market Sector Analysis Tool
Handles data retrieval from Yahoo Finance with caching and parallel fetching
"""

import yfinance as yf
import warnings
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from datetime import datetime, timedelta
warnings.filterwarnings('ignore')

from config import MIN_DATA_POINTS

# Simple in-memory cache for data fetching
_data_cache = {}
_cache_ttl = 300  # 5 minutes TTL for cache


def _get_cache_key(symbol, period, end_date, interval):
    """Generate a unique cache key for the request."""
    date_str = end_date.strftime('%Y-%m-%d') if end_date else 'latest'
    key_str = f"{symbol}_{period}_{date_str}_{interval}"
    return hashlib.md5(key_str.encode()).hexdigest()


def _is_cache_valid(cache_key):
    """Check if cached data is still valid."""
    if cache_key not in _data_cache:
        return False
    cached_time = _data_cache[cache_key].get('timestamp', 0)
    return (datetime.now().timestamp() - cached_time) < _cache_ttl


def clear_data_cache():
    """Clear the data cache."""
    global _data_cache
    _data_cache = {}


def fetch_sector_data(symbol, period='1y', min_data_points=MIN_DATA_POINTS, end_date=None, interval='1d', use_cache=True):
    """
    Fetch historical data for a sector using yfinance with caching.
    
    Args:
        symbol: Yahoo Finance symbol
        period: Time period for historical data (default '1y')
        min_data_points: Minimum required data points (default 50)
        end_date: End date for historical analysis (datetime object)
        interval: Data interval - '1h' (hourly), '1d' (daily), '1wk' (weekly)
        use_cache: Whether to use cached data if available (default True)
        
    Returns:
        DataFrame with OHLCV data or None if error/insufficient data
    """
    global _data_cache
    
    # Check cache first
    cache_key = _get_cache_key(symbol, period, end_date, interval)
    if use_cache and _is_cache_valid(cache_key):
        return _data_cache[cache_key].get('data')
    
    try:
        ticker = yf.Ticker(symbol)
        
        if end_date:
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
        
        # Cache the result
        _data_cache[cache_key] = {
            'data': data,
            'timestamp': datetime.now().timestamp()
        }
            
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


def fetch_all_sectors_parallel(sectors_dict, alternates_dict=None, period='1y', end_date=None, interval='1d', max_workers=8, progress_callback=None):
    """
    Fetch data for all sectors in parallel using ThreadPoolExecutor.
    
    Args:
        sectors_dict: Dictionary of sector names to symbols
        alternates_dict: Dictionary of sector names to alternate symbols (optional)
        period: Time period for historical data
        end_date: End date for historical analysis
        interval: Data interval
        max_workers: Maximum number of parallel threads (default 8)
        progress_callback: Optional callback function(sector_name, success, current, total)
        
    Returns:
        Tuple of (Dictionary mapping sector names to their data DataFrames, list of failed sectors)
    """
    sector_data = {}
    failed_sectors = []
    total = len(sectors_dict)
    completed = [0]  # Use list to allow modification in nested scope
    
    def fetch_single(sector_name, symbol):
        """Fetch a single sector's data."""
        alt_symbol = alternates_dict.get(sector_name) if alternates_dict else None
        data, used_symbol = fetch_sector_data_with_alternate(
            symbol, 
            alternate_symbol=alt_symbol,
            period=period,
            end_date=end_date, 
            interval=interval
        )
        return sector_name, data, used_symbol
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all fetch tasks
        futures = {
            executor.submit(fetch_single, name, sym): name 
            for name, sym in sectors_dict.items()
        }
        
        # Process results as they complete
        for future in as_completed(futures):
            completed[0] += 1
            try:
                sector_name, data, used_symbol = future.result()
                if data is not None and len(data) > 0:
                    sector_data[sector_name] = data
                    if progress_callback:
                        progress_callback(sector_name, True, completed[0], total)
                else:
                    failed_sectors.append(sector_name)
                    if progress_callback:
                        progress_callback(sector_name, False, completed[0], total)
            except Exception as e:
                sector_name = futures[future]
                failed_sectors.append(sector_name)
                if progress_callback:
                    progress_callback(sector_name, False, completed[0], total)
    
    return sector_data, failed_sectors
