import json
from typing import Any, Callable, Dict, Iterable, List, Optional


def upsert_job(connect_fn: Callable[[], object], now_fn: Callable[[], str], job: Dict[str, Any]) -> int:
    now = now_fn()
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
    with connect_fn() as conn:
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


def upsert_shortlist_score(connect_fn: Callable[[], object], now_fn: Callable[[], str], job_id: int, score: float, reasons: List[str], qualification_score: float) -> None:
    with connect_fn() as conn:
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
            (job_id, score, json.dumps(reasons), qualification_score, now_fn()),
        )


def upsert_ai_eval(connect_fn: Callable[[], object], now_fn: Callable[[], str], job_id: int, eval_json: Dict[str, Any], model: str) -> None:
    fit_score = int(eval_json.get("fit_score", 0) or 0)
    next_action = eval_json.get("next_action") or ""
    with connect_fn() as conn:
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
            (job_id, json.dumps(eval_json), model, fit_score, next_action, now_fn()),
        )


def upsert_rating(connect_fn: Callable[[], object], now_fn: Callable[[], str], job_id: int, stars: int, notes: str, tags: List[str]) -> None:
    with connect_fn() as conn:
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
            (job_id, stars, notes, json.dumps(tags), now_fn()),
        )


def upsert_status(connect_fn: Callable[[], object], now_fn: Callable[[], str], job_id: int, status: str) -> None:
    with connect_fn() as conn:
        conn.execute(
            """
            INSERT INTO status (job_id, status, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                status=excluded.status,
                created_at=excluded.created_at
            """,
            (job_id, status, now_fn()),
        )


def upsert_shortlist_feedback(connect_fn: Callable[[], object], now_fn: Callable[[], str], job_id: int, verdict: str, reason: str) -> None:
    with connect_fn() as conn:
        conn.execute(
            """
            INSERT INTO shortlist_feedback (job_id, verdict, reason, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                verdict=excluded.verdict,
                reason=excluded.reason,
                created_at=excluded.created_at
            """,
            (job_id, verdict, reason, now_fn()),
        )


def get_shortlist_feedback(connect_fn: Callable[[], object], job_id: int) -> Optional[Dict[str, Any]]:
    with connect_fn() as conn:
        row = conn.execute(
            """
            SELECT job_id, verdict, reason, created_at
            FROM shortlist_feedback
            WHERE job_id = ?
            """,
            (job_id,),
        ).fetchone()
        return dict(row) if row else None


def upsert_ai_eval_feedback(connect_fn: Callable[[], object], now_fn: Callable[[], str], job_id: int, correct_bucket: str, reasoning_quality: int) -> None:
    with connect_fn() as conn:
        conn.execute(
            """
            INSERT INTO ai_eval_feedback (job_id, correct_bucket, reasoning_quality, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                correct_bucket=excluded.correct_bucket,
                reasoning_quality=excluded.reasoning_quality,
                created_at=excluded.created_at
            """,
            (job_id, correct_bucket, reasoning_quality, now_fn()),
        )


def get_ai_eval_feedback(connect_fn: Callable[[], object], job_id: int) -> Optional[Dict[str, Any]]:
    with connect_fn() as conn:
        row = conn.execute(
            """
            SELECT job_id, correct_bucket, reasoning_quality, created_at
            FROM ai_eval_feedback
            WHERE job_id = ?
            """,
            (job_id,),
        ).fetchone()
        return dict(row) if row else None


def update_bucket(connect_fn: Callable[[], object], job_id: int, bucket: str) -> None:
    with connect_fn() as conn:
        conn.execute("UPDATE jobs SET bucket = ? WHERE id = ?", (bucket, job_id))


def update_workplace(connect_fn: Callable[[], object], job_id: int, workplace: str) -> None:
    with connect_fn() as conn:
        conn.execute("UPDATE jobs SET workplace = ? WHERE id = ?", (workplace, job_id))


def list_jobs(
    connect_fn: Callable[[], object],
    *,
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
    with connect_fn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def get_job(connect_fn: Callable[[], object], job_id: int) -> Optional[Dict[str, Any]]:
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
    with connect_fn() as conn:
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


def insert_run(connect_fn: Callable[[], object], step: str, status: str, started_at: str, ended_at: str, log: str) -> None:
    with connect_fn() as conn:
        conn.execute(
            "INSERT INTO runs (step, status, started_at, ended_at, log) VALUES (?, ?, ?, ?, ?)",
            (step, status, started_at, ended_at, log),
        )


def insert_import(connect_fn: Callable[[], object], now_fn: Callable[[], str], source: str, counts: Dict[str, Any]) -> None:
    with connect_fn() as conn:
        conn.execute(
            "INSERT INTO imports (source, counts, created_at) VALUES (?, ?, ?)",
            (source, json.dumps(counts), now_fn()),
        )


def all_job_urls(connect_fn: Callable[[], object]) -> Iterable[str]:
    with connect_fn() as conn:
        rows = conn.execute("SELECT url FROM jobs").fetchall()
        return [r["url"] for r in rows]


def insert_cover_letter(connect_fn: Callable[[], object], now_fn: Callable[[], str], job_id: int, content: str, feedback: str, model: str) -> int:
    with connect_fn() as conn:
        cur = conn.execute(
            """
            INSERT INTO cover_letters (job_id, content, feedback, model, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (job_id, content, feedback, model, now_fn()),
        )
        return int(cur.lastrowid)


def update_cover_letter(connect_fn: Callable[[], object], cover_id: int, content: str, feedback: str) -> None:
    with connect_fn() as conn:
        conn.execute(
            """
            UPDATE cover_letters
            SET content = ?, feedback = ?
            WHERE id = ?
            """,
            (content, feedback, cover_id),
        )


def list_cover_letters(connect_fn: Callable[[], object], job_id: int) -> List[Dict[str, Any]]:
    with connect_fn() as conn:
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


def get_cover_letter(connect_fn: Callable[[], object], cover_id: int) -> Optional[Dict[str, Any]]:
    with connect_fn() as conn:
        row = conn.execute(
            """
            SELECT id, job_id, content, feedback, model, created_at
            FROM cover_letters
            WHERE id = ?
            """,
            (cover_id,),
        ).fetchone()
        return dict(row) if row else None
