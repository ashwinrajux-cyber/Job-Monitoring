import requests

TIMEOUT = 15


def fetch(company):
    token = company["identifier"]
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
    resp = requests.get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for j in data.get("jobs", []):
        departments = j.get("departments") or []
        dept = departments[0]["name"] if departments else None
        jobs.append({
            "external_id": str(j["id"]),
            "title": j.get("title", "").strip(),
            "location": (j.get("location") or {}).get("name"),
            "employment_type": None,
            "experience": None,
            "department": dept,
            "url": j.get("absolute_url"),
            "posted_at": j.get("updated_at") or j.get("first_published"),
        })
    return jobs
