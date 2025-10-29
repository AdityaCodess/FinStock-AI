# finstock-ai/backend/app/api/endpoints.py
import sqlite3
import traceback # For detailed error logging in /analyze
import os       # For robust database path
import pandas as pd # For pd.notna check
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import numpy as np

# Import services
from app.services import analysis
from app.services import prediction
from app.services import news

# --- Pydantic Models ---

class StockSearchResponse(BaseModel):
    symbol: str
    name: str

class StockInfo(BaseModel):
    symbol: str
    shortName: Optional[str] = None
    longName: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    marketCap: Optional[float] = None
    currentPrice: Optional[float] = None # No alias, handle in endpoint
    dayHigh: Optional[float] = None
    dayLow: Optional[float] = None
    previousClose: Optional[float] = None

class Statistics(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    mean: Optional[float] = None
    median: Optional[float] = None
    mode: Optional[float] = None # Mode can sometimes be non-numeric if multiple modes
    std_deviation: Optional[float] = None
    variance: Optional[float] = None
    skewness: Optional[float] = None
    kurtosis: Optional[float] = None
    range: Optional[float] = None
    iqr: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    percentile_25: Optional[float] = Field(None, alias="25_percentile")
    percentile_50: Optional[float] = Field(None, alias="50_percentile")
    percentile_75: Optional[float] = Field(None, alias="75_percentile")
    coeff_of_variation: Optional[float] = None
    probability_next_day_up: Optional[float] = None
    # --- NEW FIELDS ---
    probability_next_day_down: Optional[float] = None
    mean_daily_return_percent: Optional[float] = None
    std_dev_daily_return_percent: Optional[float] = None # Volatility
    cond_prob_up_given_up: Optional[float] = None
    cond_prob_down_given_down: Optional[float] = None
    prob_2_days_up_streak: Optional[float] = None
    prob_2_days_down_streak: Optional[float] = None

class LongTermPrediction(BaseModel):
    forecast_1y: Optional[float] = None # Make optional in case calculation fails
    recommendation: str
    confidence: Optional[float] = None

class ShortTermPrediction(BaseModel):
    forecast_7d_percent: Optional[float] = None # Make optional
    recommendation: str
    confidence: Optional[float] = None

class IntradayPrediction(BaseModel):
    last_updated: str
    similar_pattern_found: str
    prediction: str
    probability: Optional[float] = None

class AIPredictions(BaseModel):
    long_term: LongTermPrediction
    short_term: ShortTermPrediction
    intraday: IntradayPrediction

class NewsArticle(BaseModel):
    source: str
    headline: str
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None

class StockNewsSentiment(BaseModel):
    articles: List[NewsArticle]
    overall_sentiment: str

class GlobalMarketSentiment(BaseModel):
    overall_market_sentiment: str
    trending_topic: str
    key_headlines: List[str]

class NewsSentiment(BaseModel):
    stock_news: StockNewsSentiment
    global_market: GlobalMarketSentiment

class HistoricalDataPoint(BaseModel):
    date: str
    close: float

class AnalysisResponse(BaseModel):
    stock_info: StockInfo
    statistics: Statistics
    ai_predictions: AIPredictions
    news_sentiment: NewsSentiment
    historical_data: List[HistoricalDataPoint]
    daily_returns_histogram: List[float] # List of daily return percentages

# --- Router Setup ---
router = APIRouter(
    prefix="/api",
    tags=["API"]
)

# --- Database Connection ---
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE_PATH = os.path.join(base_dir, "data", "stocks.db")

def get_db_connection():
    try:
        conn = sqlite3.connect(DB_FILE_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error path used: {DB_FILE_PATH}")
        raise HTTPException(status_code=500, detail=f"Database connection error: {e}")

# --- API Endpoints ---

@router.get(
    "/search",
    response_model=List[StockSearchResponse]
)
async def search_stocks(
    q: Optional[str] = Query(None, min_length=2, description="Search query")
):
    """Search for stocks by symbol or name."""
    if q is None: return []
    search_query = f"%{q}%"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT symbol, name FROM stocks WHERE symbol LIKE ? OR name LIKE ? LIMIT 10",
            (search_query, search_query)
        )
        stocks = cursor.fetchall()
        return [dict(row) for row in stocks]
    except Exception as e:
        print(f"Error during search: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"An error occurred during search: {str(e)}")
    finally:
        if conn: conn.close()


@router.get(
    "/analyze",
    response_model=AnalysisResponse
)
async def analyze_stock(
    symbol: str = Query(..., description="Stock symbol (e.g., RELIANCE.NS)")
):
    """
    Get full analysis including historical data and daily returns for charts.
    """
    try:
        # 1. Fetch Data
        hist_data, info_data = analysis.get_stock_data(symbol, period="5y")
        if not isinstance(info_data, dict):
             print(f"Warning: info_data for {symbol} is not a dict: {info_data}")
             info_data = {'symbol': symbol}

        # 2. Calculate Statistics AND get daily returns list
        stats_dict, daily_returns_list = analysis.calculate_statistics(hist_data.copy())

        # 3. Get AI Predictions
        long_term_pred_dict = prediction.get_long_term_prediction(hist_data.copy(), symbol)
        short_term_pred_dict = prediction.get_short_term_prediction(hist_data.copy(), symbol)
        intraday_pred_dict = prediction.get_intraday_prediction(symbol) # Dummy

        # 4. Get News & Sentiment
        company_name = info_data.get('shortName', info_data.get('longName', symbol))
        stock_news_dict = news.get_news_and_sentiment(symbol, company_name)
        global_market_dict = news.get_global_market_sentiment()

        # 5. Format Historical Data for Charting
        hist_data_chart = hist_data[['Close']].copy()
        hist_data_chart.dropna(inplace=True)
        historical_data_list = [] # Default empty list
        if isinstance(hist_data_chart.index, pd.DatetimeIndex):
             hist_data_chart.index = hist_data_chart.index.strftime('%Y-%m-%d')
             hist_data_chart.reset_index(inplace=True)
             index_col_name = hist_data_chart.columns[0]
             hist_data_chart.rename(columns={index_col_name: 'date', 'Close': 'close'}, inplace=True)
             historical_data_list = hist_data_chart.to_dict(orient='records')

        # 6. Format Full Response

        # Define keys to check for current price
        price_keys = ['currentPrice', 'regularMarketPrice', 'lastPrice', 'ask', 'bid']
        current_price_value = None
        for key in price_keys:
            price_val = info_data.get(key)
            if price_val is not None and isinstance(price_val, (int, float)) and pd.notna(price_val) and np.isfinite(price_val):
                current_price_value = float(price_val)
                break

        stock_info = StockInfo(
            symbol=info_data.get('symbol', symbol),
            shortName=info_data.get('shortName'),
            longName=info_data.get('longName'),
            sector=info_data.get('sector'),
            industry=info_data.get('industry'),
            marketCap=info_data.get('marketCap'),
            currentPrice=current_price_value,
            dayHigh=info_data.get('dayHigh'),
            dayLow=info_data.get('dayLow'),
            previousClose=info_data.get('previousClose')
        )

        statistics = Statistics(**stats_dict)

        ai_predictions = AIPredictions(
            long_term=LongTermPrediction(**long_term_pred_dict),
            short_term=ShortTermPrediction(**short_term_pred_dict),
            intraday=IntradayPrediction(**intraday_pred_dict)
        )

        news_sentiment = NewsSentiment(
            stock_news=StockNewsSentiment(**stock_news_dict),
            global_market=GlobalMarketSentiment(**global_market_dict)
        )

        return AnalysisResponse(
            stock_info=stock_info,
            statistics=statistics,
            ai_predictions=ai_predictions,
            news_sentiment=news_sentiment,
            historical_data=historical_data_list,
            daily_returns_histogram=daily_returns_list
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error details in /analyze for {symbol}: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

