import pytest

from job_monitor.storage import db


@pytest.fixture
def conn():
    connection = db.get_conn(":memory:")
    yield connection
    connection.close()


def make_job(external_id="job-1", title="Senior Product Designer"):
    return {
        "external_id": external_id,
        "title": title,
        "location": "Remote",
        "employment_type": "Full-time",
        "experience": "Senior",
        "department": "Design",
        "url": "https://example.com/job",
        "posted_at": "2026-07-27T00:00:00Z",
    }


def test_insert_job_dedupes_on_company_and_external_id(conn):
    db.ensure_company(conn, "Acme", "greenhouse")
    job = make_job()
    first_id = db.insert_job(conn, "Acme", job, "product_design_ux", "greenhouse ATS", "2026-07-27T00:00:00Z")
    second_id = db.insert_job(conn, "Acme", job, "product_design_ux", "greenhouse ATS", "2026-07-27T00:00:01Z")

    assert first_id is not None
    assert second_id is None
    assert db.job_exists(conn, "Acme", "job-1")


def test_mark_notified_success_flips_flag_and_logs(conn):
    db.ensure_company(conn, "Acme", "greenhouse")
    job_id = db.insert_job(conn, "Acme", make_job(), "product_design_ux", "greenhouse ATS", "2026-07-27T00:00:00Z")

    db.mark_notified(conn, job_id, "2026-07-27T00:00:01Z", success=True)

    row = conn.execute("SELECT notified FROM jobs WHERE id=?", (job_id,)).fetchone()
    assert row["notified"] == 1
    history = conn.execute("SELECT success FROM notifications WHERE job_id=?", (job_id,)).fetchall()
    assert [dict(r)["success"] for r in history] == [1]


def test_mark_notified_failure_keeps_job_unnotified_but_logs_attempt(conn):
    db.ensure_company(conn, "Acme", "greenhouse")
    job_id = db.insert_job(conn, "Acme", make_job(), "product_design_ux", "greenhouse ATS", "2026-07-27T00:00:00Z")

    db.mark_notified(conn, job_id, "2026-07-27T00:00:01Z", success=False, error="boom")

    row = conn.execute("SELECT notified FROM jobs WHERE id=?", (job_id,)).fetchone()
    assert row["notified"] == 0
    history = conn.execute("SELECT success, error FROM notifications WHERE job_id=?", (job_id,)).fetchall()
    assert [dict(r) for r in history] == [{"success": 0, "error": "boom"}]


def test_get_unnotified_jobs_excludes_never_attempted_baseline_jobs(conn):
    db.ensure_company(conn, "Acme", "greenhouse")
    db.insert_job(conn, "Acme", make_job(), "product_design_ux", "greenhouse ATS", "2026-07-27T00:00:00Z")

    assert db.get_unnotified_jobs(conn) == []


def test_get_unnotified_jobs_includes_jobs_with_a_failed_attempt(conn):
    db.ensure_company(conn, "Acme", "greenhouse")
    job_id = db.insert_job(conn, "Acme", make_job(), "product_design_ux", "greenhouse ATS", "2026-07-27T00:00:00Z")
    db.mark_notified(conn, job_id, "2026-07-27T00:00:01Z", success=False, error="boom")

    pending = db.get_unnotified_jobs(conn)
    assert [p["id"] for p in pending] == [job_id]


def test_get_unnotified_jobs_respects_max_attempts_cap(conn):
    db.ensure_company(conn, "Acme", "greenhouse")
    job_id = db.insert_job(conn, "Acme", make_job(), "product_design_ux", "greenhouse ATS", "2026-07-27T00:00:00Z")
    for _ in range(3):
        db.mark_notified(conn, job_id, "2026-07-27T00:00:01Z", success=False, error="boom")

    assert db.get_unnotified_jobs(conn, max_attempts=3) == []
    assert [p["id"] for p in db.get_unnotified_jobs(conn, max_attempts=4)] == [job_id]
    assert [p["id"] for p in db.get_unnotified_jobs(conn)] == [job_id]  # no cap = unbounded retry


def test_get_permanently_failed_jobs_only_returns_jobs_past_the_cap(conn):
    db.ensure_company(conn, "Acme", "greenhouse")
    stuck_id = db.insert_job(conn, "Acme", make_job("job-stuck"), "product_design_ux", "greenhouse ATS", "2026-07-27T00:00:00Z")
    retrying_id = db.insert_job(conn, "Acme", make_job("job-retrying"), "product_design_ux", "greenhouse ATS", "2026-07-27T00:00:00Z")

    for _ in range(3):
        db.mark_notified(conn, stuck_id, "2026-07-27T00:00:01Z", success=False, error="boom")
    db.mark_notified(conn, retrying_id, "2026-07-27T00:00:01Z", success=False, error="boom")

    stuck = db.get_permanently_failed_jobs(conn, max_attempts=3)
    assert [j["id"] for j in stuck] == [stuck_id]
