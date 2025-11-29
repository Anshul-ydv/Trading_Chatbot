from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from .utils import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class Signal:
    ticker: str
    indicator: str
    direction: str
    score: float
    details: dict[str, float]


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["sma_20"] = out["close"].rolling(window=20).mean()
    out["ema_20"] = out["close"].ewm(span=20, adjust=False).mean()
    out["ema_21"] = out["close"].ewm(span=21, adjust=False).mean()
    out["ema_50"] = out["close"].ewm(span=50, adjust=False).mean()
    out["rsi_14"] = _rsi(out["close"], period=14)
    macd, signal = _macd(out["close"])
    out["macd"] = macd
    out["macd_signal"] = signal
    out["atr_14"] = _atr(out)
    
    # Bollinger Bands
    out["bb_upper"], out["bb_lower"] = _bollinger_bands(out["close"])
    
    # Stochastic Oscillator
    out["stoch_k"], out["stoch_d"] = _stochastic(out)
    
    # Simple Support/Resistance (20-day High/Low)
    out["resistance"] = out["high"].rolling(window=20).max()
    out["support"] = out["low"].rolling(window=20).min()
    
    return out.dropna()

def _bollinger_bands(series: pd.Series, window: int = 20, num_std: int = 2) -> tuple[pd.Series, pd.Series]:
    sma = series.rolling(window=window).mean()
    std = series.rolling(window=window).std()
    upper = sma + (std * num_std)
    lower = sma - (std * num_std)
    return upper, lower

def _stochastic(df: pd.DataFrame, k_window: int = 14, d_window: int = 3) -> tuple[pd.Series, pd.Series]:
    low_min = df["low"].rolling(window=k_window).min()
    high_max = df["high"].rolling(window=k_window).max()
    k = 100 * ((df["close"] - low_min) / (high_max - low_min))
    d = k.rolling(window=d_window).mean()
    return k, d


def detect_breakout(
    ticker: str,
    df: pd.DataFrame,
    lookback: int = 20,
    volume_factor: float = 1.5,
) -> Optional[Signal]:
    if df.empty:
        return None
    recent = df.tail(lookback)
    current = recent.iloc[-1]
    prior_high = recent["high"][:-1].max()
    prior_volume = recent["volume"][:-1].mean()
    if current["close"] > prior_high and current["volume"] >= prior_volume * volume_factor:
        score = min((current["close"] - prior_high) / prior_high * 100, 10)
        return Signal(
            ticker=ticker,
            indicator="breakout",
            direction="bullish",
            score=round(score, 2),
            details={
                "close": float(current["close"]),
                "prior_high": float(prior_high),
                "volume_factor": round(current["volume"] / prior_volume, 2) if prior_volume else 0,
            },
        )
    return None


def detect_double_top_bottom(ticker: str, df: pd.DataFrame, lookback: int = 60) -> Optional[Signal]:
    if len(df) < lookback:
        return None
    window = df.tail(lookback)
    highs = window["high"].to_numpy()
    lows = window["low"].to_numpy()
    top_idx = np.argsort(highs)[-2:]
    bottom_idx = np.argsort(lows)[:2]
    top_diff = abs(highs[top_idx[0]] - highs[top_idx[1]])
    bottom_diff = abs(lows[bottom_idx[0]] - lows[bottom_idx[1]])
    if top_diff < window["close"].mean() * 0.01:
        return Signal(
            ticker=ticker,
            indicator="double_top",
            direction="bearish",
            score=6.0,
            details={"tops_diff": float(top_diff)},
        )
    if bottom_diff < window["close"].mean() * 0.01:
        return Signal(
            ticker=ticker,
            indicator="double_bottom",
            direction="bullish",
            score=6.0,
            details={"bottoms_diff": float(bottom_diff)},
        )
    return None


def _rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    avg_loss = avg_loss.replace(0, np.nan)
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(100)


def _macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[pd.Series, pd.Series]:
    fast_ema = series.ewm(span=fast, adjust=False).mean()
    slow_ema = series.ewm(span=slow, adjust=False).mean()
    macd = fast_ema - slow_ema
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd, signal_line


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.rolling(window=period).mean()
