from __future__ import annotations

import csv
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable, List

from .config import Settings, get_settings

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def ensure_date_range(start: date | None, end: date | None, window_days: int = 120) -> tuple[date, date]:
    """Provide a sensible default date range when none is supplied."""
    today = date.today()
    end = end or today
    start = start or (end - timedelta(days=window_days))
    if start > end:
        raise ValueError("start date must be before end date")
    return start, end


def read_tickers(path: str | Path | None = None, limit: int | None = None) -> List[str]:
    settings: Settings = get_settings()
    csv_path = Path(path or settings.tickers_file)
    if not csv_path.exists():
        raise FileNotFoundError(f"Ticker file not found: {csv_path}")
    tickers: List[str] = []
    with csv_path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            ticker = row.get("ticker")
            if ticker:
                tickers.append(ticker.strip().upper())
                if limit and len(tickers) >= limit:
                    break
    return tickers


def chunked(iterable: Iterable[str], size: int) -> Iterable[list[str]]:
    chunk: list[str] = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) == size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk
