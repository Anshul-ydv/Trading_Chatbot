from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

import pandas as pd

from .fa_engine import FundamentalSummary
from .ta_engine import Signal
from .utils import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class StrategyResult:
    ticker: str
    strategy: str
    score: float
    entry: float
    stop: float
    target: float
    reasons: List[str]


def score_for_strategy(
    ticker: str,
    strategy: str,
    df: pd.DataFrame,
    fundamentals: FundamentalSummary,
    signals: Iterable[Signal] | None = None,
) -> StrategyResult:
    close = float(df["close"].iloc[-1])
    atr = float(df.get("atr_14", pd.Series([close * 0.02])).iloc[-1])
    
    # Enhanced TA Scoring
    ta_score = _score_from_signals(strategy, signals or [])
    
    # Add indicator-based scoring
    rsi = float(df["rsi_14"].iloc[-1]) if "rsi_14" in df else 50
    macd = float(df["macd"].iloc[-1]) if "macd" in df else 0
    macd_sig = float(df["macd_signal"].iloc[-1]) if "macd_signal" in df else 0
    
    if strategy == "swing":
        # Swing favors RSI oversold/overbought reversals or trend continuation
        if 40 < rsi < 60: ta_score += 10
        if macd > macd_sig: ta_score += 10
    elif strategy == "breakout":
        # Breakout favors momentum
        if rsi > 60: ta_score += 10
        if macd > macd_sig and macd > 0: ta_score += 10
        
    ta_score = min(ta_score, 100)
    
    fa_score = fundamentals.score
    
    # Weights from plan: TA 60%, FA 30%, Liquidity 10% (simplified here to TA/FA split)
    weight_ta, weight_fa = (0.6, 0.4) if strategy == "breakout" else (0.5, 0.5)
    combined = ta_score * weight_ta + fa_score * weight_fa
    
    # Entry/Stop/Target rules from plan
    if strategy == "breakout":
        # Entry: next open or close after breakout (simplified to current close for ranking)
        entry = close 
        # Stop: consolidation low or ATR*1.5
        stop = close - 1.5 * atr
        # Target: measured move or 2*risk
        target = close + 3.0 * atr
    elif strategy == "swing":
        # Pullback entry near EMA
        entry = float(df["ema_20"].iloc[-1]) if "ema_20" in df else close * 0.98
        stop = entry - 2.0 * atr
        target = entry + 4.0 * atr
    else: # Day / Intraday
        entry = close
        stop = close - 1.0 * atr
        target = close + 2.0 * atr

    reasons = _build_reasons(strategy, ta_score, fa_score, fundamentals, df)
    return StrategyResult(
        ticker=ticker,
        strategy=strategy,
        score=round(combined, 2),
        entry=round(entry, 2),
        stop=round(stop, 2),
        target=round(target, 2),
        reasons=reasons,
    )


def _score_from_signals(strategy: str, signals: Iterable[Signal]) -> float:
    relevant = [s for s in signals if s.indicator in {"breakout", "double_top", "double_bottom"}]
    if not relevant:
        return 40.0
    best = max(relevant, key=lambda s: s.score)
    bonus = 10 if strategy == "breakout" and best.indicator == "breakout" else 0
    return min(best.score * 10 + bonus, 100)


def _build_reasons(
    strategy: str,
    ta_score: float,
    fa_score: float,
    fundamentals: FundamentalSummary,
    df: pd.DataFrame,
) -> List[str]:
    reasons = [f"TA score {ta_score:.1f}/100", f"FA score {fa_score:.1f}/100"]
    
    # Add specific indicator reasons
    rsi = float(df["rsi_14"].iloc[-1]) if "rsi_14" in df else 50
    if rsi > 70: reasons.append("RSI Overbought")
    elif rsi < 30: reasons.append("RSI Oversold")
    
    macd = float(df["macd"].iloc[-1]) if "macd" in df else 0
    macd_sig = float(df["macd_signal"].iloc[-1]) if "macd_signal" in df else 0
    if macd > macd_sig: reasons.append("MACD Bullish Crossover")
    
    if fundamentals.strengths:
        reasons.append(f"Strengths: {', '.join(fundamentals.strengths[:2])}")
    if fundamentals.risks:
        reasons.append(f"Watch: {', '.join(fundamentals.risks[:1])}")
    reasons.append(f"Strategy template: {strategy}")
    return reasons


def rank_strategies(
    ticker: str,
    df: pd.DataFrame,
    fundamentals: FundamentalSummary,
    signals: Iterable[Signal] | None = None,
    strategies: Iterable[str] | None = None,
) -> List[StrategyResult]:
    strategies = list(strategies or ["breakout", "swing", "intraday"])
    results = [
        score_for_strategy(ticker, strategy, df, fundamentals, signals=signals)
        for strategy in strategies
    ]
    return sorted(results, key=lambda r: r.score, reverse=True)
