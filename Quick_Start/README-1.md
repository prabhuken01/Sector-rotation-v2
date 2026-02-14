# Quick Start Guide

Welcome to the Market Sector Analysis project! This guide will help you get up and running quickly.

## Overview

Market Sector Analysis is a comprehensive tool for analyzing and visualizing market trends across different sectors. This guide provides the essential steps to get started.

## Prerequisites

Before you begin, ensure you have the following installed:
- Python 3.8 or higher
- pip (Python package manager)
- Git

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/prabhuken01/Sector-rotation-v2.git
cd Sector-rotation-v2
```

### 2. Create a Virtual Environment (Recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## Getting Started

### Option A (recommended): One folder for app + Excel

1. Use one project folder (e.g. `E:\Personal\Trading_Champion\Projects\Sector-rotation-v2\Sector-rotation-v2`).
2. Put **Sector-Company.xlsx** in that folder with one sheet named **Main**. If you have Grok_Sector/Sheet1/Sheet2, run once: `python consolidate_sector_company_to_sheet2.py`
3. Run: `streamlit run streamlit_app.py`

### Basic Usage

From the project folder:

```bash
streamlit run streamlit_app.py
```

Opens at: `http://localhost:8501`

## Documentation order

See project root: **readme-1.md** (overview), **EXCEL_ONE_PLACE_STEPS-2.md** (Excel setup), **PROJECT_FILES_AND_PURPOSE-3.md** (files), **DEPLOYMENT-4.md** (deploy), then CHANGES_LOG-5 through APP_LAYOUT_LOG-10.

## Troubleshooting

- **Module not found**: Activate venv and `pip install -r requirements.txt`
- **Excel not found**: Ensure Sector-Company.xlsx is in the same folder as streamlit_app.py (Option A)
- **Data issues**: See **implementation_guide-9.md**

## Support

See **readme-1.md** and **implementation_guide-9.md** for detailed docs and troubleshooting.

---

**Last Updated**: Feb 2026
