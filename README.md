# Job Finder Dashboard

Local FastAPI + React app to run the pipeline, review jobs, rate them, and tune preferences.

## Backend

```
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd ..
python run-backend.py
```

## Frontend

```
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Pipeline Sizes

Sizes control how many jobs are pulled, shortlisted, scraped, and evaluated.

- Large: 1000 / 120 / 50
- Medium: 500 / 60 / 20
- Small: 100 / 30 / 10

Where the numbers mean: `max_results / shortlist_k / final_top`.

## AI Eval (Batching)

`ai-eval.py` supports batching to reduce overhead per job:

```
python ai-eval.py --batch-size 5
```

Default batch size is 5. It evaluates jobs in order and writes `tier2_scored.json` after each batch.

## Cover Letter Templates

- Templates live in `cover_letter_templates.json`.
- The Cover Letters tab supports template selection and editing.
- The date is normalized to `MMMM D, YYYY` during generation.
- A header line equal to `Ruan` is replaced with the job’s company name.

## AI Cost Tracking

- Pricing lives in `ai_pricing.json`.
- Usage is logged to `ai_usage.jsonl`, with rollups in `ai_usage_totals.json`.
- Estimates are shown in the UI next to AI actions.

## Auto-Reload (Dev)

`run-backend.py` now runs Uvicorn with `reload=True`. This auto-restarts the backend on file changes.

Note: reload will restart any in-flight pipeline run.

## Notes
- Uses SQLite database `jobfinder.db` in the project root.
- Uses existing scripts (`job-scout.py`, `shortlist.py`, `deep-scrape-full.py`, `ai-eval.py`, `sort-results.py`).
- AI eval requires `OPENAI_API_KEY` in your environment.
