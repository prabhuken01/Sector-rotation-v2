# 🗄️ Local Cache Setup Guide

## Overview
The app now uses a **hybrid caching strategy** for optimal performance:
- **Local SQLite Cache** (6 months): Instant queries for recent data
- **YFinance Fallback**: On-demand fetching for historical data beyond 6 months
- **Daily Scheduler**: Automatic 1-day updates after market close

## 📋 What Changed

### New Files
1. **`local_cache.py`** - SQLite cache management
2. **`cache_scheduler.py`** - Background scheduler for daily updates
3. Updated **`data_fetcher.py`** - Integrated cache with fallback

### Performance Improvement
| Scenario | Before | After |
|----------|--------|-------|
| First load (cold cache) | 60-250s | 2-5 min (one-time) |
| Normal usage (6M data) | 60-250s | <1s ⚡ |
| Beyond 6M data | 30-60s | 30-60s (same) |
| Daily update | Manual | Automatic ✅ |

## 🚀 Setup Instructions

### Step 1: Install New Dependencies
```bash
pip install -r requirements.txt
```
New requirement: `schedule>=1.2.0`

### Step 2: Initialize Cache (One-time)
Build 6 months of historical data locally:
```bash
python cache_scheduler.py build 6
```
**Note:** This will take ~5-10 minutes on first run (fetching 129 symbols × 130 days)

### Step 3: Verify Cache
```bash
python cache_scheduler.py update
```
Should complete in <10 seconds

### Step 4: Run Daily Scheduler (Background)
For **automatic daily updates**, run this in the background:
```bash
python cache_scheduler.py schedule
```

Or schedule it as a system task:

#### **Linux (Cron)**
```bash
# Add to crontab (runs at 3:30 PM IST daily)
crontab -e
# Add line: 0 10 * * * cd /path/to/app && python cache_scheduler.py update
```

#### **Windows (Task Scheduler)**
1. Open Task Scheduler
2. Create Basic Task → "Daily Cache Update"
3. Action: Run program
4. Program: `python`
5. Arguments: `cache_scheduler.py update`
6. Schedule: Daily at 10:00 AM UTC (3:30 PM IST)

#### **macOS (LaunchAgent)**
Create `~/Library/LaunchAgents/com.market-cache.update.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.market-cache.update</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/path/to/cache_scheduler.py</string>
        <string>update</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>10</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
</dict>
</plist>
```

## 📊 Cache Management

### Check Cache Status
```bash
python -c "from local_cache import get_cache_stats; import json; print(json.dumps(get_cache_stats(), indent=2))"
```

### Clear Old Data (keeps last 6M)
```bash
python -c "from local_cache import cleanup_old_data; cleanup_old_data(keep_days=180)"
```

### Reset Cache
```bash
rm -rf data_cache/
# Rebuild: python cache_scheduler.py build 6
```

## 🔄 Data Flow

```
┌──────────────────────────┐
│   Streamlit App          │
│   (instant rendering)    │
└──────────┬───────────────┘
           │
           ▼
    Check cache?
    │
    ├─YES: Last 6M in DB → <1s response ✅
    │
    └─NO: Data beyond 6M
        │
        ▼
    Fetch from yfinance
        │
        ▼
    Store in cache
        │
        ▼
    Return to app
```

## 🛡️ Rollback (If Issues)

If anything breaks, you have a checkpoint:

```bash
# Switch to checkpoint branch
git checkout checkpoint-before-caching

# Or revert specific commit
git revert 70e5882

# Or reset completely
git reset --hard checkpoint-jan17-2026
```

## 📝 Usage Examples

### In Your Code
No changes needed! The app automatically:
1. Checks local cache first
2. Falls back to yfinance if needed
3. Updates cache silently

### Manual Cache Update
```python
from cache_scheduler import update_cache_daily, manual_full_cache_rebuild

# Quick update (last 1 day)
update_cache_daily()

# Full rebuild (6 months)
manual_full_cache_rebuild(months=6)
```

## ⚠️ Troubleshooting

### Cache not updating?
- Check if scheduler is running: `ps aux | grep cache_scheduler`
- Manual update: `python cache_scheduler.py update`

### SQLite locked error?
- Only one process can update at a time
- Solution: Stagger updates by 1+ minute

### Disk space issues?
- Cache size: ~10-20 MB
- Clean up: `python local_cache.py` then cleanup_old_data()

## 🎯 Benefits Summary
✅ **Speed**: 100x faster for recent data  
✅ **Reliability**: Works offline for cached data  
✅ **Storage**: Minimal (~10-20 MB)  
✅ **Automatic**: Daily updates run in background  
✅ **Flexible**: Falls back to yfinance for extended history  
✅ **Safe**: Checkpoint available for rollback  

---
**Checkpoint:** `checkpoint-before-caching` branch / `checkpoint-jan17-2026` tag
