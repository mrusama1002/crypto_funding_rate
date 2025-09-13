import streamlit as st
from binance.client import Client
import time

st.set_page_config(page_title="Crypto Live Tracker", layout="wide")
st.title("📊 Live Crypto Tracker (Binance Futures + MEXC Funding Rate)")

# ---------- API Input ----------
BINANCE_API_KEY = st.text_input("Enter Binance API Key:")
BINANCE_API_SECRET = st.text_input("Enter Binance API Secret:", type="password")

symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
symbol = st.selectbox("Select Symbol:", symbols)

# ---------- Binance Client ----------
client = None
if BINANCE_API_KEY and BINANCE_API_SECRET:
    try:
        client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)
    except Exception as e:
        st.error(f"❌ Binance client init error: {e}")

# ---------- MEXC Funding Rate ----------
def get_funding_rate(symbol):
    url = f"https://contract.mexc.com/api/v1/contract/funding_rate/{symbol.replace('USDT','_USDT')}"
    try:
        r = requests.get(url, timeout=10).json()
        return float(r["data"]["fundingRate"])
    except:
        return None

# ---------- Fetch Binance Data ----------
def get_binance_data(symbol):
    try:
        # Current price
        ticker = client.futures_symbol_ticker(symbol=symbol)
        price_now = float(ticker['price'])
        # Klines 1h interval
        klines = client.futures_klines(symbol=symbol, interval='1h', limit=2)
        price_1h = float(klines[-2][4])
        volume = float(klines[-1][5])
        return price_now, price_1h, volume
    except Exception as e:
        st.error(f"❌ Binance fetch error: {e}")
        return None, None, None

# ---------- Fetch and Display ----------
if client and symbol:
    price_now, price_1h, volume = get_binance_data(symbol)
    funding_rate = get_funding_rate(symbol)

    if price_now and price_1h and funding_rate is not None:
        price_change = ((price_now-price_1h)/price_1h)*100

        st.write(f"💰 Current Price (Binance): {price_now}")
        st.write(f"⏳ 1 Hour Before Price (Binance): {price_1h}")
        st.write(f"📉 Price Change (1h): {price_change:.2f}%")
        st.write(f"📊 24h Volume (Binance): {volume}")
        st.write(f"🏦 Funding Rate (MEXC): {funding_rate:.6f}")

        # Simple Signal
        if funding_rate>0.001 and price_change>1:
            signal = "🚀 Bullish"
        elif funding_rate<-0.001 and price_change<-1:
            signal = "🐻 Bearish"
        else:
            signal = "😐 Neutral"

        st.write(f"📌 Signal: {signal}")

    else:
        st.error("❌ Could not fetch full data. Check API keys or symbol.")
