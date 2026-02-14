"""
Option A: Read Sheet2 from Sector-Company.xlsx, keep only that sheet, rename it to 'Main'.
Removes Grok_Sector and Sheet1. Run once from your project folder (e.g. E: drive).
Usage: python consolidate_sector_company_to_sheet2.py [path]
  If path is given (e.g. E:\\...\\Sector-Company.xlsx), use that file; else use Sector-Company.xlsx in current directory.
"""
import pandas as pd
import os
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "Sector-Company.xlsx"
if not os.path.exists(path):
    print(f"File not found: {path}")
    exit(1)

try:
    df = pd.read_excel(path, sheet_name="Sheet2")
except Exception:
    try:
        df = pd.read_excel(path, sheet_name=1)
    except Exception:
        df = pd.read_excel(path, sheet_name=0)

cols = [c for c in df.columns if c in ["Sector", "Company Name", "Symbol", "Weight (%)"]]
if len(cols) != 4:
    print("Required columns not found. Aborting.")
    exit(1)
out = df[cols].copy()
out.to_excel(path, index=False, sheet_name="Main")
print(f"Done. {path} now has a single sheet named 'Main' ({len(out)} rows). Grok_Sector and Sheet1 removed.")
