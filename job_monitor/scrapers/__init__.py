"""
ATS scrapers. Every scraper function takes a company dict (from companies.json)
and returns a list of normalized job postings:

{
    "external_id": str,      # stable ID unique within this company, used for dedup
    "title": str,
    "location": str | None,
    "employment_type": str | None,
    "experience": str | None,
    "department": str | None,
    "url": str,              # direct application link
    "posted_at": str | None, # ISO 8601 if the source provides it
}
"""

from . import greenhouse, lever, ashby, smartrecruiters, workday, generic_html

DISPATCH = {
    "greenhouse": greenhouse.fetch,
    "lever": lever.fetch,
    "ashby": ashby.fetch,
    "smartrecruiters": smartrecruiters.fetch,
    "workday": workday.fetch,
    "generic_html": generic_html.fetch,
}


def fetch_jobs(company):
    source_type = company.get("source_type")
    fn = DISPATCH.get(source_type)
    if fn is None:
        raise ValueError(f"Unknown source_type '{source_type}' for company {company.get('name')}")
    return fn(company)
