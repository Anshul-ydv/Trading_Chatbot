from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import numpy as np
import pandas as pd

from .cache import CacheManager
from ..config import Settings, get_settings
from ..fyers_client import FyersClient
from ..utils import ensure_date_range, get_logger

try:  # pragma: no cover - optional dependency
    from nsepy import get_history as nse_get_history
    from nsepy.history import get_history_quanta as nse_get_history_quanta
except ImportError:  # pragma: no cover
    nse_get_history = None
    nse_get_history_quanta = None

try:
    import yfinance as yf
except ImportError:
    yf = None

logger = get_logger(__name__)


class FetchError(RuntimeError):
    pass


def fetch_ohlcv(
    ticker: str,
    start: date | None = None,
    end: date | None = None,
    timeframe: str = "1d",
    use_cache: bool = True,
) -> pd.DataFrame:
    """Fetch OHLCV data with cache fallback and synthetic backup."""

    start, end = ensure_date_range(start, end)
    settings = get_settings()
    cache = CacheManager(settings)

    if use_cache:
        cached = cache.read_raw(ticker, timeframe)
        if cached is not None and not cached.empty:
            if cached.index.min().date() <= start and cached.index.max().date() >= end:
                return cached.loc[str(start) : str(end)]

    manual = _load_manual_csv(ticker, timeframe, settings)
    if manual is not None:
        cache.write_raw(ticker, timeframe, manual)
        return manual.loc[str(start) : str(end)]

    # Try yfinance first (most reliable for free data)
    df = _fetch_from_yfinance(ticker, start, end, timeframe)
    
    # Fallback to nsepy if yfinance fails
    if df is None or df.empty:
        df = _fetch_from_nse(ticker, start, end)

    if (df is None or df.empty) and settings.use_fyers_fallback:
        df = _fetch_from_fyers(ticker, start, end, timeframe, settings)

    if df is None or df.empty:
        if settings.require_live_data or not settings.allow_synthetic_data:
            raise FetchError(
                f"Live data required but unavailable for {ticker}; check network/API credentials."
            )
        logger.warning("Falling back to synthetic data for %s", ticker)
        df = _synthetic_series(ticker, start, end)

    df = df.sort_index()
    cache.write_raw(ticker, timeframe, df)
    return df


def _fetch_from_yfinance(ticker: str, start: date, end: date, timeframe: str = "1d") -> Optional[pd.DataFrame]:
    if yf is None:
        return None

    # yfinance expects .NS for NSE stocks
    symbol = ticker
    
    # Remove -EQ suffix if present, as yfinance doesn't use it for NSE
    if symbol.endswith("-EQ"):
        symbol = symbol[:-3]

    # Simple heuristic: if it doesn't have a suffix, assume NSE
    if not symbol.endswith(".NS") and not symbol.endswith(".BO"):
        symbol = f"{symbol}.NS"

    # Map timeframe to yfinance interval
    # yfinance: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
    interval_map = {
        "1d": "1d",
        "1m": "1m",
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        "1h": "1h",
        "60m": "60m"
    }
    interval = interval_map.get(timeframe, "1d")

    try:
        # end date in yfinance is exclusive
        df = yf.download(
            symbol, 
            start=start, 
            end=end + timedelta(days=1), 
            interval=interval,
            progress=False, 
            auto_adjust=False,
            multi_level_index=False  # Ensure flat columns if possible
        )

        if df is None or df.empty:
            return None

        # Handle MultiIndex columns (common in newer yfinance)
        if isinstance(df.columns, pd.MultiIndex):
            # If we have a MultiIndex, we likely have (Price, Ticker)
            # We just want the Price level.
            try:
                df.columns = df.columns.get_level_values(0)
            except IndexError:
                pass

        # Standardize columns
        # yfinance returns: Open, High, Low, Close, Adj Close, Volume
        df = df.rename(columns={
            "Open": "open", 
            "High": "high", 
            "Low": "low", 
            "Close": "close", 
            "Volume": "volume"
        })

        required = ["open", "high", "low", "close", "volume"]
        # Check if all required columns are present (case insensitive check was done by rename)
        if not all(c in df.columns for c in required):
            # Sometimes yfinance returns empty df with no columns or different columns on error
            return None

        df = df[required]
        # Ensure index is datetime
        df.index = pd.to_datetime(df.index)
        return df
    except Exception as e:
        logger.warning("yfinance fetch failed for %s: %s", symbol, e)
        return None


def _fetch_from_nse(ticker: str, start: date, end: date) -> Optional[pd.DataFrame]:
    symbol = ticker
    if symbol.endswith("-EQ"):
        symbol = symbol[:-3]
    raw = _safe_nse_history(symbol=symbol, start=start, end=end)
    if raw is None or raw.empty:
        return None
    df = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.columns = [c.lower() for c in df.columns]
    return df


def _safe_nse_history(
    symbol: str,
    start: date,
    end: date,
    index: bool = False,
    futures: bool = False,
    option_type: str = "",
    expiry_date: date | None = None,
    strike_price: str | int | float = "",
    series: str = "EQ",
):
    if nse_get_history_quanta is None and nse_get_history is None:  # pragma: no cover - optional dep missing
        return None

    window = timedelta(days=120)
    frames: list[pd.DataFrame] = []
    current = start

    while current <= end:
        chunk_end = min(current + window, end)
        kwargs = {
            "symbol": symbol,
            "start": current,
            "end": chunk_end,
            "index": index,
            "futures": futures,
            "option_type": option_type,
            "expiry_date": expiry_date,
            "strike_price": strike_price,
            "series": series,
        }
        frame = _call_nse_quanta(kwargs)
        if frame is not None and not frame.empty:
            frames.append(frame)
        current = chunk_end + timedelta(days=1)

    if not frames:
        return None
    return pd.concat(frames)


def _call_nse_quanta(kwargs: dict) -> Optional[pd.DataFrame]:
    func = nse_get_history_quanta or nse_get_history
    if func is None:
        return None
    try:
        return func(**kwargs)
    except Exception as exc:  # pragma: no cover - upstream errors
        logger.error("nsepy fetch failed for %s: %s", kwargs.get("symbol"), exc)
        return None


def _fetch_from_fyers(
    ticker: str,
    start: date,
    end: date,
    timeframe: str,
    settings: Settings,
) -> Optional[pd.DataFrame]:
    try:
        client = FyersClient(settings)
    except Exception as e:
        logger.info("FYERS fallback skipped; initialization error: %s", e)
        return None
        
    if not client.configured():
        logger.info("FYERS fallback skipped; credentials not configured")
        return None
        
    df = client.fetch_history(ticker, start, end, timeframe=timeframe)
    if df is None or df.empty:
        return None
    logger.info("Fetched FYERS data for %s", ticker)
    return df


def _load_manual_csv(ticker: str, timeframe: str, settings: Settings) -> Optional[pd.DataFrame]:
    path = settings.manual_data_dir / f"{ticker.upper()}_{timeframe}.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path, parse_dates=[0], index_col=0)
    df.columns = [c.lower() for c in df.columns]
    logger.info("Loaded manual dataset for %s from %s", ticker, path)
    return df


def _synthetic_series(ticker: str, start: date, end: date) -> pd.DataFrame:
    dates = pd.date_range(start=start, end=end, freq="B")
    seed = sum(ord(c) for c in ticker)
    rng = np.random.default_rng(seed)
    prices = np.cumsum(rng.normal(0.2, 1.5, len(dates))) + 100
    prices = np.maximum(prices, 1)
    df = pd.DataFrame(index=dates)
    df["open"] = prices + rng.normal(0, 0.5, len(dates))
    df["close"] = prices + rng.normal(0, 0.5, len(dates))
    df["high"] = df[["open", "close"]].max(axis=1) + rng.normal(0.2, 0.3, len(dates))
    df["low"] = df[["open", "close"]].min(axis=1) - rng.normal(0.2, 0.3, len(dates))
    df["volume"] = rng.integers(1_000_000, 5_000_000, len(dates))
    return df.round(2)
