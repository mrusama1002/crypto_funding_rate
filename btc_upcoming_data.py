import streamlit as st
import requests
import time
from datetime import datetime

st.set_page_config(page_title="BSC Whale & Holder Tracker", layout="wide")
st.title("🚨 BSC Small-Cap Whale & Holder Alert")

# ---------------- CONFIG ----------------
BSCSCAN_API_KEY = st.text_input("Enter BscScan API Key:", "C1357E5QDJDCCSPEIKCEQIT1NDNZ7QER2X")
TELEGRAM_BOT_TOKEN = st.text_input("Enter Telegram Bot Token:", "8202693144:AAEJuDm8Ogne42y9cPG8L6ghS4jCb2hiycU")
TELEGRAM_CHAT_ID = st.text_input("Enter Telegram Chat ID:", "1417180893")

WHALE_THRESHOLD_USD = st.number_input("Whale Threshold USD:", value=100000)
HOLDER_GROWTH_ALERT = st.number_input("Holder Growth Alert %:", value=5)
CHECK_INTERVAL = st.number_input("Check Interval (seconds):", value=3600)
NUM_TOP_SMALL_CAP = st.number_input("Number of Small-Cap Coins:", value=10)

# ---------------- HELPERS ----------------
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, data=payload)
    except:
        st.warning("❌ Telegram send failed")

def get_small_cap_coins():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_asc",
        "per_page": 200,
        "page": 1
    }
    response = requests.get(url, params=params).json()
    small_caps = [coin for coin in response if coin['market_cap'] < 100_000_000]
    return small_caps[:NUM_TOP_SMALL_CAP]

def get_token_transfers(token_address):
    url = f"https://api.bscscan.com/api?module=account&action=tokentx&contractaddress={token_address}&page=1&offset=100&sort=desc&apikey={BSCSCAN_API_KEY}"
    response = requests.get(url).json()
    if response['status'] == '1':
        return response['result']
    return []

def usd_value(eth_amount):
    try:
        response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd").json()
        eth_price = response['ethereum']['usd']
        return eth_amount * eth_price
    except:
        return 0

# ---------------- MAIN ----------------
holder_history = {}

if st.button("Check Small-Cap Coins Now"):
    st.write(f"[{datetime.now()}] Checking small-cap coins...")
    coins = get_small_cap_coins()

    for coin in coins:
        symbol = coin['symbol'].upper()
        address = coin.get('platforms', {}).get('ethereum')
        if not address:
            continue  # skip if no Ethereum contract

        transfers = get_token_transfers(address)
        whale_moves = [tx for tx in transfers if usd_value(int(tx['value'])/1e18) > WHALE_THRESHOLD_USD]

        if whale_moves:
            msg = f"🚨 Whale activity detected for {symbol}! {len(whale_moves)} big transfers."
            st.write(msg)
            send_telegram_message(msg)

        current_holders = coin['total_supply']  # approximate holders
        previous_holders = holder_history.get(symbol, current_holders)
        growth = ((current_holders - previous_holders) / previous_holders) * 100 if previous_holders else 0

        if growth >= HOLDER_GROWTH_ALERT:
            msg = f"📈 Holder growth alert for {symbol}: {growth:.2f}% increase!"
            st.write(msg)
            send_telegram_message(msg)

        holder_history[symbol] = current_holders

    st.write(f"[{datetime.now()}] All tokens checked.")
