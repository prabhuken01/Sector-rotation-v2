#!/usr/bin/env python3
"""Test if Excel loading works"""

import pandas as pd
import os
import sys

excel_file = 'Sector-Company.xlsx'

print(f"Current directory: {os.getcwd()}")
print(f"Excel file exists: {os.path.exists(excel_file)}")

if os.path.exists(excel_file):
    print(f"File size: {os.path.getsize(excel_file)} bytes")
    
    try:
        xls = pd.ExcelFile(excel_file)
        print(f"✅ Sheets available: {xls.sheet_names}")
        
        # Read first sheet
        df = pd.read_excel(excel_file, sheet_name=0)
        print(f"\n✅ Data loaded successfully!")
        print(f"Shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        print(f"\nFirst 10 rows:")
        print(df.head(10))
        print(f"\nData types:")
        print(df.dtypes)
        
    except Exception as e:
        print(f"❌ Error reading Excel: {e}")
        import traceback
        traceback.print_exc()
else:
    print(f"❌ File not found: {excel_file}")
