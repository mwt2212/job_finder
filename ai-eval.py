import json
import time
from pathlib import Path
from typing import Any, Dict, Tuple

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover - fallback for legacy SDKs
    OpenAI = None  # type: ignore

from ai_usage import (
    estimate_cost,
    estimate_cost_range,
    estimate_tokens,
    get_avg_output_tokens,
    load_pricing,
    log_usage,
)
from text_cleaning import clean_job_description

# ================== PATHS (FIXED) ==================
BASE_DIR = Path(__file__).parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"
RESUME_LOCAL = BASE_DIR / "resume_profile.local.json"
RESUME = BASE_DIR / "resume_profile.json"
RESUME_EXAMPLE = BASE_DIR / "resume_profile.example.json"
PREFS = BASE_DIR / "preferences.json"
PREFS_LOCAL = BASE_DIR / "preferences.local.json"
PREFS_EXAMPLE = BASE_DIR / "preferences.example.json"
OUTFILE = ARTIFACTS_DIR / "tier2_scored.json"

client = OpenAI() if OpenAI else None

# ================== JSON SCHEMA (STRICT) ==================
JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "fit_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "qualified": {"type": "string", "enum": ["yes", "maybe", "no"]},
        "cold_call_risk": {"type": "string", "enum": ["low", "medium", "high"]},
        "employment_type_ok": {"type": "boolean"},
        "workplace_match": {"type": "string", "enum": ["good", "ok", "bad", "unknown"]},
        "workplace_type": {"type": "string", "enum": ["remote", "hybrid", "onsite", "unknown"]},
        "mobility_signal": {"type": "string", "enum": ["high", "medium", "low", "unknown"]},
        "salary_verdict": {"type": "string", "enum": ["meets", "below", "unknown"]},
        "job_summary": {"type": "string"},
        "top_reasons": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 6},
        "red_flags": {"type": "array", "items": {"type": "string"}, "minItems": 0, "maxItems": 10},
        "resume_angles": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 8},
        "missing_gaps": {"type": "array", "items": {"type": "string"}, "minItems": 0, "maxItems": 10},
        "next_action": {"type": "string", "enum": ["apply", "review_manually", "skip"]}
    },
    "required": [
        "fit_score",
        "qualified",
        "cold_call_risk",
        "employment_type_ok",
        "workplace_match",
        "workplace_type",
        "mobility_signal",
        "salary_verdict",
        "job_summary",
        "top_reasons",
        "red_flags",
        "resume_angles",
        "missing_gaps",
        "next_action"
    ]
}


def extract_output_text(resp) -> str:
    if hasattr(resp, "output_text") and resp.output_text:
        return resp.output_text

    try:
        parts = []
        for item in getattr(resp, "output", []) or []:
            for c in getattr(item, "content", []) or []:
                txt = getattr(c, "text", None)
                if txt:
                    parts.append(txt)
        return "\n".join(parts).strip()
    except Exception:
        return ""


def _extract_json_block(text: str) -> str:
    if not text:
        return ""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return ""
    return text[start : end + 1].strip()


def _extract_usage(resp) -> Dict[str, Any]:
    usage = getattr(resp, "usage", None)
    if not usage:
        return {}
    if isinstance(usage, dict):
        return usage
    payload: Dict[str, Any] = {}
    for key in ["input_tokens", "output_tokens", "total_tokens", "cached_input_tokens"]:
        val = getattr(usage, key, None)
        if val is not None:
            payload[key] = val
    for key in ["prompt_tokens", "completion_tokens"]:
        val = getattr(usage, key, None)
        if val is not None:
            payload[key] = val
    return payload


def _call_model(prompt: str, model: str, schema: dict) -> Tuple[str, Dict[str, Any]]:
    # New SDK (Responses API)
    if client and hasattr(client, "responses"):
        resp = client.responses.create(
            model=model,
            input=prompt,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "job_eval",
                    "schema": schema,
                    "strict": True,
                }
            },
        )
        return extract_output_text(resp), _extract_usage(resp)

    # New SDK (Chat Completions)
    if client and hasattr(client, "chat"):
        kwargs = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "Return only valid JSON that matches the provided schema.",
                },
                {"role": "user", "content": prompt + "\n\nJSON Schema:\n" + json.dumps(schema)},
            ],
        }
        if not model.startswith("gpt-5"):
            kwargs["temperature"] = 0
        resp = client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or "", _extract_usage(resp)

    # Legacy SDK (openai.ChatCompletion)
    import openai  # type: ignore

    kwargs = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Return only valid JSON that matches the provided schema.",
            },
            {"role": "user", "content": prompt + "\n\nJSON Schema:\n" + json.dumps(schema)},
        ],
    }
    if not model.startswith("gpt-5"):
        kwargs["temperature"] = 0
    resp = openai.ChatCompletion.create(**kwargs)
    return resp["choices"][0]["message"]["content"] or "", (resp.get("usage") or {})


def artifact_input(name: str) -> Path:
    artifact = ARTIFACTS_DIR / name
    legacy = BASE_DIR / name
    return artifact if artifact.exists() else legacy


def resolve_resume_path() -> Path:
    if RESUME_LOCAL.exists():
        return RESUME_LOCAL
    if RESUME.exists():
        return RESUME
    return RESUME_EXAMPLE


def resolve_prefs_path() -> Path:
    for path in (PREFS_LOCAL, PREFS, PREFS_EXAMPLE):
        if path.exists():
            return path
    return PREFS


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Limit number of jobs to evaluate")
    parser.add_argument("--batch-size", type=int, default=5, help="Number of jobs per model call")
    parser.add_argument("--model", type=str, default="", help="Model override")
    args = parser.parse_args()

    infile = artifact_input("tier2_full.json")
    if not infile.exists():
        raise FileNotFoundError(f"Missing input file: {infile}")
    resume_path = resolve_resume_path()
    if not resume_path.exists():
        raise FileNotFoundError(f"Missing resume file: {resume_path}")

    jobs = json.loads(infile.read_text(encoding="utf-8"))
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    if args.limit and args.limit > 0:
        jobs = jobs[: args.limit]
    resume = json.loads(resume_path.read_text(encoding="utf-8"))
    prefs_path = resolve_prefs_path()
    prefs = json.loads(prefs_path.read_text(encoding="utf-8")) if prefs_path.exists() else {}

    pricing = load_pricing()
    results = [None for _ in jobs]
    MODEL = (args.model or "").strip() or "gpt-4.1-mini"

    eval_jobs = []
    for idx, job in enumerate(jobs):
        desc = clean_job_description((job.get("description") or ""))
        if len(desc) < 200:
            eval_result = {
                "fit_score": 0,
                "qualified": "no",
                "cold_call_risk": "unknown",
                "employment_type_ok": False,
                "workplace_match": "unknown",
                "workplace_type": "unknown",
                "mobility_signal": "unknown",
                "salary_verdict": "unknown",
                "job_summary": "Description missing or too short to summarize.",
                "top_reasons": ["Job description missing or too short"],
                "red_flags": ["Description not captured; re-scrape may be needed"],
                "resume_angles": ["N/A"],
                "missing_gaps": [],
                "next_action": "review_manually"
            }
            results[idx] = {**job, "ai_model": MODEL, "ai_eval": eval_result}
        else:
            eval_jobs.append((idx, job, desc))

    batch_size = max(1, int(args.batch_size))
    array_schema = {
        "type": "array",
        "items": JSON_SCHEMA,
        "minItems": 1,
        "maxItems": batch_size,
    }

    for batch_start in range(0, len(eval_jobs), batch_size):
        batch = eval_jobs[batch_start:batch_start + batch_size]
        job_payload = []
        for _, job, desc in batch:
            job_payload.append(
                {
                    "url": job.get("url", ""),
                    "title": job.get("title", ""),
                    "company": job.get("company", ""),
                    "workplace": job.get("workplace", ""),
                    "posted": job.get("posted", ""),
                    "salary_hint": job.get("salary_hint", ""),
                    "description": desc,
                }
            )

        prompt = f"""
You are evaluating job fit for a candidate. Be strict and practical.

Candidate profile (truth source):
{json.dumps(resume, ensure_ascii=False)}

Preferences profile:
{json.dumps(prefs, ensure_ascii=False)}

Jobs to evaluate (array, in order):
{json.dumps(job_payload, ensure_ascii=False)}

Rules:
- Candidate strongly prefers minimal cold calling. If outbound-heavy or sales-centric, cold_call_risk=high and next_action=skip.
- Must be full-time. If unclear, employment_type_ok=false and next_action=review_manually.
- Hybrid preferred; remote acceptable; onsite only if standout.
- Upward mobility: favor analyst/ops/compliance/data-adjacent roles with transferable skills.
- Include job_summary: 1-2 sentences on what the role is about.
- Set workplace_type based on the full description: remote, hybrid, onsite, or unknown.
Return ONLY a JSON array that matches the schema, in the same order as the jobs list.
""".strip()

        input_tokens_est = estimate_tokens(prompt)
        avg_output_per_job = get_avg_output_tokens("ai_eval", MODEL, default=450)
        output_tokens_est = avg_output_per_job * len(batch)
        cost_est = estimate_cost(pricing, MODEL, input_tokens_est, output_tokens_est) if pricing else None
        cost_range = estimate_cost_range(pricing, MODEL, input_tokens_est, output_tokens_est) if pricing else {"low": None, "high": None}

        out_text, usage = _call_model(prompt, MODEL, array_schema)
        if not out_text:
            raise RuntimeError("Model returned empty output text; cannot parse JSON.")

        try:
            eval_batch = json.loads(out_text)
        except json.JSONDecodeError:
            json_block = _extract_json_block(out_text)
            if not json_block:
                raise
            eval_batch = json.loads(json_block)

        if not isinstance(eval_batch, list) or len(eval_batch) != len(batch):
            raise RuntimeError("Model returned invalid batch length.")

        for (idx, job, _), eval_result in zip(batch, eval_batch):
            results[idx] = {**job, "ai_model": MODEL, "ai_eval": eval_result}

        input_tokens_actual = usage.get("input_tokens") or usage.get("prompt_tokens")
        output_tokens_actual = usage.get("output_tokens") or usage.get("completion_tokens")
        cached_input_tokens = usage.get("cached_input_tokens")
        cost_actual = None
        if input_tokens_actual is not None and output_tokens_actual is not None:
            cost_actual = estimate_cost(
                pricing,
                MODEL,
                int(input_tokens_actual),
                int(output_tokens_actual),
                int(cached_input_tokens or 0),
            )

        log_usage(
            {
                "kind": "ai_eval",
                "model": MODEL,
                "unit_count": len(batch),
                "input_tokens_est": input_tokens_est,
                "output_tokens_est": output_tokens_est,
                "cost_est": cost_est,
                "cost_est_range": cost_range,
                "input_tokens": input_tokens_actual,
                "output_tokens": output_tokens_actual,
                "cached_input_tokens": cached_input_tokens,
                "cost_actual": cost_actual,
            }
        )

        OUTFILE.write_text(json.dumps([r for r in results if r], ensure_ascii=False, indent=2), encoding="utf-8")
        for (idx, job, _), eval_result in zip(batch, eval_batch):
            print(f"[{idx + 1}/{len(jobs)}] {job.get('title','')[:60]} -> {eval_result['fit_score']} ({eval_result['next_action']})")
        time.sleep(0.25)

    final_results = [r for r in results if r]
    OUTFILE.write_text(json.dumps(final_results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved {len(final_results)} scored jobs -> {OUTFILE}")


if __name__ == "__main__":
    main()
