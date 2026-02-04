# 🚀 Quick Deploy - 3 Simple Steps

## Step 1: Push to GitHub (if not already done)

```bash
git add .
git commit -m "Ready for Streamlit Cloud"
git push origin main
```

## Step 2: Deploy to Streamlit Cloud

1. Go to: **https://streamlit.io/cloud**
2. Click **"Sign in"** → Authorize with GitHub
3. Click **"New app"**
4. Select: **`Sector-rotation-v2`** repository
5. Main file: **`streamlit_app.py`**
6. Click **"Deploy"**

## Step 3: Get Your Live URL

Your app will be live at:
```
https://[your-app-name].streamlit.app
```

**That's it! No Codespaces needed!**

---

## ⚠️ Important Note

**Streamlit Cloud ≠ Codespaces**

- **Codespaces**: Development environment (you're out of free usage)
- **Streamlit Cloud**: Deployment platform (FREE, unlimited)

You can deploy to Streamlit Cloud even if you're out of Codespaces!

---

## Alternative: If You Don't Want to Use GitHub

### Option A: Railway (Direct Upload)
1. Go to https://railway.app
2. Create account
3. New Project → Upload files
4. Set start command: `streamlit run streamlit_app.py --server.port $PORT`

### Option B: Render (Direct Upload)
1. Go to https://render.com
2. Create account
3. New Web Service → Upload files
4. Set start command: `streamlit run streamlit_app.py --server.port $PORT`

---

## ✅ Recommended: Streamlit Cloud

**Why?**
- Free forever
- No Codespaces needed
- Just needs GitHub repo
- Automatic deployments
- Easy to use

**Time to deploy: 5 minutes**
