"""
Data fetching module for NSE Market Sector Analysis Tool
Handles data retrieval from Yahoo Finance with caching and parallel fetching
Now integrated with local SQLite cache for 6M data + dynamic yfinance fallback
"""

import yfinance as yf
import warnings
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from datetime import datetime, timedelta
warnings.filterwarnings('ignore')

from config import MIN_DATA_POINTS

# Try to import local cache (optional)
try:
    from local_cache import get_cached_data, cache_data, should_update_cache, initialize_cache
    LOCAL_CACHE_AVAILABLE = True
    print("✅ Local cache module loaded successfully")
except ImportError as e:
    LOCAL_CACHE_AVAILABLE = False
    print(f"⚠️ Local cache not available: {e}")
except Exception as e:
    LOCAL_CACHE_AVAILABLE = False
    print(f"⚠️ Error loading local cache: {e}")

# Simple in-memory cache for data fetching
_data_cache = {}
_cache_ttl = 300  # 5 minutes TTL for cache

# Configuration for local cache
LOCAL_CACHE_DAYS = 180  # Keep 6 months locally


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
    Fetch historical data for a sector with hybrid caching strategy:
    1. Try local SQLite cache first (6M data)
    2. Fall back to yfinance if not in cache or data beyond 6M
    3. Update cache if fetched from yfinance
    
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
    
    # Check in-memory cache first (5 minute TTL)
    cache_key = _get_cache_key(symbol, period, end_date, interval)
    if use_cache and _is_cache_valid(cache_key):
        return _data_cache[cache_key].get('data')
    
    try:
        # Determine date range
        if end_date:
            actual_end_date = end_date + timedelta(days=1)
            
            if interval == '1h':
                start_date = end_date - timedelta(days=60)
            elif interval == '1wk':
                start_date = end_date - timedelta(days=400 if period == '1y' else 800)
            else:  # Daily
                start_date = end_date - timedelta(days=400 if period == '1y' else 800)
        else:
            actual_end_date = datetime.now() + timedelta(days=1)
            if interval == '1h':
                start_date = datetime.now() - timedelta(days=60)
                period = '60d'
            else:
                start_date = datetime.now() - timedelta(days=400)
        
        # For daily data within 6M, try local cache first
        data = None
        if LOCAL_CACHE_AVAILABLE and interval == '1d' and use_cache:
            try:
                cache_start = max(start_date, datetime.now() - timedelta(days=LOCAL_CACHE_DAYS))
                data = get_cached_data(symbol, cache_start, actual_end_date)
                
                if data is not None and len(data) >= min_data_points:
                    # Cache hit - return immediately
                    _data_cache[cache_key] = {'data': data, 'timestamp': datetime.now().timestamp()}
                    return data
            except Exception as cache_err:
                # Cache read failed, fall back to yfinance
                print(f"⚠️ Cache read failed for {symbol}: {cache_err}")
                data = None
        
        # Cache miss or non-daily: fetch from yfinance
        ticker = yf.Ticker(symbol)
        
        if end_date:
            data = ticker.history(start=start_date, end=actual_end_date, interval=interval)
        else:
            data = ticker.history(period=period, interval=interval)
        
        if data is None or data.empty:
            return None
        
        # Store in local cache if daily data (but don't fail if cache write fails)
        if LOCAL_CACHE_AVAILABLE and interval == '1d':
            try:
                cache_data(symbol, data, source='yfinance')
            except Exception as cache_err:
                print(f"⚠️ Cache write failed for {symbol}: {cache_err}")
        
        # Store in memory cache
        _data_cache[cache_key] = {'data': data, 'timestamp': datetime.now().timestamp()}
        
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


def fetch_nifty_broad_universe(min_stocks=750, use_cache=True):
    """
    Fetch a broad NSE universe (Nifty 500 + Midcap 150 + Smallcap 250) from NSE India
    to get at least min_stocks (default 750) for market breadth.
    
    Uses NSE official CSV downloads with session headers. Falls back to empty list
    if NSE blocks or CSV format changes.
    
    Returns:
        List of Yahoo Finance symbols (e.g. RELIANCE.NS). May be fewer than min_stocks
        if NSE returns less or only Nifty 500 is available.
    """
    import io
    try:
        import requests
        import pandas as pd
    except ImportError:
        return []
    
    if use_cache:
        try:
            cached = getattr(fetch_nifty_broad_universe, '_nifty_broad_cache', None)
            if cached is not None and len(cached) > 0:
                return cached
        except Exception:
            pass
    
    base_url = "https://www.nseindia.com"
    # NSE index constituent CSV URLs (500 + 150 + 250 + microcap 250 for larger universe)
    csv_urls = [
        ("https://www.nseindia.com/content/indices/ind_nifty500list.csv", "Symbol"),
        ("https://www.nseindia.com/content/indices/ind_niftymidcap150list.csv", "Symbol"),
        ("https://www.nseindia.com/content/indices/ind_niftysmallcap250list.csv", "Symbol"),
        ("https://www.nseindia.com/content/indices/ind_niftymicrocap250list.csv", "Symbol"),
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/csv,application/csv,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": base_url + "/",
    }
    
    all_symbols = set()
    session = requests.Session()
    session.headers.update(headers)
    
    try:
        # Establish session (NSE often requires a prior visit)
        session.get(base_url, timeout=10)
        for url, symbol_col in csv_urls:
            try:
                r = session.get(url, timeout=15)
                if r.status_code != 200:
                    continue
                try:
                    df = pd.read_csv(io.StringIO(r.text))
                except Exception:
                    continue
                # NSE CSV column: 'Symbol' or 'Company Symbol'
                col = None
                for c in ("Symbol", "Company Symbol", symbol_col):
                    if c in df.columns:
                        col = c
                        break
                if col is None and len(df.columns) > 0:
                    col = df.columns[0]
                for s in df[col].dropna().astype(str).str.strip():
                    if not s or s.upper() in ("SYMBOL", "NAN", ""):
                        continue
                    s = s.strip().upper()
                    if not s.endswith(".NS"):
                        s = s + ".NS"
                    all_symbols.add(s)
                if len(all_symbols) >= min_stocks:
                    break
            except Exception:
                continue
    except Exception:
        pass
    finally:
        try:
            session.close()
        except Exception:
            pass
    
    result = sorted(all_symbols)
    if len(result) > 0:
        try:
            fetch_nifty_broad_universe._nifty_broad_cache = result
        except Exception:
            pass
    return result


# ---------- Market breadth history (persist Advance/Decline etc. to avoid re-fetch and iteration) ----------
BREADTH_HISTORY_FILENAME = "market_breadth_history.csv"
BREADTH_HISTORY_COLUMNS = [
    "Date", "Day", "Advances", "Declines", "Advance/Total (%)",
    "Up 4% (Daily)", "Down 4% (Daily)",
    "% Above 10 DMA", "% Above 20 DMA", "% Above 40 DMA", "% Above 50 DMA",
    "Nifty", "Nifty Chg %", "VIX"
]


def load_breadth_history(filepath=None):
    """
    Load persisted market breadth rows from CSV.
    Returns dict: date_str (YYYY-MM-DD) -> row dict (same keys as breadth_data items).
    """
    import os
    try:
        import pandas as pd
    except ImportError:
        return {}
    if filepath is None:
        filepath = os.path.join(os.path.dirname(__file__), "data_cache", BREADTH_HISTORY_FILENAME)
    if not os.path.exists(filepath):
        return {}
    try:
        df = pd.read_csv(filepath)
        if "Date" not in df.columns or df.empty:
            return {}
        out = {}
        for _, row in df.iterrows():
            d = row.get("Date")
            if pd.isna(d):
                continue
            d = str(d).strip()
            if len(d) >= 10:
                d = d[:10]
            out[d] = row.to_dict()
        return out
    except Exception:
        return {}


def save_breadth_rows(filepath=None, rows=None):
    """
    Append/merge breadth rows into the history CSV (by Date). rows: list of dicts with Date key.
    """
    import os
    try:
        import pandas as pd
    except ImportError:
        return
    if filepath is None:
        filepath = os.path.join(os.path.dirname(__file__), "data_cache", BREADTH_HISTORY_FILENAME)
    if not rows:
        return
    try:
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    except Exception:
        pass
    try:
        existing = load_breadth_history(filepath)
        for r in rows:
            d = r.get("Date")
            if d in ("Current day", ""):
                from datetime import datetime
                d = datetime.now().strftime("%Y-%m-%d")
            if isinstance(d, str) and len(d) >= 10:
                d = d[:10]
            else:
                continue
            existing[d] = {k: r.get(k) for k in BREADTH_HISTORY_COLUMNS if k in r}
        df = pd.DataFrame(list(existing.values()))
        if not df.empty and "Date" in df.columns:
            df = df.sort_values("Date", ascending=False)
        df.to_csv(filepath, index=False)
    except Exception:
        pass
