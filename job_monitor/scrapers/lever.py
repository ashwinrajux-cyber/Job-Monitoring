import requests

TIMEOUT = 15


def fetch(company):
    slug = company["identifier"]
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    resp = requests.get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for j in data:
        categories = j.get("categories") or {}
        jobs.append({
            "external_id": str(j["id"]),
            "title": (j.get("text") or "").strip(),
            "location": categories.get("location"),
            "employment_type": categories.get("commitment"),
            "experience": None,
            "department": categories.get("team") or categories.get("department"),
            "url": j.get("hostedUrl") or j.get("applyUrl"),
            "posted_at": _to_iso(j.get("createdAt")),
        })
    return jobs


def _to_iso(epoch_ms):
    if not epoch_ms:
        return None
    import datetime
    try:
        return datetime.datetime.utcfromtimestamp(epoch_ms / 1000).isoformat() + "Z"
    except (TypeError, ValueError):
        return None
