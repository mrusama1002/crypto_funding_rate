import streamlit as st
import requests
from datetime import datetime

st.set_page_config(page_title="Crypto Tracker Dashboard", layout="wide")
st.title("📊 Top Coins Whale & Holder Tracker (BSC & Ethereum)")

# ---------------- CONFIG ----------------
BSCSCAN_API_KEY = "C1357E5QDJDCCSPEIKCEQIT1NDNZ7QER2X"  # Hardcoded API key
TOP_COINS = st.number_input("Number of Top Coins to Track:", value=50)
WHALE_THRESHOLD_USD = st.number_input("Whale Threshold USD:", value=100000)
HOLDER_GROWTH_ALERT = st.number_input("Holder Growth Alert %:", value=5)

# ---------------- HELPERS ----------------
def get_top_coins(n=50):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": n,
        "page": 1
    }
    try:
        response = requests.get(url, params=params).json()
        return response
    except:
        return []

def get_token_transfers(token_address):
    if not token_address:
        return []
    url = f"https://api.bscscan.com/api?module=account&action=tokentx&contractaddress={token_address}&page=1&offset=100&sort=desc&apikey={BSCSCAN_API_KEY}"
    try:
        r = requests.get(url).json()
        if r.get('status') == '1':
            return r['result']
        return []
    except:
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

if st.button("Check Top Coins Now"):
    st.write(f"[{datetime.now()}] Checking top {TOP_COINS} coins...")
    coins = get_top_coins(TOP_COINS)
    results = []

    for coin in coins:
        symbol = coin['symbol'].upper()
        address = coin.get('platforms', {}).get('ethereum')

        transfers = get_token_transfers(address) if address else []
        whale_moves = [tx for tx in transfers if usd_value(int(tx['value'])/1e18) > WHALE_THRESHOLD_USD]
        whale_msg = f"{len(whale_moves)} whale moves" if whale_moves else "No whale moves"

        current_holders = coin['total_supply'] or 0
        previous_holders = holder_history.get(symbol, current_holders)
        growth = ((current_holders - previous_holders) / previous_holders) * 100 if previous_holders else 0
        holder_msg = f"Holder growth: {growth:.2f}%" if growth >= HOLDER_GROWTH_ALERT else "No significant growth"

        holder_history[symbol] = current_holders

        results.append({
            "Symbol": symbol,
            "Current Price": coin['current_price'],
            "Market Cap": coin['market_cap'],
            "Whale Moves": whale_msg,
            "Holder Growth": holder_msg
        })

    st.write(f"[{datetime.now()}] Completed check.")
    st.table(results)
