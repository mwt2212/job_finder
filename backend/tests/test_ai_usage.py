import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from ai_usage import estimate_cost, estimate_cost_range


def test_estimate_cost_applies_cached_input_rate():
    pricing = {
        "models": {
            "gpt-test": {
                "input": 2.0,
                "cached_input": 0.5,
                "output": 8.0,
            }
        }
    }

    cost = estimate_cost(
        pricing=pricing,
        model="gpt-test",
        input_tokens=1_000_000,
        output_tokens=500_000,
        cached_input_tokens=250_000,
    )

    assert cost == 5.625


def test_estimate_cost_range_brackets_point_estimate():
    pricing = {
        "models": {
            "gpt-test": {
                "input": 1.0,
                "cached_input": 1.0,
                "output": 1.0,
            }
        }
    }

    point = estimate_cost(pricing, "gpt-test", input_tokens=10_000, output_tokens=5_000)
    bounds = estimate_cost_range(pricing, "gpt-test", input_tokens=10_000, output_tokens=5_000, pct=0.2)

    assert bounds["low"] is not None
    assert bounds["high"] is not None
    assert bounds["low"] <= point <= bounds["high"]
