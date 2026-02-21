import io
import json
import threading
from pathlib import Path


class _ImmediateThread:
    def __init__(self, target=None, args=(), daemon=True):
        self._target = target
        self._args = args
        self.daemon = daemon

    def start(self):
        if self._target:
            self._target(*self._args)


class _DummyProc:
    def __init__(self, text="", code=0):
        self.stdout = io.StringIO(text)
        self.returncode = code

    def wait(self):
        return self.returncode


def test_run_start_validation_and_success(app_ctx, monkeypatch):
    bad_size = app_ctx.client.post("/run/start", json={"search": "Chicago", "size": "Mega", "query": ""})
    assert bad_size.status_code == 400

    monkeypatch.setattr(app_ctx.app, "_searches_read_path", lambda: None)
    missing_search_file = app_ctx.client.post("/run/start", json={"search": "Chicago", "size": "Test", "query": ""})
    assert missing_search_file.status_code == 400

    monkeypatch.setattr(app_ctx.app, "_searches_read_path", lambda: app_ctx.searches_path)
    invalid_search = app_ctx.client.post("/run/start", json={"search": "Missing", "size": "Test", "query": ""})
    assert invalid_search.status_code == 400

    monkeypatch.setattr(app_ctx.app.threading, "Thread", _ImmediateThread)
    monkeypatch.setattr(app_ctx.app, "_estimate_ai_eval", lambda size, model_override=None: {"model": "gpt-4.1-mini", "jobs_est": 1})
    monkeypatch.setattr(app_ctx.app, "log_usage", lambda entry: None)
    monkeypatch.setattr(app_ctx.app, "_run_pipeline_thread", lambda *args, **kwargs: None)
    with app_ctx.app.RUN_STATE["lock"]:
        app_ctx.app.RUN_STATE["running"] = False

    ok = app_ctx.client.post("/run/start", json={"search": "Chicago", "size": "Test", "query": ""})
    assert ok.status_code == 200
    assert ok.json()["ok"] is True

    with app_ctx.app.RUN_STATE["lock"]:
        app_ctx.app.RUN_STATE["running"] = True
    conflict = app_ctx.client.post("/run/start", json={"search": "Chicago", "size": "Test", "query": ""})
    assert conflict.status_code == 409
    with app_ctx.app.RUN_STATE["lock"]:
        app_ctx.app.RUN_STATE["running"] = False


def test_run_step_validation_and_success(app_ctx, monkeypatch, tmp_path):
    invalid = app_ctx.client.post("/run/nope")
    assert invalid.status_code == 400

    missing_script = tmp_path / "missing.py"
    monkeypatch.setattr(app_ctx.app, "_script_path", lambda step: missing_script)
    missing = app_ctx.client.post("/run/scout")
    assert missing.status_code == 404

    monkeypatch.setattr(app_ctx.app, "_script_path", lambda step: Path(__file__).resolve())
    monkeypatch.setattr(app_ctx.app.threading, "Thread", _ImmediateThread)
    monkeypatch.setattr(app_ctx.app, "_run_step_thread", lambda *args, **kwargs: None)
    monkeypatch.setattr(app_ctx.app, "log_usage", lambda entry: None)
    with app_ctx.app.RUN_STATE["lock"]:
        app_ctx.app.RUN_STATE["running"] = False

    ok = app_ctx.client.post("/run/scout?search=Chicago")
    assert ok.status_code == 200
    assert ok.json()["status"] == "started"

    with app_ctx.app.RUN_STATE["lock"]:
        app_ctx.app.RUN_STATE["running"] = True
    conflict = app_ctx.client.post("/run/scout?search=Chicago")
    assert conflict.status_code == 409
    with app_ctx.app.RUN_STATE["lock"]:
        app_ctx.app.RUN_STATE["running"] = False


def test_runs_state_and_stream_contract(app_ctx):
    with app_ctx.app.RUN_STATE["lock"]:
        app_ctx.app.RUN_STATE["running"] = False
        app_ctx.app.RUN_STATE["step"] = "pipeline"
        app_ctx.app.RUN_STATE["status"] = "ok"
        app_ctx.app.RUN_STATE["lines"] = ["line 1", "line 2"]
        app_ctx.app.RUN_STATE["progress"] = {"current": 2, "total": 2, "pct": 100.0, "label": "pipeline"}

    state = app_ctx.client.get("/runs/state")
    assert state.status_code == 200
    assert state.json()["status"] == "ok"

    stream = app_ctx.client.get("/runs/stream")
    assert stream.status_code == 200
    assert "data: line 1" in stream.text
    assert "event: done" in stream.text


def test_run_step_thread_progress_and_import_hook(app_ctx, monkeypatch):
    monkeypatch.setattr(app_ctx.app.subprocess, "Popen", lambda *a, **k: _DummyProc("Cap: 2 jobs\n[1/2]\n[2/2]\n", 0))
    imported = []
    runs = []
    monkeypatch.setattr(app_ctx.app, "_import_for_step", lambda step: imported.append(step))
    monkeypatch.setattr(app_ctx.app, "insert_run", lambda *args, **kwargs: runs.append(args))
    with app_ctx.app.RUN_STATE["lock"]:
        app_ctx.app.RUN_STATE["running"] = True
        app_ctx.app.RUN_STATE["lines"] = []
        app_ctx.app.RUN_STATE["progress"] = {"current": 0, "total": 0, "pct": 0.0, "label": ""}

    app_ctx.app._run_step_thread("scout", ["job-scout.py"])
    assert imported == ["scout"]
    assert runs
    with app_ctx.app.RUN_STATE["lock"]:
        assert app_ctx.app.RUN_STATE["running"] is False
        assert app_ctx.app.RUN_STATE["progress"]["pct"] == 100.0


def test_run_pipeline_thread_imports_each_stage(app_ctx, monkeypatch):
    monkeypatch.setattr(app_ctx.app.subprocess, "Popen", lambda *a, **k: _DummyProc("[1/1]\n", 0))
    imported = []
    monkeypatch.setattr(app_ctx.app, "_import_for_step", lambda step: imported.append(step))
    monkeypatch.setattr(app_ctx.app, "insert_run", lambda *args, **kwargs: None)
    with app_ctx.app.RUN_STATE["lock"]:
        app_ctx.app.RUN_STATE["running"] = True
        app_ctx.app.RUN_STATE["lines"] = []
        app_ctx.app.RUN_STATE["progress"] = {"current": 0, "total": 0, "pct": 0.0, "label": ""}

    app_ctx.app._run_pipeline_thread("Chicago", "Test", "")
    assert imported == ["scout", "shortlist", "scrape", "eval"]
    with app_ctx.app.RUN_STATE["lock"]:
        assert app_ctx.app.RUN_STATE["running"] is False
        assert app_ctx.app.RUN_STATE["status"] == "ok"


def test_import_endpoint_and_counts(app_ctx):
    (app_ctx.artifacts / "tier2_metadata.json").write_text(
        json.dumps(
            [
                {"url": "https://example.com/a", "title": "A", "company": "CoA", "location": "Chicago", "workplace": "hybrid", "description": "x" * 220},
                {"url": "https://example.com/b", "title": "B", "company": "CoB", "location": "Chicago", "workplace": "remote", "description": "x" * 220},
            ]
        ),
        encoding="utf-8",
    )
    (app_ctx.artifacts / "tier2_shortlist.json").write_text(
        json.dumps(
            [
                {"url": "https://example.com/a", "title": "A", "company": "CoA", "score": 10, "reasons": ["r1"], "qualification_score": 0.6},
            ]
        ),
        encoding="utf-8",
    )
    (app_ctx.artifacts / "tier2_full.json").write_text(
        json.dumps(
            [
                {"url": "https://example.com/a", "title": "A", "company": "CoA", "description": "x" * 500},
            ]
        ),
        encoding="utf-8",
    )
    (app_ctx.artifacts / "tier2_scored.json").write_text(
        json.dumps(
            [
                {
                    "url": "https://example.com/a",
                    "title": "A",
                    "company": "CoA",
                    "ai_model": "gpt-4.1-mini",
                    "ai_eval": {"fit_score": 80, "next_action": "apply", "workplace_type": "hybrid"},
                }
            ]
        ),
        encoding="utf-8",
    )
    (app_ctx.artifacts / "apply.json").write_text(
        json.dumps([{"url": "https://example.com/a", "title": "A", "company": "CoA"}]),
        encoding="utf-8",
    )
    (app_ctx.artifacts / "review.json").write_text(json.dumps([], ensure_ascii=False), encoding="utf-8")
    (app_ctx.artifacts / "skip.json").write_text(
        json.dumps([{"url": "https://example.com/b", "title": "B", "company": "CoB"}]),
        encoding="utf-8",
    )

    resp = app_ctx.client.post("/import", json={"sources": ["metadata", "shortlist", "full", "scored", "buckets"]})
    assert resp.status_code == 200
    counts = resp.json()["counts"]
    assert counts["metadata"] == 2
    assert counts["shortlist"] == 1
    assert counts["full"] == 1
    assert counts["scored"] == 1
    assert counts["buckets"]["apply"] == 1
    assert counts["buckets"]["skip"] == 1


def test_suggestions_generate_and_apply(app_ctx, monkeypatch):
    monkeypatch.setattr(
        app_ctx.app,
        "_generate_suggestions",
        lambda prefs: [{"op": "add", "path": "industry_preferences.soft_penalize", "value": "healthcare", "reason": "test"}],
    )
    generated = app_ctx.client.post("/suggestions/generate")
    assert generated.status_code == 200
    assert len(generated.json()["suggestions"]) == 1

    applied = app_ctx.client.post(
        "/suggestions/apply",
        json={"operations": [{"op": "set", "path": "qualification.min_match_score", "value": 0.61}]},
    )
    assert applied.status_code == 200
    assert applied.json()["ok"] is True

    prefs = json.loads(app_ctx.prefs_path.read_text(encoding="utf-8"))
    assert prefs["qualification"]["min_match_score"] == 0.61


def test_ai_eval_file_estimate_route_missing_file_returns_400(app_ctx):
    # No tier2_full.json in the temp artifacts for this test.
    resp = app_ctx.client.post("/ai/estimate/eval", json={"size": "Test", "model": "gpt-4.1-mini"})
    assert resp.status_code == 400
