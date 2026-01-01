import os
import json
import requests
from datetime import datetime, timedelta
from langchain_core.tools import tool

@tool
def get_alphavantage_news_sentiment(ticker: str, limit: int = 10) -> str:
    """
    Fetches news and sentiment from AlphaVantage API.
    Provides sentiment scores (-1 to 1) and topic relevance.
    
    Args:
        ticker: Stock symbol (e.g., 'AAPL', 'TSLA')
        limit: Number of articles to fetch (default: 10)
    
    Returns:
        JSON string with news articles and sentiment data
    """
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        return json.dumps({"error": "ALPHA_VANTAGE_API_KEY not configured"})

    url = "https://www.alphavantage.co/query"
    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": ticker,
        "sort": "LATEST",
        "limit": limit,
        "apikey": api_key
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if "feed" not in data:
            return json.dumps({
                "source": "AlphaVantage",
                "error": f"No data available. Response: {data.get('Note', 'Unknown error')}"
            })

        # Extract and structure relevant information
        articles = []
        for article in data["feed"][:limit]:
            # Get ticker-specific sentiment if available
            ticker_sentiment = next(
                (ts for ts in article.get("ticker_sentiment", []) 
                 if ts["ticker"] == ticker),
                None
            )
            
            articles.append({
                "title": article.get("title"),
                "summary": article.get("summary"),
                "source": article.get("source"),
                "published_at": article.get("time_published"),
                "url": article.get("url"),
                "overall_sentiment_score": article.get("overall_sentiment_score"),
                "overall_sentiment_label": article.get("overall_sentiment_label"),
                "ticker_sentiment_score": ticker_sentiment.get("ticker_sentiment_score") if ticker_sentiment else None,
                "ticker_sentiment_label": ticker_sentiment.get("ticker_sentiment_label") if ticker_sentiment else None,
                "relevance_score": ticker_sentiment.get("relevance_score") if ticker_sentiment else None
            })
        
        return json.dumps({
            "source": "AlphaVantage",
            "ticker": ticker,
            "articles": articles,
            "total_articles": len(articles)
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "source": "AlphaVantage",
            "error": str(e)
        })


@tool
def get_finnhub_company_news(ticker: str, days_back: int = 360) -> str:
    """
    Fetches company-specific news from Finnhub API.
    Excellent for North American stocks with high-quality sources.
    
    Args:
        ticker: Stock symbol
        days_back: Number of days to look back (default: 360)
    
    Returns:
        JSON string with news articles
    """
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        return json.dumps({"error": "FINNHUB_API_KEY not configured"})

    # Calculate date range
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    url = "https://finnhub.io/api/v1/company-news"
    params = {
        "symbol": ticker,
        "from": start_date,
        "to": end_date,
        "token": api_key
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if not data or isinstance(data, dict) and "error" in data:
            return json.dumps({
                "source": "Finnhub",
                "error": f"No news found for {ticker}"
            })

        # Structure the articles
        articles = []
        for article in data[:10]:  # Limit to 10 most recent
            articles.append({
                "headline": article.get("headline"),
                "summary": article.get("summary"),
                "source": article.get("source"),
                "published_at": datetime.fromtimestamp(article.get("datetime")).isoformat(),
                "url": article.get("url"),
                "category": article.get("category"),
                "image": article.get("image")
            })
        
        return json.dumps({
            "source": "Finnhub",
            "ticker": ticker,
            "date_range": f"{start_date} to {end_date}",
            "articles": articles,
            "total_articles": len(articles)
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "source": "Finnhub",
            "error": str(e)
        })
    

@tool
def get_general_market_news(category: str = "business", limit: int = 10) -> str:
    """
    Fetches general stock market and business news from NewsAPI.
    Covers broad market trends, major indices (S&P 500, Dow, Nasdaq), and overall sentiment.
    
    Args:
        category: News category ('business', 'general', 'technology')
        limit: Number of articles (default: 10)
    
    Returns:
        JSON with market-wide news articles
    """
    api_key = os.getenv("NEWSAPI_KEY")
    if not api_key:
        return json.dumps({"error": "NEWSAPI_KEY not configured"})

    url = "https://newsapi.org/v2/top-headlines"
    
    params = {
        "category": category,
        "language": "en",
        "country": "us",
        "pageSize": limit,
        "apiKey": api_key
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if data.get("status") != "ok":
            return json.dumps({
                "source": "NewsAPI Market News",
                "error": data.get("message", "Unknown error")
            })

        articles = []
        for article in data.get("articles", []):
            articles.append({
                "title": article.get("title"),
                "description": article.get("description"),
                "source": article.get("source", {}).get("name"),
                "published_at": article.get("publishedAt"),
                "url": article.get("url"),
                "content_snippet": article.get("content", "")[:200] if article.get("content") else ""
            })
        
        return json.dumps({
            "source": "General Market News (NewsAPI)",
            "category": category,
            "articles": articles,
            "total_articles": len(articles),
            "context": "Covers general stock market trends, S&P 500, Dow Jones, Nasdaq movements"
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "source": "NewsAPI Market News",
            "error": str(e)
        })


@tool
def get_geopolitical_news(query: str = "war OR sanctions OR tariffs OR trade war OR government policy") -> str:
    """
    Fetches news about geopolitical events that may affect stock markets.
    Includes: wars, government decisions, international sanctions, trade policies, political instability.
    
    Args:
        query: Search query for geopolitical events (customizable)
    
    Returns:
        JSON with geopolitical news that could impact markets
    """
    api_key = os.getenv("NEWSAPI_KEY")
    if not api_key:
        return json.dumps({"error": "NEWSAPI_KEY not configured"})

    url = "https://newsapi.org/v2/everything"
    
    # Last 7 days of geopolitical news
    from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    # Enhanced query to capture market-relevant geopolitical events
    enhanced_query = f"({query}) AND (stock market OR economy OR inflation OR oil OR commodities OR financial)"
    
    params = {
        "q": enhanced_query,
        "from": from_date,
        "sortBy": "relevancy",
        "language": "en",
        "apiKey": api_key,
        "pageSize": 10
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if data.get("status") != "ok":
            return json.dumps({
                "source": "Geopolitical News",
                "error": data.get("message", "Unknown error")
            })

        articles = []
        for article in data.get("articles", []):
            articles.append({
                "title": article.get("title"),
                "description": article.get("description"),
                "source": article.get("source", {}).get("name"),
                "published_at": article.get("publishedAt"),
                "url": article.get("url"),
                "content_snippet": article.get("content", "")[:300] if article.get("content") else ""
            })
        
        return json.dumps({
            "source": "Geopolitical Events News",
            "query_used": enhanced_query,
            "articles": articles,
            "total_results": data.get("totalResults"),
            "context": "Wars, sanctions, government policy changes, trade disputes affecting markets",
            "market_impact_areas": ["Oil/Energy", "Defense", "Tech", "Financials", "Commodities"]
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "source": "Geopolitical News",
            "error": str(e)
        })


@tool
def get_economic_indicators_news() -> str:
    """
    Fetches news about major economic indicators and central bank decisions.
    Covers: Federal Reserve decisions, GDP reports, inflation data, unemployment, interest rates.
    
    Returns:
        JSON with economic policy and indicator news
    """
    api_key = os.getenv("NEWSAPI_KEY")
    if not api_key:
        return json.dumps({"error": "NEWSAPI_KEY not configured"})

    url = "https://newsapi.org/v2/everything"
    
    from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    # Search for major economic events
    query = "(Federal Reserve OR Fed decision OR interest rates OR inflation OR GDP OR unemployment OR CPI OR economic growth OR recession)"
    
    params = {
        "q": query,
        "from": from_date,
        "sortBy": "relevancy",
        "language": "en",
        "apiKey": api_key,
        "pageSize": 10
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if data.get("status") != "ok":
            return json.dumps({
                "source": "Economic Indicators News",
                "error": data.get("message", "Unknown error")
            })

        articles = []
        for article in data.get("articles", []):
            articles.append({
                "title": article.get("title"),
                "description": article.get("description"),
                "source": article.get("source", {}).get("name"),
                "published_at": article.get("publishedAt"),
                "url": article.get("url")
            })
        
        return json.dumps({
            "source": "Economic Indicators & Central Bank News",
            "articles": articles,
            "total_results": data.get("totalResults"),
            "context": "Fed decisions, inflation data, GDP, unemployment affecting all markets",
            "key_indicators_covered": ["Interest Rates", "Inflation/CPI", "GDP", "Unemployment", "Fed Policy"]
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "source": "Economic Indicators News",
            "error": str(e)
        })


@tool
def get_alphavantage_top_gainers_losers() -> str:
    """
    Fetches the top gaining and losing stocks in the market today.
    Helps identify trending stocks and market movers.
    
    Returns:
        JSON with top gainers and losers with price change percentages
    """
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        return json.dumps({"error": "ALPHA_VANTAGE_API_KEY not configured"})

    url = "https://www.alphavantage.co/query"
    params = {
        "function": "TOP_GAINERS_LOSERS",
        "apikey": api_key
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if "top_gainers" not in data:
            return json.dumps({
                "source": "AlphaVantage Trending",
                "error": f"No data available. Response: {data.get('Note', 'Unknown error')}"
            })

        # Get top 5 gainers and losers
        top_gainers = []
        for stock in data.get("top_gainers", [])[:5]:
            top_gainers.append({
                "ticker": stock.get("ticker"),
                "price": stock.get("price"),
                "change_amount": stock.get("change_amount"),
                "change_percentage": stock.get("change_percentage"),
                "volume": stock.get("volume")
            })
        
        top_losers = []
        for stock in data.get("top_losers", [])[:5]:
            top_losers.append({
                "ticker": stock.get("ticker"),
                "price": stock.get("price"),
                "change_amount": stock.get("change_amount"),
                "change_percentage": stock.get("change_percentage"),
                "volume": stock.get("volume")
            })
        
        most_traded = []
        for stock in data.get("most_actively_traded", [])[:5]:
            most_traded.append({
                "ticker": stock.get("ticker"),
                "price": stock.get("price"),
                "change_amount": stock.get("change_amount"),
                "change_percentage": stock.get("change_percentage"),
                "volume": stock.get("volume")
            })
        
        return json.dumps({
            "source": "AlphaVantage Market Movers",
            "last_updated": data.get("last_updated"),
            "top_gainers": top_gainers,
            "top_losers": top_losers,
            "most_actively_traded": most_traded,
            "context": "Real-time trending stocks - use these to understand market momentum"
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "source": "AlphaVantage Trending",
            "error": str(e)
        })


@tool
def get_sector_news(sector: str = "technology") -> str:
    """
    Fetches news about a specific market sector using AlphaVantage.
    Useful for understanding sector-wide trends affecting multiple stocks.
    
    Args:
        sector: Sector name (technology, healthcare, energy, financial, consumer, industrial)
    
    Returns:
        JSON with sector-specific news
    """
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        return json.dumps({"error": "ALPHA_VANTAGE_API_KEY not configured"})

    url = "https://www.alphavantage.co/query"
    
    # Map sectors to AlphaVantage topics
    sector_topics = {
        "technology": "technology",
        "healthcare": "healthcare",
        "energy": "energy",
        "financial": "finance",
        "consumer": "retail_wholesale",
        "industrial": "manufacturing"
    }
    
    # Get the appropriate topic or use the sector name as fallback
    topic = sector_topics.get(sector.lower(), sector.lower())
    
    params = {
        "function": "NEWS_SENTIMENT",
        "topics": topic,
        "sort": "LATEST",
        "limit": 50,  # Get more articles to filter
        "apikey": api_key
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if "feed" not in data:
            return json.dumps({
                "source": "AlphaVantage Sector News",
                "error": f"No data available. Response: {data.get('Note', 'Unknown error')}"
            })

        # Filter and structure articles
        articles = []
        for article in data["feed"][:8]:  # Limit to top 8 most relevant
            articles.append({
                "title": article.get("title"),
                "summary": article.get("summary"),
                "source": article.get("source"),
                "published_at": article.get("time_published"),
                "url": article.get("url"),
                "overall_sentiment_score": article.get("overall_sentiment_score"),
                "overall_sentiment_label": article.get("overall_sentiment_label"),
                "topics": article.get("topics", [])
            })
        
        return json.dumps({
            "source": f"AlphaVantage {sector.title()} Sector News",
            "sector": sector,
            "topic_filter": topic,
            "articles": articles,
            "total_articles": len(articles),
            "context": f"Sector-wide trends affecting all {sector} stocks"
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "source": "AlphaVantage Sector News",
            "error": str(e)
        })


@tool
def get_trending_stocks_news(limit: int = 5) -> str:
    """
    Fetches news about the most talked-about/trending stocks on social media and news.
    Identifies top market movers and provides their tickers.
    
    Args:
        limit: Number of trending stocks to analyze
    
    Returns:
        JSON with trending stock tickers and their price movements
    """
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        return json.dumps({"error": "ALPHA_VANTAGE_API_KEY not configured"})

    url = "https://www.alphavantage.co/query"
    params = {
        "function": "TOP_GAINERS_LOSERS",
        "apikey": api_key
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if "top_gainers" not in data:
            return json.dumps({
                "source": "AlphaVantage Trending",
                "error": f"No data available. Response: {data.get('Note', 'Unknown error')}"
            })
        
        # Extract trending tickers
        trending_tickers = []
        
        # Top 3 gainers
        for gainer in data.get("top_gainers", [])[:3]:
            trending_tickers.append({
                "ticker": gainer.get("ticker"),
                "price": gainer.get("price"),
                "change": gainer.get("change_percentage"),
                "volume": gainer.get("volume"),
                "type": "Top Gainer"
            })
        
        # Top 2 losers
        for loser in data.get("top_losers", [])[:2]:
            trending_tickers.append({
                "ticker": loser.get("ticker"),
                "price": loser.get("price"),
                "change": loser.get("change_percentage"),
                "volume": loser.get("volume"),
                "type": "Top Loser"
            })
        
        return json.dumps({
            "source": "Trending Stocks Analysis",
            "last_updated": data.get("last_updated"),
            "trending_stocks": trending_tickers,
            "context": "These stocks are moving significantly today - major market movers",
            "suggestion": "Use get_alphavantage_news_sentiment with these tickers to understand WHY they're moving"
        }, indent=2)
    
    except Exception as e:
        return json.dumps({
            "source": "Trending Stocks",
            "error": str(e)
        })

