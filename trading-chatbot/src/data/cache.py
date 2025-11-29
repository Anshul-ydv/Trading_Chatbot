from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from ..config import Settings, get_settings
from ..utils import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class CacheRecord:
    ticker: str
    timeframe: str
    path: Path
    updated_at: datetime


class CacheManager:
    """Lightweight parquet-based cache for market data."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.metadata_path = self.settings.cache_dir / "metadata.json"
        self.settings.ensure_directories()

    def _raw_path(self, ticker: str, timeframe: str) -> Path:
        safe = ticker.replace("/", "-").upper()
        return self.settings.raw_cache_dir / f"{safe}_{timeframe}.parquet"

    def read_raw(self, ticker: str, timeframe: str = "1d") -> Optional[pd.DataFrame]:
        path = self._raw_path(ticker, timeframe)
        if not path.exists():
            return None
        try:
            df = pd.read_parquet(path)
            df.index = pd.to_datetime(df.index)
            return df
        except Exception as exc:  # pragma: no cover - logged for awareness
            logger.warning("Failed reading cache for %s: %s", ticker, exc)
            return None

    def write_raw(self, ticker: str, timeframe: str, df: pd.DataFrame) -> CacheRecord:
        path = self._raw_path(ticker, timeframe)
        df.to_parquet(path)
        record = CacheRecord(
            ticker=ticker,
            timeframe=timeframe,
            path=path,
            updated_at=datetime.now(UTC),
        )
        self._update_metadata(record)
        logger.info("Cached %s data at %s", ticker, path)
        return record

    def _update_metadata(self, record: CacheRecord) -> None:
        metadata = self._load_metadata()
        key = f"{record.ticker}_{record.timeframe}"
        metadata[key] = {
            "path": str(record.path),
            "updated_at": record.updated_at.isoformat(),
        }
        self.metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    def _load_metadata(self) -> dict:
        if not self.metadata_path.exists():
            return {}
        return json.loads(self.metadata_path.read_text(encoding="utf-8"))
