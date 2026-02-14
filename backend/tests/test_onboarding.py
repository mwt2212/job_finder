import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import backend.app as app
from backend.onboarding_validate import (
    validate_preferences,
    validate_resume_profile,
    validate_searches,
    validate_shortlist_rules,
)


def test_validate_resume_profile_requires_skills_and_target_roles():
    ok, errors, _warnings = validate_resume_profile({"skills": [], "target_roles": []})
    assert ok is False
    assert any("skills" in err for err in errors)
    assert any("target_roles" in err for err in errors)


def test_validate_preferences_min_match_range():
    ok, errors, _warnings = validate_preferences(
        {"qualification": {"min_match_score": 0.9}, "hard_constraints": {"min_base_salary_usd": 0}}
    )
    assert ok is False
    assert any("min_match_score" in err for err in errors)


def test_validate_shortlist_rules_requires_penalties_and_workplace():
    ok, errors, _warnings = validate_shortlist_rules({})
    assert ok is False
    assert any("workplace_score.remote" in err for err in errors)
    assert any("sales_adjacent_penalty" in err for err in errors)


def test_validate_searches_requires_linkedin_url_and_location():
    ok, errors, _warnings = validate_searches({"Test": {"url": "https://example.com", "location_label": ""}})
    assert ok is False
    assert any("LinkedIn" in err for err in errors)
    assert any("location_label" in err for err in errors)


def test_bootstrap_local_resume_uses_existing_primary(monkeypatch, tmp_path):
    resume_primary = tmp_path / "resume_profile.json"
    resume_primary.write_text(json.dumps({"skills": ["SQL"], "target_roles": ["Analyst"]}), encoding="utf-8")
    resume_local = tmp_path / "resume_profile.local.json"
    resume_example = tmp_path / "resume_profile.example.json"
    resume_example.write_text(json.dumps({"skills": ["Example"], "target_roles": ["Example"]}), encoding="utf-8")

    templates_primary = tmp_path / "cover_letter_templates.json"
    templates_primary.write_text(json.dumps({"templates": []}), encoding="utf-8")
    templates_local = tmp_path / "cover_letter_templates.local.json"
    templates_example = tmp_path / "cover_letter_templates.example.json"
    templates_example.write_text(json.dumps({"templates": [{"id": "x", "text": "example"}]}), encoding="utf-8")

    preferences_path = tmp_path / "preferences.json"
    rules_path = tmp_path / "shortlist_rules.json"
    searches_path = tmp_path / "searches.json"

    monkeypatch.setattr(app, "ARTIFACTS_DIR", tmp_path / "artifacts")
    monkeypatch.setattr(app, "RESUME_PATH", resume_primary)
    monkeypatch.setattr(app, "RESUME_LOCAL_PATH", resume_local)
    monkeypatch.setattr(app, "RESUME_EXAMPLE_PATH", resume_example)
    monkeypatch.setattr(app, "TEMPLATES_PATH", templates_primary)
    monkeypatch.setattr(app, "TEMPLATES_LOCAL_PATH", templates_local)
    monkeypatch.setattr(app, "TEMPLATES_EXAMPLE_PATH", templates_example)
    monkeypatch.setattr(app, "PREFERENCES_PATH", preferences_path)
    monkeypatch.setattr(app, "RULES_PATH", rules_path)
    monkeypatch.setattr(app, "SEARCHES_PATH", searches_path)
    monkeypatch.setattr(app, "PREFERENCES_EXAMPLE_PATH", tmp_path / "preferences.example.json")
    monkeypatch.setattr(app, "RULES_EXAMPLE_PATH", tmp_path / "shortlist_rules.example.json")
    monkeypatch.setattr(app, "SEARCHES_EXAMPLE_PATH", tmp_path / "searches.example.json")

    out = app._bootstrap_required_files()

    assert out["ok"] is True
    seeded_resume = json.loads(resume_local.read_text(encoding="utf-8"))
    assert seeded_resume["skills"] == ["SQL"]
    assert preferences_path.exists()
    assert rules_path.exists()
    assert searches_path.exists()


def test_preflight_returns_ready_false_on_failed_checks(monkeypatch):
    monkeypatch.setattr(app, "_onboarding_validation_snapshot", lambda: {"ok": False})
    monkeypatch.setattr(app, "_check_playwright_runtime", lambda: {"ok": False, "message": "no playwright", "fix_hint": "install"})
    monkeypatch.setattr(app, "_check_linkedin_session", lambda: {"ok": False, "message": "login required", "fix_hint": "run setup"})

    result = app.api_onboarding_preflight()
    assert result["ready"] is False
    assert len(result["checks"]) >= 5
    assert any(c["id"] == "playwright_runtime" and c["status"] == "fail" for c in result["checks"])
    assert any(c["id"] == "linkedin_session" and c["status"] == "fail" for c in result["checks"])

