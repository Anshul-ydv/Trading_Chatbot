# Trading Chatbot (Full Stack)

A comprehensive trading research platform featuring a React frontend, FastAPI backend, real-time data simulation, and RAG-based chat assistance.

## Architecture

- **Frontend**: React + Vite + Tailwind CSS (Dashboard, Charts, Chat).
- **Backend**: FastAPI (REST + WebSockets).
- **Analysis**: TA/FA engines, Strategy ranking, RAG Chat Agent.
- **Data**: yfinance (historical), Caching (Parquet).

## Quick Start (Local)

### 1. Backend
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173 to view the dashboard.

## Features

- **Live Dashboard**: Real-time price updates via WebSockets.
- **Strategy Screener**: Filter stocks by Breakout, Swing, or Intraday strategies.
- **AI Chat**: Ask questions about specific tickers (e.g., "Why is RELIANCE bullish?").
- **Interactive Charts**: (Placeholder for Lightweight Charts integration).

## Docker Support

Build and run the entire stack:
```bash
docker-compose up --build
```


