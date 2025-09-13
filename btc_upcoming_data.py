import streamlit as st
import requests
import pandas as pd
import ta
from datetime import datetime

# ============ SETTINGS ============
INTERVAL = "Min60"  # 1 hour candles in MEXC format
ATR_MULTIPLIER = 1.5

# ---------- MEXC API Functions ----------

def fetch_kline(symbol, interval=INTERVAL, limit=200):
    url = f"https://contract.mexc.com/api/v1/contract/kline/{symbol}"
    params = {"interval": interval, "limit": limit}
    try:
        res = requests.get(url, params=params, timeout=10)
        if res.status_code != 200:
            st.error(f"MEXC Kline error: {res.text}")
            return None
        data = res.json()
        if "data" not in data or not isinstance(data["data"], list) or len(data["data"]) == 0:
            return None
        df = pd.DataFrame(data["data"], columns=["timestamp","open","high","low","close","volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df["open"] = df["open"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["close"] = df["close"].astype(float)
        df["volume"] = df["volume"].astype(float)
        return df
    except Exception as e:
        st.error(f"Fetch kline error for {symbol}: {e}")
        return None

# ---------- AMD Signal Functions ----------

def generate_signal(df, price_baseline, price_current):
    if df is None or len(df) < 50:
        return None, None, None, None

    close = df["close"]
    high = df["high"]
    low = df["low"]

    ema20 = ta.trend.EMAIndicator(close, window=20).ema_indicator()
    ema50 = ta.trend.EMAIndicator(close, window=50).ema_indicator()
    macd = ta.trend.MACD(close)
    macd_line = macd.macd()
    macd_signal = macd.macd_signal()
    rsi = ta.momentum.RSIIndicator(close, window=14).rsi()
    atr = ta.volatility.AverageTrueRange(high, low, close, window=14).average_true_range().iloc[-1]

    last_close = close.iloc[-1]
    last_ema20 = ema20.iloc[-1]
    last_ema50 = ema50.iloc[-1]
    last_macd = macd_line.iloc[-1]
    last_macd_signal = macd_signal.iloc[-1]
    last_rsi = rsi.iloc[-1]

    entry = last_close
    target = None
    stop_loss = None
    signal = None

    # Long Condition
    if last_close > last_ema20 and last_ema20 > last_ema50 and last_macd > last_macd_signal and 40 <= last_rsi <= 60:
        signal = "✅ Long"
        target = entry + ATR_MULTIPLIER * atr
        stop_loss = entry - ATR_MULTIPLIER * atr
    # Short Condition
    elif last_close < last_ema50 and last_macd < last_macd_signal and last_rsi > 70:
        signal = "❌ Short"
        target = entry - ATR_MULTIPLIER * atr
        stop_loss = entry + ATR_MULTIPLIER * atr

    return signal, round(entry, 6), round(target, 6) if target else None, round(stop_loss, 6) if stop_loss else None

# ---------- Streamlit UI ----------

st.title("📊 AMD Setup Signal Scanner – MEXC")

# User input for coin
coin = st.text_input("Enter Futures Coin Symbol (e.g., BTC_USDT, ETH_USDT):", "BTC_USDT")

# Thresholds
price_thresh_pct = st.slider("Price Movement Threshold (%)", min_value=0.1, max_value=5.0, value=1.0, step=0.1)

if st.button("🔍 Generate Signal"):
    df = fetch_kline(coin, interval=INTERVAL, limit=200)
    if df is None:
        st.error("❌ Could not fetch kline data. Maybe wrong symbol or MEXC restricted.")
    else:
        # price baseline vs now
        price_baseline = df["close"].iloc[-2]  # one hour before
        price_current = df["close"].iloc[-1]

        signal, entry, target, stop = generate_signal(df, price_baseline, price_current)

        st.write(f"Price 1h ago: {price_baseline:.6f} USDT")
        st.write(f"Price now: {price_current:.6f} USDT")
        st.write(f"Price Change: {((price_current - price_baseline)/price_baseline)*100:.2f}%")

        if signal:
            st.success(f"Signal: {signal}")
            st.write(f"Entry: {entry}")
            st.write(f"Target: {target}")
            st.write(f"Stop Loss: {stop}")
        else:
            st.warning("⚠️ No clear signal based on price+indicators.")

        if abs((price_current - price_baseline)/price_baseline)*100 > price_thresh_pct:
            st.info(f"⚠️ Price movement > {price_thresh_pct}% threshold.")
