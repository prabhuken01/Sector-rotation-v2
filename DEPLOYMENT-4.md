# Deployment Guide

This guide explains how to deploy the NSE Market Sector Analysis Tool to free hosting platforms.

## Option 1: Streamlit Cloud (Recommended - Free)

Streamlit Cloud offers free hosting for Streamlit applications.

### Steps:

1. **Push your code to GitHub**
   ```bash
   git add .
   git commit -m "Add Top 2 Best Stocks tab and ETF default"
   git push origin main
   ```

2. **Go to [Streamlit Cloud](https://streamlit.io/cloud)**
   - Sign up/login with your GitHub account
   - Click "New app"
   - Select your repository
   - Set main file path: `streamlit_app.py`
   - Click "Deploy"

3. **Your app will be live at**: `https://your-app-name.streamlit.app`

### Requirements:
- GitHub account
- Code pushed to a GitHub repository
- No credit card required

## Option 2: Heroku (Free Tier Discontinued)

Note: Heroku no longer offers a free tier. Consider Streamlit Cloud instead.

## Option 3: Railway (Free Tier Available)

1. **Sign up at [Railway](https://railway.app)**
2. **Create a new project** from GitHub
3. **Add a start command**: `streamlit run streamlit_app.py --server.port $PORT`
4. **Set environment variables** (if needed)
5. **Deploy**

## Option 4: Render (Free Tier Available)

1. **Sign up at [Render](https://render.com)**
2. **Create a new Web Service**
3. **Connect your GitHub repository**
4. **Build command**: `pip install -r requirements.txt`
5. **Start command**: `streamlit run streamlit_app.py --server.port $PORT`
6. **Deploy**

## Environment Setup

### Required Environment Variables:
- None required (all configuration is in code)

### Optional Environment Variables:
- `STREAMLIT_SERVER_PORT`: Port number (default: 8501)
- `STREAMLIT_SERVER_ADDRESS`: Server address (default: 0.0.0.0)

## File Structure for Deployment

```
.
├── streamlit_app.py          # Main application
├── requirements.txt          # Python dependencies
├── config.py                 # Configuration
├── company_analysis.py       # Company analysis functions
├── analysis.py               # Sector analysis functions
├── indicators.py             # Technical indicators
├── data_fetcher.py           # Data fetching
├── company_symbols.py        # Company mappings
├── market_analysis.py        # Market analysis
├── local_cache.py            # Local caching (optional)
├── cache_scheduler.py        # Cache scheduler (optional)
└── Sector-Company.xlsx       # Company data (optional)
```

## Notes

- **Data Source**: The app fetches data from Yahoo Finance (yfinance library)
- **Caching**: Uses in-memory caching (5-minute TTL) for performance
- **No Database Required**: All data is fetched on-demand
- **Free Tier Limits**: 
  - Streamlit Cloud: Unlimited apps, 1GB RAM per app
  - Railway: $5 free credit monthly
  - Render: Free tier with limitations

## Troubleshooting

### Common Issues:

1. **Import Errors**: Ensure all dependencies are in `requirements.txt`
2. **Port Issues**: Use `$PORT` environment variable for cloud platforms
3. **Memory Issues**: Reduce cache TTL or limit concurrent requests
4. **Data Fetching**: Yahoo Finance may have rate limits; caching helps

## Quick Deploy Checklist

- [ ] Code pushed to GitHub
- [ ] `requirements.txt` is up to date
- [ ] All imports are correct
- [ ] Test locally first: `streamlit run streamlit_app.py`
- [ ] Deploy to chosen platform
- [ ] Test deployed app

## Support

For deployment issues, check:
- Streamlit Cloud docs: https://docs.streamlit.io/streamlit-community-cloud
- Railway docs: https://docs.railway.app
- Render docs: https://render.com/docs
