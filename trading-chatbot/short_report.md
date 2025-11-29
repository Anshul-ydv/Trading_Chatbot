# Trading Chatbot — Short Report

Reference plan: `/mnt/data/PLAN1.pdf`

## 1. Architecture snapshot

```
CLI / Notebook entrypoints
        │
        ▼
config.py → utils.py → data.fetchers ↔ data.cache
        │                    │
        │                    └─ data.screener_scraper (FA sample / live)
        ▼
 ta_engine.py ──▶ strategy_engine.py ◀── fa_engine.py
        │                        │
        ▼                        ▼
  rag_index.py ──▶ chat_agent.py ──▶ fyers_integration.py (optional)
```

* `data.fetchers` pulls NSE data (or deterministic synthetic fallback) and always writes parquet caches under `data/cache/raw` for reproducibility.
* `ta_engine` computes SMA/EMA/RSI/MACD/ATR plus breakout/pattern signals, returning typed `Signal` objects.
* `fa_engine` wraps Screener-style ratios (offline JSON or live scrape) and produces `FundamentalSummary` objects with quantitative score + qualitative strengths/risks.
* `strategy_engine` mixes TA + FA + volatility heuristics to derive Breakout/Swing/Intraday scores along with entry/stop/target proposals.
* `rag_index` keeps embeddings for prior analyses/news (Sentence-Transformers if installed, TF-IDF fallback otherwise). `chat_agent` pulls the highest-similarity snippets to ground the final explanation with a safety disclaimer.
* `fyers_integration` is a thin REST helper ready for paper trades once keys are pasted into `.env`.

## 2. Strategies & parameters

| Strategy  | TA weight | FA weight | Notes |
|-----------|-----------|-----------|-------|
| Breakout  | 0.6       | 0.4       | Requires price > prior high + 20% volume surge; ATR-based stop at max(1.5×ATR, 10% buffer).
| Swing     | 0.5       | 0.5       | Prefers mixed signals; entry slightly inside current close to mimic pullback fills.
| Intraday  | 0.5       | 0.5       | Uses same scaffolding but with tighter entry/stop for day trades.

Fundamental scoring weights: ROE (25%), P/E (20%, inverse scaled), D/E (15%, inverse), Sales growth (20%), Profit growth (20%). All metrics normalize to 0–100 before weighted aggregation.

## 3. Assumptions & limitations

1. **Data availability**: Sample fundamentals in `data/sample_fundamentals.json` stand in for Screener.in responses when offline. Update this file or enable network access with `ALLOW_SCREENER_HTTP=1`.
2. **Indicators**: `pandas_ta` is not required; all indicators are implemented manually to keep dependencies light and inspection-friendly.
3. **RAG storage**: Current store is a JSON file + numpy vectors. Swap with FAISS/SQLite if larger corpora are needed.
4. **LLM usage**: The chat agent outputs deterministic templates until an `OPENAI_API_KEY` (or compatible endpoint) is configured. Professors can grade without LLM credentials.
5. **Trading**: `fyers_integration` defaults to paper mode and logs orders locally. Live endpoints only fire when both FYERS keys exist and `live=True` is passed.

## 4. Reproducibility & grading checklist

- Run `pytest` — validates TA, FA, and caching logic.
- Execute `python -m src.main screen --strategy breakout` — prints ranked picks using cached/synthetic data.
- Open `notebooks/demo.ipynb` — demonstrates the exact pipeline imported from `src/` modules, finishing with “how to run” instructions.
- Review `assets/example_charts/` and drop three Plotly exports for submission.

## 5. Files to inspect first

1. `src/data/fetchers.py` — caching, synthetic fallback, and logging.
2. `src/ta_engine.py` — indicator/pattern definitions with docstrings.
3. `src/fa_engine.py` — Screener wrapper + scoring heuristics.
4. `src/strategy_engine.py` — scoring matrix and rationale builder.
5. `src/chat_agent.py` — RAG prompt assembly and final messaging.

## 6. Next improvements (optional)

- Add FastAPI surface in `src/main.py` for REST chat endpoints.
- Swap JSON RAG store with FAISS disk index for large corpora.
- Extend `tests/` with mocked HTTP responses for the Screener and FYERS clients.
