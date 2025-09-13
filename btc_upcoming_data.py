import requests
import pandas as pd
import ta
import streamlit as st

# ========== SETTINGS ==========
INTERVAL = "1h"
LIMIT = 100
ATR_MULTIPLIER = 1.5

# ---------- Fetch Available Contracts ----------
@st.cache_data(ttl=3600)
def get_available_contracts():
    url = "https://contract.mexc.com/api/v1/contract/detail"
    try:
        res = requests.get(url, timeout=10).json()
        if "data" not in res:
            return []
        return [c["symbol"] for c in res["data"]]
    except Exception as e:
        st.error(f"❌ Contract fetch error: {e}")
        return []

# ---------- Fetch Kline ----------
def fetch_kline(symbol, interval=INTERVAL, limit=LIMIT):
    url = f"https://contract.mexc.com/api/v1/contract/kline/{symbol}"
    params = {"interval": interval, "limit": limit}
    try:
        res = requests.get(url, params=params, timeout=10).json()
        if "data" not in res or not res["data"]:
            return None
        df = pd.DataFrame(res["data"], columns=[
            "timestamp", "open", "high", "low", "close", "volume"
        ])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df["open"] = df["open"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["close"] = df["close"].astype(float)
        df["volume"] = df["volume"].astype(float)
        return df
    except Exception as e:
        st.error(f"❌ Could not fetch kline data: {e}")
        return None

# ---------- Fetch Funding Rate ----------
def fetch_funding_rate(symbol):
    url = f"https://contract.mexc.com/api/v1/contract/funding_rate/{symbol}"
    try:
        res = requests.get(url, timeout=10).json()
        if "data" not in res or not res["data"]:
            return None

        data = res["data"]
        if isinstance(data, dict):  # agar single object aya
            data = [data]

        df = pd.DataFrame(data)
        if "fundingRate" not in df or "fundingTime" not in df:
            return None

        df["fundingRate"] = df["fundingRate"].astype(float)
        df["timestamp"] = pd.to_datetime(df["fundingTime"], unit="ms")
        return df.sort_values("timestamp")
    except Exception as e:
        st.error(f"❌ Funding rate fetch error: {e}")
        return None

# ---------- Signal Logic ----------
def generate_signal(df):
    if df is None or df.empty or len(df) < 50:
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

    signal = None
    entry = last_close
    target = None
    stop_loss = None

    if last_close > last_ema20 > last_ema50 and last_macd > last_macd_signal and 40 <= last_rsi <= 60:
        signal = "📈 Long"
        target = entry + ATR_MULTIPLIER * atr
        stop_loss = entry - ATR_MULTIPLIER * atr
    elif last_close < last_ema50 and last_macd < last_macd_signal and last_rsi > 70:
        signal = "📉 Short"
        target = entry - ATR_MULTIPLIER * atr
        stop_loss = entry + ATR_MULTIPLIER * atr

    if signal is None:
        return None, None, None, None
    return signal, round(entry, 4), round(target, 4), round(stop_loss, 4)

# ---------- STREAMLIT APP ----------
st.set_page_config(page_title="MEXC Futures Scanner", layout="centered")
st.title("📊 MEXC Futures Signal Scanner with Price + Funding Rate")

contracts = get_available_contracts()
coin = st.text_input("Enter Coin Symbol", "BTC_USDT")

if st.button("Check Signal"):
    if coin not in contracts:
        st.error(f"❌ {coin} not found in MEXC futures contracts. Try one of: {contracts[:5]}")
    else:
        df = fetch_kline(coin, interval=INTERVAL, limit=LIMIT)
        fr = fetch_funding_rate(coin)

        if df is not None and not df.empty:
            now_price = df["close"].iloc[-1]
            one_hour_ago = df["close"].iloc[-2]  # previous 1h candle

            st.info(f"💰 **Price Now:** {now_price}\n⏳ **1h Ago Price:** {one_hour_ago}")

        if fr is not None and not fr.empty:
            current_fr = fr["fundingRate"].iloc[-1]
            prev_fr = fr["fundingRate"].iloc[-2] if len(fr) > 1 else None

            st.info(f"📊 **Funding Rate Now:** {current_fr}\n⏳ **Prev Funding Rate:** {prev_fr}")

        signal, entry, target, stop = generate_signal(df)
        if signal:
            st.success(f"**{coin} → {signal}**\n\n💰 Entry: {entry}\n🎯 Target: {target}\n🛑 Stop Loss: {stop}")
        else:
            st.warning(f"No clear signal found for {coin} right now.")
