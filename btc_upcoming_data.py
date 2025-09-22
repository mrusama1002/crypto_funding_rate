import requests
import pandas as pd
import math
import streamlit as st
from datetime import datetime
import pytz

# ----------------- CONFIG -----------------
WATCHLIST = ["BTC_USDT", "ETH_USDT", "SOL_USDT", "XRP_USDT"]
INTERVALS = ["Min5","Min15","Min30","Min60", "Hour4","Day1", "Week1"]
KL_LIMIT = 300
ATR_PERIOD = 14
ATR_MULTIPLIER = 1.5
TIMEZONE = 'Asia/Karachi'  # Pakistan time
# ------------------------------------------

def interval_to_label(interval: str) -> str:
    mapping = {
        "Min1": "1m", "Min5": "5m", "Min15": "15m", "Min30": "30m",
        "Min60": "1h", "Hour4": "4h", "Day1": "1D", "Week1": "1W", "Month1": "1M"
    }
    return mapping.get(interval, interval)

def convert_time(ts):
    ts = int(ts)
    # Agar timestamp bada hai to milliseconds, nahi to seconds
    if ts > 1e12:
        dt = pd.to_datetime(ts, unit='ms', utc=True)
    else:
        dt = pd.to_datetime(ts, unit='s', utc=True)
    dt_local = dt.tz_convert('Asia/Karachi')
    return dt_local.strftime("%Y-%m-%d %H:%M")

def get_future_klines(symbol: str, interval="Min60", limit=200):
    url = f"https://contract.mexc.com/api/v1/contract/kline/{symbol}?interval={interval}&limit={limit}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data.get("success") or "data" not in data:
            return None
        df = pd.DataFrame(data["data"], columns=["time","open","high","low","close","volume","amount"])
        for col in ["open","high","low","close"]:
            df[col] = df[col].astype(float)
        return df[["time","open","high","low","close","volume"]]
    except Exception:
        return None

def compute_atr(df: pd.DataFrame, period=14):
    df2 = df.copy()
    df2["H-L"] = df2["high"] - df2["low"]
    df2["H-Cprev"] = (df2["high"] - df2["close"].shift(1)).abs()
    df2["L-Cprev"] = (df2["low"] - df2["close"].shift(1)).abs()
    df2["TR"] = df2[["H-L", "H-Cprev", "L-Cprev"]].max(axis=1)
    atr = df2["TR"].rolling(period).mean()
    return atr

def format_number(x):
    if x is None or (isinstance(x, float) and (math.isinf(x) or math.isnan(x))):
        return "N/A"
    return f"{x:,.2f}" if abs(x) >= 1 else f"{x:.6f}".rstrip('0').rstrip('.')

def generate_signal(symbol: str, df: pd.DataFrame, interval: str):
    prev = df.iloc[-2]
    last = df.iloc[-1]
    current = float(last["close"])
    prev_high = float(prev["high"])
    prev_low = float(prev["low"])
    atr = compute_atr(df, ATR_PERIOD).iloc[-1]

    int_label = interval_to_label(interval)
    dt = convert_time(last["time"])

    if current > prev_high:  # LONG
        entry = current
        tp1 = entry + 0.5 * atr
        tp2 = entry + 1.0 * atr
        tp3 = entry + 1.5 * atr
        sl = entry - ATR_MULTIPLIER * atr
        return (
            f"🚀 **BREAKOUT LONG** | {symbol} ({int_label})\n"
            f"📅 {dt}\n"
            f"💰 Current: {format_number(current)}\n"
            f"🎯 Entry: {format_number(entry)}\n"
            f"🎯 TP1: {format_number(tp1)} | TP2: {format_number(tp2)} | TP3: {format_number(tp3)}\n"
            f"🛡️ SL: {format_number(sl)}"
        )
    elif current < prev_low:  # SHORT
        entry = current
        tp1 = entry - 0.5 * atr
        tp2 = entry - 1.0 * atr
        tp3 = entry - 1.5 * atr
        sl = entry + ATR_MULTIPLIER * atr
        return (
            f"🔄 **REVERSAL SHORT** | {symbol} ({int_label})\n"
            f"📅 {dt}\n"
            f"💰 Current: {format_number(current)}\n"
            f"🎯 Entry: {format_number(entry)}\n"
            f"🎯 TP1: {format_number(tp1)} | TP2: {format_number(tp2)} | TP3: {format_number(tp3)}\n"
            f"🛡️ SL: {format_number(sl)}"
        )
    else:
        return f"ℹ️ {symbol} neutral @ {format_number(current)} ({int_label})"

# ---------- BACKTEST ----------
def backtest(df: pd.DataFrame):
    atr_series = compute_atr(df, ATR_PERIOD)
    wins, losses, neutrals = 0, 0, 0
    trades = []

    for i in range(ATR_PERIOD+1, len(df)-1):
        prev = df.iloc[i-1]
        candle = df.iloc[i]
        atr = atr_series.iloc[i]
        if math.isnan(atr):
            continue

        entry = None
        direction = None
        tp1 = sl = None

        if candle["close"] > prev["high"]:  # LONG
            entry = candle["close"]
            direction = "LONG"
            tp1 = entry + 0.5 * atr
            sl = entry - ATR_MULTIPLIER * atr
        elif candle["close"] < prev["low"]:  # SHORT
            entry = candle["close"]
            direction = "SHORT"
            tp1 = entry - 0.5 * atr
            sl = entry + ATR_MULTIPLIER * atr

        if entry:
            next_candle = df.iloc[i+1]
            high, low = next_candle["high"], next_candle["low"]
            result = "NEUTRAL"
            if direction == "LONG":
                if high >= tp1: result = "WIN"
                elif low <= sl: result = "LOSS"
            elif direction == "SHORT":
                if low <= tp1: result = "WIN"
                elif high >= sl: result = "LOSS"

            if result == "WIN": wins += 1
            elif result == "LOSS": losses += 1
            else: neutrals += 1

            trades.append({
                "time": convert_time(candle["time"]),  # Fixed datetime
                "direction": direction,
                "entry": entry,
                "tp1": tp1,
                "sl": sl,
                "result": result
            })

    return trades, wins, losses, neutrals

# ----------------- STREAMLIT APP -----------------
st.set_page_config(page_title="MEXC Futures Scanner + Backtest", layout="wide")
st.title("📊 MEXC Futures Signal Scanner + Backtest")

coin = st.selectbox("Select Coin", ["ALL"] + WATCHLIST)
intervals = st.multiselect("Select intervals", INTERVALS, default=["Min60"])

if st.button("Run Scanner"):
    symbols = WATCHLIST if coin == "ALL" else [coin]
    for sym in symbols:
        st.subheader(f"Signals for {sym}")
        for interval in intervals:
            df = get_future_klines(sym, interval, KL_LIMIT)
            if df is None:
                st.error(f"No data for {sym} ({interval})")
                continue
            signal = generate_signal(sym, df, interval)
            st.markdown(signal)

if st.button("Run Backtest"):
    symbols = WATCHLIST if coin == "ALL" else [coin]
    for sym in symbols:
        st.subheader(f"Backtest for {sym}")
        for interval in intervals:
            df = get_future_klines(sym, interval, KL_LIMIT)
            if df is None:
                st.error(f"No data for {sym} ({interval})")
                continue
            trades, wins, losses, neutrals = backtest(df)
            total = wins + losses
            acc = (wins / total * 100) if total > 0 else 0
            st.write(f"✅ Wins: {wins} | ❌ Losses: {losses} | ⚪ Neutral: {neutrals}")
            st.write(f"🎯 Accuracy: {acc:.2f}%")
            st.dataframe(pd.DataFrame(trades).tail(10))
