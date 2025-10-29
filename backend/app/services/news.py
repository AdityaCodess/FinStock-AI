# finstock-ai/backend/app/services/news.py
import feedparser # For reading RSS feeds
import random
from typing import List, Dict, Any
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer # For local sentiment analysis

# --- Initialize VADER ---
analyzer = SentimentIntensityAnalyzer()

# --- Define RSS Feed URLs (Examples) ---
# We can add more later or make this configurable
LIVEMINT_MARKET_RSS = "https://www.livemint.com/rss/markets" # General market news
# We could add more specific feeds if needed, e.g., for specific sectors

# --- Helper Functions ---

def get_sentiment_vader(text: str) -> Dict[str, Any]:
    """
    Analyzes the sentiment of a text string using VADER.
    Returns the compound score and a label (Positive/Negative/Neutral).
    """
    vs = analyzer.polarity_scores(text)
    compound_score = vs['compound']
    
    if compound_score >= 0.05:
        label = "Positive"
    elif compound_score <= -0.05:
        label = "Negative"
    else:
        label = "Neutral"
        
    return {"score": compound_score, "label": label}

def fetch_rss_feed(feed_url: str, limit: int = 5) -> List[Dict[str, str]]:
    """
    Fetches and parses an RSS feed, returning a list of articles.
    """
    try:
        feed = feedparser.parse(feed_url)
        articles = []
        for entry in feed.entries[:limit]:
            articles.append({
                "source": feed.feed.title if 'title' in feed.feed else 'RSS Feed',
                "headline": entry.title if 'title' in entry else 'No Title',
                # 'summary': entry.summary if 'summary' in entry else '' # Optional: summary can be noisy
            })
        return articles
    except Exception as e:
        print(f"Error fetching or parsing RSS feed {feed_url}: {e}")
        return []

# --- Main Service Functions ---

def get_news_and_sentiment(symbol: str, company_name: str) -> Dict[str, Any]:
    """
    Fetches stock-specific news (using a general feed for now) and analyzes sentiment locally.
    """
    # NOTE: Finding free, symbol-specific RSS feeds is hard.
    # We'll use the general market feed and *simulate* finding relevant articles.
    # A real implementation might use a paid news API or keyword filtering.
    
    all_articles = fetch_rss_feed(LIVEMINT_MARKET_RSS, limit=10)
    
    # Simulate finding articles relevant to the company name
    relevant_articles = [
        article for article in all_articles 
        if company_name.split()[0].lower() in article['headline'].lower() # Simple keyword match
    ][:3] # Take top 3 matches
    
    # If no relevant articles found, use the top 2 generic ones
    if not relevant_articles and all_articles:
        relevant_articles = all_articles[:2]
        
    # Calculate overall sentiment based on relevant headlines
    total_score = 0
    if relevant_articles:
        for article in relevant_articles:
            sentiment = get_sentiment_vader(article['headline'])
            article['sentiment_score'] = sentiment['score'] # Add score to article dict
            article['sentiment_label'] = sentiment['label']
            total_score += sentiment['score']
        
        avg_score = total_score / len(relevant_articles)
        overall_sentiment_label = get_sentiment_vader(f"Score {avg_score}")['label'] # Use VADER logic for label
    else:
        # Fallback if no news found
        relevant_articles.append({
            "source": "System", 
            "headline": f"No recent news found for {company_name}", 
            "sentiment_score": 0,
            "sentiment_label": "Neutral"
        })
        overall_sentiment_label = "Neutral"

    return {
        "articles": relevant_articles,
        "overall_sentiment": overall_sentiment_label,
        # "predicted_impact": "N/A" # VADER doesn't provide this directly
    }


def get_global_market_sentiment() -> Dict[str, Any]:
    """
    Fetches global/market news headlines from RSS and calculates average sentiment locally.
    """
    articles = fetch_rss_feed(LIVEMINT_MARKET_RSS, limit=5)
    
    total_score = 0
    headlines_only = []
    if articles:
        for article in articles:
            sentiment = get_sentiment_vader(article['headline'])
            total_score += sentiment['score']
            headlines_only.append(article['headline']) # Just collect headlines for the response
        
        avg_score = total_score / len(articles)
        overall_sentiment_label = get_sentiment_vader(f"Score {avg_score}")['label']
        # Try to guess a trending topic from the first headline
        trending_topic = headlines_only[0].split('-')[0].split('|')[0].strip() if headlines_only else "Market Update"

    else:
        overall_sentiment_label = "Neutral"
        trending_topic = "News Unavailable"
        headlines_only = ["Could not fetch market news feed."]

    return {
        "overall_market_sentiment": overall_sentiment_label,
        "trending_topic": trending_topic,
        # "predicted_impact": "N/A", # VADER doesn't provide this
        "key_headlines": headlines_only
    }