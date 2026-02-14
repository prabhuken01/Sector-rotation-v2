# Technical Reference Manual

## Overview
This technical reference manual provides comprehensive documentation for the Market Sector Analysis project. It serves as a guide for developers, analysts, and users working with the system.

---

## Table of Contents
1. [Architecture](#architecture)
2. [System Components](#system-components)
3. [API Reference](#api-reference)
4. [Data Structures](#data-structures)
5. [Configuration](#configuration)
6. [Troubleshooting](#troubleshooting)

---

## Architecture

### System Design
The Market Sector Analysis system is built on a modular architecture designed for scalability and maintainability.

**Key Principles:**
- **Modularity**: Each component operates independently
- **Scalability**: Designed to handle large datasets
- **Maintainability**: Clear separation of concerns
- **Performance**: Optimized for real-time analysis

### Technology Stack
- **Language**: Python 3.8+
- **Data Processing**: Pandas, NumPy
- **Visualization**: Matplotlib, Plotly
- **Database**: SQLite/PostgreSQL
- **APIs**: RESTful architecture

---

## System Components

### 1. Data Ingestion Module
Responsible for collecting market data from various sources.

**Features:**
- Real-time data streaming
- Batch processing capabilities
- Multiple data source support
- Error handling and validation

### 2. Analysis Engine
Core component for market sector analysis. See **UNIFIED_SCORING_LOGIC-8.md** and **implementation_guide-9.md** in project root for scoring and implementation details.

### 3. Visualization Module
Generates charts, graphs, and interactive dashboards (Streamlit).

### 4. Reporting Module
Generates automated reports and insights; CSV download in app.

---

## Documentation (project root)

- **readme-1.md** – Overview, Option A, quick start
- **EXCEL_ONE_PLACE_STEPS-2.md** – Excel (Main sheet)
- **PROJECT_FILES_AND_PURPOSE-3.md** – File list
- **DEPLOYMENT-4.md** – Deploy guide
- **UNIFIED_SCORING_LOGIC-8.md** – Scoring logic
- **implementation_guide-9.md** – Technical implementation & troubleshooting

---

## Configuration

### Environment Variables
(Optional) See DEPLOYMENT-4.md. For Option A, no env vars required; use Sector-Company.xlsx in same folder.

### config.py
- **SECTOR_COMPANY_EXCEL_PATH**: Set to `None` for Option A (file in current directory). Set to full path to use Excel elsewhere.

---

## Troubleshooting

See **implementation_guide-9.md** in project root for:
- Data fetch errors
- Reversal tab errors
- Slow load
- Historical vs live differences

---

**Last Updated**: Feb 2026
