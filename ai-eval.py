import json
import time
from pathlib import Path
from openai import OpenAI

# ================== PATHS (FIXED) ==================
BASE_DIR = Path(__file__).parent
INFILE = BASE_DIR / "tier2_full.json"
RESUME = BASE_DIR / "resume_profile.json"
PREFS = BASE_DIR / "preferences.json"
OUTFILE = BASE_DIR / "tier2_scored.json"

client = OpenAI()

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


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Limit number of jobs to evaluate")
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

    results = []
    MODEL = "gpt-4.1-mini"

    for i, job in enumerate(jobs, start=1):
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
        else:
            prompt = f"""
You are evaluating job fit for a candidate. Be strict and practical.

Candidate profile (truth source):
{json.dumps(resume, ensure_ascii=False)}

Preferences profile:
{json.dumps(prefs, ensure_ascii=False)}

Job metadata:
- url: {job.get('url','')}
- title: {job.get('title','')}
- company: {job.get('company','')}
- workplace (listing): {job.get('workplace','')}
- posted: {job.get('posted','')}
- salary_hint: {job.get('salary_hint','')}

Full job description:
{desc}

Rules:
- Candidate strongly prefers minimal cold calling. If outbound-heavy or sales-centric, cold_call_risk=high and next_action=skip.
- Must be full-time. If unclear, employment_type_ok=false and next_action=review_manually.
- Hybrid preferred; remote acceptable; onsite only if standout.
- Upward mobility: favor analyst/ops/compliance/data-adjacent roles with transferable skills.
 - Include job_summary: 1-2 sentences on what the role is about.
Return ONLY JSON that matches the schema.
""".strip()

            resp = client.responses.create(
                model=MODEL,
                input=prompt,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "job_eval",
                        "schema": JSON_SCHEMA,
                        "strict": True
                    }
                }
            )

            out_text = extract_output_text(resp)
            if not out_text:
                raise RuntimeError("Model returned empty output text; cannot parse JSON.")

            eval_result = json.loads(out_text)

        results.append({**job, "ai_eval": eval_result})
        OUTFILE.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"[{i}/{len(jobs)}] {job.get('title','')[:60]} -> {eval_result['fit_score']} ({eval_result['next_action']})")
        time.sleep(0.25)

    print(f"\nSaved {len(results)} scored jobs -> {OUTFILE}")


if __name__ == "__main__":
    main()
