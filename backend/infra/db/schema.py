from typing import Callable

SCHEMA_SQL = """
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


def init_db(connect_fn: Callable[[], object]) -> None:
    with connect_fn() as conn:
        conn.executescript(SCHEMA_SQL)
        for stmt in [
            "ALTER TABLE jobs ADD COLUMN first_seen_at TEXT",
            "ALTER TABLE jobs ADD COLUMN last_seen_at TEXT",
            "ALTER TABLE jobs ADD COLUMN scraped_at TEXT",
        ]:
            try:
                conn.execute(stmt)
            except Exception:
                pass
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
