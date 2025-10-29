# finstock-ai/backend/app/services/analysis.py
import yfinance as yf
import pandas as pd
import numpy as np # For isnan, isfinite
from fastapi import HTTPException
import traceback # Ensure traceback is imported

def get_stock_data(symbol: str, period: str = "5y"):
    """
    Fetches historical stock data from yfinance.
    """
    try:
        ticker = yf.Ticker(symbol)
        # Download historical data with daily interval
        hist = ticker.history(period=period, interval="1d")

        if hist.empty:
            raise HTTPException(status_code=404, detail=f"No data found for symbol {symbol}")

        # Try using fast_info first, fallback to .info
        try:
            # fast_info might be slightly different structure, convert to dict
            info = ticker.fast_info.to_dict()
            if 'symbol' not in info: info['symbol'] = symbol # Ensure symbol is present
        except Exception:
             print(f"Warning: fast_info failed for {symbol}, falling back to .info (slower)")
             # .info is already a dictionary
             info = ticker.info
             if not info: # Check if .info also failed
                  print(f"Warning: Could not retrieve info dict for {symbol}")
                  info = {'symbol': symbol} # Basic fallback if both fail

        return hist, info

    except Exception as e:
        # Catch-all for yfinance or other errors
        print(f"Detailed yfinance error for {symbol}: {traceback.format_exc()}")
        raise HTTPException(status_code=404, detail=f"Error fetching data from yfinance for {symbol}: {str(e)}")


def calculate_advanced_probabilities(daily_returns: pd.Series):
    """Calculates conditional probabilities and streak probabilities."""
    # Ensure returns series is not empty and has enough data
    if daily_returns.empty or len(daily_returns) < 2:
        return {
            "prob_down_day": None,
            "cond_prob_up_given_up": None,
            "cond_prob_down_given_down": None,
            "prob_2_days_up_streak": None,
            "prob_2_days_down_streak": None
        }

    # Shift returns to compare today vs yesterday
    returns_shifted = daily_returns.shift(1)

    # Create boolean series for up/down days
    is_up = daily_returns > 0
    was_up = returns_shifted > 0
    is_down = daily_returns < 0
    was_down = returns_shifted < 0

    # Total valid days (where both today's and yesterday's returns are valid and non-zero)
    # Check pd.notna to handle potential NaNs from pct_change or shift
    valid_comparison = pd.notna(daily_returns) & pd.notna(returns_shifted)
    total_valid_comparison_days = valid_comparison.sum()

    if total_valid_comparison_days == 0: # Avoid division by zero if no valid comparison days
        # Calculate prob_down_day based on all available days
        prob_down = (is_down.sum() / len(daily_returns)) * 100 if len(daily_returns) > 0 else 0
        return {
            "prob_down_day": prob_down,
            "cond_prob_up_given_up": None,
            "cond_prob_down_given_down": None,
            "prob_2_days_up_streak": None,
            "prob_2_days_down_streak": None
        }

    # Conditional Probabilities
    up_given_up = (is_up & was_up & valid_comparison).sum()
    down_given_down = (is_down & was_down & valid_comparison).sum()
    total_was_up = (was_up & valid_comparison).sum()
    total_was_down = (was_down & valid_comparison).sum()

    cond_prob_up_given_up = (up_given_up / total_was_up) * 100 if total_was_up > 0 else 0
    cond_prob_down_given_down = (down_given_down / total_was_down) * 100 if total_was_down > 0 else 0

    # Streak Probabilities (2 consecutive days using mean on valid comparisons)
    prob_2_days_up = ((is_up & was_up)[valid_comparison]).mean() * 100 if total_valid_comparison_days > 0 else 0
    prob_2_days_down = ((is_down & was_down)[valid_comparison]).mean() * 100 if total_valid_comparison_days > 0 else 0

    # Calculate prob_down_day based on all available days
    prob_down_overall = (is_down.sum() / len(daily_returns)) * 100 if len(daily_returns) > 0 else 0

    return {
        "prob_down_day": prob_down_overall,
        "cond_prob_up_given_up": cond_prob_up_given_up,
        "cond_prob_down_given_down": cond_prob_down_given_down,
        "prob_2_days_up_streak": prob_2_days_up,
        "prob_2_days_down_streak": prob_2_days_down
    }


def calculate_statistics(hist_data: pd.DataFrame):
    """
    Calculates statistical parameters, return distribution, probabilities,
    and returns the raw daily returns list.
    """
    if hist_data.empty or 'Close' not in hist_data.columns:
        raise HTTPException(status_code=500, detail="Invalid historical data for statistics")

    # --- Data Cleaning ---
    if not isinstance(hist_data.index, pd.DatetimeIndex):
         try:
             hist_data.index = pd.to_datetime(hist_data.index, errors='coerce')
             hist_data.dropna(axis=0, subset=[hist_data.index.name], inplace=True)
             if not isinstance(hist_data.index, pd.DatetimeIndex):
                  raise ValueError("Index conversion to DatetimeIndex failed")
         except Exception as e:
              raise HTTPException(status_code=500, detail=f"Could not process date index for stats: {e}")

    hist_data['Close'] = pd.to_numeric(hist_data['Close'], errors='coerce')
    hist_data.dropna(axis=0, subset=['Close'], inplace=True)
    if hist_data.empty:
         raise HTTPException(status_code=500, detail="No valid 'Close' data after cleaning")

    # --- Basic Stats ---
    start_date = hist_data.index.min().strftime('%Y-%m-%d')
    end_date = hist_data.index.max().strftime('%Y-%m-%d')
    desc = hist_data['Close'].describe()
    median = hist_data['Close'].median()
    mode_series = hist_data['Close'].mode()
    mode = mode_series.iloc[0] if not mode_series.empty else None
    variance = hist_data['Close'].var()
    skewness = hist_data['Close'].skew()
    kurtosis = hist_data['Close'].kurt()
    mean_val = desc.get('mean', 0)
    std_val = desc.get('std', 0)
    min_val = desc.get('min', 0)
    max_val = desc.get('max', 0)
    pct_25 = desc.get('25%', 0)
    pct_75 = desc.get('75%', 0)
    range_val = max_val - min_val
    iqr = pct_75 - pct_25
    coeff_var = (std_val / mean_val) * 100 if mean_val else 0

    # --- Return Distribution & Probabilities ---
    daily_returns = hist_data['Close'].pct_change().dropna() # Get daily returns, drop first NaN
    prob_rise = (daily_returns > 0).mean() * 100 if not daily_returns.empty else 0

    # Calculate advanced probabilities using the dedicated function
    adv_probs = calculate_advanced_probabilities(daily_returns)

    # Return distribution stats
    mean_daily_return = daily_returns.mean() * 100 if not daily_returns.empty else 0 # As percentage
    std_daily_return = daily_returns.std() * 100 if not daily_returns.empty else 0   # As percentage (volatility)

    stats = {
        "start_date": start_date,
        "end_date": end_date,
        "mean": mean_val,
        "median": median,
        "mode": mode,
        "std_deviation": std_val,
        "variance": variance,
        "skewness": skewness,
        "kurtosis": kurtosis,
        "range": range_val,
        "iqr": iqr,
        "min": min_val,
        "max": max_val,
        "25_percentile": pct_25,
        "50_percentile": desc.get('50%', None), # Median is already calculated
        "75_percentile": pct_75,
        "coeff_of_variation": coeff_var,
        "probability_next_day_up": prob_rise,
        # Get values from adv_probs dictionary
        "probability_next_day_down": adv_probs.get("prob_down_day"),
        "mean_daily_return_percent": mean_daily_return,
        "std_dev_daily_return_percent": std_daily_return,
        "cond_prob_up_given_up": adv_probs.get("cond_prob_up_given_up"),
        "cond_prob_down_given_down": adv_probs.get("cond_prob_down_given_down"),
        "prob_2_days_up_streak": adv_probs.get("prob_2_days_up_streak"),
        "prob_2_days_down_streak": adv_probs.get("prob_2_days_down_streak")
    }

    # Clean potential NaN/Infinity from calculated stats
    cleaned_stats = {}
    for k, v in stats.items():
        if isinstance(v, (int, float)):
            # Ensure value is not NaN and is finite
            cleaned_stats[k] = v if pd.notna(v) and np.isfinite(v) else None
        else:
            cleaned_stats[k] = v # Keep non-numeric values (like dates, mode if string) as is

    # --- Prepare daily returns data for histogram ---
    # Convert series to list, handle NaN/inf, multiply by 100 for percentage
    daily_returns_list = [
        round(r * 100, 4) for r in daily_returns.tolist()
        if pd.notna(r) and np.isfinite(r) # Ensure valid numbers
    ]

    # Return both cleaned stats and the list of daily returns
    return cleaned_stats, daily_returns_list