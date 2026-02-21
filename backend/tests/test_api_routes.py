import json


def _insert_job(app):
    return app.upsert_job(
        {
            "url": "https://example.com/job/1",
            "title": "Data Analyst",
            "company": "ExampleCo",
            "location": "Chicago, IL",
            "workplace": "hybrid",
            "posted": "1 day ago",
            "description": "x" * 400,
            "source": "Chicago",
        }
    )


def test_health_and_debug_routes(app_ctx):
    health = app_ctx.client.get("/health")
    debug = app_ctx.client.get("/debug/env")

    assert health.status_code == 200
    assert health.json()["ok"] is True
    assert debug.status_code == 200
    assert "scripts" in debug.json()


def test_jobs_get_and_list_contract(app_ctx):
    job_id = _insert_job(app_ctx.app)

    detail = app_ctx.client.get(f"/jobs/{job_id}")
    listing = app_ctx.client.get("/jobs")

    assert detail.status_code == 200
    assert detail.json()["id"] == job_id
    assert listing.status_code == 200
    assert any(j["id"] == job_id for j in listing.json())


def test_jobs_get_missing_returns_404(app_ctx):
    resp = app_ctx.client.get("/jobs/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Job not found"


def test_ratings_and_status_routes(app_ctx):
    job_id = _insert_job(app_ctx.app)

    bad = app_ctx.client.post("/ratings", json={"job_id": job_id, "stars": 6, "notes": "", "tags": []})
    assert bad.status_code == 400

    ok_rating = app_ctx.client.post("/ratings", json={"job_id": job_id, "stars": 4, "notes": "good", "tags": ["fit"]})
    ok_status = app_ctx.client.post("/status", json={"job_id": job_id, "status": "applied"})
    detail = app_ctx.client.get(f"/jobs/{job_id}")

    assert ok_rating.status_code == 200
    assert ok_rating.json()["ok"] is True
    assert ok_status.status_code == 200
    assert detail.json()["rating"] == 4
    assert detail.json()["status"] == "applied"


def test_feedback_routes_validation_and_success(app_ctx, monkeypatch):
    job_id = _insert_job(app_ctx.app)
    monkeypatch.setattr(app_ctx.app, "_auto_tune_from_shortlist", lambda *args, **kwargs: None)
    monkeypatch.setattr(app_ctx.app, "_auto_tune_from_ai", lambda *args, **kwargs: None)

    bad_short = app_ctx.client.post("/feedback/shortlist", json={"job_id": job_id, "verdict": "bad", "reason": ""})
    bad_ai_bucket = app_ctx.client.post("/feedback/ai", json={"job_id": job_id, "correct_bucket": "bad", "reasoning_quality": 3})
    bad_ai_quality = app_ctx.client.post("/feedback/ai", json={"job_id": job_id, "correct_bucket": "apply", "reasoning_quality": 6})
    ok_short = app_ctx.client.post("/feedback/shortlist", json={"job_id": job_id, "verdict": "keep", "reason": ""})
    ok_ai = app_ctx.client.post("/feedback/ai", json={"job_id": job_id, "correct_bucket": "review", "reasoning_quality": 3})

    assert bad_short.status_code == 400
    assert bad_ai_bucket.status_code == 400
    assert bad_ai_quality.status_code == 400
    assert ok_short.status_code == 200
    assert ok_short.json()["tuned"] is True
    assert ok_ai.status_code == 200
    assert ok_ai.json()["tuned"] is True


def test_settings_routes_read_write(app_ctx):
    got = app_ctx.client.get("/settings")
    assert got.status_code == 200
    assert "preferences" in got.json()
    assert "rules" in got.json()

    payload = {
        "preferences": {"qualification": {"min_match_score": 0.6}, "hard_constraints": {"min_base_salary_usd": 1000}},
        "rules": {
            "workplace_score": {"remote": 2, "hybrid": 2, "onsite": 1, "unknown": 0},
            "sales_adjacent_penalty": -9,
            "healthcare_penalty": -9,
            "wrong_field_penalty": -7,
        },
    }
    put = app_ctx.client.put("/settings", json=payload)
    assert put.status_code == 200
    assert put.json()["ok"] is True

    saved_prefs = json.loads(app_ctx.prefs_path.read_text(encoding="utf-8"))
    saved_rules = json.loads(app_ctx.rules_path.read_text(encoding="utf-8"))
    assert saved_prefs["qualification"]["min_match_score"] == 0.6
    assert saved_rules["wrong_field_penalty"] == -7


def test_searches_route_contract(app_ctx):
    resp = app_ctx.client.get("/searches")
    assert resp.status_code == 200
    data = resp.json()
    assert "searches" in data
    assert data["searches"][0]["label"] == "Chicago"


def test_onboarding_config_and_validate_routes(app_ctx):
    cfg = app_ctx.client.get("/onboarding/config")
    assert cfg.status_code == 200
    assert "resume_profile" in cfg.json()

    validate_resume = app_ctx.client.post("/onboarding/validate/resume-profile", json={"skills": ["SQL"], "target_roles": ["Analyst"]})
    validate_prefs = app_ctx.client.post(
        "/onboarding/validate/preferences",
        json={"qualification": {"min_match_score": 0.55}, "hard_constraints": {"min_base_salary_usd": 0}},
    )
    validate_rules = app_ctx.client.post(
        "/onboarding/validate/shortlist-rules",
        json={
            "workplace_score": {"remote": 1, "hybrid": 1, "onsite": 1, "unknown": 1},
            "sales_adjacent_penalty": -10,
            "healthcare_penalty": -10,
            "wrong_field_penalty": -8,
        },
    )
    validate_searches = app_ctx.app.api_onboarding_validate_searches(
        {"Chicago": {"url": "https://www.linkedin.com/jobs/search/?location=Chicago", "location_label": "Chicago, IL"}}
    )

    assert validate_resume.status_code == 200
    assert validate_resume.json()["ok"] is True
    assert validate_prefs.status_code == 200
    assert validate_prefs.json()["ok"] is True
    assert validate_rules.status_code == 200
    assert validate_rules.json()["ok"] is True
    assert validate_searches["ok"] is True


def test_onboarding_write_routes_and_searches_crud(app_ctx):
    resume_put = app_ctx.client.put("/onboarding/config/resume-profile", json={"skills": ["Python"], "target_roles": ["Analyst"]})
    prefs_put = app_ctx.client.put(
        "/onboarding/config/preferences",
        json={"qualification": {"min_match_score": 0.56}, "hard_constraints": {"min_base_salary_usd": 0}},
    )
    rules_put = app_ctx.client.put(
        "/onboarding/config/shortlist-rules",
        json={
            "workplace_score": {"remote": 1, "hybrid": 1, "onsite": 1, "unknown": 1},
            "sales_adjacent_penalty": -10,
            "healthcare_penalty": -10,
            "wrong_field_penalty": -8,
        },
    )
    searches_put = app_ctx.app.api_onboarding_put_searches(
        {"Chicago": {"url": "https://www.linkedin.com/jobs/search/?location=Chicago", "location_label": "Chicago, IL"}}
    )
    create_search = app_ctx.client.post(
        "/onboarding/searches",
        json={"label": "Denver", "location_label": "Denver, CO", "keywords": "analyst", "url": ""},
    )
    delete_search = app_ctx.client.delete("/onboarding/searches/Denver")

    assert resume_put.status_code == 200
    assert prefs_put.status_code == 200
    assert rules_put.status_code == 200
    assert searches_put["ok"] is True
    assert create_search.status_code == 200
    assert "linkedin.com/jobs/search/" in create_search.json()["item"]["url"]
    assert delete_search.status_code == 200


def test_onboarding_status_bootstrap_preflight_and_linkedin_routes(app_ctx, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setattr(app_ctx.app, "_check_playwright_runtime", lambda: {"ok": True, "message": "ok", "fix_hint": ""})
    monkeypatch.setattr(app_ctx.app, "_check_linkedin_session", lambda: {"ok": True, "message": "ok", "fix_hint": ""})
    monkeypatch.setattr(app_ctx.app, "_resolve_chrome_profile", lambda: app_ctx.tmp_path / "chrome-profile")

    status = app_ctx.client.get("/onboarding/status")
    bootstrap = app_ctx.client.post("/onboarding/bootstrap")
    preflight = app_ctx.client.post("/onboarding/preflight")
    linkedin_status = app_ctx.client.get("/onboarding/linkedin/status")
    linkedin_init = app_ctx.client.post("/onboarding/linkedin/init")

    assert status.status_code == 200
    assert "checks" in status.json()
    assert bootstrap.status_code == 200
    assert bootstrap.json()["ok"] is True
    assert preflight.status_code == 200
    assert preflight.json()["ready"] is True
    assert linkedin_status.status_code == 200
    assert linkedin_init.status_code == 200
    assert linkedin_init.json()["ok"] is True


def test_onboarding_profile_draft_and_resume_parse_edge_cases(app_ctx):
    missing = app_ctx.client.post("/onboarding/profile-draft", json={"text": "   "})
    assert missing.status_code == 400

    empty_upload = app_ctx.client.post("/onboarding/resume-parse", files={"file": ("resume.txt", b"", "text/plain")})
    assert empty_upload.status_code == 400

    good_upload = app_ctx.client.post(
        "/onboarding/resume-parse",
        files={"file": ("resume.txt", b"Data analyst with Python and SQL in Chicago", "text/plain")},
    )
    assert good_upload.status_code == 200
    assert good_upload.json()["extracted_chars"] > 0


def test_ai_pricing_and_estimate_routes(app_ctx):
    job_id = _insert_job(app_ctx.app)

    pricing = app_ctx.client.get("/ai/pricing")
    estimate_pipeline = app_ctx.client.post("/ai/estimate/pipeline", json={"size": "Test", "model": "gpt-4.1-mini"})
    estimate_cover = app_ctx.client.post("/ai/estimate/cover-letter", json={"job_id": job_id, "feedback": "", "model": "gpt-4.1"})

    assert pricing.status_code == 200
    assert "models" in pricing.json()
    assert estimate_pipeline.status_code == 200
    assert "input_tokens_est" in estimate_pipeline.json()
    assert estimate_cover.status_code == 200
    assert "cost_est_range" in estimate_cover.json()
