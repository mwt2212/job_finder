# Local Smoke Checklist

Use this checklist to validate a local install in under 10 minutes.

## Preconditions
- Run from repo root.
- Backend dependencies installed.
- Frontend dependencies installed.

## Checklist

1. Backend startup and health
- Command:
  - `python run-backend.py`
- Verify:
  - `GET /health` returns `{"ok": true, ...}`

2. Frontend load/build sanity
- Command:
  - `cd frontend && npm run build`
- Verify:
  - Build completes without errors.

3. Onboarding preflight
- Verify in UI or API:
  - `POST /onboarding/preflight`
- Pass criteria:
  - Response has `ready: true`.
  - `checks` includes `playwright_runtime` and `linkedin_session` with `status: pass`.

4. Pipeline test run
- Manual path (real run):
  - Pipeline tab -> `Size: Test` -> Start.
  - Verify run reaches finished state.
- Automated CI-safe path (mocked thread behavior via tests):
  - `pytest -q backend/tests/test_runs_import_suggestions_api.py::test_run_start_validation_and_success`
- Pass criteria:
  - Manual: pipeline start accepted and run transitions complete.
  - Automated: test passes.

5. Jobs/import visibility
- Verify:
  - Jobs endpoint responds (`GET /jobs`).
  - Import endpoint works for existing artifacts (`POST /import` with selected sources).

6. Cover letter quick check
- Verify:
  - Generate (`POST /cover-letters/generate`) for an existing job.
  - Save (`POST /cover-letters/save`).
  - Export (`GET /cover-letters/export/{cover_id}?format=txt`).

## Optional Automation
- Script:
  - `scripts/local-smoke.ps1`
- Runs a practical subset suitable for repeat local checks without requiring a live LinkedIn scrape.

## Latest Execution
- Date: 2026-02-22
- Environment: local Windows machine, repo root `C:\Users\Michael\Desktop\Job Finder`
- Results:
  - Backend health via TestClient: `PASS`
  - Frontend build (`npm run build`): `PASS`
  - Onboarding preflight via TestClient: `PASS` (`ready=true`)
  - Pipeline start route smoke (automated mocked-thread test): `PASS`
  - Full backend regression suite: `PASS` (`55 passed`)
- Notes:
  - Checklist execution used the automated CI-safe pipeline test path rather than a full live LinkedIn scrape.
