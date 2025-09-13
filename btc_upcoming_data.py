# app.py
import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="MEXC Futures — Price & Funding Checker", layout="centered")

BASE = "https://contract.mexc.com/api/v1"

# ---------- Helpers ----------
@st.cache_data(ttl=3600)
def get_contracts():
    """Fetch available MEXC futures contracts (cached 1 hour)."""
    try:
        url = f"{BASE}/contract/detail"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        j = r.json()
        if "data" in j and isinstance(j["data"], list):
            return [c.get("symbol") for c in j["data"] if c.get("symbol")]
        return []
    except Exception as e:
        st.warning(f"Could not fetch contracts list: {e}")
        return []

def fetch_fair_price(symbol):
    """Get current fair price (public)."""
    try:
        url = f"{BASE}/contract/fair_price/{symbol}"
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        j = r.json()
        # Expected: {"success": true, "code":0, "data": {"fairPrice":..., "timestamp":...}}
        if "data" in j and j["data"] and "fairPrice" in j["data"]:
            return float(j["data"]["fairPrice"]), j["data"].get("timestamp")
        # Some variants return code/data differently:
        if "success" in j and j.get("data") and "fairPrice" in j["data"]:
            return float(j["data"]["fairPrice"]), j["data"].get("timestamp")
        return None, None
    except Exception as e:
        return None, None

def fetch_1h_price(symbol):
    """Get last two 1h candles using kline Min60 and return current close and 1h-ago close."""
    try:
        # request two 1h candles (limit=2) using interval Min60
        url = f"{BASE}/contract/kline/{symbol}"
        params = {"interval": "Min60", "limit": 2}
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        j = r.json()
        # MEXC returns {"data": [...] } where each candle is [ts, open, high, low, close, volume]
        if "data" not in j or not isinstance(j["data"], list) or len(j["data"]) < 2:
            return None, None
        # take last two elements
        candle_prev = j["data"][-2]  # 1 hour ago close
        candle_now  = j["data"][-1]  # current candle close
        # sometimes structure might be nested as {"data": {"data":[...]}}, handle that:
        if isinstance(j["data"], dict) and "data" in j["data"]:
            arr = j["data"]["data"]
            if len(arr) < 2:
                return None, None
            candle_prev = arr[-2]
            candle_now  = arr[-1]
        close_prev = float(candle_prev[4])
        close_now  = float(candle_now[4])
        ts_prev = int(candle_prev[0])
        ts_now  = int(candle_now[0])
        return (close_now, ts_now), (close_prev, ts_prev)
    except Exception:
        return None, None

def fetch_funding_rate(symbol):
    """Get funding rate info (public endpoint). Returns dict or None."""
    try:
        url = f"{BASE}/contract/funding_rate/{symbol}"
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        j = r.json()
        # Example response: {"success":true,"code":0,"data": {"symbol":..,"fundingRate":..,"nextSettleTime":..,"timestamp":..}}
        # Some endpoints return single dict in data or list, handle either
        data = j.get("data")
        if data is None:
            return None
        # If data is list with records, take last
        if isinstance(data, list) and len(data) > 0:
            rec = data[-1]
        elif isinstance(data, dict):
            rec = data
        else:
            return None
        # ensure keys
        if "fundingRate" in rec:
            # fundingRate here is decimal like 0.0005 -> convert to percent if desired
            fr = float(rec["fundingRate"])
            # fields: nextSettleTime or settleTime or timestamp may be present
            ts = rec.get("nextSettleTime") or rec.get("timestamp") or rec.get("fundingTime")
            return {"fundingRate": fr, "timestamp": ts, "raw": rec}
        return None
    except Exception:
        return None

# ---------- UI ----------
st.title("MEXC Futures — Price & Funding (public)")

contracts = get_contracts()
if not contracts:
    st.info("Warning: Could not fetch contracts list. You can still type a symbol (e.g. BTC_USDT).")

symbol = st.text_input("Enter contract symbol (format like BTC_USDT)", value="BTC_USDT").strip().upper()

if st.button("Fetch Price & Funding"):
    if not symbol:
        st.error("Enter a symbol.")
    else:
        # Validate if available
        if contracts and symbol not in contracts:
            st.warning(f"{symbol} not found in fetched contracts list (still trying to fetch data). Try BTC_USDT or ETH_USDT.")
        # Fetch fair price
        fair_price, fair_ts = fetch_fair_price(symbol)
        k_now, k_prev = fetch_1h_price(symbol)
        fr = fetch_funding_rate(symbol)

        # Display price results
        st.subheader("Price")
        if fair_price is not None:
            t = datetime.utcfromtimestamp(fair_ts/1000) if fair_ts else None
            st.write(f"Fair price (MEXC): {fair_price}    (ts: {t})")
        else:
            st.write("Fair price: unavailable")

        if k_now and k_prev:
            (now_close, now_ts), (prev_close, prev_ts) = k_now, k_prev
            st.write(f"1h-ago close: {prev_close}  (ts: {datetime.utcfromtimestamp(prev_ts/1000)})")
            st.write(f"Current close: {now_close}  (ts: {datetime.utcfromtimestamp(now_ts/1000)})")
            pct = (now_close - prev_close) / prev_close * 100
            st.write(f"1h Change: {pct:.3f}%")
        else:
            st.write("Kline-based 1h prices: unavailable (check symbol / MEXC format)")

        # Display funding
        st.subheader("Funding Rate (public)")
        if fr:
            fr_pct = fr["fundingRate"] * 100  # convert to percent
            ts = fr.get("timestamp")
            ts_dt = datetime.utcfromtimestamp(int(ts)/1000) if ts else None
            st.write(f"Funding rate (decimal): {fr['fundingRate']}")
            st.write(f"Funding rate (%): {fr_pct:.6f}%")
            st.write(f"Next/last settle ts: {ts_dt}")
            # If you want previous funding record, attempt to request list form:
            # (some responses include lists; we returned the last record only)
        else:
            st.write("Funding rate: unavailable (public endpoint may be limited for this symbol)")

        st.info("If data missing: try these symbols -> BTC_USDT, ETH_USDT, SOL_USDT. If still missing, MEXC may restrict that symbol or the endpoint structure differs.")
