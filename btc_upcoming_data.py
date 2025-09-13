import streamlit as st
import requests
import time
from datetime import datetime, timedelta

BASE_URL = "https://contract.mexc.com"

def get_current_price(symbol):
    try:
        url = f"{BASE_URL}/api/v1/contract/fair_price/{symbol}"
        res = requests.get(url).json()
        return float(res["data"]["fairPrice"])
    except Exception as e:
        st.error(f"❌ Price fetch error: {e}")
        return None

def get_price_1h_before(symbol):
    try:
        end_time = int(time.time() * 1000)
        start_time = end_time - 2 * 3600 * 1000  # last 2h
        url = f"{BASE_URL}/api/v1/contract/kline/{symbol}?interval=Min1&start={start_time}&end={end_time}"
        res = requests.get(url).json()
        if "data" in res and len(res["data"]) > 60:
            one_hour_before = res["data"][-61]  # 61 candles back = 1 hour
            return float(one_hour_before[4])  # close price
        return None
    except Exception as e:
        st.error(f"❌ Kline fetch error: {e}")
        return None

def get_funding_rate(symbol):
    try:
        url = f"{BASE_URL}/api/v1/contract/funding_rate/{symbol}"
        res = requests.get(url).json()
        if "data" in res and len(res["data"]) > 0:
            latest = res["data"][-1]
            return float(latest["fundingRate"]), int(latest["settleTime"])
        return None, None
    except Exception as e:
        st.error(f"❌ Funding rate fetch error: {e}")
        return None, None

st.title("📊 MEXC Futures Data Tracker")

symbol = st.text_input("Enter symbol (e.g. BTC_USDT, ETH_USDT, SOL_USDT)", "BTC_USDT")

if st.button("Fetch Data"):
    current_price = get_current_price(symbol)
    past_price = get_price_1h_before(symbol)
    funding_rate, funding_time = get_funding_rate(symbol)

    if current_price:
        st.success(f"💰 Current Price: {current_price}")
    if past_price:
        st.info(f"⏳ Price 1 Hour Ago: {past_price}")
    if funding_rate is not None:
        st.warning(f"📉 Current Funding Rate: {funding_rate * 100:.4f}% (Last settlement: {datetime.utcfromtimestamp(funding_time/1000)})")
