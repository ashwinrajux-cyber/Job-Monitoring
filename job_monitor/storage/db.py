import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    name TEXT PRIMARY KEY,
    source_type TEXT,
    baseline_done INTEGER NOT NULL DEFAULT 0,
    last_checked_at TEXT,
    last_success_at TEXT,
    last_error TEXT,
    status TEXT NOT NULL DEFAULT 'never_run'
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    external_id TEXT NOT NULL,
    title TEXT NOT NULL,
    location TEXT,
    employment_type TEXT,
    experience TEXT,
    department TEXT,
    category TEXT NOT NULL,
    url TEXT,
    source TEXT,
    posted_at TEXT,
    first_seen_at TEXT NOT NULL,
    notified INTEGER NOT NULL DEFAULT 0,
    UNIQUE(company_name, external_id)
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    sent_at TEXT NOT NULL,
    success INTEGER NOT NULL,
    error TEXT,
    FOREIGN KEY(job_id) REFERENCES jobs(id)
);

CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company_name);
CREATE INDEX IF NOT EXISTS idx_jobs_first_seen ON jobs(first_seen_at);
"""


def get_conn(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def ensure_company(conn, name, source_type):
    conn.execute(
        """INSERT INTO companies (name, source_type, status)
           VALUES (?, ?, 'never_run')
           ON CONFLICT(name) DO UPDATE SET source_type=excluded.source_type""",
        (name, source_type),
    )
    conn.commit()


def is_baseline_done(conn, name):
    row = conn.execute("SELECT baseline_done FROM companies WHERE name=?", (name,)).fetchone()
    return bool(row and row["baseline_done"])


def mark_baseline_done(conn, name):
    conn.execute("UPDATE companies SET baseline_done=1 WHERE name=?", (name,))
    conn.commit()


def record_company_run(conn, name, now_iso, success, error=None):
    if success:
        conn.execute(
            """UPDATE companies SET last_checked_at=?, last_success_at=?, status='ok', last_error=NULL
               WHERE name=?""",
            (now_iso, now_iso, name),
        )
    else:
        conn.execute(
            """UPDATE companies SET last_checked_at=?, status='error', last_error=?
               WHERE name=?""",
            (now_iso, str(error), name),
        )
    conn.commit()


def job_exists(conn, company_name, external_id):
    row = conn.execute(
        "SELECT 1 FROM jobs WHERE company_name=? AND external_id=?",
        (company_name, external_id),
    ).fetchone()
    return row is not None


def insert_job(conn, company_name, job, category, source, now_iso):
    """Insert a new job. Returns the row id, or None if it already existed (duplicate)."""
    try:
        cur = conn.execute(
            """INSERT INTO jobs
               (company_name, external_id, title, location, employment_type, experience,
                department, category, url, source, posted_at, first_seen_at, notified)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
            (
                company_name,
                job["external_id"],
                job["title"],
                job.get("location"),
                job.get("employment_type"),
                job.get("experience"),
                job.get("department"),
                category,
                job.get("url"),
                source,
                job.get("posted_at"),
                now_iso,
            ),
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None


def mark_notified(conn, job_id, now_iso, success, error=None):
    conn.execute("UPDATE jobs SET notified=1 WHERE id=?", (job_id,))
    conn.execute(
        "INSERT INTO notifications (job_id, sent_at, success, error) VALUES (?, ?, ?, ?)",
        (job_id, now_iso, 1 if success else 0, error),
    )
    conn.commit()


# ---- read helpers for the dashboard ----

def get_stats(conn):
    total_companies = conn.execute("SELECT COUNT(*) c FROM companies").fetchone()["c"]
    active_companies = conn.execute(
        "SELECT COUNT(*) c FROM companies WHERE status='ok'"
    ).fetchone()["c"]
    error_companies = conn.execute(
        "SELECT COUNT(*) c FROM companies WHERE status='error'"
    ).fetchone()["c"]
    total_jobs = conn.execute("SELECT COUNT(*) c FROM jobs").fetchone()["c"]
    total_notified = conn.execute("SELECT COUNT(*) c FROM jobs WHERE notified=1").fetchone()["c"]
    last_success = conn.execute(
        "SELECT MAX(last_success_at) t FROM companies"
    ).fetchone()["t"]
    return {
        "total_companies": total_companies,
        "active_companies": active_companies,
        "error_companies": error_companies,
        "total_jobs": total_jobs,
        "total_notified": total_notified,
        "last_success_at": last_success,
    }


def get_recent_jobs(conn, limit=200):
    rows = conn.execute(
        """SELECT * FROM jobs ORDER BY first_seen_at DESC LIMIT ?""", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


def get_notification_history(conn, limit=200):
    rows = conn.execute(
        """SELECT n.sent_at, n.success, n.error, j.company_name, j.title, j.url
           FROM notifications n JOIN jobs j ON j.id = n.job_id
           ORDER BY n.sent_at DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_company_status(conn):
    rows = conn.execute(
        """SELECT name, source_type, baseline_done, last_checked_at, last_success_at,
                  last_error, status FROM companies ORDER BY name"""
    ).fetchall()
    return [dict(r) for r in rows]
