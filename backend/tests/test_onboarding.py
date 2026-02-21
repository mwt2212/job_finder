import json
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import backend.app as app
from backend.onboarding_validate import (
    validate_preferences,
    validate_resume_profile,
    validate_searches,
    validate_shortlist_rules,
)
from backend.onboarding_schema import DEFAULT_PREFERENCES


def test_validate_resume_profile_requires_skills_and_target_roles():
    ok, errors, _warnings = validate_resume_profile({"skills": [], "target_roles": []})
    assert ok is False
    assert any("skills" in err for err in errors)
    assert any("target_roles" in err for err in errors)


def test_default_preferences_no_location_city_field():
    search_filters = DEFAULT_PREFERENCES.get("search_filters", {})
    assert "location_city" not in search_filters


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
    monkeypatch.setattr(app, "PREFERENCES_LOCAL_PATH", tmp_path / "preferences.local.json")
    monkeypatch.setattr(app, "RULES_PATH", rules_path)
    monkeypatch.setattr(app, "RULES_LOCAL_PATH", tmp_path / "shortlist_rules.local.json")
    monkeypatch.setattr(app, "SEARCHES_PATH", searches_path)
    monkeypatch.setattr(app, "SEARCHES_LOCAL_PATH", tmp_path / "searches.local.json")
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


def test_onboarding_put_resume_profile_rejects_invalid_payload(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "RESUME_LOCAL_PATH", tmp_path / "resume_profile.local.json")
    with pytest.raises(HTTPException) as exc:
        app.api_onboarding_put_resume_profile({"skills": [], "target_roles": []})
    assert exc.value.status_code == 400


def test_onboarding_search_create_update_delete_cycle(tmp_path, monkeypatch):
    searches_path = tmp_path / "searches.json"
    searches_path.write_text(json.dumps({"Chicago": {"url": "https://www.linkedin.com/jobs/search/?location=Chicago", "location_label": "Chicago, IL"}}), encoding="utf-8")
    monkeypatch.setattr(app, "SEARCHES_PATH", searches_path)
    monkeypatch.setattr(app, "SEARCHES_LOCAL_PATH", tmp_path / "searches.local.json")

    created = app.api_onboarding_create_search(
        app.OnboardingSearchIn(label="Denver", location_label="Denver, CO", keywords="analyst", url="")
    )
    assert created["ok"] is True
    assert created["item"]["label"] == "Denver"
    assert "linkedin.com/jobs/search/" in created["item"]["url"]

    updated = app.api_onboarding_update_search(
        "Denver",
        app.OnboardingSearchUpdateIn(label="Denver Metro", location_label="Denver, CO", keywords="operations analyst"),
    )
    assert updated["ok"] is True
    assert updated["item"]["label"] == "Denver Metro"

    deleted = app.api_onboarding_delete_search("Denver Metro")
    assert deleted["ok"] is True


def test_onboarding_linkedin_init_returns_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(app, "BASE_DIR", tmp_path)
    monkeypatch.setattr(app, "_resolve_chrome_profile", lambda: tmp_path / "chrome-profile")
    out = app.api_onboarding_linkedin_init()
    assert out["ok"] is True
    assert out["script_path"].endswith("setup-linkedin-profile.py")


def test_searches_read_prefers_local_file(monkeypatch, tmp_path):
    local_path = tmp_path / "searches.local.json"
    base_path = tmp_path / "searches.json"
    local_path.write_text(
        json.dumps({"Local": {"url": "https://www.linkedin.com/jobs/search/?location=Local", "location_label": "Local, ST"}}),
        encoding="utf-8",
    )
    base_path.write_text(
        json.dumps({"Base": {"url": "https://www.linkedin.com/jobs/search/?location=Base", "location_label": "Base, ST"}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(app, "SEARCHES_LOCAL_PATH", local_path)
    monkeypatch.setattr(app, "SEARCHES_PATH", base_path)
    monkeypatch.setattr(app, "SEARCHES_EXAMPLE_PATH", tmp_path / "searches.example.json")

    loaded = app._load_searches_map()
    assert "Local" in loaded
    assert "Base" not in loaded


def test_onboarding_put_preferences_writes_local_if_present(monkeypatch, tmp_path):
    local_prefs = tmp_path / "preferences.local.json"
    local_prefs.write_text(json.dumps({"qualification": {"min_match_score": 0.55}}), encoding="utf-8")
    base_prefs = tmp_path / "preferences.json"

    monkeypatch.setattr(app, "PREFERENCES_LOCAL_PATH", local_prefs)
    monkeypatch.setattr(app, "PREFERENCES_PATH", base_prefs)

    payload = {"qualification": {"min_match_score": 0.55}, "hard_constraints": {"min_base_salary_usd": 0}}
    out = app.api_onboarding_put_preferences(payload)
    assert out["ok"] is True
    assert out["path"].endswith("preferences.local.json")
    saved = json.loads(local_prefs.read_text(encoding="utf-8"))
    assert saved["qualification"]["min_match_score"] == 0.55


def test_onboarding_migrate_adds_schema_versions_and_backups(monkeypatch, tmp_path):
    resume_path = tmp_path / "resume_profile.json"
    prefs_path = tmp_path / "preferences.json"
    rules_path = tmp_path / "shortlist_rules.json"
    searches_path = tmp_path / "searches.json"

    resume_path.write_text(json.dumps({"skills": ["SQL"], "target_roles": ["Analyst"]}), encoding="utf-8")
    prefs_path.write_text(json.dumps({}), encoding="utf-8")
    rules_path.write_text(json.dumps({"workplace_score": {"remote": 1, "hybrid": 1, "onsite": 1, "unknown": 1}}), encoding="utf-8")
    searches_path.write_text(
        json.dumps({"Chicago": {"url": "https://www.linkedin.com/jobs/search/?location=Chicago", "location_label": "Chicago, IL"}}),
        encoding="utf-8",
    )

    monkeypatch.setattr(app, "RESUME_PATH", resume_path)
    monkeypatch.setattr(app, "RESUME_LOCAL_PATH", tmp_path / "resume_profile.local.json")
    monkeypatch.setattr(app, "PREFERENCES_PATH", prefs_path)
    monkeypatch.setattr(app, "PREFERENCES_LOCAL_PATH", tmp_path / "preferences.local.json")
    monkeypatch.setattr(app, "RULES_PATH", rules_path)
    monkeypatch.setattr(app, "RULES_LOCAL_PATH", tmp_path / "shortlist_rules.local.json")
    monkeypatch.setattr(app, "SEARCHES_PATH", searches_path)
    monkeypatch.setattr(app, "SEARCHES_LOCAL_PATH", tmp_path / "searches.local.json")

    out = app.api_onboarding_migrate()
    assert out["ok"] is True
    assert out["migrated_count"] >= 1

    migrated_prefs = json.loads(prefs_path.read_text(encoding="utf-8"))
    assert migrated_prefs["schema_version"] == "1.0"
    assert "qualification" in migrated_prefs
    assert "hard_constraints" in migrated_prefs

    migrated_rules = json.loads(rules_path.read_text(encoding="utf-8"))
    assert migrated_rules["schema_version"] == "1.0"
    assert "sales_adjacent_penalty" in migrated_rules

    migrated_searches = json.loads(searches_path.read_text(encoding="utf-8"))
    assert migrated_searches["Chicago"]["schema_version"] == "1.0"

    backup_files = list(tmp_path.glob("*.bak.*"))
    assert backup_files, "Migration should create backup files before write"


def test_onboarding_profile_draft_returns_structured_payload():
    out = app.api_onboarding_profile_draft(app.OnboardingProfileDraftIn(text="I want a data analyst role in Denver, CO. Strong in Python and SQL."))
    assert "resume_profile" in out
    assert "preferences" in out
    assert "shortlist_rules" in out
    assert "searches" in out
    assert isinstance(out.get("confidence"), float)


def test_onboarding_resume_parse_txt_upload():
    client = TestClient(app.app)
    resp = client.post(
        "/onboarding/resume-parse",
        files={"file": ("resume.txt", b"Data analyst with Python and SQL in Denver, CO", "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"] == "resume.txt"
    assert data["extracted_chars"] > 0
    assert "draft" in data
    assert "resume_profile" in data["draft"]
