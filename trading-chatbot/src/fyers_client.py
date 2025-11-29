from __future__ import annotations

from datetime import date
import pandas as pd
from fyers_apiv3 import fyersModel

from .config import Settings, get_settings
from .utils import get_logger

logger = get_logger(__name__)

class FyersClient:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.client = None
        self._authenticate()

    def _authenticate(self):
        """Initialize the FyersModel instance."""
        if not self.settings.fyers_client_id or not self.settings.fyers_access_token:
            logger.warning("Fyers credentials (CLIENT_ID or ACCESS_TOKEN) missing.")
            return

        try:
            self.client = fyersModel.FyersModel(
                client_id=self.settings.fyers_client_id,
                token=self.settings.fyers_access_token,
                log_path=str(self.settings.data_dir)
            )
            # Verify connection (optional, maybe a lightweight call)
            # response = self.client.get_profile()
            # if response.get("s") != "ok":
            #     logger.error("Fyers authentication failed: %s", response)
            #     self.client = None
        except Exception as e:
            logger.error("Error initializing Fyers client: %s", e)
            self.client = None

    def configured(self) -> bool:
        return self.client is not None

    def fetch_history(
        self, 
        ticker: str, 
        start: date, 
        end: date, 
        timeframe: str = "1d"
    ) -> pd.DataFrame | None:
        if not self.client:
            return None

        # Map timeframe to Fyers resolution
        # Fyers: 1, 2, 3, 5, 10, 15, 20, 30, 60, 120, 240, 1D
        resolution_map = {
            "1m": "1", "2m": "2", "5m": "5", "15m": "15", 
            "30m": "30", "60m": "60", "1h": "60", "1d": "1D"
        }
        resolution = resolution_map.get(timeframe, "1D")

        # Format symbol
        symbol = ticker
        if not symbol.startswith(self.settings.fyers_symbol_prefix):
            # If it doesn't have a prefix (like NSE:), add it.
            # Also check if it needs suffix removal or addition based on your convention
            # Assuming ticker comes in as "RELIANCE" or "RELIANCE.NS"
            clean_ticker = ticker.replace(".NS", "").replace(".BO", "")
            symbol = f"{self.settings.fyers_symbol_prefix}{clean_ticker}{self.settings.fyers_symbol_suffix}"

        data = {
            "symbol": symbol,
            "resolution": resolution,
            "date_format": "1",  # 1: yyyy-mm-dd
            "range_from": str(start),
            "range_to": str(end),
            "cont_flag": "1"
        }

        try:
            response = self.client.history(data=data)
            if response.get("s") != "ok":
                logger.warning("Fyers history fetch failed for %s: %s", symbol, response.get("message"))
                return None

            candles = response.get("candles", [])
            if not candles:
                return None

            # Fyers returns [timestamp, open, high, low, close, volume]
            # Timestamp is epoch for intraday, but might be different for daily?
            # Doc says: "timestamp": 1618425000 (Epoch)
            
            df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
            
            # Convert timestamp to datetime
            # Note: Fyers timestamps are in seconds (usually) but sometimes milliseconds?
            # v3 docs say seconds for history.
            # Let's check the first value magnitude.
            if not df.empty:
                first_ts = df["timestamp"].iloc[0]
                unit = 's'
                if first_ts > 10000000000: # > 10 billion, likely ms
                    unit = 'ms'
                
                # Localize to IST if needed, but for now just UTC or naive
                df["date"] = pd.to_datetime(df["timestamp"], unit=unit).dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
                df = df.set_index("date")
                df = df.drop(columns=["timestamp"])
                
                # Ensure columns are float
                cols = ["open", "high", "low", "close", "volume"]
                df[cols] = df[cols].apply(pd.to_numeric)
                
                return df

        except Exception as e:
            logger.error("Fyers API error for %s: %s", symbol, e)
            return None
