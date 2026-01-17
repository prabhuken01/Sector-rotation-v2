"""
Background Scheduler for Daily Cache Updates
Runs daily after market close to update latest 1 day of data
Can be run as a scheduled task (cron, Task Scheduler, etc.)
"""

import schedule
import time
from datetime import datetime, timedelta
import yfinance as yf
from local_cache import cache_data, should_update_cache, initialize_cache, get_cache_stats
from config import SECTORS
from company_symbols import SECTOR_COMPANIES


def update_cache_daily():
    """Update cache with latest 1 day of market data for all symbols."""
    print(f"\n📅 Starting daily cache update at {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    
    initialize_cache()
    
    # Get all symbols
    all_symbols = list(SECTORS.values()) + [
        symbol for sector_companies in SECTOR_COMPANIES.values() 
        for symbol in sector_companies.keys()
    ]
    
    updated_count = 0
    failed_count = 0
    
    for symbol in all_symbols:
        try:
            # Fetch last 2 days (to ensure we get today's data)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=2)
            
            print(f"  Updating {symbol}...", end=" ")
            
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date, interval='1d')
            
            if data is not None and not data.empty:
                # Clean column names
                data.columns = [col.lower().replace(' ', '_') for col in data.columns]
                cache_data(symbol, data, source='yfinance-daily-update')
                print("✅")
                updated_count += 1
            else:
                print("⚠️ No data")
                failed_count += 1
        except Exception as e:
            print(f"❌ Error: {str(e)[:30]}")
            failed_count += 1
    
    print(f"\n✅ Daily update complete: {updated_count} updated, {failed_count} failed")
    print(f"Cache stats: {get_cache_stats()}")


def schedule_daily_updates(hour=15, minute=30):
    """
    Schedule daily cache updates at specified time (IST).
    Default: 3:30 PM IST (after NSE market close at 3:30 PM)
    
    Args:
        hour: Hour in 24-hour format (0-23)
        minute: Minute (0-59)
    """
    time_str = f"{hour:02d}:{minute:02d}"
    schedule.every().day.at(time_str).do(update_cache_daily)
    
    print(f"📅 Cache update scheduled daily at {time_str} IST")
    
    # Run scheduler loop (call this in background)
    while True:
        schedule.run_pending()
        time.sleep(60)


def manual_full_cache_rebuild(months=6):
    """
    Manually rebuild full cache with 6 months of historical data.
    Use this for initial setup or cache reset.
    
    Args:
        months: Number of months of history to cache
    """
    print(f"\n🔄 Starting full cache rebuild ({months} months of data)...")
    
    initialize_cache()
    
    # Get all symbols
    all_symbols = list(SECTORS.values()) + [
        symbol for sector_companies in SECTOR_COMPANIES.values() 
        for symbol in sector_companies.keys()
    ]
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30 * months)
    
    print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Symbols to fetch: {len(all_symbols)}\n")
    
    updated_count = 0
    failed_count = 0
    
    for i, symbol in enumerate(all_symbols, 1):
        try:
            print(f"  [{i}/{len(all_symbols)}] Fetching {symbol}...", end=" ")
            
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date, interval='1d')
            
            if data is not None and not data.empty:
                # Clean column names
                data.columns = [col.lower().replace(' ', '_') for col in data.columns]
                cache_data(symbol, data, source='yfinance-initial-cache')
                print(f"✅ ({len(data)} days)")
                updated_count += 1
            else:
                print("⚠️ No data")
                failed_count += 1
        except Exception as e:
            print(f"❌ {str(e)[:30]}")
            failed_count += 1
        
        # Brief pause to avoid overwhelming yfinance
        time.sleep(0.5)
    
    print(f"\n✅ Cache rebuild complete!")
    print(f"Summary: {updated_count} symbols cached, {failed_count} failed")
    print(f"Final cache stats: {get_cache_stats()}")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'build':
            months = int(sys.argv[2]) if len(sys.argv) > 2 else 6
            manual_full_cache_rebuild(months=months)
        elif sys.argv[1] == 'update':
            update_cache_daily()
        elif sys.argv[1] == 'schedule':
            schedule_daily_updates()
    else:
        print("Usage:")
        print("  python cache_scheduler.py build [months]     - Build initial cache (default 6 months)")
        print("  python cache_scheduler.py update              - Update cache with latest 1 day")
        print("  python cache_scheduler.py schedule            - Run scheduler (background)")
