import pytest

from job_monitor import main as main_module
from job_monitor.storage import db

CATEGORIES = [{"key": "product_design_ux", "label": "Product Design/UX"}]


def make_job(external_id="job-1"):
    return {
        "external_id": external_id,
        "title": "Senior Product Designer",
        "location": "Remote",
        "employment_type": "Full-time",
        "experience": "Senior",
        "department": "Design",
        "url": "https://example.com/job",
        "posted_at": "2026-07-27T00:00:00Z",
    }


@pytest.fixture
def conn():
    connection = db.get_conn(":memory:")
    yield connection
    connection.close()


def insert_failed_job(conn, external_id="job-1", attempts=1):
    db.ensure_company(conn, "Acme", "greenhouse")
    job_id = db.insert_job(conn, "Acme", make_job(external_id), "product_design_ux", "greenhouse ATS", "2026-07-27T00:00:00Z")
    for _ in range(attempts):
        db.mark_notified(conn, job_id, "2026-07-27T00:00:01Z", success=False, error="boom")
    return job_id


def test_retry_resends_a_previously_failed_job_and_succeeds(conn, monkeypatch):
    insert_failed_job(conn, attempts=1)
    monkeypatch.setattr(main_module.telegram, "send", lambda *a, **k: (True, None))

    pending_count, sent_count = main_module.retry_failed_notifications(conn, CATEGORIES)

    assert (pending_count, sent_count) == (1, 1)
    assert db.get_unnotified_jobs(conn) == []  # now notified, no longer a retry candidate


def test_retry_stops_after_hitting_the_attempt_cap(conn, monkeypatch):
    insert_failed_job(conn, attempts=main_module.MAX_NOTIFY_ATTEMPTS)
    calls = []
    monkeypatch.setattr(main_module.telegram, "send", lambda *a, **k: calls.append(1) or (False, "still broken"))

    pending_count, sent_count = main_module.retry_failed_notifications(conn, CATEGORIES)

    assert (pending_count, sent_count) == (0, 0)
    assert calls == []  # never retried - already past the cap


def test_permanently_failed_jobs_surfaced_once_cap_is_hit(conn):
    stuck_id = insert_failed_job(conn, external_id="job-stuck", attempts=main_module.MAX_NOTIFY_ATTEMPTS)
    insert_failed_job(conn, external_id="job-retrying", attempts=1)

    stuck = db.get_permanently_failed_jobs(conn, main_module.MAX_NOTIFY_ATTEMPTS)

    assert [j["id"] for j in stuck] == [stuck_id]


def test_dry_run_never_calls_telegram_or_mutates_notification_state(conn, monkeypatch):
    insert_failed_job(conn, attempts=1)
    calls = []
    monkeypatch.setattr(main_module.telegram, "send", lambda *a, **k: calls.append(1) or (True, None))
    monkeypatch.setattr(main_module, "DRY_RUN", True)

    pending_count, sent_count = main_module.retry_failed_notifications(conn, CATEGORIES)

    assert calls == []
    assert sent_count == 0
    assert len(db.get_unnotified_jobs(conn)) == 1  # untouched - still pending for a real run later
