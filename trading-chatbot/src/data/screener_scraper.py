from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from bs4 import BeautifulSoup

from ..config import Settings, get_settings
from ..utils import get_logger

logger = get_logger(__name__)
USER_AGENT = "Mozilla/5.0 (compatible; TradingChatbot/1.0; +https://example.com/bot)"


class ScreenerClient:
    """Scrapes or loads Screener.in metrics with offline fallbacks."""

    def __init__(self, settings: Settings | None = None, allow_network: bool | None = None) -> None:
        self.settings = settings or get_settings()
        flag = os.getenv("ALLOW_SCREENER_HTTP", "0")
        self.allow_network = allow_network if allow_network is not None else flag == "1"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def fetch(self, ticker: str) -> Dict[str, Any]:
        ticker = ticker.upper()
        
        # 1. Try Screener (First Priority)
        if self.allow_network:
            try:
                live = self._scrape_live(ticker)
                if live:
                    live["source"] = "screener"
                    return live
            except Exception as exc:  # pragma: no cover - network branch
                logger.warning("Live scrape failed for %s: %s", ticker, exc)

        # 2. Try yfinance (Second Priority)
        try:
            import yfinance as yf
            symbol = f"{ticker}.NS" if not ticker.endswith(".NS") else ticker
            info = yf.Ticker(symbol).info
            if info and "marketCap" in info:
                return {
                    "market_cap": info.get("marketCap", 0) / 10000000, # Convert to Crores
                    "market_cap_cr": round(info.get("marketCap", 0) / 10000000, 2),
                    "pe_ratio": info.get("trailingPE", 0),
                    "roe": info.get("returnOnEquity", 0) * 100 if info.get("returnOnEquity") else 0,
                    "debt_to_equity": info.get("debtToEquity", 0) / 100 if info.get("debtToEquity") else 0,
                    "promoter_holding": info.get("heldPercentInsiders", 0) * 100 if info.get("heldPercentInsiders") else 0,
                    "sales_growth_3y": info.get("revenueGrowth", 0) * 100 if info.get("revenueGrowth") else 0,
                    "profit_growth_3y": info.get("earningsGrowth", 0) * 100 if info.get("earningsGrowth") else 0,
                    "source": "yfinance"
                }
        except Exception as e:
            logger.warning(f"yfinance fundamentals failed for {ticker}: {e}")

        # 3. Fallback to sample/dummy
        return self._load_sample(ticker)

    def _sample_path(self) -> Path:
        return Path(self.settings.sample_fundamentals_file)

    def _load_sample(self, ticker: str) -> Dict[str, Any]:
        sample_path = self._sample_path()
        if not sample_path.exists():
            # Return dummy data if file missing
            return self._dummy_fundamentals(ticker)
            
        try:
            data = json.loads(sample_path.read_text(encoding="utf-8"))
            if ticker not in data:
                logger.warning(f"No fundamentals for {ticker} in sample file; using dummy data")
                return self._dummy_fundamentals(ticker)
            return data[ticker]
        except Exception as e:
            logger.error(f"Error reading sample fundamentals: {e}")
            return self._dummy_fundamentals(ticker)

    def _dummy_fundamentals(self, ticker: str) -> Dict[str, Any]:
        """Return safe default values when data is missing."""
        return {
            "market_cap": 0.0,
            "pe_ratio": 0.0,
            "roe": 0.0,
            "debt_to_equity": 0.0,
            "promoter_holding": 0.0,
            "sales_growth_3y": 0.0,
            "profit_growth_3y": 0.0,
            "note": "Data unavailable"
        }

    def _scrape_live(self, ticker: str) -> Optional[Dict[str, Any]]:
        url = self.settings.screener_base_url.format(ticker=ticker)
        response = self.session.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        mapping = {
            "market_cap": "Market Cap",
            "pe_ratio": "P/E",
            "roe": "ROE",
            "debt_to_equity": "Debt to equity",
            "promoter_holding": "Promoter holding",
            "sales_growth_3y": "Sales growth 3Years",
            "profit_growth_3y": "Profit growth",
        }
        ratios: Dict[str, Any] = {}
        for key, label in mapping.items():
            value = _extract_ratio(soup, label)
            if value is not None:
                ratios[key] = value
        if not ratios:
            return None
        return ratios


def _extract_ratio(soup: BeautifulSoup, label: str) -> Optional[float]:
    pattern = re.compile(label, re.IGNORECASE)
    node = soup.find(string=pattern)
    if not node:
        return None
    parent = node.find_parent(["tr", "li", "div"])
    if not parent:
        return None
    text = parent.get_text(" ", strip=True)
    parts = re.findall(r"[-+]?\d*\.?\d+", text)
    if not parts:
        return None
    try:
        return float(parts[0])
    except ValueError:
        return None


def scrape_screener(ticker: str) -> Dict[str, Any]:
    client = ScreenerClient()
    return client.fetch(ticker)
