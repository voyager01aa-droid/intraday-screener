import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="Intraday 5-Min Screener", layout="wide")
st.title("📈 5-Minute Intraday Stock Screener")

# List of stocks (Nifty liquid stocks for example)
tickers = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", 
    "SBIN.NS", "ITC.NS", "KOTAKBANK.NS", "L&T.NS", "AXISBANK.NS"
]

@st.cache_data(ttl=60) # Refreshes data every 60 seconds
def get_stock_data():
    results = []
    for ticker in tickers:
        try:
            # Fetch 5-minute data for the last 5 days
            df = yf.download(ticker, period="5d", interval="5m", progress=False)
            if df.empty:
                continue
            
            # Calculate Indicators
            df['EMA_3'] = ta.ema(df['Close'], length=3)
            df['EMA_6'] = ta.ema(df['Close'], length=6)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            df.ta.vwap(append=True) # Adds VWAP_D
            df['Vol_SMA'] = ta.sma(df['Volume'], length=20)
            
            # Get latest 2 candles for crossover logic
            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            # 1. Bullish & Bearish Crossover Logic
            bullish_cross = (prev['EMA_3'] <= prev['EMA_6']) and (last['EMA_3'] > last['EMA_6'])
            bearish_cross = (prev['EMA_3'] >= prev['EMA_6']) and (last['EMA_3'] < last['EMA_6'])
            
            # 2. Probability Score Calculation (0 to 100%)
            bull_score = 0
            bear_score = 0
            
            if last['EMA_3'] > last['EMA_6']: bull_score += 25
            if last['EMA_3'] < last['EMA_6']: bear_score += 25
                
            if last['Close'] > last['VWAP_D']: bull_score += 25
            if last['Close'] < last['VWAP_D']: bear_score += 25
                
            if last['RSI'] > 60: bull_score += 25
            if last['RSI'] < 40: bear_score += 25
                
            if last['Volume'] > last['Vol_SMA']: 
                bull_score += 25
                bear_score += 25

            # Store final data
            results.append({
                "Stock": ticker.replace(".NS", ""),
                "Close": round(last['Close'], 2),
                "RSI": round(last['RSI'], 2),
                "EMA_3": round(last['EMA_3'], 2),
                "EMA_6": round(last['EMA_6'], 2),
                "VWAP": round(last['VWAP_D'], 2),
                "Bullish_Prob": f"{bull_score}%",
                "Bearish_Prob": f"{bear_score}%",
                "Bull_Cross": bullish_cross,
                "Bear_Cross": bearish_cross
            })
        except Exception:
            continue
            
    return pd.DataFrame(results)

# Fetching Data
with st.spinner("Fetching 5-minute data from market..."):
    df = get_stock_data()

if df.empty:
    st.error("Market data fetch karne me error aayi. Thodi der baad try karein.")
else:
    # Creating 8 Tabs as requested
    t1, t2, t3, t4, t5, t6, t7, t8 = st.tabs([
        "🔴 High Prob Bearish", "🟢 High Prob Bullish", 
        "📈 Highest RSI", "📉 Lowest RSI", 
        "⬆️ 3-6 EMA Bull Cross", "⬇️ 3-6 EMA Bear Cross", 
        "🔼 VWAP Uptrend", "🔽 VWAP Downtrend"
    ])
    
    with t1:
        st.subheader("Highly Probable Bearish Stocks (Score 75% - 100%)")
        bearish_df = df[df['Bearish_Prob'].isin(["75%", "100%"])].sort_values(by='Bearish_Prob', ascending=False)
        st.dataframe(bearish_df[['Stock', 'Close', 'Bearish_Prob', 'RSI', 'VWAP']], use_container_width=True)

    with t2:
        st.subheader("Highly Probable Bullish Stocks (Score 75% - 100%)")
        bullish_df = df[df['Bullish_Prob'].isin(["75%", "100%"])].sort_values(by='Bullish_Prob', ascending=False)
        st.dataframe(bullish_df[['Stock', 'Close', 'Bullish_Prob', 'RSI', 'VWAP']], use_container_width=True)

    with t3:
        st.subheader("Highest RSI Stocks")
        high_rsi = df.sort_values(by='RSI', ascending=False)
        st.dataframe(high_rsi[['Stock', 'Close', 'RSI']], use_container_width=True)

    with t4:
        st.subheader("Lowest RSI Stocks")
        low_rsi = df.sort_values(by='RSI', ascending=True)
        st.dataframe(low_rsi[['Stock', 'Close', 'RSI']], use_container_width=True)

    with t5:
        st.subheader("3 EMA crosses 6 EMA (Upwards)")
        bull_cross = df[df['Bull_Cross'] == True]
        st.dataframe(bull_cross[['Stock', 'Close', 'EMA_3', 'EMA_6']], use_container_width=True)

    with t6:
        st.subheader("3 EMA crosses 6 EMA (Downwards)")
        bear_cross = df[df['Bear_Cross'] == True]
        st.dataframe(bear_cross[['Stock', 'Close', 'EMA_3', 'EMA_6']], use_container_width=True)

    with t7:
        st.subheader("VWAP Uptrend (Price > VWAP)")
        vwap_up = df[df['Close'] > df['VWAP']]
        st.dataframe(vwap_up[['Stock', 'Close', 'VWAP']], use_container_width=True)

    with t8:
        st.subheader("VWAP Downtrend (Price < VWAP)")
        vwap_down = df[df['Close'] < df['VWAP']]
        st.dataframe(vwap_down[['Stock', 'Close', 'VWAP']], use_container_width=True)

st.caption("Data is delayed as per Yahoo Finance 5-minute intervals. Refresh the page to update.")
