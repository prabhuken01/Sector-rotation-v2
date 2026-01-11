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
git clone https://github.com/prabhuken01/market-sector-analysis.git
cd market-sector-analysis
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

### Basic Usage

To run the basic analysis:

```bash
python main.py
```

### Configuration

Edit the `config.yaml` file to customize:
- Data sources
- Analysis parameters
- Output formats
- Sector focus areas

## Directory Structure

```
market-sector-analysis/
├── Quick_Start/          # Quick start guide (you are here)
├── data/                 # Input data files
├── src/                  # Source code
├── output/               # Analysis results
├── config.yaml           # Configuration file
├── requirements.txt      # Project dependencies
└── README.md             # Main project documentation
```

## Common Tasks

### Running an Analysis

```bash
python src/analyzer.py --sector technology --date 2026-01-10
```

### Viewing Results

Results are saved in the `output/` directory. View them using:

```bash
python src/visualize.py
```

### Updating Data

To fetch the latest market data:

```bash
python src/data_fetcher.py
```

## Troubleshooting

### Issue: Module not found errors

**Solution**: Ensure your virtual environment is activated and all dependencies are installed:
```bash
pip install -r requirements.txt
```

### Issue: Data files missing

**Solution**: Download data files using:
```bash
python src/data_fetcher.py --download
```

### Issue: Configuration errors

**Solution**: Verify `config.yaml` syntax and ensure all required fields are present.

## Next Steps

1. **Read the Main README**: Check out the main [README.md](../README.md) for detailed documentation
2. **Explore Examples**: Look in the `examples/` directory for sample analyses
3. **Check Documentation**: Review the `docs/` folder for API reference
4. **Join the Community**: Visit our discussions for help and feedback

## Useful Resources

- [Project Documentation](../README.md)
- [API Reference](../docs/api.md)
- [Examples](../examples/)
- [Contributing Guidelines](../CONTRIBUTING.md)

## Support

If you encounter any issues:
1. Check the [Troubleshooting](#troubleshooting) section above
2. Search existing GitHub issues
3. Create a new issue with detailed information
4. Contact the maintainers

## Quick Reference

| Command | Purpose |
|---------|---------|
| `python main.py` | Run default analysis |
| `python src/analyzer.py` | Run custom analysis |
| `python src/visualize.py` | Generate visualizations |
| `python src/data_fetcher.py` | Update data sources |
| `pip install -r requirements.txt` | Install dependencies |

---

**Last Updated**: 2026-01-10

Happy analyzing! 📊
