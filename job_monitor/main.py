"""
Entry point for one monitoring cycle: fetch every enabled company's jobs,
filter to configured role categories, dedup against the DB, notify on
genuinely new matches, and regenerate the dashboard.

Run manually with `python -m job_monitor.main`, or on a schedule via
.github/workflows/monitor.yml (every 10 minutes, 24/7, independent of your
laptop).
"""
import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = Path(__file__).resolve().parent / "config"
DATA_DIR = ROOT / "data"
DASHBOARD_DIR = ROOT / "docs"
DB_PATH = DATA_DIR / "jobs.db"

sys.path.insert(0, str(ROOT))

from job_monitor.scrapers import fetch_jobs  # noqa: E402
from job_monitor.filters.match import match_category  # noqa: E402
from job_monitor.storage import db  # noqa: E402
from job_monitor.notify import telegram  # noqa: E402
from job_monitor.dashboard.generate import render  # noqa: E402

MAX_ATTEMPTS = 2
RETRY_DELAY_SECONDS = 3


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def now_local_display():
    return datetime.now().astimezone().strftime("%Y-%m-%d %I:%M %p %Z")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_with_retry(company):
    last_err = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return fetch_jobs(company), None
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < MAX_ATTEMPTS:
                time.sleep(RETRY_DELAY_SECONDS)
    return None, last_err


def process_company(conn, company, categories):
    name = company["name"]
    source_type = company["source_type"]
    db.ensure_company(conn, name, source_type)

    jobs, err = fetch_with_retry(company)
    ts = now_iso()

    if err is not None:
        db.record_company_run(conn, name, ts, success=False, error=err)
        print(f"[ERROR] {name}: {err}")
        return {"company": name, "new_jobs": 0, "notified": 0, "error": str(err)}

    baseline_done = db.is_baseline_done(conn, name)
    source_label = company.get("career_page") or f"{source_type} ATS"

    new_count = 0
    notified_count = 0
    for job in jobs:
        category = match_category(job.get("title"), categories)
        if not category:
            continue
        if db.job_exists(conn, name, job["external_id"]):
            continue

        job_id = db.insert_job(conn, name, job, category, source_label, ts)
        if job_id is None:
            continue  # race/duplicate
        new_count += 1

        if baseline_done:
            job_with_source = dict(job, source=source_label)
            category_label = next((c["label"] for c in categories if c["key"] == category), category)
            success, notify_err = telegram.send(name, job_with_source, category_label, now_local_display())
            db.mark_notified(conn, job_id, now_iso(), success, notify_err)
            if success:
                notified_count += 1
            else:
                print(f"[NOTIFY-FAIL] {name} / {job['title']}: {notify_err}")

    if not baseline_done:
        db.mark_baseline_done(conn, name)
        print(f"[BASELINE] {name}: stored {new_count} existing matching job(s) without notifying")

    db.record_company_run(conn, name, ts, success=True)
    return {"company": name, "new_jobs": new_count, "notified": notified_count, "error": None}


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)

    companies = load_json(CONFIG_DIR / "companies.json")
    roles = load_json(CONFIG_DIR / "roles.json")
    categories = roles["categories"]

    conn = db.get_conn(str(DB_PATH))

    results = []
    for company in companies:
        if not company.get("enabled", True):
            continue
        try:
            results.append(process_company(conn, company, categories))
        except Exception:  # noqa: BLE001 - never let one bad company kill the whole run
            traceback.print_exc()
            results.append({"company": company.get("name"), "new_jobs": 0, "notified": 0, "error": "unexpected failure"})

    render(conn, str(DASHBOARD_DIR / "index.html"))
    conn.close()

    total_new = sum(r["new_jobs"] for r in results)
    total_notified = sum(r["notified"] for r in results)
    errors = [r for r in results if r["error"]]
    print(f"\nRun complete: {len(results)} companies checked, {total_new} new matching job(s), "
          f"{total_notified} notification(s) sent, {len(errors)} error(s).")
    if errors:
        for r in errors:
            print(f"  - {r['company']}: {r['error']}")


if __name__ == "__main__":
    main()
