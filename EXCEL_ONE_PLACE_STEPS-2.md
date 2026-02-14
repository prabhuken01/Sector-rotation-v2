# Sector-Company Excel: One Place to Edit (Option A)

## The idea

- **One Excel file** = your input. The app reads only the sheet named **Main** for the sector–company list.
- **Option A**: One folder for app and Excel (e.g. `E:\Personal\Trading_Champion\Projects\Sector-rotation-v2\Sector-rotation-v2`). No path in config needed; the app finds `Sector-Company.xlsx` in the same folder.

---

## Option A – One folder (recommended)

1. **Use one project folder**  
   e.g. `E:\Personal\Trading_Champion\Projects\Sector-rotation-v2\Sector-rotation-v2`  
   Ensure this folder has the **latest code** (copy from repo or worktree).

2. **Put Sector-Company.xlsx in that folder**  
   If the file still has Grok_Sector, Sheet1, Sheet2:
   - Open a terminal in that folder.
   - Run: `python consolidate_sector_company_to_sheet2.py`  
     Or with full path: `python consolidate_sector_company_to_sheet2.py "E:\...\Sector-Company.xlsx"`
   - The script keeps only the content of **Sheet2**, renames it to **Main**, and removes Grok_Sector and Sheet1.

3. **Run the app from that folder**  
   `streamlit run streamlit_app.py`  
   The app will load **Sector-Company.xlsx** from the same directory and read the sheet **Main**.

4. **Edit the Excel only in that folder**  
   Add rows as needed. The app uses columns: **Sector**, **Company Name**, **Symbol**, **Weight (%)**.

---

## What the app uses

- **Sheet:** **Main** (or **Sheet2** as fallback if Main is missing).
- **Columns:** Sector, Company Name, Symbol, Weight (%).
- **Config:** Leave `SECTOR_COMPANY_EXCEL_PATH = None` in **config.py** so the app uses the file in the current directory.

---

## Summary

| Goal | What to do |
|------|------------|
| One place to edit | Use **Option A**: one folder for app + Excel (e.g. E: drive). |
| Remove Grok_Sector, Sheet1 | Run `consolidate_sector_company_to_sheet2.py` once. |
| Sheet name | Use **Main** (script renames Sheet2 to Main). |
| Latest code on E: | Copy/sync from repo or worktree to your E: project folder. |
