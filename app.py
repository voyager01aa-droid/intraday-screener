import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import io

# ⚙️ Page Setup
st.set_page_config(page_title="Advanced Nifty Screener", layout="wide")
st.title("📈 Advanced Intraday Stock Screener (5-Min)")

# 🎛️ Sidebar for Index Selection
st.sidebar.header("Screener Settings")
index_choice = st.sidebar.selectbox(
    "Kaunsa Index Scan Karna Hai?",
    ["Nifty 50", "Nifty 100", "Nifty 200", "Nifty 500"]
)
st.sidebar.caption("⏳ Note: Nifty 500 scan karne me 30 se 60 seconds lag sakte hain. Please wait.")

# 📥 Fetch Official Symbols from NSE
@st.cache_data(ttl=86400) # Cache list for 24 hours
def get_tickers(index_name):
    urls = {
        "Nifty 50": "ind_nifty50list.csv",
        "Nifty 100": "ind_nifty100list.csv",
        "Nifty 200": "ind_nifty200list.csv",
        "Nifty 500": "ind_nifty500list.csv"
    }
    url = f"https://archives.nseindia.com/content/indices/{urls[index_name]}"
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        df = pd.read_csv(io.StringIO(response.text))
        # Add .NS to match Yahoo Finance symbols
        return [f"{sym}.NS" for sym in df['Symbol'].tolist()]
    except Exception as e:
        st.error("NSE server se list nahi aayi. Using fallback Top 10.")
        return ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", 
                "SBIN.NS", "ITC.NS", "KOTAKBANK.NS", "LT.NS", "AXISBANK.NS"]

# 🚀 BULK Download & Calculate
@st.cache_data(ttl=300) # Auto-refresh every 5 minutes
def get_bulk_data(tickers_list):
    results = []
    
    # Ek sath 50-500 stocks download karne ka superfast method
    try:
        data = yf.download(tickers_list, period="5d", interval="5m", group_by="ticker", progress=False, threads=True)
    except Exception:
        return pd.DataFrame()
        
    for ticker in tickers_list:
        try:
            # Handle data structure
            if len(tickers_list) > 1:
                if ticker not in data: continue
                df = data[ticker].copy()
            else:
                df = data.copy()
            
            df.dropna(inplace=True)
            if df.empty or len(df) < 20: continue
            
            df.columns = [c.capitalize() for c in df.columns]
            if 'Close' not in df.columns: continue
            
            # Indicator Calculations
            df['EMA_3'] = df['Close'].ewm(span=3, adjust=False).mean()
            df['EMA_6'] = df['Close'].ewm(span=6, adjust=False).mean()
            
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / (loss + 1e-10)
            df['RSI'] = 100 - (100 / (1 + rs))
            
            df['Typical_Price'] = (df['High'] + df['Low'] + df['Close']) / 3
            df['TP_Vol'] = df['Typical_Price'] * df['Volume']
            df['Date_Str'] = pd.to_datetime(df.index).strftime('%Y-%m-%d')
            df['Cum_TP_Vol'] = df.groupby('Date_Str')['TP_Vol'].cumsum()
            df['Cum_Vol'] = df.groupby('Date_Str')['Volume'].cumsum()
            df['VWAP'] = df['Cum_TP_Vol'] / df['Cum_Vol']
            
            df['Vol_SMA'] = df['Volume'].rolling(window=20).mean()
            
            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            bull_cross = (prev['EMA_3'] <= prev['EMA_6']) and (last['EMA_3'] > last['EMA_6'])
            bear_cross = (prev['EMA_3'] >= prev['EMA_6']) and (last['EMA_3'] < last['EMA_6'])
            
            # Score System
            bull_score = 0
            bear_score = 0
            
            if last['EMA_3'] > last['EMA_6']: bull_score += 25
            if last['EMA_3'] < last['EMA_6']: bear_score += 25
            if last['Close'] > last['VWAP']: bull_score += 25
            if last['Close'] < last['VWAP']: bear_score += 25
            if last['RSI'] > 60: bull_score += 25
            if last['RSI'] < 40: bear_score += 25
            if last['Volume'] > last['Vol_SMA']: 
                bull_score += 25
                bear_score += 25

            results.append({
                "Stock": ticker.replace(".NS", ""),
                "Close": round(float(last['Close']), 2),
                "RSI": round(float(last['RSI']), 2) if not pd.isna(last['RSI']) else 50.0,
                "EMA_3": round(float(last['EMA_3']), 2),
                "EMA_6": round(float(last['EMA_6']), 2),
                "VWAP": round(float(last['VWAP']), 2),
                "Bullish_Prob": f"{bull_score}%",
                "Bearish_Prob": f"{bear_score}%",
                "Bull_Cross": bool(bull_cross),
                "Bear_Cross": bool(bear_cross)
            })
        except Exception:
            continue
            
    return pd.DataFrame(results)

# 🏁 Main Execution Loop
tickers = get_tickers(index_choice)

with st.spinner(f"🚀 Scanning {len(tickers)} stocks for {index_choice}. Please wait..."):
    df = get_bulk_data(tickers)

if df.empty:
    st.error("❌ Data download fail ho gaya. Thodi der me auto-refresh hoga.")
else:
    st.success(f"✅ Successfully scanned {len(df)} active stocks from {index_choice}!")
    
    # 📑 Dashboard Tabs
    t1, t2, t3, t4, t5, t6, t7, t8 = st.tabs([
        "🔴 High Prob Bearish", "🟢 High Prob Bullish", 
        "📈 Highest RSI", "📉 Lowest RSI", 
        "⬆️ 3-6 EMA Bull", "⬇️ 3-6 EMA Bear", 
        "🔼 VWAP Up", "🔽 VWAP Down"
    ])
    
    with t1:
        st.subheader("Highly Probable Bearish Stocks (75% - 100%)")
        bearish_df = df[df['Bearish_Prob'].isin(["75%", "100%"])].sort_values(by='Bearish_Prob', ascending=False)
        st.dataframe(bearish_df[['Stock', 'Close', 'Bearish_Prob', 'RSI', 'VWAP']], use_container_width=True, hide_index=True)

    with t2:
        st.subheader("Highly Probable Bullish Stocks (75% - 100%)")
        bullish_df = df[df['Bullish_Prob'].isin(["75%", "100%"])].sort_values(by='Bullish_Prob', ascending=False)
        st.dataframe(bullish_df[['Stock', 'Close', 'Bullish_Prob', 'RSI', 'VWAP']], use_container_width=True, hide_index=True)

    with t3:
        st.subheader("Highest RSI Stocks")
        high_rsi = df.sort_values(by='RSI', ascending=False)
        st.dataframe(high_rsi[['Stock', 'Close', 'RSI']], use_container_width=True, hide_index=True)

    with t4:
        st.subheader("Lowest RSI Stocks")
        low_rsi = df.sort_values(by='RSI', ascending=True)
        st.dataframe(low_rsi[['Stock', 'Close', 'RSI']], use_container_width=True, hide_index=True)

    with t5:
        st.subheader("3 EMA crosses 6 EMA (Upwards)")
        bull_cross = df[df['Bull_Cross'] == True]
        st.dataframe(bull_cross[['Stock', 'Close', 'EMA_3', 'EMA_6']], use_container_width=True, hide_index=True)

    with t6:
        st.subheader("3 EMA crosses 6 EMA (Downwards)")
        bear_cross = df[df['Bear_Cross'] == True]
        st.dataframe(bear_cross[['Stock', 'Close', 'EMA_3', 'EMA_6']], use_container_width=True, hide_index=True)

    with t7:
        st.subheader("VWAP Uptrend (Price > VWAP)")
        vwap_up = df[df['Close'] > df['VWAP']]
        st.dataframe(vwap_up[['Stock', 'Close', 'VWAP']], use_container_width=True, hide_index=True)

    with t8:
        st.subheader("VWAP Downtrend (Price < VWAP)")
        vwap_down = df[df['Close'] < df['VWAP']]
        st.dataframe(vwap_down[['Stock', 'Close', 'VWAP']], use_container_width=True, hide_index=True)
