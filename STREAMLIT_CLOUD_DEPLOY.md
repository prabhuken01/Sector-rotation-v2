# Streamlit Cloud Deployment Guide

## Quick Deploy Steps

### 1. Prepare Your Repository

Make sure your code is committed and pushed to GitHub:

```bash
git status
git add .
git commit -m "Add Top 2 Best Stocks tab and ETF default"
git push origin main
```

### 2. Deploy to Streamlit Cloud

1. **Go to [Streamlit Cloud](https://streamlit.io/cloud)**
   - Visit: https://streamlit.io/cloud
   - Click "Sign in" and authorize with your GitHub account

2. **Create New App**
   - Click the "New app" button
   - Select your GitHub repository: `Sector-rotation-v2` (or your repo name)
   - Select branch: `main` (or your default branch)

3. **Configure App Settings**
   - **Main file path**: `streamlit_app.py`
   - **App URL**: Choose a custom name (e.g., `nse-sector-analysis`)
   - **Python version**: 3.11 (or latest available)

4. **Deploy**
   - Click "Deploy" button
   - Wait for build to complete (usually 2-5 minutes)

5. **Access Your App**
   - Your app will be live at: `https://your-app-name.streamlit.app`
   - Share this URL with others!

## File Structure Required

```
your-repo/
├── streamlit_app.py          ← Main file (required)
├── requirements.txt          ← Dependencies (required)
├── .streamlit/
│   └── config.toml           ← Config (optional, already created)
├── config.py
├── company_analysis.py
├── analysis.py
├── indicators.py
├── data_fetcher.py
├── company_symbols.py
└── ... (other Python files)
```

## What Happens During Deployment

1. **Build Phase**: Streamlit Cloud installs dependencies from `requirements.txt`
2. **Run Phase**: Starts your app with `streamlit run streamlit_app.py`
3. **Live**: Your app is accessible via the provided URL

## Troubleshooting

### Build Fails
- Check `requirements.txt` has all dependencies
- Ensure Python version compatibility
- Check build logs in Streamlit Cloud dashboard

### App Crashes
- Check logs in Streamlit Cloud dashboard
- Verify all imports are correct
- Ensure data sources (Yahoo Finance) are accessible

### Import Errors
- Make sure all Python files are in the repository
- Check that all modules are listed in `requirements.txt`

## Environment Variables (Optional)

If needed, you can add environment variables in Streamlit Cloud:
- Go to your app settings
- Add environment variables if required
- Currently, none are needed for this app

## Updating Your App

After making changes:
1. Commit and push to GitHub
2. Streamlit Cloud automatically redeploys
3. Changes go live in 1-2 minutes

## Cost

- **Free**: Unlimited apps
- **1GB RAM** per app (free tier)
- **No credit card required**

## Support

- Streamlit Cloud Docs: https://docs.streamlit.io/streamlit-community-cloud
- Community Forum: https://discuss.streamlit.io

## Your App URL Format

After deployment, your app will be at:
```
https://[your-app-name].streamlit.app
```

Example:
```
https://nse-sector-analysis.streamlit.app
```
