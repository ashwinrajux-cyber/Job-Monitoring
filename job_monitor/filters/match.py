"""
Matches a job title against the enabled categories in roles.json.

A title matches a category if it contains at least one of the category's
include_keywords (case-insensitive substring match) and none of its
exclude_keywords. The first matching enabled category wins.
"""


def match_category(title, categories):
    if not title:
        return None
    lowered = title.lower()
    for cat in categories:
        if not cat.get("enabled"):
            continue
        includes = cat.get("include_keywords", [])
        excludes = cat.get("exclude_keywords", [])
        if any(kw in lowered for kw in includes) and not any(kw in lowered for kw in excludes):
            return cat["key"]
    return None


def enabled_categories(categories):
    return [c for c in categories if c.get("enabled")]
