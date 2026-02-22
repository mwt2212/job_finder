$ErrorActionPreference = "Stop"

Write-Host "[1/4] Backend health + preflight smoke (TestClient)..."
@'
from fastapi.testclient import TestClient
import backend.app as app_mod

client = TestClient(app_mod.app)
health = client.get("/health")
preflight = client.post("/onboarding/preflight")
assert health.status_code == 200 and health.json().get("ok") is True
assert preflight.status_code == 200
print("health_ok=", health.json().get("ok"))
print("preflight_ready=", preflight.json().get("ready"))
'@ | python -

Write-Host "[2/4] Pipeline start route smoke (mocked-thread test)..."
pytest -q backend/tests/test_runs_import_suggestions_api.py::test_run_start_validation_and_success

Write-Host "[3/4] Full backend regression suite..."
pytest -q backend/tests

Write-Host "[4/4] Frontend production build..."
Push-Location frontend
npm run build
Pop-Location

Write-Host "Local smoke checks completed."
