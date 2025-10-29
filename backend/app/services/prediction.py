# finstock-ai/backend/app/services/prediction.py
import pandas as pd
import random
import joblib # To load our saved .pkl files
import os

# --- Parameters ---
MODEL_DIR = "app/model_store/" # Path from the app/ directory

# --- Helper to Load Models ---
def load_simple_model(symbol: str, model_type: str) -> float:
    """
    Loads the saved value from a .pkl file for a given symbol and model type.
    Returns the loaded value, or 0.0 if the file is not found or fails to load.
    """
    file_path = os.path.join(MODEL_DIR, f"{symbol}_{model_type}.pkl")
    if not os.path.exists(file_path):
        print(f"   ⚠️ Model file not found: {file_path}. Returning 0.0")
        return 0.0
    try:
        value = joblib.load(file_path)
        return float(value) # Ensure it's a float
    except Exception as e:
        print(f"   ❌ Error loading model file {file_path}: {e}")
        return 0.0

# --- Prediction Functions ---

def get_long_term_prediction(hist_data: pd.DataFrame, symbol: str):
    """
    Uses the pre-calculated annualized slope (from .pkl) for long-term prediction.
    """
    # Load the pre-calculated slope
    annualized_slope = load_simple_model(symbol, "long_term")

    # Simple logic based on slope:
    current_price = hist_data['Close'].iloc[-1]
    # Estimate 1-year target based on current price + annualized slope
    predicted_target_1y = current_price + annualized_slope

    if annualized_slope > (current_price * 0.05): # If yearly trend > 5% of current price
        recommendation = "Strong Buy Trend"
        confidence = 0.75
    elif annualized_slope > 0:
        recommendation = "Positive Trend"
        confidence = 0.65
    elif annualized_slope < -(current_price * 0.05):
         recommendation = "Strong Sell Trend"
         confidence = 0.75
    elif annualized_slope < 0:
        recommendation = "Negative Trend"
        confidence = 0.65
    else:
        recommendation = "Neutral Trend"
        confidence = 0.50

    return {
        "forecast_1y": round(predicted_target_1y, 2), # Changed from dummy random value
        "recommendation": recommendation,
        "confidence": confidence # Made slightly less random
    }

def get_short_term_prediction(hist_data: pd.DataFrame, symbol: str):
    """
    Uses the pre-calculated 30-day momentum (from .pkl) for short-term prediction.
    """
    # Load the pre-calculated momentum
    momentum_pct = load_simple_model(symbol, "short_term")

    # Simple logic based on momentum:
    if momentum_pct > 3.0: # If price increased > 3% in last 30 days
        recommendation = "Buy (Momentum)"
        confidence = 0.80
    elif momentum_pct > 0.5:
         recommendation = "Hold/Weak Buy"
         confidence = 0.60
    elif momentum_pct < -3.0:
        recommendation = "Sell (Momentum)"
        confidence = 0.80
    elif momentum_pct < -0.5:
        recommendation = "Hold/Weak Sell"
        confidence = 0.60
    else:
        recommendation = "Hold (Neutral)"
        confidence = 0.50

    return {
        "forecast_7d_percent": round(momentum_pct / 4, 2), # Rough guess for 7d based on 30d
        "recommendation": recommendation,
        "confidence": confidence
    }

def get_intraday_prediction(symbol: str):
    """
    Placeholder for the Intraday Similarity Engine.
    Keeps returning dummy data for now.
    """
    similar_pattern = f"Historical Pattern ({random.choice(['June', 'July', 'Aug'])} {random.randint(2023, 2024)})"
    outcome_prob = random.uniform(0.60, 0.85)
    prediction_text = f"Likely {random.uniform(0.1, 0.6):.1f}% {'rise' if random.random() > 0.4 else 'drop'} in next {random.choice([15, 30])} mins"

    return {
        "last_updated": datetime.now().strftime("%H:%M:%S"), # Use current time
        "similar_pattern_found": similar_pattern,
        "prediction": prediction_text,
        "probability": round(outcome_prob, 2)
    }

# Need datetime for the intraday placeholder
from datetime import datetime