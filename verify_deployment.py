#!/usr/bin/env python3
"""
Quick verification script to check if all imports work correctly
Run this before deploying to Streamlit Cloud
"""

print("🔍 Verifying imports...")

try:
    import streamlit as st
    print("✅ streamlit")
except ImportError as e:
    print(f"❌ streamlit: {e}")

try:
    import pandas as pd
    print("✅ pandas")
except ImportError as e:
    print(f"❌ pandas: {e}")

try:
    import numpy as np
    print("✅ numpy")
except ImportError as e:
    print(f"❌ numpy: {e}")

try:
    import yfinance as yf
    print("✅ yfinance")
except ImportError as e:
    print(f"❌ yfinance: {e}")

try:
    from config import SECTORS, SECTOR_ETFS, DEFAULT_MOMENTUM_WEIGHTS
    print("✅ config")
except ImportError as e:
    print(f"❌ config: {e}")

try:
    from data_fetcher import fetch_sector_data
    print("✅ data_fetcher")
except ImportError as e:
    print(f"❌ data_fetcher: {e}")

try:
    from indicators import calculate_rsi, calculate_adx
    print("✅ indicators")
except ImportError as e:
    print(f"❌ indicators: {e}")

try:
    from company_symbols import SECTOR_COMPANIES
    print("✅ company_symbols")
except ImportError as e:
    print(f"❌ company_symbols: {e}")

try:
    # Try importing the main app (this will test all dependencies)
    import streamlit_app
    print("✅ streamlit_app (main file)")
except Exception as e:
    print(f"❌ streamlit_app: {e}")

print("\n✅ Verification complete!")
print("If all checks passed, you're ready to deploy!")
