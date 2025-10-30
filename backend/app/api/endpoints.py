# finstock-ai/backend/app/api/endpoints.py
import sqlite3
import traceback
import os
import pandas as pd
import numpy as np
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from app.services import analysis
from app.services import prediction
from app.services import news

# --- Pydantic Models (Unchanged) ---
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
    currentPrice: Optional[float] = None
    dayHigh: Optional[float] = None
    dayLow: Optional[float] = None
    previousClose: Optional[float] = None

class Statistics(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    mean: Optional[float] = None
    median: Optional[float] = None
    mode: Optional[float] = None
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
    probability_next_day_down: Optional[float] = None
    mean_daily_return_percent: Optional[float] = None
    std_dev_daily_return_percent: Optional[float] = None
    cond_prob_up_given_up: Optional[float] = None
    cond_prob_down_given_down: Optional[float] = None
    prob_2_days_up_streak: Optional[float] = None
    prob_2_days_down_streak: Optional[float] = None

class LongTermPrediction(BaseModel):
    forecast_1y: Optional[float] = None
    recommendation: str
    confidence: Optional[float] = None

class ShortTermPrediction(BaseModel):
    forecast_7d_percent: Optional[float] = None
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
    daily_returns_histogram: List[float]

# --- Router Setup (Unchanged) ---
router = APIRouter(prefix="/api", tags=["API"])
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
@router.get("/search", response_model=List[StockSearchResponse])
async def search_stocks(q: Optional[str] = Query(None, min_length=2, description="Search query")):
    if q is None: return []
    search_query = f"%{q}%"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT symbol, name FROM stocks WHERE symbol LIKE ? OR name LIKE ? LIMIT 10", (search_query, search_query))
        stocks = cursor.fetchall()
        return [dict(row) for row in stocks]
    except Exception as e:
        print(f"Error during search: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"An error occurred during search: {str(e)}")
    finally:
        if conn: conn.close()

@router.get("/analyze", response_model=AnalysisResponse)
async def analyze_stock(
    symbol: str = Query(..., description="Stock symbol (e.g., RELIANCE.NS)"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    try:
        # 1. Fetch Data
        hist_data_raw, info_data = analysis.get_stock_data(symbol, start_date=start_date, end_date=end_date)
        if not isinstance(info_data, dict): info_data = {'symbol': symbol}

        # --- THIS IS THE FIX ---
        # 2. Clean Data ONCE
        if not isinstance(hist_data_raw.index, pd.DatetimeIndex):
             hist_data_raw.index = pd.to_datetime(hist_data_raw.index, errors='coerce')
             hist_data_raw.dropna(axis=0, subset=[hist_data_raw.index.name], inplace=True)
        
        hist_data = hist_data_raw.copy()
        hist_data['Close'] = pd.to_numeric(hist_data['Close'], errors='coerce')
        hist_data.dropna(axis=0, subset=['Close'], inplace=True) # Drop rows where Close is NaN

        if hist_data.empty:
            raise HTTPException(status_code=404, detail="No valid historical data to analyze after cleaning.")
        # --- END FIX ---

        # 3. Calculate Statistics (using the CLEANED hist_data)
        stats_dict, daily_returns_list = analysis.calculate_statistics(hist_data)

        # 4. Get AI Predictions (using the CLEANED hist_data)
        long_term_pred_dict = prediction.get_long_term_prediction(hist_data, symbol)
        short_term_pred_dict = prediction.get_short_term_prediction(hist_data, symbol)
        intraday_pred_dict = prediction.get_intraday_prediction(symbol)

        # 5. Get News & Sentiment (Unchanged)
        company_name = info_data.get('shortName', info_data.get('longName', symbol))
        stock_news_dict = news.get_news_and_sentiment(symbol, company_name)
        global_market_dict = news.get_global_market_sentiment()

        # 6. Format Historical Data for Charting (using the CLEANED hist_data)
        hist_data_chart = hist_data[['Close']].copy()
        hist_data_chart.index.name = 'Date'
        hist_data_chart.reset_index(inplace=True)
        hist_data_chart['date'] = hist_data_chart['Date'].dt.strftime('%Y-%m-%d') # Format date as string
        hist_data_chart.rename(columns={'Close': 'close'}, inplace=True)
        historical_data_list = hist_data_chart[['date', 'close']].to_dict(orient='records') # Send clean list

        # 7. Format Full Response
        latest_close_price = hist_data['Close'].iloc[-1] if not hist_data.empty else None
        prev_close_price = hist_data['Close'].iloc[-2] if len(hist_data) > 1 else None

        stock_info = StockInfo(
            symbol=info_data.get('symbol', symbol),
            shortName=info_data.get('shortName'), longName=info_data.get('longName'),
            sector=info_data.get('sector'), industry=info_data.get('industry'),
            marketCap=info_data.get('marketCap'),
            currentPrice=latest_close_price, # Use reliable price
            dayHigh=hist_data['High'].iloc[-1] if 'High' in hist_data.columns and not hist_data.empty else info_data.get('dayHigh'),
            dayLow=hist_data['Low'].iloc[-1] if 'Low' in hist_data.columns and not hist_data.empty else info_data.get('dayLow'),
            previousClose=prev_close_price if prev_close_price else info_data.get('previousClose')
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
            stock_info=stock_info, statistics=statistics, ai_predictions=ai_predictions,
            news_sentiment=news_sentiment, historical_data=historical_data_list,
            daily_returns_histogram=daily_returns_list
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error details in /analyze for {symbol}: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")