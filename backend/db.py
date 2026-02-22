import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from backend.infra.db import repository, schema

BASE_DIR = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = BASE_DIR / "artifacts"
ARTIFACT_DB_PATH = ARTIFACTS_DIR / "jobfinder.db"
LEGACY_DB_PATH = BASE_DIR / "jobfinder.db"


def _resolve_db_path() -> Path:
    if ARTIFACT_DB_PATH.exists() or not LEGACY_DB_PATH.exists():
        return ARTIFACT_DB_PATH
    return LEGACY_DB_PATH


DB_PATH = _resolve_db_path()


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def init_db() -> None:
    schema.init_db(_connect)


def upsert_job(job: Dict[str, Any]) -> int:
    return repository.upsert_job(_connect, _now, job)


def upsert_shortlist_score(job_id: int, score: float, reasons: List[str], qualification_score: float) -> None:
    repository.upsert_shortlist_score(_connect, _now, job_id, score, reasons, qualification_score)


def upsert_ai_eval(job_id: int, eval_json: Dict[str, Any], model: str) -> None:
    repository.upsert_ai_eval(_connect, _now, job_id, eval_json, model)


def upsert_rating(job_id: int, stars: int, notes: str, tags: List[str]) -> None:
    repository.upsert_rating(_connect, _now, job_id, stars, notes, tags)


def upsert_status(job_id: int, status: str) -> None:
    repository.upsert_status(_connect, _now, job_id, status)


def upsert_shortlist_feedback(job_id: int, verdict: str, reason: str) -> None:
    repository.upsert_shortlist_feedback(_connect, _now, job_id, verdict, reason)


def get_shortlist_feedback(job_id: int) -> Optional[Dict[str, Any]]:
    return repository.get_shortlist_feedback(_connect, job_id)


def upsert_ai_eval_feedback(job_id: int, correct_bucket: str, reasoning_quality: int) -> None:
    repository.upsert_ai_eval_feedback(_connect, _now, job_id, correct_bucket, reasoning_quality)


def get_ai_eval_feedback(job_id: int) -> Optional[Dict[str, Any]]:
    return repository.get_ai_eval_feedback(_connect, job_id)


def update_bucket(job_id: int, bucket: str) -> None:
    repository.update_bucket(_connect, job_id, bucket)


def update_workplace(job_id: int, workplace: str) -> None:
    repository.update_workplace(_connect, job_id, workplace)


def list_jobs(
    search: Optional[str] = None,
    workplace: Optional[str] = None,
    status_filter: Optional[str] = None,
    rating: Optional[int] = None,
    min_score: Optional[float] = None,
    scraped_from: Optional[str] = None,
    scraped_to: Optional[str] = None,
    source: Optional[str] = None,
    require_description: bool = True,
) -> List[Dict[str, Any]]:
    return repository.list_jobs(
        _connect,
        search=search,
        workplace=workplace,
        status_filter=status_filter,
        rating=rating,
        min_score=min_score,
        scraped_from=scraped_from,
        scraped_to=scraped_to,
        source=source,
        require_description=require_description,
    )


def get_job(job_id: int) -> Optional[Dict[str, Any]]:
    return repository.get_job(_connect, job_id)


def insert_run(step: str, status: str, started_at: str, ended_at: str, log: str) -> None:
    repository.insert_run(_connect, step, status, started_at, ended_at, log)


def insert_import(source: str, counts: Dict[str, Any]) -> None:
    repository.insert_import(_connect, _now, source, counts)


def all_job_urls() -> Iterable[str]:
    return repository.all_job_urls(_connect)


def insert_cover_letter(job_id: int, content: str, feedback: str, model: str) -> int:
    return repository.insert_cover_letter(_connect, _now, job_id, content, feedback, model)


def update_cover_letter(cover_id: int, content: str, feedback: str) -> None:
    repository.update_cover_letter(_connect, cover_id, content, feedback)


def list_cover_letters(job_id: int) -> List[Dict[str, Any]]:
    return repository.list_cover_letters(_connect, job_id)


def get_cover_letter(cover_id: int) -> Optional[Dict[str, Any]]:
    return repository.get_cover_letter(_connect, cover_id)
