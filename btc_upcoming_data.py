import requests
import pandas as pd
import streamlit as st
from datetime import datetime
import math
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
import os

# Suppress TensorFlow logging messages
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

# ----------------- CONFIG -----------------
WATCHLIST = ["BTC_USDT", "ETH_USDT", "SOL_USDT", "XRP_USDT"]
INTERVALS = ["Min5", "Min15", "Min30", "Min60", "Hour4", "Day1"]
KL_LIMIT = 200
ATR_PERIOD = 14
ATR_MULTIPLIER = 1.5
BACKTEST_SLICES = 5 # Number of recent slices to backtest
# ------------------------------------------

# ----------------- AI CONFIG -----------------
N_TIMESTEPS = 60
EPOCHS = 20
BATCH_SIZE = 32
# ---------------------------------------------

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
                "time", "open", "high", "low", "close", "volume", "amount"
        ])
        for col in ["open", "high", "low", "close"]:
            df[col] = df[col].astype(float)
        return df[["time", "open", "high", "low", "close", "volume"]]
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

def prepare_data_for_lstm(df: pd.DataFrame):
    if df is None or len(df) < N_TIMESTEPS + 1:
        return None, None, None, None
    data = df['close'].values.reshape(-1, 1)
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(data)
    X, y = [], []
    for i in range(N_TIMESTEPS, len(scaled_data)):
        X.append(scaled_data[i-N_TIMESTEPS:i, 0])
        y.append(scaled_data[i, 0])
    X, y = np.array(X), np.array(y)
    X = np.reshape(X, (X.shape[0], X.shape[1], 1))
    return X, y, scaler, data

def create_and_train_lstm_model(X_train, y_train):
    if X_train is None or y_train is None or len(X_train) == 0:
        return None
    model = Sequential()
    model.add(LSTM(units=50, return_sequences=True, input_shape=(X_train.shape[1], 1)))
    model.add(LSTM(units=50, return_sequences=False))
    model.add(Dense(units=25))
    model.add(Dense(units=1))
    model.compile(optimizer='adam', loss='mean_squared_error')
    model.fit(X_train, y_train, epochs=EPOCHS, batch_size=BATCH_SIZE, verbose=0)
    return model

def predict_next_price(model, df, scaler):
    if model is None or df is None or len(df) < N_TIMESTEPS:
        return None
    last_data = df['close'].values[-N_TIMESTEPS:].reshape(-1, 1)
    scaled_last_data = scaler.transform(last_data)
    X_test = np.reshape(scaled_last_data, (1, N_TIMESTEPS, 1))
    prediction_scaled = model.predict(X_test, verbose=0)[0][0]
    prediction_unscaled = scaler.inverse_transform([[prediction_scaled]])[0][0]
    return prediction_unscaled

def generate_signal(symbol: str, df: pd.DataFrame, interval: str, prediction: float):
    last = df.iloc[-1]
    current = float(last["close"])
    atr = compute_atr(df, ATR_PERIOD) or (current * 0.005)

    int_label = interval_to_label(interval)

    if prediction is None:
        return f"ℹ️ {symbol} neutral @ {format_number(current)} ({int_label})\n\n🧠 AI prediction not available."

    if prediction > current:
        entry = current
        tp1 = round(entry + 0.5 * atr, 6)
        tp2 = round(entry + 1.0 * atr, 6)
        tp3 = round(entry + 1.5 * atr, 6)
        stop_loss = round(entry - ATR_MULTIPLIER * atr, 6)

        return (
            f"🚀 **AI LONG SIGNAL** 🚀 | ⏱ {int_label}\n"
            f"💰 Current Price: {format_number(current)}\n"
            f"🧠 Predicted Price: {format_number(prediction)}\n"
            f"🎯 Entry: **{format_number(entry)}**\n"
            f"🎯 TP1: {format_number(tp1)} | TP2: {format_number(tp2)} | TP3: {format_number(tp3)}\n"
            f"🛡️ SL: {format_number(stop_loss)}\n"
            f"📈 Direction: **Go Long**"
        )
    elif prediction < current:
        entry = current
        tp1 = round(entry - 0.5 * atr, 6)
        tp2 = round(entry - 1.0 * atr, 6)
        tp3 = round(entry - 1.5 * atr, 6)
        stop_loss = round(entry + ATR_MULTIPLIER * atr, 6)

        return (
            f"📉 **AI SHORT SIGNAL** 📉 | ⏱ {int_label}\n"
            f"💰 Current Price: {format_number(current)}\n"
            f"🧠 Predicted Price: {format_number(prediction)}\n"
            f"🎯 Entry: **{format_number(entry)}**\n"
            f"🎯 TP1: {format_number(tp1)} | TP2: {format_number(tp2)} | TP3: {format_number(tp3)}\n"
            f"🛡️ SL: {format_number(stop_loss)}\n"
            f"📉 Direction: **Go Short**"
        )
    else:
        return f"ℹ️ {symbol} neutral @ {format_number(current)} ({int_label})\n\n🧠 AI predicts no significant movement."

def backtest_strategy(df: pd.DataFrame, scaler, model):
    if df is None or len(df) < N_TIMESTEPS + BACKTEST_SLICES:
        return None, None, None

    backtest_data = df.iloc[-(N_TIMESTEPS + BACKTEST_SLICES):]
    profit_loss = 0
    trades = 0
    wins = 0

    # Start backtesting from a point in the recent past
    for i in range(BACKTEST_SLICES):
        slice_df = backtest_data.iloc[:N_TIMESTEPS + i]
        current_df = slice_df.copy()

        # Get the AI prediction for the next candle
        prediction = predict_next_price(model, current_df, scaler)

        if prediction is not None:
            current_price = current_df.iloc[-1]["close"]
            actual_next_price = backtest_data.iloc[N_TIMESTEPS + i]["close"]
            
            # Simulate a trade based on the prediction
            if prediction > current_price:
                # Long position: Profit is positive if next price goes up
                pnl = (actual_next_price - current_price) / current_price
            elif prediction < current_price:
                # Short position: Profit is positive if next price goes down
                pnl = (current_price - actual_next_price) / current_price
            else:
                pnl = 0

            profit_loss += pnl
            if pnl > 0:
                wins += 1
            trades += 1

    win_rate = (wins / trades) * 100 if trades > 0 else 0
    total_pnl = profit_loss * 100 # Convert to percentage

    return round(total_pnl, 2), round(win_rate, 2), trades

# ----------------- STREAMLIT APP -----------------
st.set_page_config(page_title="MEXC AI Signal Scanner", layout="wide")

st.title("📊 MEXC Futures Signal Scanner with AI Backtesting")
st.markdown("This app provides **AI-powered trading signals** and **backtests their performance** on recent historical data.")
st.markdown("---")

# User input coin
coin_input = st.text_input("Enter coin (e.g. BTC_USDT) or type ALL:", "ALL").upper()
intervals = st.multiselect("Select intervals", INTERVALS, default=INTERVALS)

if st.button("Run Scanner"):
    if not intervals:
        st.error("Please select at least one interval.")
    else:
        symbols = WATCHLIST if coin_input == "ALL" else [coin_input]
        for sym in symbols:
            st.subheader(f"Signals for {sym}")
            for interval in intervals:
                with st.spinner(f'Fetching and training for {sym} ({interval})...'):
                    df = get_future_klines(sym, interval, KL_LIMIT)
                    if df is None or len(df) < N_TIMESTEPS + BACKTEST_SLICES:
                        st.error(f"Not enough data for {sym} ({interval}) to run AI and backtest.")
                        continue

                    # Prepare data for AI model
                    X, y, scaler, _ = prepare_data_for_lstm(df)
                    if X is None or y is None:
                        st.warning(f"Not enough data to train AI model for {sym} ({interval}). Skipping.")
                        ai_prediction = None
                    else:
                        model = create_and_train_lstm_model(X, y)
                        ai_prediction = predict_next_price(model, df, scaler)

                # Generate and display current signal
                st.markdown(f"### Current AI Signal for {sym} ({interval_to_label(interval)})")
                signal = generate_signal(sym, df, interval, ai_prediction)
                st.markdown(signal)

                # Run and display backtest results
                st.markdown("---")
                st.markdown(f"### Backtest Results for {sym} ({interval_to_label(interval)})")
                with st.spinner("Running backtest..."):
                    backtest_pnl, backtest_winrate, num_trades = backtest_strategy(df, scaler, model)
                    if backtest_pnl is not None:
                        st.metric(label="Total P&L (%)", value=f"{backtest_pnl}%", delta=f"{backtest_pnl}%")
                        st.metric(label="Win Rate (%)", value=f"{backtest_winrate}%")
                        st.markdown(f"Trades simulated: **{num_trades}**")
                    else:
                        st.warning("Backtest could not be performed due to insufficient data.")
                
                st.markdown("---")
