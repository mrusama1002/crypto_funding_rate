import streamlit as st
import requests
import time
import hmac, hashlib

st.set_page_config(page_title="MEXC Futures Dashboard", layout="wide")
st.title("📊 MEXC Futures Private API Dashboard")

# --- User API Input ---
API_KEY = st.text_input("Enter MEXC API Key:")
API_SECRET = st.text_input("Enter MEXC API Secret:", type="password")

symbol = st.text_input("Enter Futures Symbol (e.g. BTC_USDT, ETH_USDT):", "BTC_USDT")

# --- Helper Functions ---
BASE = "https://contract.mexc.com"

def sign_request(params, secret):
    """Sign the request using HMAC SHA256"""
    query_string = '&'.join([f"{k}={v}" for k,v in sorted(params.items())])
    signature = hmac.new(secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    return signature

def private_request(endpoint, params):
    """Send signed request"""
    params["api_key"] = API_KEY
    params["req_time"] = str(int(time.time()*1000))
    params["sign"] = sign_request(params, API_SECRET)
    url = f"{BASE}{endpoint}"
    try:
        r = requests.get(url, params=params, timeout=10)
        return r.json()
    except:
        return None

# --- Fetch Data ---
def fetch_funding_rate(symbol):
    url = f"{BASE}/api/v1/private/funding_rate"
    params = {"symbol":symbol}
    data = private_request("/api/v1/private/funding_rate", params)
    if data and "data" in data:
        return float(data["data"]["fundingRate"])
    return None

def fetch_oi(symbol):
    data = private_request("/api/v1/private/open_interest", {"symbol":symbol})
    if data and "data" in data:
        return float(data["data"]["amount"])
    return None

def fetch_1h_price(symbol):
    # last 2 hours Kline
    end = int(time.time()*1000)
    start = end - 2*60*60*1000
    params = {"symbol":symbol,"interval":"Hour1","start":start,"end":end}
    data = private_request("/api/v1/private/kline", params)
    if data and "data" in data and len(data["data"])>0:
        price_1h_ago = float(data["data"][0][4])
        price_now = float(data["data"][-1][4])
        return price_1h_ago, price_now
    return None, None

def fetch_volume(symbol):
    data = private_request("/api/v1/private/ticker", {"symbol":symbol})
    if data and "data" in data:
        return float(data["data"]["amount24"])
    return None

# --- Generate Signal ---
def generate_signal(funding, oi, price_change):
    if funding>0.001 and oi>0 and price_change>1:
        return "🚀 Bullish"
    elif funding<-0.001 and oi>0 and price_change<-1:
        return "🐻 Bearish"
    else:
        return "😐 Neutral"

# --- Main ---
if st.button("Fetch Data"):

    if not API_KEY or not API_SECRET:
        st.error("❌ Enter your API Key and Secret first.")
    elif not symbol:
        st.error("❌ Enter symbol.")
    else:
        funding = fetch_funding_rate(symbol)
        oi = fetch_oi(symbol)
        price_1h, price_now = fetch_1h_price(symbol)
        vol = fetch_volume(symbol)

        if None in [funding, oi, price_1h, price_now, vol]:
            st.error("❌ Could not fetch full data. Check API keys or symbol.")
        else:
            price_change = ((price_now-price_1h)/price_1h)*100

            st.write(f"💰 Current Price: {price_now}")
            st.write(f"⏳ 1 Hour Before Price: {price_1h}")
            st.write(f"📉 Price Change: {price_change:.2f}%")
            st.write(f"🏦 Funding Rate: {funding:.6f}")
            st.write(f"📊 Open Interest (OI): {oi}")
            st.write(f"📦 24h Volume: {vol}")

            signal = generate_signal(funding, oi, price_change)
            st.write(f"📌 Signal: {signal}")
