import streamlit as st
import requests

st.set_page_config(page_title="MEXC Futures Dashboard", layout="wide")
st.title("📊 MEXC Futures Data Tracker")

# ---------- Get Futures Contracts ----------
def get_futures_contracts():
    url = "https://contract.mexc.com/api/v1/contract/detail"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if "data" in data:
            return [c["symbol"] for c in data["data"]]
        return []
    except:
        return []

contracts = get_futures_contracts()

symbol = st.selectbox("Select Futures Symbol:", contracts, index=0 if contracts else None)

# ---------- API Functions ----------
def get_fair_price(symbol):
    url = f"https://contract.mexc.com/api/v1/contract/fair_price/{symbol}"
    try:
        r = requests.get(url, timeout=10).json()
        return float(r["data"]["fairPrice"])
    except:
        return None

def get_kline_price(symbol, interval="1h", lookback=1):
    url = f"https://contract.mexc.com/api/v1/contract/kline/{symbol}?interval={interval}&limit={lookback+1}"
    try:
        r = requests.get(url, timeout=10).json()
        if "data" in r and len(r["data"]) > 0:
            return float(r["data"][0][4])  # close price
        return None
    except:
        return None

def get_funding_rate(symbol):
    url = f"https://contract.mexc.com/api/v1/contract/funding_rate/{symbol}"
    try:
        r = requests.get(url, timeout=10).json()
        if "data" in r:
            return float(r["data"]["rate"])
        return None
    except:
        return None

def get_volume(symbol):
    url = f"https://contract.mexc.com/api/v1/contract/ticker/{symbol}"
    try:
        r = requests.get(url, timeout=10).json()
        if "data" in r:
            return float(r["data"]["amount24"])
        return None
    except:
        return None

# ---------- Fetch Data ----------
if symbol:
    current_price = get_fair_price(symbol)
    one_hour_before = get_kline_price(symbol)
    funding_rate = get_funding_rate(symbol)
    volume = get_volume(symbol)

    if current_price and one_hour_before and funding_rate is not None:
        price_change = ((current_price - one_hour_before) / one_hour_before) * 100

        st.subheader(f"Results for {symbol}")
        st.write(f"💰 **Current Price:** {current_price}")
        st.write(f"⏳ **1 Hour Before Price:** {one_hour_before}")
        st.write(f"📉 **Price Change (1h):** {price_change:.2f}%")
        st.write(f"🏦 **Funding Rate:** {funding_rate:.6f}")
        st.write(f"📊 **24h Volume:** {volume}")

        # Simple signal
        if funding_rate > 0.001 and price_change > 1:
            signal = "🚀 Bullish Signal"
        elif funding_rate < -0.001 and price_change < -1:
            signal = "🐻 Bearish Signal"
        else:
            signal = "😐 Neutral"

        st.write(f"📌 **Signal:** {signal}")
    else:
        st.error("❌ Could not fetch full data for this symbol.")
else:
    st.warning("⚠️ No futures contracts available from API.")
