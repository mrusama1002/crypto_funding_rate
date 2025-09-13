import streamlit as st
import requests
import time

st.set_page_config(page_title="Crypto Signal Tracker", layout="wide")
st.title("📊 MEXC Funding + Binance Price/Volume Tracker")

# --- Select Symbol ---
symbols = ["BTC_USDT", "ETH_USDT", "SOL_USDT"]
symbol = st.selectbox("Select Symbol:", symbols)

# ---------- MEXC Functions ----------
def get_funding_rate(symbol):
    url = f"https://contract.mexc.com/api/v1/contract/funding_rate/{symbol}"
    try:
        r = requests.get(url, timeout=10).json()
        return float(r["data"]["fundingRate"])
    except:
        return None

# ---------- Binance Functions ----------
def get_binance_ohlcv(symbol, interval="1h", limit=2):
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        r = requests.get(url, timeout=10).json()
        if len(r) >= 2:
            price_1h_ago = float(r[-2][4])  # Close price 1 hour ago
            price_now = float(r[-1][4])    # Latest close price
            volume = float(r[-1][5])       # Latest volume
            return price_1h_ago, price_now, volume
        return None, None, None
    except:
        return None, None, None

# ---------- Fetch Data ----------
funding_rate = get_funding_rate(symbol)
price_1h, price_now, volume = get_binance_ohlcv(symbol)

if funding_rate is not None and price_now is not None:
    price_change = ((price_now - price_1h)/price_1h*100) if price_1h else None

    st.write(f"💰 Current Price: {price_now}")
    st.write(f"🏦 MEXC Funding Rate: {funding_rate:.6f}")

    if price_1h:
        st.write(f"⏳ 1 Hour Before Price (Binance): {price_1h}")
        st.write(f"📉 Price Change (1h): {price_change:.2f}%")
    else:
        st.write("⏳ 1 Hour Before Price: Not Available")

    if volume:
        st.write(f"📊 24h Volume (Binance): {volume}")
    else:
        st.write("📊 24h Volume: Not Available")

    # Simple Signal
    if funding_rate>0.001 and price_change and price_change>1:
        signal = "🚀 Bullish"
    elif funding_rate<-0.001 and price_change and price_change<-1:
        signal = "🐻 Bearish"
    else:
        signal = "😐 Neutral"

    st.write(f"📌 Signal: {signal}")

else:
    st.error("❌ Could not fetch full data. Check symbol or API endpoints.")
