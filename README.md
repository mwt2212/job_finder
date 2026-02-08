# Job Finder Dashboard

Local FastAPI + React app to run the pipeline, review jobs, rate them, and tune preferences.

## Backend

```
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

## Frontend

```
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Notes
- Uses SQLite database `jobfinder.db` in the project root.
- Uses existing scripts (`job-scout.py`, `shortlist.py`, `deep-scrape-full.py`, `ai-eval.py`, `sort-results.py`).
- AI eval requires `OPENAI_API_KEY` in your environment.
