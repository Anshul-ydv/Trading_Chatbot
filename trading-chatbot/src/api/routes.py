from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel

from ..data.fetchers import fetch_ohlcv
from ..ta_engine import compute_indicators, detect_breakout, detect_double_top_bottom
from ..fa_engine import evaluate_fundamentals
from ..strategy_engine import rank_strategies
from ..chat_agent import ChatAgent
from ..utils import read_tickers
from datetime import date, timedelta

router = APIRouter()

class StrategyResponse(BaseModel):
    ticker: str
    strategy: str
    score: float
    entry: float
    stop: float
    target: float
    reasons: List[str]

class ChatRequest(BaseModel):
    ticker: str
    strategy: Optional[str] = None
    question: Optional[str] = None

class ChatResponse(BaseModel):
    response: str

class AddTickerRequest(BaseModel):
    ticker: str

@router.post("/tickers")
async def add_ticker(request: AddTickerRequest):
    ticker = request.ticker.upper().strip()
    # Append to tickers.csv
    # We need to find the path. Using utils.read_tickers logic in reverse or just appending
    from ..config import get_settings
    import csv
    
    settings = get_settings()
    csv_path = settings.tickers_file
    
    # Check if exists
    existing = read_tickers()
    if ticker in existing:
        return {"message": f"{ticker} already exists"}
        
    with open(csv_path, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([ticker, "NSE"]) # Assuming NSE for now
        
    return {"message": f"Added {ticker}"}

@router.delete("/tickers/{ticker}")
async def remove_ticker(ticker: str):
    ticker = ticker.upper().strip()
    from ..config import get_settings
    import csv
    
    settings = get_settings()
    csv_path = settings.tickers_file
    
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail="Ticker file not found")
        
    # Read all tickers
    rows = []
    found = False
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            if row["ticker"].strip().upper() == ticker:
                found = True
                continue
            rows.append(row)
            
    if not found:
        raise HTTPException(status_code=404, detail="Ticker not found")
        
    # Write back
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        
    return {"message": f"Removed {ticker}"}

class Candle(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    ema_21: Optional[float] = None
    support: Optional[float] = None
    resistance: Optional[float] = None

@router.get("/history/{ticker}", response_model=List[Candle])
async def get_history(ticker: str, days: int = 180):
    start = date.today() - timedelta(days=days)
    df = fetch_ohlcv(ticker, start=start)
    
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail="No data found")
        
    # Compute indicators for the chart
    enriched = compute_indicators(df)
    
    # Convert DataFrame to list of dicts for lightweight-charts
    candles = []
    # We iterate over the enriched df to get indicators
    # Note: compute_indicators drops NaNs, so we might lose the first few candles.
    # If we want all candles, we should merge or be careful.
    # For charting, it's okay to show what we have.
    
    for idx, row in enriched.iterrows():
        candles.append(Candle(
            time=idx.strftime("%Y-%m-%d"),
            open=row['open'],
            high=row['high'],
            low=row['low'],
            close=row['close'],
            volume=int(row['volume']),
            ema_21=row.get('ema_21'),
            support=row.get('support'),
            resistance=row.get('resistance')
        ))
    return candles

@router.get("/screen", response_model=List[StrategyResponse])
async def screen_stocks(
    strategy: Optional[str] = None,
    limit: int = 10,
    lookback_days: int = 180
):
    tickers = read_tickers(limit=limit)
    results = []
    
    start = date.today() - timedelta(days=lookback_days)
    
    for ticker in tickers:
        try:
            df = fetch_ohlcv(ticker, start=start)
            if df is None or df.empty:
                continue
                
            enriched = compute_indicators(df)
            signals = []
            for detector in [detect_breakout, detect_double_top_bottom]:
                sig = detector(ticker, enriched)
                if sig:
                    signals.append(sig)
            
            fundamentals = evaluate_fundamentals(ticker)
            strategies = rank_strategies(ticker, enriched, fundamentals, signals=signals)
            
            for s in strategies:
                if strategy and s.strategy.lower() != strategy.lower():
                    continue
                
                results.append(StrategyResponse(
                    ticker=ticker,
                    strategy=s.strategy,
                    score=s.score,
                    entry=s.entry,
                    stop=s.stop,
                    target=s.target,
                    reasons=s.reasons
                ))
        except Exception as e:
            print(f"Error processing {ticker}: {e}")
            continue
            
    return sorted(results, key=lambda x: x.score, reverse=True)

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        agent = ChatAgent()
        
        # We need to fetch context first
        start = date.today() - timedelta(days=180)
        df = fetch_ohlcv(request.ticker, start=start)
        
        if df is None or df.empty:
            return ChatResponse(response=f"I couldn't retrieve data for {request.ticker}. Please check the ticker symbol or try again later.")

        enriched = compute_indicators(df)
        fundamentals = evaluate_fundamentals(request.ticker)
        
        # Find the best strategy if not provided
        strategies = rank_strategies(request.ticker, enriched, fundamentals)
        
        if not strategies:
             return ChatResponse(response=f"I analyzed {request.ticker} but couldn't find a clear trading strategy at this moment.")

        chosen_strategy = next((s for s in strategies if s.strategy == request.strategy), strategies[0])
        
        response_text = agent.explain(
            request.ticker, 
            chosen_strategy, 
            fundamentals, 
            user_question=request.question
        )
        
        return ChatResponse(response=response_text)
    except Exception as e:
        print(f"Chat error: {e}")
        return ChatResponse(response=f"I encountered an error analyzing {request.ticker}. Please try again.")
