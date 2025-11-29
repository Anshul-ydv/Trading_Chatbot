from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

try:  # pragma: no cover - optional dependency for local dev
    from dotenv import load_dotenv  # type: ignore
except ImportError:  # pragma: no cover
    def load_dotenv(*_, **__):
        return False

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    load_dotenv()


@dataclass(slots=True)
class Settings:
    """Centralised application configuration."""

    base_dir: Path = BASE_DIR
    data_dir: Path = BASE_DIR / "data"
    cache_dir: Path = data_dir / "cache"
    raw_cache_dir: Path = cache_dir / "raw"
    processed_cache_dir: Path = cache_dir / "processed"
    manual_data_dir: Path = data_dir / "manual"
    tickers_file: Path = data_dir / "tickers.csv"
    sample_fundamentals_file: Path = data_dir / "sample_fundamentals.json"
    rag_store: Path = data_dir / "rag_store.json"
    screener_base_url: str = "https://www.screener.in/company/{ticker}/"
    
    # Fyers v3 Configuration
    fyers_client_id: str | None = os.getenv("FYERS_CLIENT_ID")  # App ID
    fyers_secret_key: str | None = os.getenv("FYERS_SECRET_KEY")
    fyers_redirect_uri: str | None = os.getenv("FYERS_REDIRECT_URI")
    fyers_access_token: str | None = os.getenv("FYERS_ACCESS_TOKEN")
    fyers_symbol_prefix: str = os.getenv("FYERS_SYMBOL_PREFIX", "NSE:")
    fyers_symbol_suffix: str = os.getenv("FYERS_SYMBOL_SUFFIX", "-EQ")
    
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    embeddings_model: str = os.getenv(
        "EMBEDDINGS_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    )
    llm_provider: str = os.getenv("LLM_PROVIDER", "template").lower()
    llm_model: str = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "gpt-oss")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    ollama_timeout: int = int(os.getenv("OLLAMA_TIMEOUT", "180"))
    
    use_fyers_fallback: bool = os.getenv("USE_FYERS_FALLBACK", "0") == "1"
    require_live_data: bool = os.getenv("REQUIRE_LIVE_DATA", "0") == "1"
    allow_synthetic_data: bool = os.getenv("ALLOW_SYNTHETIC_DATA", "1") == "1"
    default_strategy: str = os.getenv("DEFAULT_STRATEGY", "breakout")

    def ensure_directories(self) -> None:
        """Create required directories if they do not exist."""
        for path in (
            self.data_dir,
            self.cache_dir,
            self.raw_cache_dir,
            self.processed_cache_dir,
            self.manual_data_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
