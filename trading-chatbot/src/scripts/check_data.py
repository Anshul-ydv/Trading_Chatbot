import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.data.fetchers import fetch_ohlcv
from src.config import get_settings
from datetime import date, timedelta

def check_data_source():
    settings = get_settings()
    print(f"Settings: REQUIRE_LIVE_DATA={settings.require_live_data}, ALLOW_SYNTHETIC_DATA={settings.allow_synthetic_data}")
    
    ticker = "RELIANCE"
    end = date.today()
    start = end - timedelta(days=5)
    
    print(f"\nFetching data for {ticker}...")
    try:
        df = fetch_ohlcv(ticker, start, end, use_cache=False)
        if df is not None and not df.empty:
            print("✅ Data fetched successfully.")
            print(df.head())
            
            # Check if it looks synthetic (volume is random integer in range 1M-5M, prices around 100 + random)
            # Synthetic logic: prices = np.cumsum(...) + 100. 
            # Real Reliance price is ~2500-3000.
            last_close = df.iloc[-1]['close']
            print(f"Last Close: {last_close}")
            
            if last_close < 500: # Reliance is definitely > 500
                print("⚠️ WARNING: Data looks synthetic (Price too low for Reliance).")
            else:
                print("✅ Data looks real.")
        else:
            print("❌ Data fetch returned empty.")
    except Exception as e:
        print(f"❌ Data fetch failed: {e}")

if __name__ == "__main__":
    check_data_source()
