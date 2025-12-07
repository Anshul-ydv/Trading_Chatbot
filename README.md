# Trading Chatbot

End-to-end trading research app (Indian markets) with FastAPI + React, live quotes, TA/FA screening, strategy ranking, and an LLM-powered RAG chat assistant.

## At a Glance
- **Frontend**: React (Vite) + Tailwind + `lightweight-charts` for TradingView-style charts.
- **Backend**: FastAPI (REST + WebSocket) with background poller.
- **Analysis**: TA engine (EMA/RSI/MACD/Bollinger/Stoch/ATR/Support-Resistance), FA engine (Screener.in → yfinance fallback), strategy scoring (Breakout/Swing/Day), RAG Chat Agent.
- **Data**: yfinance/nsepy + optional Fyers; caching to Parquet.
- **LLM**: OpenAI or local Ollama (configure via `.env`).

## Architecture (Mermaid)
```mermaid
flowchart TD
	subgraph Frontend [Frontend (React)]
		UI[Dashboard & Chat]
		WS[WebSocket Client]
		Chart[Lightweight Charts]
	end

	subgraph Backend [FastAPI]
		API[REST Endpoints]
		WSS[WebSocket Server]
		Poller[Background Poller]
		TA[TA Engine]
		FA[FA Engine]
		Strat[Strategy Engine]
		Chat[Chat Agent]
		RAG[RAG Index]
		LLM[LLM Client]
	end

	subgraph Sources [Data Sources]
		Fy[Fyers]
		NSE[nsepy]
		YF[yfinance]
		Scr[Screener.in]
		News[Google News RSS]
		Cache[Parquet/Cache]
	end

	UI -- REST --> API
	WS <---> WSS
	Chart <-- REST --> API
	API --> TA
	API --> FA
	API --> Strat
	API --> Chat
	Chat --> RAG
	Chat --> LLM
	Poller --> WSS
	Poller --> Fy
	API --> NSE
	API --> YF
	API --> Scr
	API --> News
	API <--> Cache
```

## Data & Indicator Flow
1) Fetch OHLCV (yfinance/nsepy; Fyers for live). Cache to `data/cache/raw/`.
2) `compute_indicators` (EMA 20/21/50, RSI, MACD, ATR, Bollinger, Stoch, Support/Resistance).
3) Strategy scoring (Breakout/Swing/Day) → entry/stop/target + reasons.
4) Fundamentals (Screener.in first, yfinance fallback) → FA score.
5) Chat: retrieve context (TA/FA/News) → build prompt → LLM → Markdown tables/bullets.
6) WebSocket pushes live quotes/updates to the frontend.

## Quick Start (Local)

**Backend**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
# open http://localhost:5173
```

## Docker Compose
```bash
docker-compose up --build
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

## Key Endpoints
- `GET /api/screen?strategy=breakout` — ranked stocks with scores/reasons.
- `GET /api/history/{ticker}` — OHLCV + indicators for chart (includes EMA21/support/resistance).
- `POST /api/chat` — chatbot Q&A (RAG + LLM).
- `POST /api/tickers` / `DELETE /api/tickers/{ticker}` — manage watchlist.

## Configuration
- Copy `.env.example` to `.env` and set: LLM provider/model, Fyers keys (optional), Screener/HTTP flags.
- Tickers: `data/tickers.csv` (mounted via volume in Docker).
- Caching: `data/cache/` is persisted; safe to delete to refetch.

## Testing
```bash
pytest -q
```

## Project Structure (high level)
- `src/` — FastAPI app, TA/FA engines, strategy engine, chat agent, data fetchers.
- `frontend/` — React app (Vite), chart, chat, watchlist.
- `data/` — tickers, cache (Parquet), fundamentals samples.
- `Dockerfile.backend`, `docker-compose.yml` — containerized dev/run.
- `notebooks/` — ad-hoc exploration.

## Notes & Safety
- Educational/demo only — not investment advice.
- .env should never be committed; ensure secrets stay local.


