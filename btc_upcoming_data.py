import streamlit as st
import requests
import time
from datetime import datetime, timedelta

# --- Functions ---
def get_funding_rate(symbol, lookback_hours=0):
    url = f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}&limit=1000"
    data = requests.get(url).json()
    if lookback_hours == 0:
        return float(data[-1]['fundingRate']) * 100
    else:
        target_time = int((datetime.utcnow() - timedelta(hours=lookback_hours)).timestamp() * 1000)
        past = min(data, key=lambda x: abs(int(x['fundingTime']) - target_time))
        return float(past['fundingRate']) * 100

def get_open_interest(symbol):
    url = f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}"
    data = requests.get(url).json()
    return float(data['openInterest'])

def get_open_interest_hist(symbol, lookback_hours=1):
    url = f"https://fapi.binance.com/futures/data/openInterestHist?symbol={symbol}&period=5m&limit=500"
    data = requests.get(url).json()
    target_time = int((datetime.utcnow() - timedelta(hours=lookback_hours)).timestamp() * 1000)
    past = min(data, key=lambda x: abs(int(x['timestamp']) - target_time))
    return float(past['sumOpenInterest'])

def get_price(symbol, lookback_hours=0):
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=1m&limit=60"
    data = requests.get(url).json()
    if lookback_hours == 0:
        return float(data[-1][4])  # latest close price
    else:
        return float(data[0][4])   # price ~1h ago

def generate_signal(funding, oi, baseline_funding, baseline_oi, funding_threshold, oi_threshold_percent):
    signal = "Neutral"
    if funding > funding_threshold:
        signal = "🚨 Long Crowding → Potential Pullback"
    elif funding < -funding_threshold:
        signal = "🚀 Short Crowding → Potential Rally"
    if baseline_oi:
        oi_change = ((oi - baseline_oi) / baseline_oi) * 100
        if oi_change > oi_threshold_percent:
            signal += f" | 📈 OI Surge Alert! (+{oi_change:.2f}%)"
    return signal

# --- Streamlit UI ---
st.title("📊 Crypto Futures Signal Tracker")
st.write("Track **Funding Rate, Open Interest, and Price** vs 1h ago baseline")

symbol = st.text_input("Enter Coin Symbol (e.g. BTCUSDT, ETHUSDT):", "BTCUSDT").upper()
funding_threshold = 0.10   # %
oi_threshold_percent = 2   # %
refresh = 30               # seconds

if st.button("Start Tracking"):
    # --- Baselines (1h ago) ---
    baseline_funding = get_funding_rate(symbol, lookback_hours=1)
    baseline_oi = get_open_interest_hist(symbol, lookback_hours=1)
    baseline_price = get_price(symbol, lookback_hours=1)

    st.success(f"Baseline (1h ago) for {symbol} set ✅")
    st.write(f"**Baseline Funding Rate (1h ago):** {baseline_funding:.4f}%")
    st.write(f"**Baseline Open Interest (1h ago):** {baseline_oi}")
    st.write(f"**Baseline Price (1h ago):** {baseline_price}")

    placeholder = st.empty()

    while True:
        try:
            funding = get_funding_rate(symbol)
            oi = get_open_interest(symbol)
            price = get_price(symbol)

            signal = generate_signal(funding, oi, baseline_funding, baseline_oi, funding_threshold, oi_threshold_percent)

            with placeholder.container():
                st.subheader(f"Results for {symbol}")
                st.metric("Current Funding Rate (%)", f"{funding:.4f}", f"{funding - baseline_funding:.4f}")
                st.metric("Current Open Interest", f"{oi}", f"{oi - baseline_oi:.2f}")
                st.metric("Current Price", f"{price}", f"{price - baseline_price:.2f}")
                st.write(f"**Signal:** {signal}")

            time.sleep(refresh)

        except Exception as e:
            st.error(f"Error: {e}")
            time.sleep(10)
