from datetime import date, timedelta

from src.config import get_settings
from src.data.fetchers import fetch_ohlcv


def test_fetch_ohlcv_returns_data_and_caches():
    start = date.today() - timedelta(days=30)
    df = fetch_ohlcv("RELIANCE", start=start)
    assert not df.empty
    settings = get_settings()
    cached_files = list(settings.raw_cache_dir.glob("RELIANCE_1d.parquet"))
    assert cached_files, "Expected cached parquet file to be created"
