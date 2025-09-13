import streamlit as st
import requests
from datetime import datetime, timedelta

# =============== API FUNCTIONS ===============

def get_funding_rate(symbol, lookback_hours=0):
    """Fetch funding rate history from Binance Futures"""
    url = "https://fapi.binance.com/fapi/v1/fundingRate"
    params = {"symbol": symbol.replace("_", ""), "limit": 1000}
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        return None, None
    data = resp.json()
    if not data:
        return None, None

    if lookback_hours == 0:
        # Latest funding
        return float(data[-1]["fundingRate"]), datetime.utcfromtimestamp(int(data[-1]["fundingTime"]) / 1000)

    # Baseline (lookback_hours ago)
    target_time = int((datetime.utcnow() - timedelta(hours=lookback_hours)).timestamp() * 1000)
    past = min(data, key=lambda x: abs(int(x["fundingTime"]) - target_time))
    return float(past["fundingRate"]), datetime.utcfromtimestamp(int(past["fundingTime"]) / 1000)


def get_open_interest(symbol):
    """Fetch open interest from Binance Futures"""
    url = "https://fapi.binance.com/fapi/v1/openInterest"
    params = {"symbol": symbol.replace("_", "")}
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        return None
    data = resp.json()
    return float(data["openInterest"]) if "openInterest" in data else None


def get_price(symbol, lookback_hours=0):
    """Fetch price from Binance Futures"""
    url = "https://fapi.binance.com/fapi/v1/klines"
    interval = "1h"
    limit = lookback_hours + 1
    params = {"symbol": symbol.replace("_", ""), "interval": interval, "limit": limit}
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        return None
    data = resp.json()
    if not data:
        return None
    if lookback_hours == 0:
        return float(data[-1][4])  # close price
    else:
        return float(data[-(lookback_hours+1)][4])


# =============== STREAMLIT APP ===============

st.title("📊 Crypto Futures Signal Tracker")

symbol = st.text_input("Enter Symbol (e.g., BTC_USDT, ETH_USDT)", "BTC_USDT").upper()

funding_threshold = st.slider("Funding Rate Threshold (%)", 0.01, 0.5, 0.10, 0.01)
oi_threshold = st.slider("OI Surge Threshold (%)", 0.5, 5.0, 2.0, 0.1)

if st.button("🔍 Check Signal"):
    with st.spinner("Fetching data..."):
        funding_now, t_now = get_funding_rate(symbol, lookback_hours=0)
        funding_base, t_base = get_funding_rate(symbol, lookback_hours=1)
        oi_now = get_open_interest(symbol)
        price_now = get_price(symbol, lookback_hours=0)
        price_base = get_price(symbol, lookback_hours=1)

    if not all([funding_now, funding_base, oi_now, price_now, price_base]):
        st.error("❌ No data available. Try another symbol (maybe this coin has no futures data).")
    else:
        st.success(f"✅ Data Fetched for {symbol}")
        st.write(f"**Funding Rate Now:** {funding_now*100:.4f}%  (at {t_now})")
        st.write(f"**Funding Rate 1h Ago:** {funding_base*100:.4f}%  (at {t_base})")
        st.write(f"**Open Interest Now:** {oi_now:,.2f}")
        st.write(f"**Price Now:** {price_now:,.2f} USDT")
        st.write(f"**Price 1h Ago:** {price_base:,.2f} USDT")

        # ========== Signal Logic ==========
        signal = None
        if funding_now > funding_threshold/100:
            signal = "🚨 Long Crowding → Potential Pullback"
        elif funding_now < -funding_threshold/100:
            signal = "🚨 Short Crowding → Potential Rally"

        oi_change = ((oi_now - oi_now*0.98) / oi_now*0.98) * 100 if oi_now else 0

        if oi_now and oi_change > oi_threshold:
            if signal:
                signal += " | 📈 OI Surge Alert!"
            else:
                signal = "📈 OI Surge Alert!"

        if signal:
            st.warning(f"**Signal:** {signal}")
        else:
            st.info(f"No clear signal found for {symbol} right now.")
