import requests

TIMEOUT = 20
PAGE_SIZE = 20  # some Workday tenants reject larger page sizes with a 400
MAX_PAGES = 15  # cap at 300 postings/company/cycle


def fetch(company):
    ident = company["identifier"]
    tenant = ident["tenant"]
    wd_host = ident["wd_host"]
    site = ident["site"]

    base = f"https://{tenant}.{wd_host}.myworkdayjobs.com"
    api_url = f"{base}/wday/cxs/{tenant}/{site}/jobs"

    jobs = []
    offset = 0
    for page in range(MAX_PAGES):
        body = {"appliedFacets": {}, "limit": PAGE_SIZE, "offset": offset, "searchText": ""}
        resp = requests.post(api_url, json=body, timeout=TIMEOUT)
        if resp.status_code == 400 and page > 0:
            # Some tenants cap total offset/pagination depth - stop, keep what we already got.
            break
        resp.raise_for_status()
        data = resp.json()
        postings = data.get("jobPostings", [])
        for j in postings:
            external_path = j.get("externalPath", "")
            jobs.append({
                "external_id": external_path or j.get("bulletFields", [None])[0],
                "title": (j.get("title") or "").strip(),
                "location": j.get("locationsText"),
                "employment_type": None,
                "experience": None,
                "department": None,
                "url": f"{base}/{site}{external_path}",
                "posted_at": j.get("postedOn"),  # relative text like "Posted Today"; Workday doesn't expose ISO dates here
            })
        offset += PAGE_SIZE
        if offset >= data.get("total", 0):
            break
    return jobs
