from job_monitor.filters.match import match_category

CATEGORIES = [
    {
        "key": "product_design_ux",
        "label": "Product Design/UX",
        "enabled": True,
        "include_keywords": ["product designer", "ux designer", "ui/ux"],
        "exclude_keywords": ["ux writer"],
    },
    {
        "key": "product_manager",
        "label": "Product Manager",
        "enabled": False,
        "include_keywords": ["product manager"],
        "exclude_keywords": [],
    },
]


def test_matches_enabled_category_case_insensitively():
    assert match_category("Senior Product Designer", CATEGORIES) == "product_design_ux"


def test_no_match_returns_none():
    assert match_category("Backend Software Engineer", CATEGORIES) is None


def test_exclude_keyword_blocks_an_otherwise_matching_title():
    assert match_category("UX Writer", CATEGORIES) is None


def test_disabled_category_is_never_matched():
    assert match_category("Product Manager, Growth", CATEGORIES) is None


def test_empty_title_returns_none():
    assert match_category("", CATEGORIES) is None
    assert match_category(None, CATEGORIES) is None
