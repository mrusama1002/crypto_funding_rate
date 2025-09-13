import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# ---------- Binance Futures API ----------
BASE_URL = "https://fapi.binance.com"

def fetch_ohlcv(symbol, interval="1h", limit=100):
    url = f"{BASE_URL}/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        data = requests.get(url, timeout=10).json()
        df = pd.DataFrame(data, columns=[
            "timestamp","open","high","low","close","volume",
            "close_time","quote_asset_volume","num_trades",
            "taker_buy_base","taker_buy_quote","ignore"
        ])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df["open"] = df["open"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["close"] = df["close"].astype(float)
        df["volume"] = df["volume"].astype(float)
        return df[["timestamp","open","high","low","close","volume"]]
    except Exception as e:
        st.error(f"❌ Binance OHLCV fetch error: {e}")
        return None

def fetch_open_interest(symbol):
    url = f"{BASE_URL}/futures/data/openInterestHist?symbol={symbol}&period=5m&limit=100"
    try:
        return requests.get(url, timeout=10).json()
    except:
        return []

def fetch_funding_rate(symbol):
    url = f"{BASE_URL}/fapi/v1/fundingRate?symbol={symbol}&limit=100"
    try:
        return requests.get(url, timeout=10).json()
    except:
        return []

# ---------- AMD Signal ----------
def check_signals(symbol, oi_thresh, funding_thresh):
    # OI Data
    oi_data = fetch_open_interest(symbol)
    if not oi_data or not isinstance(oi_data, list) or "timestamp" not in oi_data[0]:
        return f"❌ No valid OI data for {symbol} (maybe API restricted)."

    now = int(datetime.utcnow().timestamp() * 1000)
    one_hour_ago = now - 3600 * 1000

    try:
        past_oi = min(oi_data, key=lambda x: abs(int(x.get("timestamp", 0)) - one_hour_ago))
        latest_oi = oi_data[-1]
        oi_change = (float(latest_oi["sumOpenInterest"]) - float(past_oi["sumOpenInterest"])) / float(past_oi["sumOpenInterest"]) * 100
    except Exception as e:
        return f"❌ OI calculation failed: {e}"

    # Funding
    funding = fetch_funding_rate(symbol)
    if not funding or "fundingRate" not in funding[-1]:
        return f"❌ No valid funding data for {symbol}"
    last_funding = float(funding[-1]["fundingRate"]) * 100

    # Signal Logic
    if oi_change > oi_thresh and last_funding > funding_thresh:
        return f"🚀 LONG Signal on {symbol}\nOI ↑ {oi_change:.2f}% | Funding {last_funding:.4f}%"
    elif oi_change < -oi_thresh and last_funding < -funding_thresh:
        return f"🔻 SHORT Signal on {symbol}\nOI ↓ {oi_change:.2f}% | Funding {last_funding:.4f}%"
    else:
        return f"⚠️ No clear signal for {symbol}\nOI Change: {oi_change:.2f}% | Funding: {last_funding:.4f}%"
# ---------- STREAMLIT APP ----------
st.title("📊 AMD Setup Signal Scanner")

# Dropdown for Futures coins
coins = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT", "XRPUSDT", "LTCUSDT"]
selected_coin = st.selectbox("Select a Futures Coin", coins)

# Threshold controls
funding_threshold = st.number_input("Funding Rate Threshold (%)", value=0.10, step=0.01)
oi_threshold = st.number_input("OI Surge Threshold (%)", value=2.0, step=0.5)

# Run Signal
if st.button("🔍 Check Signal"):
    result = check_signals(selected_coin, oi_threshold, funding_threshold)
    st.write(result)

