import io
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
