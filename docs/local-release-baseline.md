# Local Release Baseline

## Snapshot Date
- 2026-02-22

## Repository and Runtime Baseline
- Repo root: `C:\Users\Michael\Desktop\Job Finder`
- Backend entrypoint: `run-backend.py`
- Frontend entrypoint: `frontend/src/main.jsx`
- Default DB path: `artifacts/jobfinder.db`
- LinkedIn setup script: `setup-linkedin-profile.py`

## Environment Snapshot
- Python: `3.10.5`
- Node: `v24.13.0`
- npm: `11.6.2`
- Playwright: `1.58.0`
- `OPENAI_API_KEY` set: `True`
- `JOBFINDER_CHROME_PROFILE`: unset (runtime default resolves to repo-local `chrome-profile/`)

## Required Gate Results
- Backend tests:
  - Command: `pytest -q backend/tests`
  - Result: `55 passed`
- Frontend production build:
  - Command: `cd frontend && npm run build`
  - Result: success (`vite build` completed)

## Stage 0 Notes
- Baseline gates are green for local release readiness work.
- No behavior/contract changes were made in this stage.
