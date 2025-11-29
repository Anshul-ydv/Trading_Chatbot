import asyncio
import json
import random
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router as api_router
from .data.fetchers import fetch_ohlcv
from .utils import get_logger, read_tickers

logger = get_logger(__name__)

# Simple connection manager for WebSockets
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

async def poll_prices():
    """Background task to fetch real ticker updates for the UI."""
    while True:
        # Reload tickers every cycle to pick up new additions
        try:
            tickers = read_tickers(limit=20)
        except FileNotFoundError:
            tickers = ["NIFTY50"]

        for ticker in tickers:
            try:
                # Fetch latest 1-day candle to get real price
                # In a real high-freq app, we'd use a lighter weight call or websocket stream
                # But for this demo, we can reuse fetch_ohlcv with a short range
                end = datetime.now().date()
                start = end - timedelta(days=5)
                df = fetch_ohlcv(ticker, start=start, end=end, use_cache=False)
                
                if df is not None and not df.empty:
                    latest = df.iloc[-1]
                    # Calculate change from previous close if available
                    change = 0.0
                    if len(df) > 1:
                        prev_close = df.iloc[-2]['close']
                        change = ((latest['close'] - prev_close) / prev_close) * 100
                    
                    payload = {
                        "symbol": ticker,
                        "ltp": round(float(latest['close']), 2),
                        "volume": int(latest['volume']),
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "change": round(float(change), 2),
                    }
                    await manager.broadcast(json.dumps(payload))
            except Exception as e:
                logger.error(f"Error fetching update for {ticker}: {e}")
                
        await asyncio.sleep(10) # Poll every 10s for faster updates


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting background poller...")
    asyncio.create_task(poll_prices())
    yield
    # Shutdown
    logger.info("Stopping background poller...")

app = FastAPI(title="Trading Chatbot API", lifespan=lifespan)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

@app.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/")
async def root():
    return {"message": "Trading Chatbot API is running"}
