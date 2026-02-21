CURRENT_SCHEMA_VERSION = "1.0"

DEFAULT_PREFERENCES = {
    "search_filters": {"radius_miles": 10, "posted_within_hours": 24},
    "hard_constraints": {"min_base_salary_usd": None},
    "qualification": {"min_match_score": 0.55},
}

DEFAULT_SHORTLIST_RULES = {
    "workplace_score": {"remote": 10, "hybrid": 12, "onsite": 6, "unknown": 2},
    "sales_adjacent_penalty": -10,
    "healthcare_penalty": -10,
    "wrong_field_penalty": -8,
}
