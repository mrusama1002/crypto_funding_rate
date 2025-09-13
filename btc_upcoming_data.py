import streamlit as st
import requests
import time

st.set_page_config(page_title="MEXC Futures Dashboard", layout="wide")
st.title("📊 MEXC Futures Public API Tracker")

BASE = "https://contract.mexc.com"

# --- Verified Perpetual Symbols ---
symbols = ["BTC_USDT", "ETH_USDT", "SOL_USDT", "XRP_USDT", "LTC_USDT"]
symbol = st.selectbox("Select Futures Symbol:", symbols)

# --- Fetch Functions ---
def get_fair_price(symbol):
    url = f"{BASE}/api/v1/contract/fair_price/{symbol}"
    try:
        r = requests.get(url, timeout=10).json()
        return float(r["data"]["fairPrice"])
    except:
        return None

def get_funding_rate(symbol):
    url = f"{BASE}/api/v1/contract/funding_rate/{symbol}"
    try:
        r = requests.get(url, timeout=10).json()
        return float(r["data"]["fundingRate"])
    except:
        return None

def get_kline_price(symbol):
    # last 2 hours Kline (Hour1 interval)
    end = int(time.time() * 1000)
    start = end - 2*60*60*1000
    url = f"{BASE}/api/v1/contract/kline/{symbol}?interval=Hour1&start={start}&end={end}"
    try:
        r = requests.get(url, timeout=10).json()
        if "data" in r and len(r["data"])>0:
            return float(r["data"][0][4])  # 1h ago close
        return None
    except:
        return None

def get_volume(symbol):
    url = f"{BASE}/api/v1/contract/ticker/{symbol}"
    try:
        r = requests.get(url, timeout=10).json()
        return float(r["data"]["amount24"])
    except:
        return None

# --- Fetch Data ---
current_price = get_fair_price(symbol)
funding_rate = get_funding_rate(symbol)
price_1h = get_kline_price(symbol)
volume = get_volume(symbol)

if current_price and funding_rate is not None:
    price_change = ((current_price - price_1h)/price_1h*100) if price_1h else None

    st.write(f"💰 Current Price: {current_price}")
    st.write(f"🏦 Funding Rate: {funding_rate:.6f}")

    if price_1h:
        st.write(f"⏳ 1 Hour Before Price: {price_1h}")
        st.write(f"📉 Price Change (1h): {price_change:.2f}%")
    else:
        st.write("⏳ 1 Hour Before Price: Not Available")

    if volume:
        st.write(f"📊 24h Volume: {volume}")
    else:
        st.write("📊 24h Volume: Not Available")

    # Simple signal
    if funding_rate>0.001 and price_change and price_change>1:
        signal = "🚀 Bullish Signal"
    elif funding_rate<-0.001 and price_change and price_change<-1:
        signal = "🐻 Bearish Signal"
    else:
        signal = "😐 Neutral"
    st.write(f"📌 Signal: {signal}")

else:
    st.error("❌ Could not fetch data. Symbol may be restricted or API down.")
