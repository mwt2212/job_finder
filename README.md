# Job Finder Dashboard

Local-first job intelligence pipeline with a FastAPI backend, React dashboard, and feedback-driven ranking loop.

## Preview

![Job Finder Dashboard](docs/dashboard-preview.png)

## Highlights

- End-to-end pipeline: `scout -> shortlist -> scrape -> eval` (+ optional `sort`)
- Unified operations UI for jobs, ratings, settings, pipeline runs, and cover letters
- Local SQLite persistence with importable JSON/CSV artifacts
- Feedback-to-tuning loop with guarded, idempotent behavior
- Cost-aware AI eval and cover-letter generation tracking

## Architecture

Core services:
- `backend/app.py`: API routes, pipeline orchestration, imports, tuning hooks
- `backend/db.py`: SQLite schema + persistence access layer
- `frontend/src/App.jsx`: single-page dashboard UI

Pipeline scripts:
- `job-scout.py`: LinkedIn job metadata capture
- `shortlist.py`: rule + preference-based ranking
- `deep-scrape-full.py`: full description scraping
- `ai-eval.py`: structured AI fit analysis
- `sort-results.py`: bucket into apply/review/skip

Data boundaries:
- Runtime data: `artifacts/`
- Database: `artifacts/jobfinder.db`
- Source/config: repo files (`backend/`, `frontend/`, root config JSON)

## Quick Start

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd ..
python run-backend.py
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Configuration

Environment variables:
- `OPENAI_API_KEY`: required for AI eval and AI cover-letter generation
- `VITE_API_BASE`: frontend API base URL (default `http://127.0.0.1:8001`)
- `JOBFINDER_CHROME_PROFILE`: scraper browser profile directory
- `JOBFINDER_VIEWPORT`: optional scraper viewport override as `WIDTHxHEIGHT` (example: `1280x1440`)

Portability defaults:
- If `JOBFINDER_CHROME_PROFILE` is unset, scripts use repo-local `chrome-profile/`
- If `JOBFINDER_VIEWPORT` is unset, scrapers auto-size to half monitor width and full monitor height

Frontend env setup:

```powershell
cd frontend
copy .env.example .env
```

## Pipeline Sizing

Size presets are `max_results / shortlist_k / final_top`:
- Large: `1000 / 120 / 50`
- Medium: `500 / 60 / 20`
- Small: `100 / 30 / 10`

## Data Lifecycle

Generated outputs (safe to reset):
- `artifacts/tier2_metadata.json`
- `artifacts/tier2_shortlist.json`
- `artifacts/tier2_shortlist.csv`
- `artifacts/tier2_full.json`
- `artifacts/tier2_scored.json`
- `artifacts/apply.json`, `artifacts/review.json`, `artifacts/skip.json`
- `artifacts/*.csv` exports, logs, and cover-letter outputs
- `artifacts/jobfinder.db`

Persistent operator config:
- `preferences.json`
- `shortlist_rules.json`
- `searches.json`
- `resume_profile.json`
- `cover_letter_templates.json`
- `ai_pricing.json`

## AI Cost Tracking

- Pricing source: `ai_pricing.json`
- Usage log: `artifacts/ai_usage.jsonl`
- Rollups: `artifacts/ai_usage_totals.json`

## Troubleshooting

Frontend cannot reach backend:
- Start backend on `127.0.0.1:8001`
- Or set `VITE_API_BASE` in `frontend/.env`

Scraper captures fewer jobs per page than expected:
- Let auto viewport sizing run by default
- Or force `JOBFINDER_VIEWPORT` to a known-good value

Chrome profile lock error:
- Close Chrome instances sharing the same profile
- Or set `JOBFINDER_CHROME_PROFILE` to a dedicated folder

AI calls fail:
- Confirm `OPENAI_API_KEY` is exported in the backend shell

## Quick Reset

```powershell
Remove-Item -Recurse -Force artifacts
New-Item -ItemType Directory artifacts
python run-backend.py
```

## Privacy

- Treat `resume_profile.json`, `cover_letter_templates.json`, and browser profile data as private
- Keep runtime artifacts out of commits
- Sanitize local personal content before publishing the repository
