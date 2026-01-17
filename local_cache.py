"""
Local Cache Manager - SQLite-based storage for market data
Stores 6 months of historical data locally with daily updates
Falls back to yfinance for data beyond 6 months
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os
import json
from pathlib import Path

# Cache database location
CACHE_DIR = Path('.') / 'data_cache'
CACHE_DB = CACHE_DIR / 'market_data.db'

# Configuration
LOCAL_CACHE_DAYS = 180  # Keep 6 months locally
MAX_CACHE_SIZE_MB = 100  # Max local cache size


def initialize_cache():
    """Initialize local SQLite database for market data caching."""
    CACHE_DIR.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(CACHE_DB)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            adj_close REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, date)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cache_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT UNIQUE NOT NULL,
            last_updated TEXT,
            data_range_start TEXT,
            data_range_end TEXT,
            source TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create indices for faster queries
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol_date ON market_data(symbol, date DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_date ON market_data(date DESC)')
    
    conn.commit()
    conn.close()


def get_cached_data(symbol, start_date, end_date):
    """
    Retrieve cached data for a symbol within date range.
    
    Args:
        symbol: Stock symbol
        start_date: Start date (datetime)
        end_date: End date (datetime)
        
    Returns:
        DataFrame with OHLCV data or None if not in cache
    """
    if not CACHE_DB.exists():
        return None
    
    try:
        conn = sqlite3.connect(CACHE_DB)
        conn.row_factory = sqlite3.Row
        
        query = '''
            SELECT date, open, high, low, close, volume, adj_close
            FROM market_data
            WHERE symbol = ? AND date BETWEEN ? AND ?
            ORDER BY date ASC
        '''
        
        df = pd.read_sql_query(
            query,
            conn,
            params=(symbol, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
        )
        
        conn.close()
        
        if df.empty:
            return None
        
        # Convert to proper types
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        
        return df
    except Exception as e:
        print(f"⚠️ Cache read error for {symbol}: {e}")
        return None


def cache_data(symbol, df, source='yfinance'):
    """
    Store market data in local cache.
    
    Args:
        symbol: Stock symbol
        df: DataFrame with OHLCV data (index is date)
        source: Data source identifier
    """
    if df is None or df.empty:
        return False
    
    try:
        initialize_cache()
        
        conn = sqlite3.connect(CACHE_DB)
        cursor = conn.cursor()
        
        # Reset index if it's named 'Date'
        df_insert = df.reset_index()
        if 'Date' in df_insert.columns:
            df_insert = df_insert.rename(columns={'Date': 'date'})
        elif df_insert.index.name == 'Date':
            df_insert.index.name = 'date'
            df_insert = df_insert.reset_index()
        
        # Add symbol column
        df_insert['symbol'] = symbol
        
        # Reorder and select columns
        df_insert = df_insert[['symbol', 'date', 'open', 'high', 'low', 'close', 'volume', 'adj_close']]
        df_insert['date'] = pd.to_datetime(df_insert['date']).dt.strftime('%Y-%m-%d')
        
        # Insert data (replace if exists)
        for _, row in df_insert.iterrows():
            cursor.execute('''
                INSERT OR REPLACE INTO market_data 
                (symbol, date, open, high, low, close, volume, adj_close)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', tuple(row))
        
        # Update metadata
        min_date = df_insert['date'].min()
        max_date = df_insert['date'].max()
        
        cursor.execute('''
            INSERT OR REPLACE INTO cache_metadata 
            (symbol, last_updated, data_range_start, data_range_end, source)
            VALUES (?, ?, ?, ?, ?)
        ''', (symbol, datetime.now().isoformat(), min_date, max_date, source))
        
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        print(f"⚠️ Cache write error for {symbol}: {e}")
        return False


def should_update_cache(symbol, days_old=1):
    """
    Check if cache needs updating for a symbol.
    
    Args:
        symbol: Stock symbol
        days_old: Days since last update to trigger refresh
        
    Returns:
        True if update needed, False otherwise
    """
    if not CACHE_DB.exists():
        return True
    
    try:
        conn = sqlite3.connect(CACHE_DB)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT last_updated FROM cache_metadata WHERE symbol = ?',
            (symbol,)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return True
        
        last_updated = datetime.fromisoformat(result[0])
        days_since = (datetime.now() - last_updated).days
        
        return days_since >= days_old
    except Exception as e:
        print(f"⚠️ Cache metadata check error for {symbol}: {e}")
        return True


def get_cache_stats():
    """Get cache statistics."""
    if not CACHE_DB.exists():
        return {"status": "No cache", "size_mb": 0}
    
    try:
        conn = sqlite3.connect(CACHE_DB)
        cursor = conn.cursor()
        
        # Count records
        cursor.execute('SELECT COUNT(*) FROM market_data')
        total_records = cursor.fetchone()[0]
        
        # Count symbols
        cursor.execute('SELECT COUNT(DISTINCT symbol) FROM market_data')
        total_symbols = cursor.fetchone()[0]
        
        # Get date range
        cursor.execute('SELECT MIN(date), MAX(date) FROM market_data')
        date_range = cursor.fetchone()
        
        conn.close()
        
        # File size
        size_mb = CACHE_DB.stat().st_size / (1024 * 1024)
        
        return {
            "status": "Active",
            "total_records": total_records,
            "total_symbols": total_symbols,
            "date_range": date_range,
            "size_mb": f"{size_mb:.2f}",
            "cache_db_path": str(CACHE_DB)
        }
    except Exception as e:
        return {"status": "Error", "error": str(e)}


def cleanup_old_data(keep_days=180):
    """Remove data older than keep_days from cache."""
    if not CACHE_DB.exists():
        return
    
    try:
        cutoff_date = (datetime.now() - timedelta(days=keep_days)).strftime('%Y-%m-%d')
        
        conn = sqlite3.connect(CACHE_DB)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM market_data WHERE date < ?', (cutoff_date,))
        deleted = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        if deleted > 0:
            print(f"✅ Cleaned up {deleted} old records from cache")
    except Exception as e:
        print(f"⚠️ Cleanup error: {e}")


if __name__ == '__main__':
    # Test cache
    initialize_cache()
    print("✅ Cache initialized")
    print(get_cache_stats())
