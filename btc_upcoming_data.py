import streamlit as st
import requests
from datetime import datetime

BASE = "https://contract.mexc.com/api/v1"

def fetch_fair_price(symbol):
    url = f"{BASE}/contract/fair_price/{symbol}"
    r = requests.get(url, timeout=10).json()
    return float(r["data"]["fairPrice"])

def fetch_1h_prices(symbol):
    url = f"{BASE}/contract/kline/{symbol}"
    params = {"interval":"Min60", "limit":2}
    r = requests.get(url, params=params, timeout=10).json()
    data = r["data"]
    price_1h_ago = float(data[-2][4])
    price_now = float(data[-1][4])
    volume = float(data[-1][5])
    return price_now, price_1h_ago, volume

def fetch_funding(symbol):
    url = f"{BASE}/contract/funding_rate/{symbol}"
    r = requests.get(url, timeout=10).json()
    return float(r["data"]["fundingRate"])

def generate_signal(funding_rate, price_now, price_1h_ago):
    change_pct = (price_now - price_1h_ago) / price_1h_ago * 100
    if funding_rate > 0 and change_pct > 0:
        signal = "Long 🚀"
    elif funding_rate < 0 and change_pct < 0:
        signal = "Short 🔻"
    else:
        signal = "Neutral ⚖️"
    return signal, change_pct

# --------- STREAMLIT APP ---------
st.title("📊 MEXC Futures – Signal Dashboard (Public)")

symbol = st.text_input("Enter symbol (e.g. BTC_USDT)", "BTC_USDT")

if st.button("Fetch Data"):
    try:
        price_now, price_1h_ago, vol = fetch_1h_prices(symbol)
        funding = fetch_funding(symbol)
        signal, change_pct = generate_signal(funding, price_now, price_1h_ago)

        st.write(f"**Funding rate:** {funding*100:.4f}%")
        st.write(f"**1 hour before price:** {price_1h_ago}")
        st.write(f"**Current price:** {price_now}")
        st.write(f"**Change:** {price_now - price_1h_ago:.2f} ({change_pct:.2f}%)")
        st.write(f"**Signal:** {signal}")
        st.write(f"**Volume (last 1h):** {vol}")
    except Exception as e:
        st.error(f"❌ Error: {e}")
