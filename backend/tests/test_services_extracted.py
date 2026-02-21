from pathlib import Path

import pytest

from backend.domain.services import ai_service, cover_letter_service, onboarding_service, pipeline_service, tuning_service


def test_pipeline_service_script_args_and_size():
    def resolver(step: str) -> Path:
        return Path(f"C:/tmp/{step}.py")

    args = pipeline_service.script_args("scout", "Chicago", "analyst", resolver)
    assert args == ["C:\\tmp\\scout.py", "--search", "Chicago", "--query", "analyst"]

    presets = {"Small": {"max_results": 100, "shortlist_k": 30, "final_top": 10}}
    eval_args = pipeline_service.script_args_with_size(
        "eval",
        "Chicago",
        "Small",
        "",
        presets,
        resolver,
        eval_model="gpt-4.1-mini",
    )
    assert eval_args == ["C:\\tmp\\eval.py", "--limit", "10", "--model", "gpt-4.1-mini"]


def test_tuning_service_apply_operation_and_suggestions():
    prefs = {}
    tuning_service.apply_operation(prefs, {"op": "add", "path": "industry_preferences.soft_penalize", "value": "healthcare"})
    tuning_service.apply_operation(prefs, {"op": "add", "path": "industry_preferences.soft_penalize", "value": "healthcare"})
    assert prefs["industry_preferences"]["soft_penalize"] == ["healthcare"]

    rows = [
        {"title": "Data Analyst", "company": "Health Co", "description": "medical analytics"},
        {"title": "Ops Analyst", "company": "Example", "description": "hospital operations"},
        {"title": "Analyst", "company": "Example", "description": "finance"},
        {"title": "Analyst", "company": "Example", "description": "data"},
        {"title": "Analyst", "company": "Example", "description": "product"},
    ]
    suggestions = tuning_service.generate_suggestions_from_low_rated_rows({"industry_preferences": {"soft_penalize": []}}, rows)
    assert suggestions
    assert suggestions[0]["path"] == "industry_preferences.soft_penalize"


def test_cover_letter_service_parse_and_assemble():
    parsed = cover_letter_service.parse_model_paragraphs('{"paragraphs":["One","Two"]}')
    assert parsed == ["One", "Two"]

    sections = {
        "header": ["January 1, 2020", "Ruan"],
        "greeting": "Dear Hiring Manager,",
        "body": [],
        "signature": ["Sincerely,", "Michael Thomsen"],
    }
    out = cover_letter_service.assemble_cover_letter(
        sections,
        ["First paragraph.", "Second paragraph."],
        ensure_date=True,
        company="Atigro",
    )
    assert "Atigro" in out
    assert "Dear Hiring Manager," in out
    assert "    First paragraph." in out


def test_onboarding_service_validation_snapshot(monkeypatch):
    def fake_validate_all(resume, prefs, rules, searches):
        return {"ok": bool(resume) and bool(prefs) and bool(rules) and bool(searches)}

    monkeypatch.setattr(onboarding_service, "validate_all", fake_validate_all)
    result = onboarding_service.onboarding_validation_snapshot({"a": 1}, {"b": 1}, {"c": 1}, {"d": 1})
    assert result == {"ok": True}


def test_ai_service_estimate_shapes():
    presets = {"Small": {"final_top": 10}}
    out = ai_service.estimate_ai_eval("Small", presets, {"skills": []}, {"hard_constraints": {}}, model_override=None, batch_size=5)
    assert out["jobs_est"] == 10
    assert out["jobs_max"] == 10
    assert out["model"] == "gpt-4.1-mini"
    assert out["input_tokens_est"] >= 0
    assert out["output_tokens_est"] >= 0

    out2 = ai_service.estimate_ai_eval_from_jobs(
        total_jobs=20,
        job_count=12,
        avg_desc_chars=4800,
        resume={"skills": []},
        prefs={"hard_constraints": {}},
        model_override="gpt-4.1-mini",
        batch_size=5,
    )
    assert out2["jobs_total"] == 20
    assert out2["jobs_est"] == 12
    assert out2["skipped_jobs_est"] == 8


def test_ai_service_invalid_size_raises():
    with pytest.raises(ValueError):
        ai_service.estimate_ai_eval("Unknown", {}, {}, {})
