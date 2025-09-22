import requests
import pandas as pd
import streamlit as st
from datetime import datetime
import math

# ----------------- CONFIG -----------------
WATCHLIST = ["BTC_USDT", "ETH_USDT", "SOL_USDT", "XRP_USDT"]
INTERVALS = ["Min5","Min15","Min30","Min60", "Hour4","Day1", "Week1"]   # scan multiple intervals
KL_LIMIT = 200
ATR_PERIOD = 14
ATR_MULTIPLIER = 1.5
# ------------------------------------------

def interval_to_label(interval: str) -> str:
    mapping = {
        "Min1": "1m", "Min5": "5m", "Min15": "15m", "Min30": "30m",
        "Min60": "1h", "Hour4": "4h", "Day1": "1D", "Week1": "1W", "Month1": "1M"
    }
    return mapping.get(interval, interval)

def get_future_klines(symbol: str, interval="Min60", limit=200):
    url = f"https://contract.mexc.com/api/v1/contract/kline/{symbol}?interval={interval}&limit={limit}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data.get("success") or "data" not in data:
            return None
        df = pd.DataFrame(data["data"], columns=[
            "time","open","high","low","close","volume","amount"
        ])
        for col in ["open","high","low","close"]:
            df[col] = df[col].astype(float)
        return df[["time","open","high","low","close","volume"]]
    except Exception:
        return None

def compute_atr(df: pd.DataFrame, period=14):
    if df is None or len(df) < period + 1:
        return None
    df2 = df.copy()
    df2["H-L"] = df2["high"] - df2["low"]
    df2["H-Cprev"] = (df2["high"] - df2["close"].shift(1)).abs()
    df2["L-Cprev"] = (df2["low"] - df2["close"].shift(1)).abs()
    df2["TR"] = df2[["H-L", "H-Cprev", "L-Cprev"]].max(axis=1)
    atr = df2["TR"].rolling(period).mean().iloc[-1]
    return None if pd.isna(atr) else float(atr)

def format_number(x):
    if x is None or (isinstance(x, float) and (math.isinf(x) or math.isnan(x))):
        return "N/A"
    return f"{x:,.2f}" if abs(x) >= 1 else f"{x:.6f}".rstrip('0').rstrip('.')

def generate_signal(symbol: str, df: pd.DataFrame, interval: str):
    now = datetime.now().strftime("%d-%b %I:%M %p")
    prev = df.iloc[-2]
    last = df.iloc[-1]

    current = float(last["close"])
    prev_high = float(prev["high"])
    prev_low = float(prev["low"])
    atr = compute_atr(df, ATR_PERIOD) or abs(prev_high - prev_low) or (current * 0.005)

    int_label = interval_to_label(interval)

    if current > prev_high:
        entry = current
        tp1 = round(entry + 0.5 * atr, 6)
        tp2 = round(entry + 1.0 * atr, 6)
        tp3 = round(entry + 1.5 * atr, 6)
        stop_loss = round(entry - ATR_MULTIPLIER * atr, 6)

        return (
f"🚀 **BREAKOUT ALERT** 🚀 | ⏱ {int_label}\n"
f"💰 Current: {format_number(current)}\n"
f"🎯 Entry: {format_number(entry)}\n"
f"🎯 TP1: {format_number(tp1)} | TP2: {format_number(tp2)} | TP3: {format_number(tp3)}\n"
f"🛡️ SL: {format_number(stop_loss)}\n"
f"📈 Direction: **Go Long 🚀**"
        )
    elif current < prev_low:
        entry = current
        tp1 = round(entry - 0.5 * atr, 6)
        tp2 = round(entry - 1.0 * atr, 6)
        tp3 = round(entry - 1.5 * atr, 6)
        stop_loss = round(entry + ATR_MULTIPLIER * atr, 6)

        return (
f"🔄 **REVERSAL ALERT** 🔄 | ⏱ {int_label}\n"
f"💰 Current: {format_number(current)}\n"
f"🎯 Entry: {format_number(entry)}\n"
f"🎯 TP1: {format_number(tp1)} | TP2: {format_number(tp2)} | TP3: {format_number(tp3)}\n"
f"🛡️ SL: {format_number(stop_loss)}\n"
f"📉 Direction: **Go Short 📉**"
        )
    else:
        return f"ℹ️ {symbol} neutral @ {format_number(current)} ({int_label})"

# ----------------- STREAMLIT APP -----------------
st.set_page_config(page_title="MEXC Futures Signal Scanner", layout="wide")

st.title("📊 MEXC Futures Signal Scanner Price Action")

# User input coin
coin_input = st.text_input("Enter coin (e.g. BTC_USDT) or type ALL:", "ALL").upper()
intervals = st.multiselect("Select intervals", INTERVALS, default=INTERVALS)

if st.button("Run Scanner"):
    symbols = WATCHLIST if coin_input == "ALL" else [coin_input]
    for sym in symbols:
        st.subheader(f"Signals for {sym}")
        for interval in intervals:
            df = get_future_klines(sym, interval, KL_LIMIT)
            if df is None:
                st.error(f"No data for {sym} ({interval})")
                continue
            signal = generate_signal(sym, df, interval)
            st.markdown(signal)
