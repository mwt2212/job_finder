import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

BASE_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"
PRICING_PATH = BASE_DIR / "ai_pricing.json"
USAGE_LOG_PATH = ARTIFACTS_DIR / "ai_usage.jsonl"
TOTALS_PATH = ARTIFACTS_DIR / "ai_usage_totals.json"
LEGACY_TOTALS_PATH = BASE_DIR / "ai_usage_totals.json"


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))


def load_pricing() -> Dict[str, Any]:
    if PRICING_PATH.exists():
        return json.loads(PRICING_PATH.read_text(encoding="utf-8"))
    return {"models": {}}


def get_model_pricing(pricing: Dict[str, Any], model: str) -> Optional[Dict[str, Any]]:
    return (pricing.get("models") or {}).get(model)


def estimate_cost(
    pricing: Dict[str, Any],
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
) -> Optional[float]:
    info = get_model_pricing(pricing, model)
    if not info:
        return None
    input_price = float(info.get("input", 0.0))
    cached_price = float(info.get("cached_input", input_price))
    output_price = float(info.get("output", 0.0))
    cached = max(0, int(cached_input_tokens))
    uncached = max(0, int(input_tokens) - cached)
    cost = (uncached / 1_000_000) * input_price
    cost += (cached / 1_000_000) * cached_price
    cost += (int(output_tokens) / 1_000_000) * output_price
    return round(cost, 6)


def estimate_range(value: int, pct: float = 0.2) -> Dict[str, int]:
    if value <= 0:
        return {"low": 0, "high": 0}
    low = max(0, int(math.floor(value * (1.0 - pct))))
    high = max(0, int(math.ceil(value * (1.0 + pct))))
    return {"low": low, "high": high}


def estimate_cost_range(
    pricing: Dict[str, Any],
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
    pct: float = 0.2,
) -> Dict[str, Optional[float]]:
    in_range = estimate_range(input_tokens, pct)
    out_range = estimate_range(output_tokens, pct)
    low = estimate_cost(pricing, model, in_range["low"], out_range["low"], cached_input_tokens)
    high = estimate_cost(pricing, model, in_range["high"], out_range["high"], cached_input_tokens)
    return {"low": low, "high": high}


def _load_totals() -> Dict[str, Any]:
    if TOTALS_PATH.exists():
        return json.loads(TOTALS_PATH.read_text(encoding="utf-8"))
    if LEGACY_TOTALS_PATH.exists():
        return json.loads(LEGACY_TOTALS_PATH.read_text(encoding="utf-8"))
    return {
        "estimated": {"input_tokens": 0, "output_tokens": 0, "cost": 0.0},
        "actual": {"input_tokens": 0, "output_tokens": 0, "cached_input_tokens": 0, "cost": 0.0},
        "by_model": {},
        "by_kind": {},
        "last_updated": None,
    }


def _bump_section(section: Dict[str, Any], key: str, value: float) -> None:
    if value is None:
        return
    if key not in section:
        section[key] = 0
    section[key] += value


def _update_totals(totals: Dict[str, Any], entry: Dict[str, Any]) -> None:
    model = entry.get("model") or "unknown"
    kind = entry.get("kind") or "unknown"
    unit_count = int(entry.get("unit_count") or 1)

    est_in = entry.get("input_tokens_est")
    est_out = entry.get("output_tokens_est")
    est_cost = entry.get("cost_est")
    act_in = entry.get("input_tokens")
    act_out = entry.get("output_tokens")
    act_cached = entry.get("cached_input_tokens")
    act_cost = entry.get("cost_actual")

    if est_in is not None:
        _bump_section(totals["estimated"], "input_tokens", int(est_in))
    if est_out is not None:
        _bump_section(totals["estimated"], "output_tokens", int(est_out))
    if est_cost is not None:
        _bump_section(totals["estimated"], "cost", float(est_cost))

    if act_in is not None:
        _bump_section(totals["actual"], "input_tokens", int(act_in))
    if act_out is not None:
        _bump_section(totals["actual"], "output_tokens", int(act_out))
    if act_cached is not None:
        _bump_section(totals["actual"], "cached_input_tokens", int(act_cached))
    if act_cost is not None:
        _bump_section(totals["actual"], "cost", float(act_cost))

    by_model = totals["by_model"].setdefault(model, {"count": 0, "input_tokens": 0, "output_tokens": 0, "cost": 0.0})
    if act_in is not None:
        by_model["input_tokens"] += int(act_in)
    if act_out is not None:
        by_model["output_tokens"] += int(act_out)
    if act_cost is not None:
        by_model["cost"] += float(act_cost)
    if act_in is not None or act_out is not None:
        by_model["count"] += unit_count

    by_kind = totals["by_kind"].setdefault(kind, {})
    by_kind_model = by_kind.setdefault(model, {"count": 0, "input_tokens": 0, "output_tokens": 0, "cost": 0.0})
    if act_in is not None:
        by_kind_model["input_tokens"] += int(act_in)
    if act_out is not None:
        by_kind_model["output_tokens"] += int(act_out)
    if act_cost is not None:
        by_kind_model["cost"] += float(act_cost)
    if act_in is not None or act_out is not None:
        by_kind_model["count"] += unit_count

    totals["last_updated"] = datetime.utcnow().isoformat() + "Z"


def log_usage(entry: Dict[str, Any]) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = dict(entry)
    payload["ts"] = datetime.utcnow().isoformat() + "Z"
    USAGE_LOG_PATH.open("a", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False) + "\n")
    totals = _load_totals()
    _update_totals(totals, payload)
    TOTALS_PATH.write_text(json.dumps(totals, ensure_ascii=False, indent=2), encoding="utf-8")


def get_avg_output_tokens(kind: str, model: str, default: int) -> int:
    totals = _load_totals()
    model_stats = (totals.get("by_kind") or {}).get(kind, {}).get(model, {})
    count = int(model_stats.get("count") or 0)
    if count <= 0:
        return default
    output_tokens = int(model_stats.get("output_tokens") or 0)
    return max(1, int(round(output_tokens / count)))
