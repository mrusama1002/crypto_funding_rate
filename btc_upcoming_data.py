import streamlit as st
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="MEXC Futures Dashboard", layout="wide")

st.title("📊 MEXC Futures Data Tracker")

# User input
symbol = st.text_input("Enter Futures Coin Symbol (e.g. BTC_USDT, ETH_USDT, SOL_USDT):", "BTC_USDT")

def get_fair_price(symbol):
    """Fetch current fair price from MEXC"""
    url = f"https://contract.mexc.com/api/v1/contract/fair_price/{symbol}"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        return float(data["data"]["fairPrice"])
    except:
        return None

def get_kline_price(symbol, interval="1h", lookback=1):
    """Fetch 1 hour before price using Kline"""
    url = f"https://contract.mexc.com/api/v1/contract/kline/{symbol}?interval={interval}&limit={lookback+1}"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if "data" in data and len(data["data"]) > 0:
            # 1 hour before ka closing price
            return float(data["data"][0][4])
        return None
    except:
        return None

def get_funding_rate(symbol):
    """Fetch latest funding rate"""
    url = f"https://contract.mexc.com/api/v1/contract/funding_rate/{symbol}"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if "data" in data:
            return float(data["data"]["rate"])
        return None
    except:
        return None

def get_volume(symbol):
    """Fetch recent 24h volume"""
    url = f"https://contract.mexc.com/api/v1/contract/ticker/{symbol}"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if "data" in data:
            return float(data["data"]["amount24"])
        return None
    except:
        return None

# Fetch data
current_price = get_fair_price(symbol)
one_hour_before = get_kline_price(symbol)
funding_rate = get_funding_rate(symbol)
volume = get_volume(symbol)

# Display results
if current_price and one_hour_before and funding_rate is not None:
    price_change = ((current_price - one_hour_before) / one_hour_before) * 100

    st.subheader(f"Results for {symbol}")
    st.write(f"💰 **Current Price:** {current_price}")
    st.write(f"⏳ **1 Hour Before Price:** {one_hour_before}")
    st.write(f"📉 **Price Change (1h):** {price_change:.2f}%")
    st.write(f"🏦 **Funding Rate:** {funding_rate:.6f}")
    st.write(f"📊 **24h Volume:** {volume}")

    # Generate a simple signal
    if funding_rate > 0.001 and price_change > 1:
        signal = "🚀 Bullish Signal"
    elif funding_rate < -0.001 and price_change < -1:
        signal = "🐻 Bearish Signal"
    else:
        signal = "😐 Neutral"

    st.write(f"📌 **Signal:** {signal}")

else:
    st.error("❌ Could not fetch data. Check symbol (must be futures, e.g. BTC_USDT).")
