import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import backend.app as app
import backend.db as db


@pytest.fixture
def app_ctx(monkeypatch, tmp_path):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)

    resume_path = tmp_path / "resume_profile.json"
    prefs_path = tmp_path / "preferences.json"
    rules_path = tmp_path / "shortlist_rules.json"
    searches_path = tmp_path / "searches.json"
    templates_path = tmp_path / "cover_letter_templates.json"
    setup_script = tmp_path / "setup-linkedin-profile.py"
    setup_script.write_text("print('setup')\n", encoding="utf-8")

    resume_path.write_text(
        json.dumps(
            {
                "skills": ["Python", "SQL"],
                "target_roles": ["Data Analyst"],
                "education": {"degree": "BS"},
            }
        ),
        encoding="utf-8",
    )
    prefs_path.write_text(
        json.dumps({"qualification": {"min_match_score": 0.55}, "hard_constraints": {"min_base_salary_usd": 0}}),
        encoding="utf-8",
    )
    rules_path.write_text(
        json.dumps(
            {
                "workplace_score": {"remote": 1, "hybrid": 2, "onsite": 0, "unknown": 0},
                "sales_adjacent_penalty": -10,
                "healthcare_penalty": -10,
                "wrong_field_penalty": -8,
            }
        ),
        encoding="utf-8",
    )
    searches_path.write_text(
        json.dumps(
            {
                "Chicago": {
                    "url": "https://www.linkedin.com/jobs/search/?keywords=analyst&location=Chicago%2C+IL&sortBy=DD",
                    "location_label": "Chicago, IL",
                }
            }
        ),
        encoding="utf-8",
    )
    templates_path.write_text(json.dumps({"templates": []}), encoding="utf-8")

    monkeypatch.setattr(app, "BASE_DIR", tmp_path)
    monkeypatch.setattr(app, "ARTIFACTS_DIR", artifacts)
    monkeypatch.setattr(app, "EXPORT_DIR", artifacts / "cover_letters")
    monkeypatch.setattr(app, "RESUME_PATH", resume_path)
    monkeypatch.setattr(app, "RESUME_LOCAL_PATH", tmp_path / "resume_profile.local.json")
    monkeypatch.setattr(app, "RESUME_EXAMPLE_PATH", tmp_path / "resume_profile.example.json")
    monkeypatch.setattr(app, "PREFERENCES_PATH", prefs_path)
    monkeypatch.setattr(app, "PREFERENCES_LOCAL_PATH", tmp_path / "preferences.local.json")
    monkeypatch.setattr(app, "PREFERENCES_EXAMPLE_PATH", tmp_path / "preferences.example.json")
    monkeypatch.setattr(app, "RULES_PATH", rules_path)
    monkeypatch.setattr(app, "RULES_LOCAL_PATH", tmp_path / "shortlist_rules.local.json")
    monkeypatch.setattr(app, "RULES_EXAMPLE_PATH", tmp_path / "shortlist_rules.example.json")
    monkeypatch.setattr(app, "SEARCHES_PATH", searches_path)
    monkeypatch.setattr(app, "SEARCHES_LOCAL_PATH", tmp_path / "searches.local.json")
    monkeypatch.setattr(app, "SEARCHES_EXAMPLE_PATH", tmp_path / "searches.example.json")
    monkeypatch.setattr(app, "TEMPLATES_PATH", templates_path)
    monkeypatch.setattr(app, "TEMPLATES_LOCAL_PATH", tmp_path / "cover_letter_templates.local.json")
    monkeypatch.setattr(app, "TEMPLATES_EXAMPLE_PATH", tmp_path / "cover_letter_templates.example.json")

    monkeypatch.setattr(db, "DB_PATH", artifacts / "jobfinder.db")
    db.init_db()

    with app.RUN_STATE["lock"]:
        app.RUN_STATE["running"] = False
        app.RUN_STATE["step"] = None
        app.RUN_STATE["lines"] = []
        app.RUN_STATE["status"] = None
        app.RUN_STATE["progress"] = {"current": 0, "total": 0, "pct": 0.0, "label": ""}

    with TestClient(app.app) as client:
        yield SimpleNamespace(
            app=app,
            db=db,
            client=client,
            tmp_path=tmp_path,
            artifacts=artifacts,
            resume_path=resume_path,
            prefs_path=prefs_path,
            rules_path=rules_path,
            searches_path=searches_path,
            templates_path=templates_path,
        )
