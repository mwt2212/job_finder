from typing import Any, Dict, List, Tuple


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _warn_unknown_top_level(data: Dict[str, Any], allowed: set[str], warnings: List[str], label: str) -> None:
    for key in data.keys():
        if key not in allowed:
            warnings.append(f"{label}: unknown key '{key}'")


def validate_resume_profile(data: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    allowed_keys = {
        "education",
        "experience",
        "skills",
        "target_roles",
        "roles_to_avoid",
        "constraints",
        "career_goal",
        "schema_version",
    }
    _warn_unknown_top_level(data, allowed_keys, warnings, "resume_profile")

    skills = _as_list(data.get("skills"))
    target_roles = _as_list(data.get("target_roles"))

    if not any(str(s).strip() for s in skills):
        errors.append("resume_profile.skills must contain at least one non-empty value")
    if not any(str(r).strip() for r in target_roles):
        errors.append("resume_profile.target_roles must contain at least one non-empty value")

    return (len(errors) == 0, errors, warnings)


def validate_preferences(data: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    allowed_keys = {
        "profile_version",
        "search_filters",
        "hard_constraints",
        "workplace_preferences",
        "ranking_weights",
        "red_flag_keywords",
        "output",
        "industry_preferences",
        "role_preferences",
        "qualification",
        "employment",
        "travel",
        "tuning",
        "schema_version",
    }
    _warn_unknown_top_level(data, allowed_keys, warnings, "preferences")

    qualification = _as_dict(data.get("qualification"))
    min_match_score = qualification.get("min_match_score")
    if min_match_score is None:
        errors.append("preferences.qualification.min_match_score is required")
    elif not _is_number(min_match_score):
        errors.append("preferences.qualification.min_match_score must be numeric")
    elif not (0.35 <= float(min_match_score) <= 0.85):
        errors.append("preferences.qualification.min_match_score must be in range [0.35, 0.85]")

    hard_constraints = _as_dict(data.get("hard_constraints"))
    min_salary = hard_constraints.get("min_base_salary_usd")
    if min_salary not in (None, ""):
        if isinstance(min_salary, bool):
            errors.append("preferences.hard_constraints.min_base_salary_usd must be an integer >= 0")
        elif isinstance(min_salary, float) and not min_salary.is_integer():
            errors.append("preferences.hard_constraints.min_base_salary_usd must be an integer >= 0")
        elif not _is_number(min_salary) or int(min_salary) < 0:
            errors.append("preferences.hard_constraints.min_base_salary_usd must be an integer >= 0")

    return (len(errors) == 0, errors, warnings)


def validate_shortlist_rules(data: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    allowed_keys = {
        "target_n",
        "hard_reject_patterns",
        "not_entry_level_patterns",
        "optional_reject_patterns",
        "title_boosts",
        "company_penalties",
        "workplace_score",
        "recency_scoring",
        "sales_adjacent_penalty",
        "healthcare_penalty",
        "wrong_field_penalty",
        "schema_version",
    }
    _warn_unknown_top_level(data, allowed_keys, warnings, "shortlist_rules")

    workplace = _as_dict(data.get("workplace_score"))
    for key in ("remote", "hybrid", "onsite", "unknown"):
        if key not in workplace:
            errors.append(f"shortlist_rules.workplace_score.{key} is required")
        elif not _is_number(workplace.get(key)):
            errors.append(f"shortlist_rules.workplace_score.{key} must be numeric")

    for key in ("sales_adjacent_penalty", "healthcare_penalty", "wrong_field_penalty"):
        value = data.get(key)
        if value is None:
            errors.append(f"shortlist_rules.{key} is required")
            continue
        if not _is_number(value):
            errors.append(f"shortlist_rules.{key} must be numeric")
            continue
        if not (-50 <= float(value) <= 0):
            errors.append(f"shortlist_rules.{key} should be between -50 and 0")

    return (len(errors) == 0, errors, warnings)


def _coerce_searches(searches: Any) -> Dict[str, Dict[str, Any]]:
    if isinstance(searches, dict):
        out: Dict[str, Dict[str, Any]] = {}
        for label, cfg in searches.items():
            if isinstance(cfg, dict):
                out[str(label)] = cfg
        return out
    if isinstance(searches, list):
        out = {}
        for item in searches:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or "").strip()
            if not label:
                continue
            cfg = {k: v for k, v in item.items() if k != "label"}
            out[label] = cfg
        return out
    return {}


def validate_searches(data: Any) -> Tuple[bool, List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    searches = _coerce_searches(data)
    if not searches:
        errors.append("searches must include at least one search")
        return (False, errors, warnings)

    labels_seen = set()
    for label, cfg in searches.items():
        normalized = label.strip().lower()
        if normalized in labels_seen:
            errors.append(f"searches has duplicate label '{label}'")
        labels_seen.add(normalized)

        url = str(cfg.get("url") or "").strip()
        location_label = str(cfg.get("location_label") or "").strip()

        if not label.strip():
            errors.append("searches entry label must be non-empty")
        if not url:
            errors.append(f"searches['{label}'].url is required")
        elif "linkedin.com/jobs/search" not in url.lower():
            errors.append(f"searches['{label}'].url must look like a LinkedIn jobs search URL")
        if not location_label:
            errors.append(f"searches['{label}'].location_label is required")

        for key in cfg.keys():
            if key not in {"url", "location_label", "keywords", "schema_version"}:
                warnings.append(f"searches['{label}']: unknown key '{key}'")

    return (len(errors) == 0, errors, warnings)


def validate_all(
    resume_profile: Dict[str, Any],
    preferences: Dict[str, Any],
    shortlist_rules: Dict[str, Any],
    searches: Any,
) -> Dict[str, Any]:
    resume_ok, resume_errors, resume_warnings = validate_resume_profile(resume_profile)
    prefs_ok, prefs_errors, prefs_warnings = validate_preferences(preferences)
    rules_ok, rules_errors, rules_warnings = validate_shortlist_rules(shortlist_rules)
    searches_ok, searches_errors, searches_warnings = validate_searches(searches)

    results = {
        "resume_profile": {"ok": resume_ok, "errors": resume_errors, "warnings": resume_warnings},
        "preferences": {"ok": prefs_ok, "errors": prefs_errors, "warnings": prefs_warnings},
        "shortlist_rules": {"ok": rules_ok, "errors": rules_errors, "warnings": rules_warnings},
        "searches": {"ok": searches_ok, "errors": searches_errors, "warnings": searches_warnings},
    }
    results["ok"] = all(v["ok"] for k, v in results.items() if k != "ok")
    return results


def linkedin_url_for_search(label: str, location_label: str, keywords: str = "") -> str:
    from urllib.parse import quote_plus

    base = "https://www.linkedin.com/jobs/search/"
    terms = keywords.strip() if keywords else label.strip()
    params = [("keywords", terms), ("location", location_label.strip()), ("sortBy", "DD")]
    query = "&".join(f"{k}={quote_plus(v)}" for k, v in params if v)
    return f"{base}?{query}" if query else base
