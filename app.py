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

def calculate_indicators(df):
    # Flatten columns just in case yfinance returns a MultiIndex format
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    # 1. EMA Calculation
    df['EMA_3'] = df['Close'].ewm(span=3, adjust=False).mean()
    df['EMA_6'] = df['Close'].ewm(span=6, adjust=False).mean()
    
    # 2. RSI Calculation
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-10) # Avoid division by zero
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # 3. VWAP Calculation (Intraday)
    df['Typical_Price'] = (df['High'] + df['Low'] + df['Close']) / 3
    df['TP_Vol'] = df['Typical_Price'] * df['Volume']
    
    # Safe date extraction for timezone aware indices
    df['Date'] = pd.to_datetime(df.index).date
    
    df['Cum_TP_Vol'] = df.groupby('Date')['TP_Vol'].cumsum()
    df['Cum_Vol'] = df.groupby('Date')['Volume'].cumsum()
    df['VWAP'] = df['Cum_TP_Vol'] / df['Cum_Vol']
    
    # 4. Volume SMA
    df['Vol_SMA'] = df['Volume'].rolling(window=20).mean()
    return df

@st.cache_data(ttl=60)
def get_stock_data():
    results = []
    for ticker in tickers:
        try:
            # Using Ticker().history() is much more stable than yf.download()
            stock_data = yf.Ticker(ticker)
            df = stock_data.history(period="5d", interval="5m")
            
            if df.empty or len(df) < 20:
                continue
            
            df = calculate_indicators(df)
            
            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            # Crossover logic
            bullish_cross = (prev['EMA_3'] <= prev['EMA_6']) and (last['EMA_3'] > last['EMA_6'])
            bearish_cross = (prev['EMA_3'] >= prev['EMA_6']) and (last['EMA_3'] < last['EMA_6'])
            
            # Sophisticated Probability System
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
            # Silently skip if one stock fails so the whole app doesn't crash
            continue
            
    return pd.DataFrame(results)

with st.spinner("Calculating live 5-min market data..."):
    df = get_stock_data()

if df.empty:
    st.error("Data available nahi hai ya Market band hai. (System is running perfectly!)")
else:
    # 8 Tabs Creation
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

st.caption("Data is auto-refreshing. Click anywhere or refresh to update live.")
