# finstock-ai/backend/training/1_collect_data.py
import yfinance as yf
import pandas as pd
import os
from datetime import datetime

print("🚀 Starting Data Collection Script...")

# --- Parameters ---
STOCK_SYMBOLS = [
    'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS',
    'HINDUNILVR.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'ITC.NS', 'LTIM.NS',
    'WIPRO.NS', 'ASIANPAINT.NS', 'MARUTI.NS', 'LT.NS', 'AXISBANK.NS'
]
START_DATE = "2010-01-01"
END_DATE = datetime.now().strftime('%Y-%m-%d')
DATA_DIR = "../data/daily/" # Relative path from training/ to data/daily/

print(f"📈 Stocks: {', '.join(STOCK_SYMBOLS)}")
print(f"📅 Period: {START_DATE} to {END_DATE}")
print(f"💾 Saving to: {DATA_DIR}")

# --- Ensure Data Directory Exists ---
os.makedirs(DATA_DIR, exist_ok=True)
print("Data directory checked/created.")

# --- Fetch and Save Data ---
failed_symbols = []
for symbol in STOCK_SYMBOLS:
    try:
        print(f"   Fetching daily data for {symbol}...")
        # Download daily historical data using yfinance
        hist_daily = yf.download(
            tickers=symbol,
            start=START_DATE,
            end=END_DATE,
            interval="1d",
            progress=False # Keep console clean
        )

        if not hist_daily.empty:
            # Clean column names (remove spaces if any, though yfinance usually doesn't have them)
            #hist_daily.columns = hist_daily.columns.str.replace(' ', '_')
            # Ensure index is DatetimeIndex
            hist_daily.index = pd.to_datetime(hist_daily.index)

            # Save to CSV
            file_path = os.path.join(DATA_DIR, f"{symbol}_daily.csv")
            hist_daily.to_csv(file_path)
            print(f"   ✅ Saved {symbol} to {os.path.basename(file_path)}")
        else:
            print(f"   ⚠️ No daily data found for {symbol}")
            failed_symbols.append(symbol)

    except Exception as e:
        print(f"   ❌ Error fetching daily data for {symbol}: {e}")
        failed_symbols.append(symbol)

# --- Summary ---
print("\n--- Data Collection Complete ---")
if failed_symbols:
    print(f"⚠️ Failed to fetch data for: {', '.join(failed_symbols)}")
else:
    print("✅ Successfully fetched and saved data for all symbols.")
print("------------------------------")