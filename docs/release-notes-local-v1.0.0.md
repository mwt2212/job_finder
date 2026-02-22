# Local Release Notes v1.0.0

## Release Scope
- Release model: local-only usage on user machines.
- This release does not target hosted multi-user deployment.

## Getting Started (Concise)
1. Run one-command setup script.
2. Launch app with one-click start script.
3. Complete Onboarding bootstrap + preflight.
4. Run pipeline in `Test` size first.

One-command setup (Windows, from repo root):

```bat
scripts\setup-local.bat
```
This script checks whether `OPENAI_API_KEY` is currently set and prints guidance if missing.

One-click local start (Windows, from repo root):

```bat
scripts\start-local.bat
```

## Installation Commands (Windows, from repo root)

Manual backend setup:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
cd ..
```

Manual frontend setup:

```powershell
cd frontend
npm install
cd ..
```

Run:

```powershell
backend\.venv\Scripts\python.exe run-backend.py
```
```powershell
cd frontend
npm run dev
```

## Required Environment Variables
- `OPENAI_API_KEY` (required for AI eval + cover letters)
- `VITE_API_BASE` (optional; default `http://127.0.0.1:8001`)
- `JOBFINDER_CHROME_PROFILE` (optional; defaults to repo-local `chrome-profile/`)
- `JOBFINDER_VIEWPORT` (optional; format `WIDTHxHEIGHT`)

Windows example:
```bat
setx OPENAI_API_KEY "your_key_here"
```
Then open a new terminal before launching the app.

OpenAI API key and billing setup:
1. Sign in at `https://platform.openai.com/`.
2. Create a key at `https://platform.openai.com/api-keys`.
3. Add billing/credits in OpenAI billing settings.
4. Set `OPENAI_API_KEY` locally (command above), then relaunch terminals.

AI eval budget guide (approx jobs per $1):
- Token baseline used: ~`1331` input + ~`244` output tokens per evaluated job (from local usage totals).
- Estimated jobs per $1 (about +/-20% variance):
  - `gpt-4.1-mini`: ~`1083` (`~902-1354`)
  - `gpt-5-mini`: ~`1217` (`~1014-1521`)
  - `gpt-4.1`: ~`217` (`~180-271`)
  - `gpt-5` / `gpt-5.1`: ~`243` (`~203-304`)
- Actual costs vary with prompt size, response length, and number of eligible jobs.

`frontend/.env` note:
- Usually optional for local use.
- Use it only when overriding `VITE_API_BASE` to a non-default backend URL.

## Operational Notes
- Pipeline execution order is fixed: `scout -> shortlist -> scrape -> eval`.
- Pipeline start is gated by onboarding preflight.
- LinkedIn scraping requires a valid session in the configured Chrome profile.

## Known Limitations
- Local-only operational model (no auth/multi-user tenancy).
- Frontend does not currently have automated component/e2e tests.
- Live LinkedIn scraping behavior depends on session/cookies and LinkedIn availability.
- Live OpenAI behavior/cost/latency depends on external API conditions.
- Smoke automation uses a route-level pipeline start test, not a full live scrape.

## Troubleshooting Links
- Main setup and troubleshooting: `README.md`
- LinkedIn and preflight runbook: `README.md` (One-Time LinkedIn Login Setup + Troubleshooting)
- Local data backup/restore/recovery: `docs/local-data-and-recovery.md`
- Local smoke checklist: `docs/local-smoke-checklist.md`

## Validation Snapshot for This Release
- Backend tests: `pytest -q backend/tests` -> pass
- Frontend build: `cd frontend && npm run build` -> pass
- Local smoke script: `scripts/local-smoke.ps1` -> pass (see checklist notes)
