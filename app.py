import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Intraday 5-Min Screener", layout="wide")
st.title("📈 5-Minute Intraday Stock Screener")

# List of stocks
tickers = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", 
    "SBIN.NS", "ITC.NS", "KOTAKBANK.NS", "L&T.NS", "AXISBANK.NS"
]

def get_stock_data():
    results = []
    errors = [] # 🛠 Error pakadne ke liye naya system
    
    for ticker in tickers:
        try:
            stock_data = yf.Ticker(ticker)
            df = stock_data.history(period="5d", interval="5m")
            
            # Check 1: Kya Yahoo ne empty data bheja?
            if df.empty:
                errors.append(f"{ticker}: Yahoo Finance returned empty data.")
                continue
                
            # Check 2: Kya data chota hai?
            if len(df) < 20:
                errors.append(f"{ticker}: Not enough candles (only {len(df)}). Need 20.")
                continue
                
            # Make sure columns are properly named
            df.columns = [c.capitalize() for c in df.columns]
            
            if 'Close' not in df.columns:
                errors.append(f"{ticker}: 'Close' price missing in data.")
                continue
            
            # 1. EMA Calculation
            df['EMA_3'] = df['Close'].ewm(span=3, adjust=False).mean()
            df['EMA_6'] = df['Close'].ewm(span=6, adjust=False).mean()
            
            # 2. RSI Calculation
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / (loss + 1e-10) 
            df['RSI'] = 100 - (100 / (1 + rs))
            
            # 3. VWAP Calculation (BUG FIXED)
            df['Typical_Price'] = (df['High'] + df['Low'] + df['Close']) / 3
            df['TP_Vol'] = df['Typical_Price'] * df['Volume']
            
            # Safe Date extraction string format me
            df['Date_Str'] = pd.to_datetime(df.index).strftime('%Y-%m-%d')
            
            df['Cum_TP_Vol'] = df.groupby('Date_Str')['TP_Vol'].cumsum()
            df['Cum_Vol'] = df.groupby('Date_Str')['Volume'].cumsum()
            df['VWAP'] = df['Cum_TP_Vol'] / df['Cum_Vol']
            
            # 4. Volume SMA
            df['Vol_SMA'] = df['Volume'].rolling(window=20).mean()
            
            # Logic calculation
            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            bullish_cross = (prev['EMA_3'] <= prev['EMA_6']) and (last['EMA_3'] > last['EMA_6'])
            bearish_cross = (prev['EMA_3'] >= prev['EMA_6']) and (last['EMA_3'] < last['EMA_6'])
            
            # Probabilities
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
                "Bull_Cross": bool(bullish_cross),
                "Bear_Cross": bool(bear_cross)
            })
        except Exception as e:
            errors.append(f"{ticker} Code Error: {str(e)}")
            continue
            
    return pd.DataFrame(results), errors

with st.spinner("Fetching live 5-min market data..."):
    df, errors = get_stock_data()

# 🛠 ERROR DISPLAY SYSTEM 
if df.empty:
    st.error("❌ Data calculate nahi ho paya!")
    st.warning("🔍 **ACTUAL ERROR (Iska screenshot bhejna agar theek na ho):**")
    for err in errors:
        st.write(f"- {err}")
else:
    if errors:
        with st.expander("⚠️ Kuch stocks me issue hai (Click to view)"):
            for err in errors:
                st.write(f"- {err}")
                
    # Creating Tabs
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
