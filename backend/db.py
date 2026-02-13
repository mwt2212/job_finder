import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "jobfinder.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                title TEXT,
                company TEXT,
                location TEXT,
                workplace TEXT,
                posted TEXT,
                description TEXT,
                salary_hint TEXT,
                source TEXT,
                raw_card_text TEXT,
                bucket TEXT,
                created_at TEXT,
                first_seen_at TEXT,
                last_seen_at TEXT,
                scraped_at TEXT
            );

            CREATE TABLE IF NOT EXISTS shortlist_scores (
                job_id INTEGER PRIMARY KEY,
                score REAL,
                reasons TEXT,
                qualification_score REAL,
                created_at TEXT,
                FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS ai_eval (
                job_id INTEGER PRIMARY KEY,
                eval_json TEXT,
                model TEXT,
                fit_score INTEGER,
                next_action TEXT,
                created_at TEXT,
                FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS ratings (
                job_id INTEGER PRIMARY KEY,
                stars INTEGER,
                notes TEXT,
                tags TEXT,
                created_at TEXT,
                FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS status (
                job_id INTEGER PRIMARY KEY,
                status TEXT,
                created_at TEXT,
                FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS shortlist_feedback (
                job_id INTEGER PRIMARY KEY,
                verdict TEXT,
                reason TEXT,
                created_at TEXT,
                FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS ai_eval_feedback (
                job_id INTEGER PRIMARY KEY,
                correct_bucket TEXT,
                reasoning_quality INTEGER,
                created_at TEXT,
                FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                step TEXT,
                status TEXT,
                started_at TEXT,
                ended_at TEXT,
                log TEXT
            );

            CREATE TABLE IF NOT EXISTS imports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                counts TEXT,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS cover_letters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER,
                content TEXT,
                feedback TEXT,
                model TEXT,
                created_at TEXT,
                FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
            );
            """
        )
        for stmt in [
            "ALTER TABLE jobs ADD COLUMN first_seen_at TEXT",
            "ALTER TABLE jobs ADD COLUMN last_seen_at TEXT",
            "ALTER TABLE jobs ADD COLUMN scraped_at TEXT",
        ]:
            try:
                conn.execute(stmt)
            except Exception:
                pass
        # backfill timestamps for existing rows
        try:
            conn.execute("UPDATE jobs SET first_seen_at = COALESCE(first_seen_at, created_at)")
            conn.execute("UPDATE jobs SET last_seen_at = COALESCE(last_seen_at, created_at)")
            conn.execute("UPDATE jobs SET scraped_at = COALESCE(scraped_at, created_at)")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE shortlist_feedback ADD COLUMN reason TEXT")
        except Exception:
            pass


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def upsert_job(job: Dict[str, Any]) -> int:
    now = _now()
    fields = {
        "url": job.get("url"),
        "title": job.get("title"),
        "company": job.get("company"),
        "location": job.get("location"),
        "workplace": job.get("workplace"),
        "posted": job.get("posted"),
        "description": job.get("description"),
        "salary_hint": job.get("salary_hint"),
        "source": job.get("source"),
        "raw_card_text": job.get("card_text") or job.get("raw_card_text"),
        "bucket": job.get("bucket"),
        "scraped_at": job.get("scraped_at"),
    }
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO jobs (url, title, company, location, workplace, posted, description, salary_hint, source, raw_card_text, bucket, created_at, first_seen_at, last_seen_at, scraped_at)
            VALUES (:url, :title, :company, :location, :workplace, :posted, :description, :salary_hint, :source, :raw_card_text, :bucket, :created_at, :first_seen_at, :last_seen_at, :scraped_at)
            ON CONFLICT(url) DO UPDATE SET
                title=excluded.title,
                company=excluded.company,
                location=excluded.location,
                workplace=excluded.workplace,
                posted=excluded.posted,
                description=COALESCE(excluded.description, jobs.description),
                salary_hint=COALESCE(excluded.salary_hint, jobs.salary_hint),
                source=COALESCE(excluded.source, jobs.source),
                raw_card_text=COALESCE(excluded.raw_card_text, jobs.raw_card_text),
                bucket=COALESCE(excluded.bucket, jobs.bucket),
                last_seen_at=excluded.last_seen_at,
                scraped_at=COALESCE(excluded.scraped_at, jobs.scraped_at)
            """,
            {**fields, "created_at": now, "first_seen_at": now, "last_seen_at": now, "scraped_at": fields["scraped_at"]},
        )
        if cur.lastrowid:
            return int(cur.lastrowid)
        row = conn.execute("SELECT id FROM jobs WHERE url = ?", (fields["url"],)).fetchone()
        return int(row["id"]) if row else -1


def upsert_shortlist_score(job_id: int, score: float, reasons: List[str], qualification_score: float) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO shortlist_scores (job_id, score, reasons, qualification_score, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                score=excluded.score,
                reasons=excluded.reasons,
                qualification_score=excluded.qualification_score,
                created_at=excluded.created_at
            """,
            (job_id, score, json.dumps(reasons), qualification_score, _now()),
        )


def upsert_ai_eval(job_id: int, eval_json: Dict[str, Any], model: str) -> None:
    fit_score = int(eval_json.get("fit_score", 0) or 0)
    next_action = eval_json.get("next_action") or ""
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO ai_eval (job_id, eval_json, model, fit_score, next_action, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                eval_json=excluded.eval_json,
                model=excluded.model,
                fit_score=excluded.fit_score,
                next_action=excluded.next_action,
                created_at=excluded.created_at
            """,
            (job_id, json.dumps(eval_json), model, fit_score, next_action, _now()),
        )


def upsert_rating(job_id: int, stars: int, notes: str, tags: List[str]) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO ratings (job_id, stars, notes, tags, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                stars=excluded.stars,
                notes=excluded.notes,
                tags=excluded.tags,
                created_at=excluded.created_at
            """,
            (job_id, stars, notes, json.dumps(tags), _now()),
        )


def upsert_status(job_id: int, status: str) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO status (job_id, status, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                status=excluded.status,
                created_at=excluded.created_at
            """,
            (job_id, status, _now()),
        )


def upsert_shortlist_feedback(job_id: int, verdict: str, reason: str) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO shortlist_feedback (job_id, verdict, reason, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                verdict=excluded.verdict,
                reason=excluded.reason,
                created_at=excluded.created_at
            """,
            (job_id, verdict, reason, _now()),
        )


def upsert_ai_eval_feedback(job_id: int, correct_bucket: str, reasoning_quality: int) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO ai_eval_feedback (job_id, correct_bucket, reasoning_quality, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                correct_bucket=excluded.correct_bucket,
                reasoning_quality=excluded.reasoning_quality,
                created_at=excluded.created_at
            """,
            (job_id, correct_bucket, reasoning_quality, _now()),
        )

def update_bucket(job_id: int, bucket: str) -> None:
    with _connect() as conn:
        conn.execute("UPDATE jobs SET bucket = ? WHERE id = ?", (bucket, job_id))


def update_workplace(job_id: int, workplace: str) -> None:
    with _connect() as conn:
        conn.execute("UPDATE jobs SET workplace = ? WHERE id = ?", (workplace, job_id))


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
    where = []
    params: List[Any] = []

    if search:
        where.append("(j.title LIKE ? OR j.company LIKE ? OR j.description LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like, like])

    if workplace:
        where.append("j.workplace = ?")
        params.append(workplace)

    if status_filter:
        where.append("s.status = ?")
        params.append(status_filter)

    if rating is not None:
        where.append("r.stars = ?")
        params.append(rating)

    if min_score is not None:
        where.append("COALESCE(a.fit_score, ss.score, 0) >= ?")
        params.append(min_score)

    if source:
        where.append("j.source = ?")
        params.append(source)

    if require_description:
        where.append("j.description IS NOT NULL AND length(j.description) >= 200")

    if scraped_from:
        where.append("j.scraped_at >= ?")
        params.append(scraped_from)
    if scraped_to:
        where.append("j.scraped_at < ?")
        params.append(scraped_to)

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    query = f"""
        SELECT
            j.id,
            j.url,
            j.title,
            j.company,
            j.location,
            j.workplace,
            j.posted,
            j.scraped_at,
            j.salary_hint,
            j.bucket,
            COALESCE(a.fit_score, ss.score, 0) AS score,
            r.stars AS rating,
            s.status AS status
        FROM jobs j
        LEFT JOIN shortlist_scores ss ON ss.job_id = j.id
        LEFT JOIN ai_eval a ON a.job_id = j.id
        LEFT JOIN ratings r ON r.job_id = j.id
        LEFT JOIN status s ON s.job_id = j.id
        {where_sql}
        ORDER BY score DESC
        LIMIT 500
    """
    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def get_job(job_id: int) -> Optional[Dict[str, Any]]:
    query = """
        SELECT
            j.*, ss.score AS shortlist_score, ss.reasons, ss.qualification_score,
            a.eval_json, a.fit_score, a.next_action, a.model,
            r.stars AS rating, r.notes, r.tags,
            s.status AS status,
            sf.verdict AS shortlist_verdict,
            sf.reason AS shortlist_reason,
            af.correct_bucket AS correct_bucket,
            af.reasoning_quality AS reasoning_quality
        FROM jobs j
        LEFT JOIN shortlist_scores ss ON ss.job_id = j.id
        LEFT JOIN ai_eval a ON a.job_id = j.id
        LEFT JOIN ratings r ON r.job_id = j.id
        LEFT JOIN status s ON s.job_id = j.id
        LEFT JOIN shortlist_feedback sf ON sf.job_id = j.id
        LEFT JOIN ai_eval_feedback af ON af.job_id = j.id
        WHERE j.id = ?
    """
    with _connect() as conn:
        row = conn.execute(query, (job_id,)).fetchone()
        if not row:
            return None
        data = dict(row)
        if data.get("reasons"):
            data["reasons"] = json.loads(data["reasons"])
        if data.get("eval_json"):
            data["eval_json"] = json.loads(data["eval_json"])
        if data.get("tags"):
            data["tags"] = json.loads(data["tags"])
        return data


def insert_run(step: str, status: str, started_at: str, ended_at: str, log: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO runs (step, status, started_at, ended_at, log) VALUES (?, ?, ?, ?, ?)",
            (step, status, started_at, ended_at, log),
        )


def insert_import(source: str, counts: Dict[str, Any]) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO imports (source, counts, created_at) VALUES (?, ?, ?)",
            (source, json.dumps(counts), _now()),
        )


def all_job_urls() -> Iterable[str]:
    with _connect() as conn:
        rows = conn.execute("SELECT url FROM jobs").fetchall()
        return [r["url"] for r in rows]


def insert_cover_letter(job_id: int, content: str, feedback: str, model: str) -> int:
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO cover_letters (job_id, content, feedback, model, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (job_id, content, feedback, model, _now()),
        )
        return int(cur.lastrowid)


def update_cover_letter(cover_id: int, content: str, feedback: str) -> None:
    with _connect() as conn:
        conn.execute(
            """
            UPDATE cover_letters
            SET content = ?, feedback = ?
            WHERE id = ?
            """,
            (content, feedback, cover_id),
        )


def list_cover_letters(job_id: int) -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, job_id, content, feedback, model, created_at
            FROM cover_letters
            WHERE job_id = ?
            ORDER BY created_at DESC
            """,
            (job_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_cover_letter(cover_id: int) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT id, job_id, content, feedback, model, created_at
            FROM cover_letters
            WHERE id = ?
            """,
            (cover_id,),
        ).fetchone()
        return dict(row) if row else None
    
