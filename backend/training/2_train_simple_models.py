# finstock-ai/backend/training/2_train_simple_models.py
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression # For long-term trend
import joblib # For saving the simple "models"
import os
import glob # To find all the CSV files
import traceback # For detailed error logging

print("🚀 Starting Simple Model Training Script...")

# --- Parameters ---
DATA_DIR = "../data/daily/"       # Where the CSVs are stored
MODEL_DIR = "../model_store/"     # Where to save the .pkl files
LONG_TERM_YEARS = 5              # Number of years for long-term trend calculation
SHORT_TERM_DAYS = 30             # Number of days for short-term momentum

print(f"💾 Loading data from: {DATA_DIR}")
print(f"💾 Saving models to: {MODEL_DIR}")
print(f"📈 Long-term trend: Last {LONG_TERM_YEARS} years")
print(f"📈 Short-term momentum: Last {SHORT_TERM_DAYS} days")

# --- Ensure Model Directory Exists ---
os.makedirs(MODEL_DIR, exist_ok=True)
print("Model directory checked/created.")

# --- Define Simple "Model" Functions ---

def train_long_term_model(df: pd.DataFrame, years: int) -> float:
    """
    Calculates the slope of the closing price over the last N years using linear regression.
    Returns the annualized slope (approximate yearly growth trend).
    """
    try:
        # Filter data for the last N years
        end_date = df.index.max()
        start_date = end_date - pd.DateOffset(years=years)
        df_filtered = df[df.index >= start_date].copy()

        if len(df_filtered) < 2: # Need at least two points for regression
            print(f"   ⚠️ Not enough data for {years}-year trend.")
            return 0.0

        # Prepare data for Linear Regression
        # We use days since the start as the independent variable (X)
        df_filtered['days'] = (df_filtered.index - df_filtered.index.min()).days
        X = df_filtered[['days']]
        y = df_filtered['Close']

        # Fit the model
        model = LinearRegression()
        model.fit(X, y)

        # Slope represents price change per day
        daily_slope = model.coef_[0]

        # Annualize the slope (approximate)
        annualized_slope = daily_slope * 252 # Assuming ~252 trading days/year
        return annualized_slope
    except Exception as e:
        print(f"   ❌ Error calculating long-term trend:")
        traceback.print_exc() # Print full traceback
        return 0.0


def train_short_term_model(df: pd.DataFrame, days: int) -> float:
    """
    Calculates the percentage change over the last N days.
    Returns the percentage change.
    """
    try:
        if len(df) < days:
            print(f"   ⚠️ Not enough data for {days}-day momentum.")
            return 0.0

        # Get the closing price N days ago and the latest price
        price_n_days_ago = df['Close'].iloc[-days]
        latest_price = df['Close'].iloc[-1]

        if price_n_days_ago == 0: # Avoid division by zero
            return 0.0

        # Calculate percentage change
        momentum_pct = ((latest_price - price_n_days_ago) / price_n_days_ago) * 100
        return momentum_pct
    except Exception as e:
        print(f"   ❌ Error calculating short-term momentum:")
        traceback.print_exc() # Print full traceback
        return 0.0

# --- Find CSV Files ---
csv_files = glob.glob(os.path.join(DATA_DIR, "*_daily.csv"))
print(f"\nFound {len(csv_files)} CSV files to process.")

# --- Loop Through Files, Train, and Save ---
failed_models = []
for file_path in csv_files:
    symbol = os.path.basename(file_path).replace("_daily.csv", "")
    print(f"\nProcessing {symbol}...")

    try:
        # Load data without automatic date parsing initially
        df = pd.read_csv(file_path, index_col=0)
        print(f"   Columns loaded: {df.columns.tolist()}")

        # --- REVISED INDEX CLEANING ---
        # Reset the index to become a column (likely named 'Date' or similar from CSV)
        index_col_name = df.index.name if df.index.name is not None else 'Date' # Guess original index name
        if index_col_name in df.columns: # Avoid conflict if 'Date' already a column
             index_col_name = f"{index_col_name}_Index"
        df.reset_index(names=[index_col_name], inplace=True)

        # Convert that column to datetime
        try:
             df[index_col_name] = pd.to_datetime(df[index_col_name], format='%Y-%m-%d', errors='coerce')
        except ValueError:
             print(f"   ⚠️ Could not parse '{index_col_name}' with specific format, falling back.")
             df[index_col_name] = pd.to_datetime(df[index_col_name], errors='coerce')

        # Drop rows where the date conversion failed (NaT)
        df.dropna(subset=[index_col_name], inplace=True)

        # Set the cleaned date column back as the index
        df.set_index(index_col_name, inplace=True)
        # --------------------------------

        # Check if index is now correctly DatetimeIndex
        if not isinstance(df.index, pd.DatetimeIndex):
             print(f"   ❌ Error: Index could not be converted to DatetimeIndex for {symbol}.")
             failed_models.append(symbol)
             continue

        # --- Column cleaning remains the same ---
        if 'Close' not in df.columns:
            print(f"   ❌ Error: 'Close' column not found in {symbol}. Available columns: {df.columns.tolist()}")
            failed_models.append(symbol)
            continue

        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
        df.dropna(axis=0, subset=['Close'], inplace=True)

        if df.empty:
             print(f"   ⚠️ Empty data for {symbol} after cleaning. Skipping.")
             failed_models.append(symbol)
             continue

        # "Train" simple models
        long_term_slope = train_long_term_model(df, LONG_TERM_YEARS)
        short_term_momentum = train_short_term_model(df, SHORT_TERM_DAYS)

        # Save the results
        long_term_model_path = os.path.join(MODEL_DIR, f"{symbol}_long_term.pkl")
        short_term_model_path = os.path.join(MODEL_DIR, f"{symbol}_short_term.pkl")

        # We save the calculated value directly as our "model" artifact
        joblib.dump(long_term_slope, long_term_model_path)
        joblib.dump(short_term_momentum, short_term_model_path)

        print(f"   📈 Long-term (annualized slope): {long_term_slope:.2f}")
        print(f"   📈 Short-term ({SHORT_TERM_DAYS}-day % change): {short_term_momentum:.2f}%")
        print(f"   ✅ Saved simple models for {symbol}.")

    except Exception as e:
        print(f"   ❌ Failed processing {symbol}:") # General catch-all
        traceback.print_exc() # Print full traceback here too
        failed_models.append(symbol)

# --- Summary ---
print("\n--- Simple Model Training Complete ---")
if failed_models:
    print(f"⚠️ Failed to process models for: {', '.join(failed_models)}")
else:
    print("✅ Successfully processed and saved simple models for all symbols.")
print("------------------------------------")