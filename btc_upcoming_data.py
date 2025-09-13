import streamlit as st
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="Crypto OI & Funding Tracker", layout="centered")
st.title("📊 Crypto OI & Funding Tracker")

# --------------------------
# Fetch All Supported Perpetual Symbols
# --------------------------
def get_perpetual_symbols():
    url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
    try:
        data = requests.get(url, timeout=5).json()
        symbols = [
            s['symbol'] for s in data['symbols']
            if s['contractType'] == 'PERPETUAL' and s['quoteAsset'] == 'USDT'
        ]
        return sorted(symbols)
    except:
        return ["BTCUSDT", "ETHUSDT"]  # fallback

# --------------------------
# API Functions
# --------------------------
def get_funding_rate(symbol, lookback_hours=0):
    url = f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}&limit=1000"
    try:
        data = requests.get(url, timeout=5).json()
    except:
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
    except:
        return None
    if not isinstance(data, list) or len(data) == 0:
        return None

    target_time = int((datetime.utcnow() - timedelta(hours=lookback_hours)).timestamp() * 1000)
    past = min(data, key=lambda x: abs(int(x.get('timestamp', 0)) - target_time))
    return float(past.get('sumOpenInterest', 0))


def get_price(symbol, lookback_hours=0):
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=1h&limit=2"
    try:
        data = requests.get(url, timeout=5).json()
    except:
        return None
    if not isinstance(data, list) or len(data) == 0:
        return None

    if lookback_hours == 0:
        return float(data[-1][4])  # last close
    else:
        return float(data[-2][4])  # one hour before close


# --------------------------
# Streamlit UI
# --------------------------
perp_symbols = get_perpetual_symbols()
symbol = st.selectbox("Select Perpetual Coin Symbol", perp_symbols, index=perp_symbols.index("BTCUSDT"))

funding_threshold = st.number_input("Funding Rate Threshold (%)", value=0.10, step=0.01)
oi_threshold = st.number_input("OI Surge Threshold (%)", value=2.0, step=0.1)

if st.button("🔍 Check Data"):
    st.info(f"Fetching data for **{symbol}**...")

    baseline_funding = get_funding_rate(symbol, lookback_hours=1)
    current_funding = get_funding_rate(symbol, lookback_hours=0)

    baseline_oi = get_open_interest_hist(symbol, lookback_hours=1)
    current_oi = get_open_interest_hist(symbol, lookback_hours=0)

    baseline_price = get_price(symbol, lookback_hours=1)
    current_price = get_price(symbol, lookback_hours=0)

    if None in [baseline_funding, current_funding, baseline_oi, current_oi, baseline_price, current_price]:
        st.error("❌ No data available for this symbol. Try another one (maybe no OI data).")
    else:
        # Calculations
        oi_change = ((current_oi - baseline_oi) / baseline_oi) * 100 if baseline_oi else 0
        funding_change = current_funding - baseline_funding
        price_change = ((current_price - baseline_price) / baseline_price) * 100 if baseline_price else 0

        # Display Results
        st.subheader(f"📌 Results for {symbol}")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Baseline Funding (1h ago)", f"{baseline_funding:.4f}%")
            st.metric("Baseline OI (1h ago)", f"{baseline_oi:,.2f}")
            st.metric("Baseline Price (1h ago)", f"${baseline_price:,.2f}")

        with col2:
            st.metric("Current Funding", f"{current_funding:.4f}%", delta=f"{funding_change:.4f}%")
            st.metric("Current OI", f"{current_oi:,.2f}", delta=f"{oi_change:.2f}%")
            st.metric("Current Price", f"${current_price:,.2f}", delta=f"{price_change:.2f}%")

        # Alerts
        st.subheader("⚠️ Alerts")
        if abs(funding_change) > funding_threshold:
            st.warning(f"Funding rate moved {funding_change:.4f}% (Threshold {funding_threshold}%)")

        if abs(oi_change) > oi_threshold:
            st.warning(f"Open Interest changed {oi_change:.2f}% (Threshold {oi_threshold}%)")

        if abs(price_change) > 0.5:  # example price alert
            st.info(f"Price moved {price_change:.2f}% in last 1h")
