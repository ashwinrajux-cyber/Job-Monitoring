import requests

TIMEOUT = 15


def fetch(company):
    board = company["identifier"]
    url = f"https://api.ashbyhq.com/posting-api/job-board/{board}"
    resp = requests.get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for j in data.get("jobs", []):
        if not j.get("isListed", True):
            continue
        jobs.append({
            "external_id": str(j["id"]),
            "title": (j.get("title") or "").strip(),
            "location": j.get("location"),
            "employment_type": j.get("employmentType"),
            "experience": None,
            "department": j.get("department") or j.get("team"),
            "url": j.get("jobUrl") or j.get("applyUrl"),
            "posted_at": j.get("publishedAt"),
        })
    return jobs
