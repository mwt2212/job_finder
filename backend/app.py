import json
import subprocess
import sys
import threading
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Iterator
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db import (
    init_db,
    upsert_job,
    upsert_shortlist_score,
    upsert_ai_eval,
    upsert_rating,
    upsert_status,
    upsert_shortlist_feedback,
    upsert_ai_eval_feedback,
    update_bucket,
    list_jobs,
    get_job,
    insert_run,
    insert_import,
)

BASE_DIR = Path(__file__).resolve().parents[1]
PREFERENCES_PATH = BASE_DIR / "preferences.json"
RULES_PATH = BASE_DIR / "shortlist_rules.json"
SEARCHES_PATH = BASE_DIR / "searches.json"

SCRIPTS = {
    "scout": BASE_DIR / "job-scout.py",
    "shortlist": BASE_DIR / "shortlist.py",
    "scrape": BASE_DIR / "deep-scrape-full.py",
    "eval": BASE_DIR / "ai-eval.py",
    "sort": BASE_DIR / "sort-results.py",
}

app = FastAPI(title="Job Finder Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"] ,
    allow_headers=["*"] ,
)

RUN_STATE = {
    "running": False,
    "step": None,
    "lines": [],
    "status": None,
    "progress": {"current": 0, "total": 0, "pct": 0.0, "label": ""},
    "lock": threading.Lock(),
}

SIZE_PRESETS = {
    "Large": {"max_results": 1000, "shortlist_k": 120, "final_top": 25},
    "Medium": {"max_results": 500, "shortlist_k": 60, "final_top": 10},
    "Small": {"max_results": 100, "shortlist_k": 30, "final_top": 5},
}


class RatingIn(BaseModel):
    job_id: int
    stars: int
    notes: Optional[str] = ""
    tags: List[str] = []


class StatusIn(BaseModel):
    job_id: int
    status: str


class SuggestionsApplyIn(BaseModel):
    operations: List[Dict[str, Any]]


class ImportIn(BaseModel):
    sources: Optional[List[str]] = None


class StartIn(BaseModel):
    search: str
    size: str
    query: Optional[str] = ""


class ShortlistFeedbackIn(BaseModel):
    job_id: int
    verdict: str  # keep/remove
    reason: Optional[str] = ""


class AiEvalFeedbackIn(BaseModel):
    job_id: int
    correct_bucket: str  # apply/review/skip
    reasoning_quality: int  # 1-5


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/jobs")
def api_list_jobs(
    search: Optional[str] = None,
    workplace: Optional[str] = None,
    status: Optional[str] = None,
    rating: Optional[int] = None,
    min_score: Optional[float] = None,
    date_filter: Optional[str] = None,
    source: Optional[str] = None,
    require_description: Optional[bool] = True,
):
    scraped_from = None
    scraped_to = None
    if date_filter:
        now = datetime.now(ZoneInfo("America/Chicago"))
        if date_filter == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
            scraped_from = start.astimezone(ZoneInfo("UTC")).isoformat().replace("+00:00", "Z")
            scraped_to = end.astimezone(ZoneInfo("UTC")).isoformat().replace("+00:00", "Z")
        elif date_filter == "last24":
            start = now - timedelta(hours=24)
            scraped_from = start.astimezone(ZoneInfo("UTC")).isoformat().replace("+00:00", "Z")
            scraped_to = now.astimezone(ZoneInfo("UTC")).isoformat().replace("+00:00", "Z")

    return list_jobs(
        search=search,
        workplace=workplace,
        status_filter=status,
        rating=rating,
        min_score=min_score,
        scraped_from=scraped_from,
        scraped_to=scraped_to,
        source=source,
        require_description=require_description,
    )


@app.get("/jobs/{job_id}")
def api_get_job(job_id: int):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/ratings")
def api_rate_job(payload: RatingIn):
    if payload.stars < 1 or payload.stars > 5:
        raise HTTPException(status_code=400, detail="Stars must be 1-5")
    upsert_rating(payload.job_id, payload.stars, payload.notes or "", payload.tags)
    return {"ok": True}


@app.post("/status")
def api_status(payload: StatusIn):
    upsert_status(payload.job_id, payload.status)
    return {"ok": True}


@app.post("/feedback/shortlist")
def api_shortlist_feedback(payload: ShortlistFeedbackIn):
    if payload.verdict not in {"keep", "remove"}:
        raise HTTPException(status_code=400, detail="Invalid verdict")
    upsert_shortlist_feedback(payload.job_id, payload.verdict, payload.reason or "")
    _auto_tune_from_shortlist(payload.job_id, payload.verdict, payload.reason or "")
    return {"ok": True}


@app.post("/feedback/ai")
def api_ai_feedback(payload: AiEvalFeedbackIn):
    if payload.correct_bucket not in {"apply", "review", "skip"}:
        raise HTTPException(status_code=400, detail="Invalid bucket")
    if payload.reasoning_quality < 1 or payload.reasoning_quality > 5:
        raise HTTPException(status_code=400, detail="Reasoning quality must be 1-5")
    upsert_ai_eval_feedback(payload.job_id, payload.correct_bucket, payload.reasoning_quality)
    _auto_tune_from_ai(payload.job_id, payload.correct_bucket)
    return {"ok": True}


@app.get("/settings")
def api_get_settings():
    prefs = _load_json(PREFERENCES_PATH)
    rules = _load_json(RULES_PATH)
    return {"preferences": prefs, "rules": rules}


@app.get("/searches")
def api_get_searches():
    if not SEARCHES_PATH.exists():
        return {"searches": []}
    data = json.loads(SEARCHES_PATH.read_text(encoding="utf-8"))
    items = [{"label": k, "url": v.get("url", "")} for k, v in data.items()]
    return {"searches": items}


@app.put("/settings")
def api_put_settings(payload: Dict[str, Any]):
    prefs = payload.get("preferences")
    rules = payload.get("rules")
    if prefs is not None:
        _save_json(PREFERENCES_PATH, prefs)
    if rules is not None:
        _save_json(RULES_PATH, rules)
    return {"ok": True}


@app.post("/run/start")
def api_run_start(payload: StartIn):
    if payload.size not in SIZE_PRESETS:
        raise HTTPException(status_code=400, detail="Invalid size")
    if not SEARCHES_PATH.exists():
        raise HTTPException(status_code=400, detail="Missing searches.json")
    searches = json.loads(SEARCHES_PATH.read_text(encoding="utf-8"))
    if payload.search not in searches:
        raise HTTPException(status_code=400, detail="Invalid search")
    with RUN_STATE["lock"]:
        if RUN_STATE["running"]:
            raise HTTPException(status_code=409, detail="Another step is running")
        RUN_STATE["running"] = True
        RUN_STATE["step"] = "pipeline"
        RUN_STATE["lines"] = [f"Starting pipeline ({payload.size})..."]
        RUN_STATE["status"] = "running"
        RUN_STATE["progress"] = {"current": 0, "total": 0, "pct": 0.0, "label": "pipeline"}

    thread = threading.Thread(
        target=_run_pipeline_thread,
        args=(payload.search, payload.size, payload.query or ""),
        daemon=True,
    )
    thread.start()
    return {"ok": True, "status": "started"}


@app.post("/run/{step}")
def api_run_step(step: str, search: Optional[str] = None, query: Optional[str] = None):
    if step not in SCRIPTS:
        raise HTTPException(status_code=400, detail="Invalid step")
    script = SCRIPTS[step]
    if not script.exists():
        raise HTTPException(status_code=404, detail=f"Missing script: {script.name}")

    with RUN_STATE["lock"]:
        if RUN_STATE["running"]:
            raise HTTPException(status_code=409, detail="Another step is running")
        RUN_STATE["running"] = True
        RUN_STATE["step"] = step
        RUN_STATE["lines"] = [f"Starting {step}..."]
        RUN_STATE["status"] = "running"
        RUN_STATE["progress"] = {"current": 0, "total": 0, "pct": 0.0, "label": step}

    args = _script_args(step, search, query)
    thread = threading.Thread(target=_run_step_thread, args=(step, args), daemon=True)
    thread.start()
    return {"ok": True, "status": "started"}


@app.get("/runs/stream")
def api_stream_runs():
    def event_stream() -> Iterator[str]:
        cursor = 0
        while True:
            with RUN_STATE["lock"]:
                lines = list(RUN_STATE["lines"])
                running = RUN_STATE["running"]
                status = RUN_STATE["status"]

            while cursor < len(lines):
                line = lines[cursor]
                cursor += 1
                yield f"data: {line}\n\n"

            if not running:
                yield f"event: done\ndata: {status}\n\n"
                break

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/runs/state")
def api_run_state():
    with RUN_STATE["lock"]:
        return {
            "running": RUN_STATE["running"],
            "step": RUN_STATE["step"],
            "status": RUN_STATE["status"],
            "lines": list(RUN_STATE["lines"]),
            "progress": RUN_STATE["progress"],
        }


def _run_step_thread(step: str, args: List[str]) -> None:
    started = datetime.utcnow().isoformat() + "Z"
    log_lines = []
    status = "ok"

    try:
        proc = subprocess.Popen(
            [sys.executable, "-u", *args],
            cwd=str(BASE_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            clean = line.rstrip()
            log_lines.append(clean)
            with RUN_STATE["lock"]:
                RUN_STATE["lines"].append(clean)
                _update_progress_from_line(step, clean)
        proc.wait()
        if proc.returncode != 0:
            status = "error"
    except Exception as exc:
        status = "error"
        err_line = f"Error: {exc}"
        log_lines.append(err_line)
        with RUN_STATE["lock"]:
            RUN_STATE["lines"].append(err_line)

    ended = datetime.utcnow().isoformat() + "Z"
    insert_run(step, status, started, ended, "\n".join(log_lines))

    if status == "ok":
        _import_for_step(step)

    with RUN_STATE["lock"]:
        RUN_STATE["running"] = False
        RUN_STATE["status"] = status
        if status == "ok":
            RUN_STATE["progress"]["pct"] = 100.0


def _update_progress_from_line(step: str, line: str) -> None:
    m0 = re.search(r"Cap:\s*(\d+)\s*jobs", line)
    if m0:
        total = int(m0.group(1))
        RUN_STATE["progress"] = {"current": 0, "total": total, "pct": 0.0, "label": step}
        return

    # Generic [i/total] progress
    m = re.search(r"\[(\d+)\s*/\s*(\d+)\]", line)
    if m:
        current = int(m.group(1))
        total = int(m.group(2))
        pct = (current / total) * 100.0 if total else 0.0
        RUN_STATE["progress"] = {"current": current, "total": total, "pct": pct, "label": step}
        return

    # Scout: "Added X jobs | Total: Y"
    m2 = re.search(r"Total:\s*(\d+)", line)
    if m2:
        current = int(m2.group(1))
        total = RUN_STATE["progress"].get("total", 0)
        pct = (current / total) * 100.0 if total else 0.0
        RUN_STATE["progress"] = {"current": current, "total": total, "pct": pct, "label": step}
        return

    # Scout: "Reached cap of N jobs"
    m3 = re.search(r"Reached cap of\s*(\d+)", line)
    if m3:
        total = int(m3.group(1))
        RUN_STATE["progress"] = {"current": total, "total": total, "pct": 100.0, "label": step}
        return


def _script_args(step: str, search: Optional[str], query: Optional[str] = None) -> List[str]:
    script = SCRIPTS[step]
    args = [str(script)]
    if step == "scout" and search:
        args.extend(["--search", search])
    if step == "scout" and query:
        args.extend(["--query", query])
    return args


def _script_args_with_size(step: str, search: str, size: str, query: str) -> List[str]:
    cfg = SIZE_PRESETS[size]
    args = _script_args(step, search, query)
    if step == "scout":
        args.extend(["--max-results", str(cfg["max_results"])])
    if step == "shortlist":
        args.extend(["--target-n", str(cfg["shortlist_k"])])
    if step == "scrape":
        args.extend(["--limit", str(cfg["final_top"])])
    if step == "eval":
        args.extend(["--limit", str(cfg["final_top"])])
    if step == "sort":
        args.extend(["--final-top", str(cfg["final_top"])])
    return args


def _run_pipeline_thread(search: str, size: str, query: str) -> None:
    started = datetime.utcnow().isoformat() + "Z"
    status = "ok"
    log_lines: List[str] = []
    steps = ["scout", "shortlist", "scrape", "eval", "sort"]

    try:
        for step in steps:
            with RUN_STATE["lock"]:
                RUN_STATE["step"] = step
                RUN_STATE["lines"].append(f"== {step} ==")
            args = _script_args_with_size(step, search, size, query)
            proc = subprocess.Popen(
                [sys.executable, "-u", *args],
                cwd=str(BASE_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                clean = line.rstrip()
                log_lines.append(clean)
                with RUN_STATE["lock"]:
                    RUN_STATE["lines"].append(clean)
                    _update_progress_from_line(step, clean)
            proc.wait()
            if proc.returncode != 0:
                status = "error"
                break
            _import_for_step(step)
    except Exception as exc:
        status = "error"
        log_lines.append(f"Error: {exc}")
        with RUN_STATE["lock"]:
            RUN_STATE["lines"].append(f"Error: {exc}")

    ended = datetime.utcnow().isoformat() + "Z"
    insert_run("pipeline", status, started, ended, "\n".join(log_lines))
    with RUN_STATE["lock"]:
        RUN_STATE["running"] = False
        RUN_STATE["status"] = status
        if status == "ok":
            RUN_STATE["progress"]["pct"] = 100.0



@app.post("/import")
def api_import(payload: ImportIn):
    sources = payload.sources or []
    counts = import_all(sources)
    return {"ok": True, "counts": counts}


@app.post("/suggestions/generate")
def api_generate_suggestions():
    prefs = _load_json(PREFERENCES_PATH)
    suggestions = _generate_suggestions(prefs)
    return {"suggestions": suggestions}


@app.post("/suggestions/apply")
def api_apply_suggestions(payload: SuggestionsApplyIn):
    prefs = _load_json(PREFERENCES_PATH)
    for op in payload.operations:
        _apply_op(prefs, op)
    _save_json(PREFERENCES_PATH, prefs)
    return {"ok": True}


# ------------------ Helpers ------------------

def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_tuning_log(entry: Dict[str, Any]) -> None:
    log_path = BASE_DIR / "tuning_log.jsonl"
    entry["ts"] = datetime.utcnow().isoformat() + "Z"
    log_path.open("a", encoding="utf-8").write(json.dumps(entry, ensure_ascii=False) + "\n")


def _import_for_step(step: str) -> None:
    if step == "scout":
        import_metadata(BASE_DIR / "tier2_metadata.json")
    elif step == "shortlist":
        import_shortlist(BASE_DIR / "tier2_shortlist.json")
    elif step == "scrape":
        import_full(BASE_DIR / "tier2_full.json")
    elif step == "eval":
        import_scored(BASE_DIR / "tier2_scored.json")
    elif step == "sort":
        import_buckets(
            {
                "apply": BASE_DIR / "apply.json",
                "review": BASE_DIR / "review.json",
                "skip": BASE_DIR / "skip.json",
            }
        )


def import_all(only_sources: Optional[List[str]] = None) -> Dict[str, Any]:
    counts: Dict[str, Any] = {}

    def want(name: str) -> bool:
        return not only_sources or name in only_sources

    if want("metadata"):
        counts["metadata"] = import_metadata(BASE_DIR / "tier2_metadata.json")
    if want("shortlist"):
        counts["shortlist"] = import_shortlist(BASE_DIR / "tier2_shortlist.json")
    if want("full"):
        counts["full"] = import_full(BASE_DIR / "tier2_full.json")
    if want("scored"):
        counts["scored"] = import_scored(BASE_DIR / "tier2_scored.json")
    if want("buckets"):
        counts["buckets"] = import_buckets(
            {
                "apply": BASE_DIR / "apply.json",
                "review": BASE_DIR / "review.json",
                "skip": BASE_DIR / "skip.json",
            }
        )

    insert_import(",".join(only_sources or ["all"]), counts)
    return counts


def import_metadata(path: Path) -> int:
    if not path.exists():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    scraped_at = datetime.utcnow().isoformat() + "Z"
    count = 0
    for job in data:
        upsert_job({**job, "scraped_at": scraped_at})
        count += 1
    return count


def import_shortlist(path: Path) -> int:
    if not path.exists():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    count = 0
    for job in data:
        job_id = upsert_job(job)
        if job_id <= 0:
            continue
        score = float(job.get("score", 0) or 0)
        reasons = job.get("reasons") or []
        qualification_score = float(job.get("qualification_score", 0) or 0)
        upsert_shortlist_score(job_id, score, reasons, qualification_score)
        count += 1
    return count


def import_full(path: Path) -> int:
    if not path.exists():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    count = 0
    for job in data:
        upsert_job(job)
        count += 1
    return count


def import_scored(path: Path) -> int:
    if not path.exists():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    count = 0
    for job in data:
        job_id = upsert_job(job)
        if job_id <= 0:
            continue
        eval_json = job.get("ai_eval") or {}
        upsert_ai_eval(job_id, eval_json, model="gpt-4.1-mini")
        count += 1
    return count


def import_buckets(paths: Dict[str, Path]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for bucket, path in paths.items():
        if not path.exists():
            counts[bucket] = 0
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        count = 0
        for job in data:
            job_id = upsert_job({"url": job.get("url"), "bucket": bucket, **job})
            if job_id > 0:
                update_bucket(job_id, bucket)
                count += 1
        counts[bucket] = count
    return counts


def _generate_suggestions(prefs: Dict[str, Any]) -> List[Dict[str, Any]]:
    suggestions: List[Dict[str, Any]] = []

    # Basic heuristic: if many low-rated jobs mention healthcare, suggest adding it
    from db import _connect

    healthcare_terms = ["health", "medical", "hospital", "clinic"]

    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT j.title, j.company, j.description, r.stars
            FROM jobs j
            JOIN ratings r ON r.job_id = j.id
            WHERE r.stars <= 2
            """
        ).fetchall()

    if rows:
        low_total = len(rows)
        health_hits = 0
        for row in rows:
            blob = " ".join([row["title"] or "", row["company"] or "", row["description"] or ""]).lower()
            if any(term in blob for term in healthcare_terms):
                health_hits += 1

        if health_hits / low_total >= 0.2:
            existing = set(
                (prefs.get("industry_preferences", {}) or {}).get("soft_penalize", [])
            )
            if "healthcare" not in existing:
                suggestions.append(
                    {
                        "op": "add",
                        "path": "industry_preferences.soft_penalize",
                        "value": "healthcare",
                        "reason": "Many low-rated jobs appear healthcare-related; add soft penalty.",
                    }
                )

    return suggestions


def _apply_op(prefs: Dict[str, Any], op: Dict[str, Any]) -> None:
    path = op.get("path", "")
    value = op.get("value")
    if not path:
        return
    parts = path.split(".")
    cur = prefs
    for part in parts[:-1]:
        if part not in cur or not isinstance(cur[part], dict):
            cur[part] = {}
        cur = cur[part]

    key = parts[-1]
    if op.get("op") == "add":
        if key not in cur or not isinstance(cur[key], list):
            cur[key] = []
        if value not in cur[key]:
            cur[key].append(value)
    elif op.get("op") == "set":
        cur[key] = value


def _auto_tune_from_shortlist(job_id: int, verdict: str, reason: str) -> None:
    job = get_job(job_id)
    if not job:
        return
    prefs = _load_json(PREFERENCES_PATH)
    rules = _load_json(RULES_PATH)

    text = " ".join(
        [
            job.get("title", ""),
            job.get("company", ""),
            job.get("description", "") or "",
            job.get("raw_card_text", "") or "",
        ]
    ).lower()

    changed = []

    def clamp(val: int, lo: int, hi: int) -> int:
        return max(lo, min(hi, val))

    reason = (reason or "").lower()

    adjusted_min_match = False
    if verdict == "remove":
        if "wrong field" in reason:
            rules["wrong_field_penalty"] = clamp(int(rules.get("wrong_field_penalty", -6)) - 2, -30, -2)
            changed.append({"rules.wrong_field_penalty": rules["wrong_field_penalty"]})
        if "not qualified" in reason:
            q = prefs.get("qualification", {})
            q["min_match_score"] = round(min(0.85, max(0.35, float(q.get("min_match_score", 0.55)) + 0.03)), 2)
            prefs["qualification"] = q
            changed.append({"preferences.qualification.min_match_score": q["min_match_score"]})
            adjusted_min_match = True
        if "salesy" in reason:
            rules["sales_adjacent_penalty"] = clamp(int(rules.get("sales_adjacent_penalty", -8)) - 3, -30, -2)
            changed.append({"rules.sales_adjacent_penalty": rules["sales_adjacent_penalty"]})
        if "healthcare" in reason:
            rules["healthcare_penalty"] = clamp(int(rules.get("healthcare_penalty", -10)) - 3, -30, -2)
            changed.append({"rules.healthcare_penalty": rules["healthcare_penalty"]})
        if "low pay" in reason:
            q = prefs.get("qualification", {})
            q["min_match_score"] = round(min(0.85, max(0.35, float(q.get("min_match_score", 0.55)) + 0.01)), 2)
            prefs["qualification"] = q
            changed.append({"preferences.qualification.min_match_score": q["min_match_score"]})
            adjusted_min_match = True
        if "onsite" in reason:
            ws = rules.get("workplace_score", {})
            ws["onsite"] = max(-10, int(ws.get("onsite", 8)) - 2)
            rules["workplace_score"] = ws
            changed.append({"rules.workplace_score.onsite": ws["onsite"]})
            wp = prefs.get("workplace_preferences", {})
            weights = wp.get("workplace_type_weight", {})
            if "onsite" in weights:
                weights["onsite"] = max(0.0, round(float(weights.get("onsite", 0.6)) - 0.05, 2))
                wp["workplace_type_weight"] = weights
                prefs["workplace_preferences"] = wp
                changed.append({"preferences.workplace_type_weight.onsite": weights["onsite"]})

        if any(t in text for t in ["health", "medical", "hospital", "clinic", "patient"]):
            rules["healthcare_penalty"] = clamp(int(rules.get("healthcare_penalty", -10)) - 2, -30, -2)
            changed.append({"rules.healthcare_penalty": rules["healthcare_penalty"]})
        if any(t in text for t in ["sales", "account executive", "business development", "quota", "cold call"]):
            rules["sales_adjacent_penalty"] = clamp(int(rules.get("sales_adjacent_penalty", -8)) - 2, -30, -2)
            changed.append({"rules.sales_adjacent_penalty": rules["sales_adjacent_penalty"]})

        if not adjusted_min_match:
            q = prefs.get("qualification", {})
            q["min_match_score"] = round(min(0.85, max(0.35, float(q.get("min_match_score", 0.55)) + 0.02)), 2)
            prefs["qualification"] = q
            changed.append({"preferences.qualification.min_match_score": q["min_match_score"]})
    else:
        q = prefs.get("qualification", {})
        q["min_match_score"] = round(min(0.8, max(0.35, float(q.get("min_match_score", 0.55)) - 0.02)), 2)
        prefs["qualification"] = q
        changed.append({"preferences.qualification.min_match_score": q["min_match_score"]})

    if changed:
        _save_json(PREFERENCES_PATH, prefs)
        _save_json(RULES_PATH, rules)
        _append_tuning_log({"source": "shortlist", "job_id": job_id, "verdict": verdict, "reason": reason, "changes": changed})


def _auto_tune_from_ai(job_id: int, correct_bucket: str) -> None:
    job = get_job(job_id)
    if not job:
        return
    prefs = _load_json(PREFERENCES_PATH)
    tuning = prefs.get("tuning", {}) or {}
    thresholds = tuning.get("sort_thresholds", {}) or {}

    apply_min = int(thresholds.get("apply_min_score", 75))
    review_min = int(thresholds.get("review_min_score", 55))

    model_action = (job.get("next_action") or "").lower()
    if not model_action:
        return

    changed = []

    if correct_bucket == "apply" and model_action != "apply":
        apply_min = max(60, apply_min - 2)
        changed.append({"tuning.sort_thresholds.apply_min_score": apply_min})
    elif correct_bucket == "skip" and model_action != "skip":
        review_min = max(40, review_min - 2)
        changed.append({"tuning.sort_thresholds.review_min_score": review_min})
    elif correct_bucket == "review" and model_action == "apply":
        apply_min = min(85, apply_min + 2)
        changed.append({"tuning.sort_thresholds.apply_min_score": apply_min})

    if review_min >= apply_min:
        review_min = apply_min - 10
        changed.append({"tuning.sort_thresholds.review_min_score": review_min})

    if changed:
        tuning["sort_thresholds"] = {"apply_min_score": apply_min, "review_min_score": review_min}
        prefs["tuning"] = tuning
        _save_json(PREFERENCES_PATH, prefs)
        _append_tuning_log({"source": "ai_eval", "job_id": job_id, "changes": changed})
