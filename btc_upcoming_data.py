import streamlit as st
import requests
import pandas as pd
import hmac, hashlib, time
from datetime import datetime

BASE = "https://contract.mexc.com"

# ============ AUTH HELPERS ============
def sign_request(params, secret):
    qs = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
    sig = hmac.new(secret.encode(), qs.encode(), hashlib.sha256).hexdigest()
    return qs + "&signature=" + sig

def private_get(path, params, api_key, api_secret):
    params["api_key"] = api_key
    params["req_time"] = int(time.time() * 1000)
    query = sign_request(params, api_secret)
    url = f"{BASE}{path}?{query}"
    headers = {"Content-Type": "application/json"}
    r = requests.get(url, headers=headers, timeout=10)
    return r.json()

def public_get(path, params=None):
    url = f"{BASE}{path}"
    r = requests.get(url, params=params, timeout=10)
    return r.json()

# ============ DATA FETCHERS ============
def get_price_data(symbol):
    # latest price
    url = f"{BASE}/api/v1/contract/fair_price/{symbol}"
    r = requests.get(url).json()
    current_price = float(r["data"]["fairPrice"])

    # last 2 hourly candles
    url = f"{BASE}/api/v1/contract/kline/{symbol}"
    r = requests.get(url, params={"interval":"Min60", "limit":2}).json()
    data = r["data"]
    price_1h_ago = float(data[-2][4])  # close price
    vol_1h = float(data[-1][5])        # last candle volume
    return current_price, price_1h_ago, vol_1h

def get_funding(symbol):
    url = f"{BASE}/api/v1/contract/funding_rate/{symbol}"
    r = requests.get(url).json()
    fr = float(r["data"]["fundingRate"])
    return fr

# ============ SIGNAL LOGIC ============
def generate_signal(funding_rate, current_price, price_1h_ago):
    change = (current_price - price_1h_ago) / price_1h_ago * 100
    signal = "Neutral"

    if funding_rate > 0 and change > 0:
        signal = "Long"
    elif funding_rate < 0 and change < 0:
        signal = "Short"
    return signal, change

# ============ STREAMLIT APP ============
st.title("📊 MEXC Futures Signal Dashboard")

api_key = st.text_input("API Key (safe in secrets ideally)", type="password")
api_secret = st.text_input("API Secret (safe in secrets ideally)", type="password")
symbol = st.text_input("Enter Futures Symbol", "BTC_USDT")

if st.button("Fetch Data"):
    try:
        current_price, price_1h_ago, vol = get_price_data(symbol)
        funding = get_funding(symbol)
        signal, change = generate_signal(funding, current_price, price_1h_ago)

        st.write(f"**Funding rate:** {funding*100:.4f}%")
        st.write(f"**1h ago price:** {price_1h_ago}")
        st.write(f"**Current price:** {current_price}")
        st.write(f"**Change:** {current_price-price_1h_ago:.2f} ({change:.2f}%)")
        st.write(f"**Signal:** {signal}")
        st.write(f"**Volume (last 1h):** {vol}")
    except Exception as e:
        st.error(f"❌ Error: {e}")
