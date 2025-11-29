from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .data.screener_scraper import scrape_screener
from .utils import get_logger

logger = get_logger(__name__)

FUNDAMENTAL_WEIGHTS = {
    "roe": 0.25,
    "pe_ratio": 0.2,
    "debt_to_equity": 0.15,
    "sales_growth_3y": 0.2,
    "profit_growth_3y": 0.2,
}


@dataclass(slots=True)
class FundamentalSummary:
    ticker: str
    metrics: Dict[str, float]
    score: float
    strengths: List[str]
    risks: List[str]


def evaluate_fundamentals(ticker: str) -> FundamentalSummary:
    metrics = scrape_screener(ticker)
    score = _score_metrics(metrics)
    strengths, risks = _qualitative_flags(metrics)
    return FundamentalSummary(
        ticker=ticker,
        metrics=metrics,
        score=round(score, 2),
        strengths=strengths,
        risks=risks,
    )


def _score_metrics(metrics: Dict[str, float]) -> float:
    total = 0.0
    for key, weight in FUNDAMENTAL_WEIGHTS.items():
        value = metrics.get(key)
        if value is None:
            continue
        normalized = _normalize(key, value)
        total += normalized * weight
    return min(max(total, 0), 100)


def _normalize(key: str, value: float) -> float:
    match key:
        case "roe" | "sales_growth_3y" | "profit_growth_3y":
            return min(value, 30) / 30 * 100
        case "pe_ratio":
            return 100 - min(value, 40) / 40 * 100
        case "debt_to_equity":
            return 100 - min(value, 2) / 2 * 100
        case _:
            return 50


def _qualitative_flags(metrics: Dict[str, float]) -> tuple[List[str], List[str]]:
    strengths: List[str] = []
    risks: List[str] = []
    if metrics.get("roe", 0) > 18:
        strengths.append("ROE above 18% indicates efficient capital use")
    if metrics.get("profit_growth_3y", 0) > 15:
        strengths.append("Profit growth trend is strong")
    if metrics.get("pe_ratio", 0) < 20:
        strengths.append("Valuation under 20x earnings")
    if metrics.get("debt_to_equity", 0) > 1:
        risks.append("High leverage could pressure cash flows")
    if metrics.get("sales_growth_3y", 0) < 5:
        risks.append("Sales growth has been muted")
    return strengths, risks
