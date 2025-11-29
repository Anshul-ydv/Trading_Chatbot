import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.fyers_client import FyersClient
from src.config import get_settings
from datetime import date, timedelta

def test_fyers_connection():
    print("Testing Fyers API v3 Integration...")
    settings = get_settings()
    
    if not settings.fyers_client_id or not settings.fyers_access_token:
        print("❌ Fyers credentials missing in .env file.")
        print("Please set FYERS_CLIENT_ID and FYERS_ACCESS_TOKEN.")
        return

    client = FyersClient(settings)
    
    if not client.configured():
        print("❌ Fyers client failed to initialize.")
        return

    print("✅ Fyers client initialized.")
    
    # Test fetching data
    ticker = "NSE:SBIN-EQ"
    end = date.today()
    start = end - timedelta(days=5)
    
    print(f"Fetching history for {ticker} from {start} to {end}...")
    df = client.fetch_history(ticker, start, end, timeframe="1d")
    
    if df is not None and not df.empty:
        print("✅ Data fetch successful!")
        print(df.head())
    else:
        print("⚠️ Data fetch returned empty or failed. Check permissions or symbol format.")

if __name__ == "__main__":
    test_fyers_connection()
