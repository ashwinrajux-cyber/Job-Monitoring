import requests

TIMEOUT = 15
PAGE_SIZE = 100
MAX_PAGES = 5  # safety cap; 500 postings is far more than any single company needs per cycle


def fetch(company):
    company_id = company["identifier"]
    jobs = []
    offset = 0
    for _ in range(MAX_PAGES):
        url = (
            f"https://api.smartrecruiters.com/v1/companies/{company_id}/postings"
            f"?limit={PAGE_SIZE}&offset={offset}"
        )
        resp = requests.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("content", [])
        for j in content:
            loc = j.get("location") or {}
            employment = (j.get("typeOfEmployment") or {}).get("label")
            experience = (j.get("experienceLevel") or {}).get("label")
            dept = (j.get("department") or {}).get("label")
            jobs.append({
                "external_id": str(j["id"]),
                "title": (j.get("name") or "").strip(),
                "location": loc.get("fullLocation") or _fallback_location(loc),
                "employment_type": employment,
                "experience": experience,
                "department": dept,
                "url": f"https://jobs.smartrecruiters.com/{company_id}/{j['id']}",
                "posted_at": j.get("releasedDate"),
            })
        offset += PAGE_SIZE
        if offset >= data.get("totalFound", 0):
            break
    return jobs


def _fallback_location(loc):
    parts = [loc.get("city"), loc.get("region"), loc.get("country")]
    return ", ".join(p for p in parts if p) or None
