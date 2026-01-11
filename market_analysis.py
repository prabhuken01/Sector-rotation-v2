import yfinance as yf
import pandas as pd
import numpy as np

# --- 1. CONFIGURATION ---
SECTORS = {
    "Nifty 50": "^NSEI",          # BENCHMARK
    "PSU Bank": "^CNXPSUBANK",
    "Pvt Bank": "^CNXPVTBANK",
    "IT": "^CNXIT",
    "Pharma": "^CNXPHARMA",
    "FMCG": "^CNXFMCG",
    "Auto": "^CNXAUTO",
    "Metal": "^CNXMETAL",
    "Realty": "^CNXREALTY",
    "Media": "^CNXMEDIA",
    "Energy": "^CNXENERGY",
    "Infra": "^CNXINFRA",
    "Commodities": "^CNXCMDT"
}

# Parameters
RSI_PERIOD = 14
ADX_PERIOD = 14
CMF_PERIOD = 20
RS_LOOKBACK = 10 
Z_SCORE_WINDOW = 50 

# --- 2. CALCULATOR FUNCTIONS ---
def get_indicators(df):
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=RSI_PERIOD).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIOD).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # ADX & DI Spread
    plus_dm = df['High'].diff()
    minus_dm = df['Low'].diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    
    tr1 = df['High'] - df['Low']
    tr2 = abs(df['High'] - df['Close'].shift(1))
    tr3 = abs(df['Low'] - df['Close'].shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(ADX_PERIOD).mean()
    
    df['Plus_DI'] = 100 * (plus_dm.rolling(ADX_PERIOD).mean() / atr)
    df['Minus_DI'] = 100 * (abs(minus_dm).rolling(ADX_PERIOD).mean() / atr)
    
    dx = (abs(df['Plus_DI'] - df['Minus_DI']) / abs(df['Plus_DI'] + df['Minus_DI'])) * 100
    df['ADX'] = dx.rolling(ADX_PERIOD).mean()
    df['DI_Spread'] = df['Plus_DI'] - df['Minus_DI']

    # CMF
    mfv = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / (df['High'] - df['Low'])
    mfv = mfv.fillna(0.0) * df['Volume']
    df['CMF'] = mfv.rolling(CMF_PERIOD).sum() / df['Volume'].rolling(CMF_PERIOD).sum()

    # Z-Score ADX
    df['ADX_Z'] = (df['ADX'] - df['ADX'].rolling(Z_SCORE_WINDOW).mean()) / df['ADX'].rolling(Z_SCORE_WINDOW).std()
    
    return df

# --- 3. DATA FETCHING ---
print("📥 Fetching market data for all sectors...")
full_data = yf.download(list(SECTORS.values()), period="1y", progress=False)

# Cleaning MultiIndex
if isinstance(full_data.columns, pd.MultiIndex):
    full_data = full_data.swaplevel(0, 1, axis=1) 

results = []
nifty_close = full_data['Close']['^NSEI']
latest_date = full_data.index[-1].strftime('%Y-%m-%d') # CAPTURE THE DATE

for name, ticker in SECTORS.items():
    if name == "Nifty 50": continue 
    
    try:
        df = pd.DataFrame({
            'Open': full_data['Open'][ticker],
            'High': full_data['High'][ticker],
            'Low': full_data['Low'][ticker],
            'Close': full_data['Close'][ticker],
            'Volume': full_data['Volume'][ticker]
        }).dropna()

        df = get_indicators(df)

        # Comparative RS (Ratio vs Nifty)
        rs_ratio = df['Close'] / nifty_close
        df['RS_Rating'] = rs_ratio.pct_change(RS_LOOKBACK) * 100 

        curr = df.iloc[-1]
        
        results.append({
            "Sector": name,
            "Price": round(curr['Close'], 2),
            "RSI": round(curr['RSI'], 1),
            "ADX_Z": round(curr['ADX_Z'], 2),
            "DI_Spread": round(curr['DI_Spread'], 1),
            "RS_Rating": round(curr['RS_Rating'], 2),
            "CMF": round(curr['CMF'], 3)
        })

    except Exception as e:
        pass 

df_res = pd.DataFrame(results)

# --- 4. SCORING LOGIC ---

# MOMENTUM SCORE CALCULATION
# We weight RS_Rating higher because outperformance is key in momentum
df_res['Mom_Score'] = (df_res['ADX_Z'] * 1.0) + (df_res['RS_Rating'] * 2.0)

# REVERSAL FILTER
# We don't use a 'score' sum here, but strict filtering criteria
df_res['Rev_Status'] = "No"
df_res.loc[(df_res['RSI'] < 50) & (df_res['ADX_Z'] < 0.5) & (df_res['CMF'] > 0), 'Rev_Status'] = "Watch"
df_res.loc[(df_res['RSI'] < 40) & (df_res['ADX_Z'] < -0.5) & (df_res['CMF'] > 0.1), 'Rev_Status'] = "BUY_DIV"


# --- 5. TABS & DISPLAY ---

tab_momentum = df_res.sort_values(by='Mom_Score', ascending=False)
tab_reversal = df_res[df_res['Rev_Status'] != 'No'].sort_values(by='CMF', ascending=False)

print("\n" + "="*80)
print(f"📅 ANALYSIS REFERENCE DATE: {latest_date}")
print("="*80)

print("\n🧮 SCORING METHODOLOGY (Displayed)")
print("-" * 40)
print("1. Momentum Score = (ADX Z-Score) + (2 x Relative Strength Rating)")
print("   - Why? We prize 'Outperformance vs Nifty' (RS) double the raw trend strength.")
print("   - Interpretation: Score > 3.0 is Super Bullish. Score < 0 is Laggard.")
print("\n2. Reversal Logic = RSI < 50 + Low Trend (Z < 0.5) + Positive Money Flow (CMF > 0)")
print("   - Why? We want beaten-down sectors where institutions are silently buying.")
print("-" * 40)

print(f"\n🚀 [TAB 1] MOMENTUM RANKING (Sorted by Score)")
print(tab_momentum[['Sector', 'Mom_Score', 'Price', 'RS_Rating', 'DI_Spread', 'ADX_Z']].to_string(index=False))

print(f"\n\n⚓ [TAB 2] REVERSAL CANDIDATES (Bottom Fishing)")
if not tab_reversal.empty:
    print(tab_reversal[['Sector', 'Rev_Status', 'Price', 'RSI', 'CMF', 'ADX_Z']].to_string(index=False))
else:
    print(">> No sectors currently meet the strict Reversal/Accumulation criteria.")