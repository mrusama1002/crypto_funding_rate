import streamlit as st
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="Crypto OI & Funding Tracker", layout="centered")

st.title("📊 Crypto OI & Funding Tracker")

# --------------------------
# API Functions (Safe with checks)
# --------------------------
def get_funding_rate(symbol, lookback_hours=0):
    url = f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}&limit=1000"
    try:
        data = requests.get(url, timeout=5).json()
    except Exception:
        return None

    if not isinstance(data, list) or len(data) == 0:
        return None

    if lookback_hours == 0:
        return float(data[-1].get('fundingRate', 0)) * 100
    else:
        target_time = int((datetime.utcnow() - timedelta(hours=lookback_hours)).timestamp() * 1000)
        past = min(data, key=lambda x: abs(int(x.get('fundingTime', 0)) - target_time))
        return float(past.get('fundingRate', 0)) * 100


def get_open_interest_hist(symbol, lookback_hours=1):
    url = f"https://fapi.binance.com/futures/data/openInterestHist?symbol={symbol}&period=5m&limit=500"
    try:
        data = requests.get(url, timeout=5).json()
    except Exception:
        return None

    if not isinstance(data, list) or len(data) == 0:
        return None

    target_time = int((datetime.utcnow() - timedelta(hours=lookback_hours)).timestam
