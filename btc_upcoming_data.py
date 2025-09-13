import streamlit as st
import requests
from datetime import datetime

st.set_page_config(page_title="BSC Small-Cap Tracker", layout="wide")
st.title("📊 BSC Small-Cap Whale & Holder Tracker (Dashboard Only)")

# ---------------- CONFIG ----------------
BSCSCAN_API_KEY = st.text_input("Enter BscScan API Key:", "C1357E5QDJDCCSPEIKCEQIT1NDNZ7QER2X")
WHALE_THRESHOLD_USD = st.number_input("Whale Threshold USD:", value=100000)
HOLDER_GROWTH_ALERT = st.number_input("Holder Growth Alert %:", value=5)
NUM_TOP_SMALL_CAP = st.number_input("Number of Small-Cap Coins:", value=10)

# ---------------- HELPERS ----------------
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

    results = []

    for coin in coins:
        symbol = coin['symbol'].upper()
        address = coin.get('platforms', {}).get('ethereum')
        if not address:
            continue  # skip if no Ethereum contract

        transfers = get_token_transfers(address)
        whale_moves = [tx for tx in transfers if usd_value(int(tx['value'])/1e18) > WHALE_THRESHOLD_USD]

        whale_msg = f"{len(whale_moves)} whale moves" if whale_moves else "No whale moves"

        current_holders = coin['total_supply']  # approximate holders
        previous_holders = holder_history.get(symbol, current_holders)
        growth = ((current_holders - previous_holders) / previous_holders) * 100 if previous_holders else 0
        holder_msg = f"Holder growth: {growth:.2f}%" if growth >= HOLDER_GROWTH_ALERT else "No significant growth"

        holder_history[symbol] = current_holders

        results.append({
            "Symbol": symbol,
            "Whale Moves": whale_msg,
            "Holder Growth": holder_msg,
            "Market Cap": coin['market_cap'],
            "Current Price": coin['current_price']
        })

    # Show results as table
    st.write(f"[{datetime.now()}] All tokens checked.")
    st.table(results)
