from src.fa_engine import evaluate_fundamentals


def test_evaluate_fundamentals_loads_sample_data():
    summary = evaluate_fundamentals("RELIANCE")
    assert summary.metrics["roe"] > 0
    assert 0 <= summary.score <= 100
