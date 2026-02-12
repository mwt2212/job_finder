import json
import time
from pathlib import Path

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover - fallback for legacy SDKs
    OpenAI = None  # type: ignore

# ================== PATHS (FIXED) ==================
BASE_DIR = Path(__file__).parent
INFILE = BASE_DIR / "tier2_full.json"
RESUME = BASE_DIR / "resume_profile.json"
PREFS = BASE_DIR / "preferences.json"
OUTFILE = BASE_DIR / "tier2_scored.json"

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


def _call_model(prompt: str, model: str, schema: dict) -> str:
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
        return extract_output_text(resp)

    # New SDK (Chat Completions)
    if client and hasattr(client, "chat"):
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Return only valid JSON that matches the provided schema.",
                },
                {"role": "user", "content": prompt + "\n\nJSON Schema:\n" + json.dumps(schema)},
            ],
            temperature=0,
        )
        return resp.choices[0].message.content or ""

    # Legacy SDK (openai.ChatCompletion)
    import openai  # type: ignore

    resp = openai.ChatCompletion.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "Return only valid JSON that matches the provided schema.",
            },
            {"role": "user", "content": prompt + "\n\nJSON Schema:\n" + json.dumps(schema)},
        ],
        temperature=0,
    )
    return resp["choices"][0]["message"]["content"] or ""


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Limit number of jobs to evaluate")
    parser.add_argument("--batch-size", type=int, default=5, help="Number of jobs per model call")
    args = parser.parse_args()

    if not INFILE.exists():
        raise FileNotFoundError(f"Missing input file: {INFILE}")
    if not RESUME.exists():
        raise FileNotFoundError(f"Missing resume file: {RESUME}")

    jobs = json.loads(INFILE.read_text(encoding="utf-8"))
    if args.limit and args.limit > 0:
        jobs = jobs[: args.limit]
    resume = json.loads(RESUME.read_text(encoding="utf-8"))
    prefs = json.loads(PREFS.read_text(encoding="utf-8")) if PREFS.exists() else {}

    results = [None for _ in jobs]
    MODEL = "gpt-4.1-mini"

    eval_jobs = []
    for idx, job in enumerate(jobs):
        desc = (job.get("description") or "").strip()
        if len(desc) < 200:
            eval_result = {
                "fit_score": 0,
                "qualified": "no",
                "cold_call_risk": "unknown",
                "employment_type_ok": False,
                "workplace_match": "unknown",
                "mobility_signal": "unknown",
                "salary_verdict": "unknown",
                "job_summary": "Description missing or too short to summarize.",
                "top_reasons": ["Job description missing or too short"],
                "red_flags": ["Description not captured; re-scrape may be needed"],
                "resume_angles": ["N/A"],
                "missing_gaps": [],
                "next_action": "review_manually"
            }
            results[idx] = {**job, "ai_eval": eval_result}
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
Return ONLY a JSON array that matches the schema, in the same order as the jobs list.
""".strip()

        out_text = _call_model(prompt, MODEL, array_schema)
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
            results[idx] = {**job, "ai_eval": eval_result}

        OUTFILE.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        for (idx, job, _), eval_result in zip(batch, eval_batch):
            print(f"[{idx + 1}/{len(jobs)}] {job.get('title','')[:60]} -> {eval_result['fit_score']} ({eval_result['next_action']})")
        time.sleep(0.25)

    print(f"\nSaved {len(results)} scored jobs -> {OUTFILE}")


if __name__ == "__main__":
    main()
