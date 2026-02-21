import json
from typing import Any, Callable, Dict, Optional

from ai_usage import (
    estimate_cost,
    estimate_cost_range,
    estimate_tokens,
    get_avg_output_tokens,
    load_pricing,
)


def _ai_eval_base_prompt(resume: Dict[str, Any], prefs: Dict[str, Any]) -> str:
    return f"""
You are evaluating job fit for a candidate. Be strict and practical.

Candidate profile (truth source):
{json.dumps(resume, ensure_ascii=False)}

Preferences profile:
{json.dumps(prefs, ensure_ascii=False)}

Jobs to evaluate (array, in order):
[]

Rules:
- Candidate strongly prefers minimal cold calling. If outbound-heavy or sales-centric, cold_call_risk=high and next_action=skip.
- Must be full-time. If unclear, employment_type_ok=false and next_action=review_manually.
- Hybrid preferred; remote acceptable; onsite only if standout.
- Upward mobility: favor analyst/ops/compliance/data-adjacent roles with transferable skills.
- Include job_summary: 1-2 sentences on what the role is about.
Return ONLY a JSON array that matches the schema, in the same order as the jobs list.
""".strip()


def estimate_ai_eval(
    size: str,
    size_presets: Dict[str, Dict[str, int]],
    resume: Dict[str, Any],
    prefs: Dict[str, Any],
    model_override: Optional[str] = None,
    batch_size: int = 5,
    estimate_tokens_fn: Callable[[str], int] = estimate_tokens,
    get_avg_output_tokens_fn: Callable[[str, str, int], int] = get_avg_output_tokens,
    load_pricing_fn: Callable[[], Dict[str, Any]] = load_pricing,
    estimate_cost_fn: Callable[[Dict[str, Any], str, int, int], Optional[float]] = estimate_cost,
    estimate_cost_range_fn: Callable[[Dict[str, Any], str, int, int], Dict[str, Any]] = estimate_cost_range,
) -> Dict[str, Any]:
    cfg = size_presets.get(size)
    if not cfg:
        raise ValueError("Invalid size")

    final_top = int(cfg.get("final_top") or 0)
    job_count = final_top
    avg_desc_chars = 4800

    base_prompt = _ai_eval_base_prompt(resume, prefs)
    base_tokens = estimate_tokens_fn(base_prompt)
    sample_job = {
        "url": "https://example.com",
        "title": "Example Title",
        "company": "Example Co",
        "workplace": "remote",
        "posted": "1 day ago",
        "salary_hint": "",
        "description": "x" * avg_desc_chars,
    }
    per_job_tokens = estimate_tokens_fn(json.dumps(sample_job, ensure_ascii=False))
    batches = max(1, (job_count + batch_size - 1) // batch_size)
    input_tokens_est = batches * base_tokens + job_count * per_job_tokens

    model = (model_override or "").strip() or "gpt-4.1-mini"
    output_per_job = get_avg_output_tokens_fn("ai_eval", model, default=450)
    output_tokens_est = output_per_job * job_count

    pricing = load_pricing_fn()
    cost_est = estimate_cost_fn(pricing, model, input_tokens_est, output_tokens_est) if pricing else None
    cost_range = estimate_cost_range_fn(pricing, model, input_tokens_est, output_tokens_est) if pricing else {"low": None, "high": None}

    return {
        "model": model,
        "jobs_est": job_count,
        "jobs_max": final_top,
        "input_tokens_est": input_tokens_est,
        "output_tokens_est": output_tokens_est,
        "cost_est": cost_est,
        "cost_est_range": cost_range,
        "avg_desc_chars": avg_desc_chars,
        "batch_size": batch_size,
    }


def estimate_ai_eval_from_jobs(
    *,
    total_jobs: int,
    job_count: int,
    avg_desc_chars: int,
    resume: Dict[str, Any],
    prefs: Dict[str, Any],
    model_override: Optional[str] = None,
    batch_size: int = 5,
    estimate_tokens_fn: Callable[[str], int] = estimate_tokens,
    get_avg_output_tokens_fn: Callable[[str, str, int], int] = get_avg_output_tokens,
    load_pricing_fn: Callable[[], Dict[str, Any]] = load_pricing,
    estimate_cost_fn: Callable[[Dict[str, Any], str, int, int], Optional[float]] = estimate_cost,
    estimate_cost_range_fn: Callable[[Dict[str, Any], str, int, int], Dict[str, Any]] = estimate_cost_range,
) -> Dict[str, Any]:
    base_prompt = _ai_eval_base_prompt(resume, prefs)
    base_tokens = estimate_tokens_fn(base_prompt)
    sample_job = {
        "url": "https://example.com",
        "title": "Example Title",
        "company": "Example Co",
        "workplace": "remote",
        "posted": "1 day ago",
        "salary_hint": "",
        "description": "x" * avg_desc_chars,
    }
    per_job_tokens = estimate_tokens_fn(json.dumps(sample_job, ensure_ascii=False))
    batches = (job_count + batch_size - 1) // batch_size if job_count > 0 else 0
    input_tokens_est = batches * base_tokens + job_count * per_job_tokens

    model = (model_override or "").strip() or "gpt-4.1-mini"
    output_per_job = get_avg_output_tokens_fn("ai_eval", model, default=450)
    output_tokens_est = output_per_job * job_count

    pricing = load_pricing_fn()
    cost_est = estimate_cost_fn(pricing, model, input_tokens_est, output_tokens_est) if pricing else None
    cost_range = estimate_cost_range_fn(pricing, model, input_tokens_est, output_tokens_est) if pricing else {"low": None, "high": None}

    return {
        "model": model,
        "jobs_est": job_count,
        "jobs_max": total_jobs,
        "jobs_total": total_jobs,
        "skipped_jobs_est": max(0, total_jobs - job_count),
        "input_tokens_est": input_tokens_est,
        "output_tokens_est": output_tokens_est,
        "cost_est": cost_est,
        "cost_est_range": cost_range,
        "avg_desc_chars": avg_desc_chars,
        "batch_size": batch_size,
    }
