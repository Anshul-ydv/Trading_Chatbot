import pandas as pd

from src.ta_engine import compute_indicators, detect_breakout


def _sample_df() -> pd.DataFrame:
    idx = pd.date_range("2023-01-01", periods=60, freq="B")
    base = pd.Series(range(60), index=idx, dtype=float) + 100
    df = pd.DataFrame(index=idx)
    df["open"] = base
    df["close"] = base + 1
    df["high"] = df["close"] + 0.5
    df["low"] = df["open"] - 0.5
    df["volume"] = 1_000_000
    return df


def test_compute_indicators_adds_expected_columns():
    enriched = compute_indicators(_sample_df())
    for column in ["sma_20", "ema_20", "rsi_14", "macd", "atr_14"]:
        assert column in enriched.columns


def test_detect_breakout_flags_new_high():
    df = _sample_df()
    df.loc[df.index[-1], "close"] = df["high"].max() + 5
    df.loc[df.index[-1], "high"] = df["close"].max() + 5
    df.loc[df.index[-1], "volume"] = 2_000_000
    signal = detect_breakout("TEST", compute_indicators(df))
    assert signal is not None
    assert signal.indicator == "breakout"
