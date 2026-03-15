"""
tools/news_tools.py
News retrieval and sentiment analysis tools.
Uses NewsAPI if key is set, otherwise falls back to yfinance news.
"""

import os
import json
import requests
from datetime import datetime, timedelta

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


def get_company_news(ticker: str, max_articles: int = 10) -> dict:
    """Retrieves the latest news articles about a company by its ticker symbol.

    Args:
        ticker: The stock ticker symbol (e.g. 'AAPL', 'TSLA').
        max_articles: Maximum number of articles to return. Defaults to 10.

    Returns:
        dict: status and result containing a list of news articles with title, publisher, date, and summary.
    """
    news_api_key = os.getenv("NEWS_API_KEY", "").strip()
    articles = []

    # --- Try NewsAPI first ---
    if news_api_key:
        try:
            # Get company name from yfinance to build a better query
            company_name = ticker.upper()
            if YFINANCE_AVAILABLE:
                info = yf.Ticker(ticker.upper()).info
                company_name = info.get("shortName", ticker.upper())

            url = "https://newsapi.org/v2/everything"
            params = {
                "q": f"{company_name} OR {ticker.upper()} stock",
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": max_articles,
                "apiKey": news_api_key,
                "from": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
            }
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for art in data.get("articles", []):
                    articles.append({
                        "title": art.get("title", ""),
                        "publisher": art.get("source", {}).get("name", ""),
                        "published_at": art.get("publishedAt", ""),
                        "description": art.get("description", ""),
                        "url": art.get("url", ""),
                    })
        except Exception:
            pass

    # --- Fallback: yfinance news ---
    if not articles and YFINANCE_AVAILABLE:
        try:
            stock = yf.Ticker(ticker.upper())
            yf_news = stock.news or []
            for item in yf_news[:max_articles]:
                content = item.get("content", {})
                articles.append({
                    "title": content.get("title", item.get("title", "")),
                    "publisher": content.get("provider", {}).get("displayName", "Yahoo Finance"),
                    "published_at": content.get("pubDate", ""),
                    "description": content.get("summary", ""),
                    "url": content.get("canonicalUrl", {}).get("url", ""),
                })
        except Exception as e:
            return {"status": "error", "error_message": f"Could not fetch news: {e}"}

    if not articles:
        return {
            "status": "success",
            "data": {
                "ticker": ticker.upper(),
                "articles": [],
                "message": "No recent news found. Set NEWS_API_KEY in .env for broader coverage.",
            }
        }

    return {
        "status": "success",
        "data": {
            "ticker": ticker.upper(),
            "article_count": len(articles),
            "articles": articles,
        }
    }


def get_social_sentiment(ticker: str) -> dict:
    """Retrieves social media sentiment and short interest data for a stock.

    Args:
        ticker: The stock ticker symbol.

    Returns:
        dict: status and result with short interest, insider sentiment, and institutional ownership data.
    """
    if not YFINANCE_AVAILABLE:
        return {"status": "error", "error_message": "yfinance not installed"}

    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info

        sentiment_data = {
            "ticker": ticker.upper(),
            "short_ratio": info.get("shortRatio", "N/A"),
            "short_percent_of_float": info.get("shortPercentOfFloat", "N/A"),
            "shares_short": info.get("sharesShort", "N/A"),
            "shares_short_prior_month": info.get("sharesShortPriorMonth", "N/A"),
            "held_by_insiders_pct": info.get("heldPercentInsiders", "N/A"),
            "held_by_institutions_pct": info.get("heldPercentInstitutions", "N/A"),
            "float_shares": info.get("floatShares", "N/A"),
            "shares_outstanding": info.get("sharesOutstanding", "N/A"),
            "beta": info.get("beta", "N/A"),
        }

        # Recent insider transactions
        try:
            insider_df = stock.insider_transactions
            if insider_df is not None and not insider_df.empty:
                recent_insider = insider_df.head(5).reset_index()
                sentiment_data["recent_insider_transactions"] = recent_insider.to_dict(orient="records")
        except Exception:
            pass

        # Major institutional holders
        try:
            inst_df = stock.institutional_holders
            if inst_df is not None and not inst_df.empty:
                sentiment_data["top_institutional_holders"] = inst_df.head(5).to_dict(orient="records")
        except Exception:
            pass

        return {"status": "success", "data": sentiment_data}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}
