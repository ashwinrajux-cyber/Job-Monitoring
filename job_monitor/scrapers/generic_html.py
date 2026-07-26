"""
Best-effort fallback for career pages that aren't on a known ATS API.

This is inherently fragile: it just pulls every link on the page whose visible
text looks like a job title and lets the keyword filter in filters/match.py
decide relevance. It works reasonably well for simple static listing pages,
but sites that render their job list via client-side JS (React/Vue without a
server-rendered fallback) will return no results here - if that happens for
one of your companies, look for their underlying ATS (check the network tab
for calls to greenhouse/lever/ashby/smartrecruiters/myworkdayjobs.com domains)
and use that source_type instead; it will be far more reliable.
"""
import hashlib
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

TIMEOUT = 15
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; job-monitor/1.0)"}
MIN_TEXT_LEN = 4
MAX_TEXT_LEN = 120
SKIP_SCHEMES = ("mailto:", "javascript:", "tel:", "#")


def fetch(company):
    url = company["identifier"]
    resp = requests.get(url, timeout=TIMEOUT, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    jobs = []
    seen_hrefs = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(SKIP_SCHEMES):
            continue
        text = " ".join(a.get_text(separator=" ").split()).strip()
        if not (MIN_TEXT_LEN <= len(text) <= MAX_TEXT_LEN):
            continue
        absolute = urljoin(url, href)
        if absolute in seen_hrefs:
            continue
        seen_hrefs.add(absolute)
        jobs.append({
            "external_id": hashlib.sha256(absolute.encode()).hexdigest()[:16],
            "title": text,
            "location": None,
            "employment_type": None,
            "experience": None,
            "department": None,
            "url": absolute,
            "posted_at": None,
        })
    return jobs
