import streamlit as st
import requests
import pandas as pd
import ta

# ============ SETTINGS ============
INTERVAL = "1h"
ATR_MULTIPLIER = 1.5

# ---------- BINANCE API ----------
def fetch_ohlcv(symbol, interval=INTERVAL, limit=200):
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200:
            st.error(f"Binance error: {res.text}")
            return None
        data = res.json()
        if not isinstance(data, list) or len(data) == 0:
            return None
        df = pd.DataFrame(data, columns=[
            "timestamp","open","high","low","close","volume",
            "close_time","quote_asset_volume","num_trades",
            "taker_buy_base","taker_buy_quote","ignore"
        ])
        df["open"] = df["open"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["close"] = df["close"].astype(float)
        df["volume"] = df["volume"].astype(float)
        return df[["timestamp","open","high","low","close","volume"]]
    except Exception as e:
        st.error(f"❌ Binance OHLCV fetch error for {symbol}: {e}")
        return None

# ---------- AMD Signal ----------
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

    # Long Condition
    if last_close > last_ema20 and last_ema20 > last_ema50 and last_macd > last_macd_signal and 40 <= last_rsi <= 60:
        signal = "✅ Long"
        target = entry + ATR_MULTIPLIER*atr
        stop_loss = entry - ATR_MULTIPLIER*atr
    # Short Condition
    elif last_close < last_ema50 and last_macd < last_macd_signal and last_rsi > 70:
        signal = "❌ Short"
        target = entry - ATR_MULTIPLIER*atr
        stop_loss = entry + ATR_MULTIPLIER*atr

    if signal is None:
        return None, None, None, None

    return signal, round(entry,4), round(target,4), round(stop_loss,4)

# ---------- STREAMLIT UI ----------
st.set_page_config(page_title="AMD Crypto Signal Scanner", layout="centered")

st.title("📊 AMD Setup Signal Scanner")
st.write("Check **Binance Perpetual Futures** coins for Long/Short signals")

coin = st.text_input("Enter Symbol (e.g. BTCUSDT, ETHUSDT, DOGEUSDT)", "BTCUSDT").upper()

if st.button("🔍 Get Signal"):
    df = fetch_ohlcv(coin)
    if df is not None:
        signal, entry, target, stop = generate_signal(df)
        if signal:
            st.success(f"**{coin} Signal:** {signal}")
            st.write(f"💰 Entry: `{entry}`")
            st.write(f"🎯 Target: `{target}`")
            st.write(f"🛑 Stop Loss: `{stop}`")
        else:
            st.warning(f"No clear signal found for {coin} right now.")
    else:
        st.error("❌ No data fetched. Maybe wrong symbol or Binance restriction.")
