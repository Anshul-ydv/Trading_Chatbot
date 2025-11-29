from __future__ import annotations

import requests
import xml.etree.ElementTree as ET
from typing import List, Dict
from ..utils import get_logger

logger = get_logger(__name__)

def fetch_news(ticker: str, limit: int = 3) -> List[Dict[str, str]]:
    """Fetch latest news for a ticker from Google News RSS."""
    # Clean ticker for search (remove .NS etc if present, though usually passed clean)
    search_term = ticker.replace(".NS", "").replace(".BO", "")
    url = f"https://news.google.com/rss/search?q={search_term}+stock+news+india&hl=en-IN&gl=IN&ceid=IN:en"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        items = root.findall(".//item")
        
        news_list = []
        for item in items[:limit]:
            title = item.find("title").text if item.find("title") is not None else "No title"
            link = item.find("link").text if item.find("link") is not None else ""
            pubDate = item.find("pubDate").text if item.find("pubDate") is not None else ""
            
            news_list.append({
                "title": title,
                "link": link,
                "published": pubDate
            })
            
        return news_list
    except Exception as e:
        logger.error(f"Error fetching news for {ticker}: {e}")
        return []
