import io
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import backend.app as app


class DummyProc:
    def __init__(self, text=""):
        self.stdout = io.StringIO(text)
        self.returncode = 0

    def wait(self):
        return self.returncode


def test_pipeline_thread_runs_without_basedir_nameerror(monkeypatch):
    calls = []

    def fake_popen(*args, **kwargs):
        calls.append(kwargs.get("cwd"))
        return DummyProc("Cap: 1 jobs\nReached cap of 1 jobs — stopping.\n")

    monkeypatch.setattr(app.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(app, "insert_run", lambda *args, **kwargs: None)
    monkeypatch.setattr(app, "_import_for_step", lambda *args, **kwargs: None)

    app._run_pipeline_thread("Chicago", "Medium", "")

    assert calls, "Pipeline should invoke subprocess"
    assert all(calls), "Pipeline should set cwd for subprocess"


def test_shortlist_feedback_idempotent_payload_does_not_retune(monkeypatch):
    monkeypatch.setattr(
        app,
        "get_shortlist_feedback",
        lambda job_id: {"job_id": job_id, "verdict": "remove", "reason": "low pay"},
    )

    upsert_calls = []
    tune_calls = []
    monkeypatch.setattr(app, "upsert_shortlist_feedback", lambda *args, **kwargs: upsert_calls.append((args, kwargs)))
    monkeypatch.setattr(app, "_auto_tune_from_shortlist", lambda *args, **kwargs: tune_calls.append((args, kwargs)))

    payload = app.ShortlistFeedbackIn(job_id=123, verdict="remove", reason="low pay")
    out = app.api_shortlist_feedback(payload)

    assert out["ok"] is True
    assert out["tuned"] is False
    assert out["message"] == "No feedback change"
    assert upsert_calls == []
    assert tune_calls == []


def test_shortlist_feedback_remove_without_reason_does_not_tune(monkeypatch):
    monkeypatch.setattr(app, "get_shortlist_feedback", lambda job_id: None)

    upsert_calls = []
    tune_calls = []

    def _upsert(job_id, verdict, reason):
        upsert_calls.append((job_id, verdict, reason))

    monkeypatch.setattr(app, "upsert_shortlist_feedback", _upsert)
    monkeypatch.setattr(app, "_auto_tune_from_shortlist", lambda *args, **kwargs: tune_calls.append((args, kwargs)))

    payload = app.ShortlistFeedbackIn(job_id=45, verdict="remove", reason="")
    out = app.api_shortlist_feedback(payload)

    assert out["ok"] is True
    assert out["tuned"] is False
    assert out["message"] == "Reason required for auto-tune on remove"
    assert upsert_calls == [(45, "remove", "")]
    assert tune_calls == []


def test_low_pay_reason_increases_salary_floor_not_match_threshold(monkeypatch, tmp_path):
    prefs_path = tmp_path / "preferences.json"
    rules_path = tmp_path / "shortlist_rules.json"

    original_prefs = {
        "qualification": {"min_match_score": 0.55},
        "hard_constraints": {},
    }
    original_rules = {
        "wrong_field_penalty": -6,
        "sales_adjacent_penalty": -8,
        "healthcare_penalty": -10,
        "workplace_score": {"onsite": 8},
    }

    prefs_path.write_text(json.dumps(original_prefs), encoding="utf-8")
    rules_path.write_text(json.dumps(original_rules), encoding="utf-8")

    monkeypatch.setattr(app, "PREFERENCES_PATH", prefs_path)
    monkeypatch.setattr(app, "PREFERENCES_LOCAL_PATH", tmp_path / "preferences.local.json")
    monkeypatch.setattr(app, "RULES_PATH", rules_path)
    monkeypatch.setattr(app, "RULES_LOCAL_PATH", tmp_path / "shortlist_rules.local.json")
    monkeypatch.setattr(
        app,
        "get_job",
        lambda job_id: {
            "id": job_id,
            "salary_hint": "$50K - $60K",
            "description": "Compensation range is $50K to $60K base salary.",
        },
    )
    monkeypatch.setattr(app, "_append_tuning_log", lambda entry: None)

    app._auto_tune_from_shortlist(job_id=99, verdict="remove", reason="low pay")

    updated_prefs = json.loads(prefs_path.read_text(encoding="utf-8"))
    updated_rules = json.loads(rules_path.read_text(encoding="utf-8"))

    assert updated_prefs["hard_constraints"]["min_base_salary_usd"] == 51000
    assert updated_prefs["qualification"]["min_match_score"] == 0.55
    assert updated_rules == original_rules


def test_ai_eval_estimate_from_file_counts_only_eligible_jobs(monkeypatch, tmp_path):
    artifact_file = tmp_path / "tier2_full.json"
    artifact_file.write_text(
        json.dumps(
            [
                {"description": "short"},
                {"description": ""},
                {"description": "x" * 600},
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(app, "ARTIFACTS_DIR", tmp_path)
    monkeypatch.setattr(app, "_load_resume_profile", lambda: {})
    monkeypatch.setattr(app, "_load_preferences", lambda: {})
    monkeypatch.setattr(app, "get_avg_output_tokens", lambda kind, model, default=0: 120)
    monkeypatch.setattr(
        app,
        "load_pricing",
        lambda: {"models": {"gpt-4.1-mini": {"input": 0.4, "cached_input": 0.1, "output": 1.6}}},
    )

    out = app._estimate_ai_eval_from_file(None)

    assert out["jobs_total"] == 3
    assert out["jobs_est"] == 1
    assert out["skipped_jobs_est"] == 2
    assert out["output_tokens_est"] == 120
    assert out["input_tokens_est"] > 0
    assert out["cost_est"] is not None


def test_ai_eval_estimate_from_file_zero_eligible_jobs_is_zero_cost(monkeypatch, tmp_path):
    artifact_file = tmp_path / "tier2_full.json"
    artifact_file.write_text(
        json.dumps(
            [
                {"description": ""},
                {"description": "too short"},
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(app, "ARTIFACTS_DIR", tmp_path)
    monkeypatch.setattr(app, "_load_resume_profile", lambda: {})
    monkeypatch.setattr(app, "_load_preferences", lambda: {})
    monkeypatch.setattr(app, "get_avg_output_tokens", lambda kind, model, default=0: 120)
    monkeypatch.setattr(
        app,
        "load_pricing",
        lambda: {"models": {"gpt-4.1-mini": {"input": 0.4, "cached_input": 0.1, "output": 1.6}}},
    )

    out = app._estimate_ai_eval_from_file(None)

    assert out["jobs_total"] == 2
    assert out["jobs_est"] == 0
    assert out["skipped_jobs_est"] == 2
    assert out["input_tokens_est"] == 0
    assert out["output_tokens_est"] == 0
    assert out["cost_est"] == 0.0


def test_profile_draft_does_not_set_location_city_in_preferences():
    out = app._build_profile_draft_from_text("Data analyst in Des Moines, IA with Python and SQL.")
    prefs = out["preferences"]
    search_filters = prefs.get("search_filters", {})
    assert "location_city" not in search_filters


def test_evaluation_preferences_payload_strips_location_city():
    prefs = {
        "qualification": {"min_match_score": 0.55},
        "search_filters": {"location_city": "Chicago, IL", "radius_miles": 10, "posted_within_hours": 24},
    }
    cleaned = app._evaluation_preferences_payload(prefs)
    assert "location_city" not in cleaned.get("search_filters", {})
    assert cleaned["search_filters"]["radius_miles"] == 10
