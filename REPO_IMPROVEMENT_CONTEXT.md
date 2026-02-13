# Repository Improvement Context (Handoff)

This file captures the current repo critique and implementation context so future sessions can continue without re-discovery.

## Why this exists

You asked for a full-repo critique and a durable handoff artifact before compacting.  
Use this file as the source of truth for the next improvement passes.

---

## Current Repo State (Summary)

- Project: local job-finder pipeline + dashboard (FastAPI backend + React frontend).
- Pipeline shape: `scout -> shortlist -> scrape -> eval` (sort step intentionally skipped in full pipeline thread).
- Data persistence: SQLite (`jobfinder.db`) + JSON/CSV artifacts.
- Tuning exists and is now guarded (idempotent feedback checks, reason-required remove tuning, simplified tuning deltas, low-pay mapped to salary floor).

---

## Key Issues Identified

### 1) Repository hygiene / data boundaries

Problem:
- Generated and personal artifacts are tracked in git (DB, pipeline outputs, logs, personal profile/template data).
- This bloats history and mixes runtime/private data with source.

What was observed:
- Tracked examples included: `jobfinder.db`, `tier2_*.json`, `tier2_*.csv`, `tuning_log.jsonl`, apply/review/skip outputs.
- `.gitignore` now contains relevant ignores, but tracked files still remain tracked unless removed from index.

Straightforward fix:
- Keep runtime data under a dedicated `artifacts/` folder and ignore it.
- Untrack currently tracked artifacts with:
  - `git rm -r --cached .`
  - `git add .`
  - verify with `git status`.

---

### 2) Machine-specific path assumptions

Problem:
- Scraper scripts hardcode local Windows paths for Chrome profile.

What was observed:
- `job-scout.py` and `deep-scrape-full.py` use `C:\Users\Michael\Desktop\Job Finder\chrome-profile`.

Straightforward fix:
- Load profile path from env var with sane default:
  - e.g. `JOBFINDER_CHROME_PROFILE`
  - fallback to repo-local `chrome-profile/`.
- Document in README.

---

### 3) Sensitive personal content in tracked files

Problem:
- Personal resume profile and cover letter template content are committed.

What was observed:
- `resume_profile.json` contains personal career history/preferences.
- `cover_letter_templates.json` includes personally authored content/name.

Straightforward fix:
- Move to local-only files:
  - `resume_profile.local.json`
  - `cover_letter_templates.local.json`
- Commit sanitized examples:
  - `resume_profile.example.json`
  - `cover_letter_templates.example.json`
- Update app loading order: local override first, then example/default.

---

### 4) Thin automated test coverage

Problem:
- Only a narrow pipeline-thread test exists.

What was observed:
- `backend/tests/test_pipeline.py` has a single focused test.

Straightforward fix:
- Add 3 targeted tests (no large test suite expansion):
  1. shortlist feedback idempotence (same payload does not re-tune),
  2. remove with blank reason does not tune,
  3. low-pay reason increases salary floor (not qualification threshold).

---

### 5) Frontend API endpoint hardcoded

Problem:
- Frontend API base URL is fixed to localhost address.

What was observed:
- `frontend/src/App.jsx` has `const API = "http://127.0.0.1:8001"`.

Straightforward fix:
- Use Vite env var:
  - `const API = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8001"`
- Add `.env.example` with `VITE_API_BASE`.

---

### 6) Scrape content quality can include noisy page chrome

Problem:
- Full description extraction may include LinkedIn boilerplate and recommendations.

What was observed:
- `deep-scrape-full.py` accepts the first visible long text block.
- Resulting descriptions can contain non-job content.

Straightforward fix:
- Add a post-extraction cleaner to trim text at known boilerplate markers.
- Reuse same cleaner for tuning/scoring inputs for consistency.

---

### 7) README under-communicates architecture and data lifecycle

Problem:
- README is clean but minimal relative to project complexity.

Straightforward fix:
- Expand with short sections:
  1. Architecture
  2. Data lifecycle (what is generated vs persistent)
  3. Config files and precedence
  4. Privacy/local data policy
  5. Troubleshooting
  6. Quick reset / clean artifacts

---

## Tuning-System Notes (Current Intended Behavior)

These were recently improved and should be preserved:

- Feedback endpoints:
  - same feedback payload for same job => no retune (idempotent),
  - remove + blank reason => no auto-tune.
- Tuning changes are now smaller and single-path per event.
- `low pay` maps to salary floor increase, not qualification threshold.
- Noisy keyword auto-penalties from raw text were removed from tuning branch.

When making further tuning edits, avoid reintroducing:
- multi-penalty compounding from one click,
- global changes from blank/ambiguous feedback,
- raw-page keyword pollution.

---

## Recommended Execution Plan (Practical Order)

1. **Repo/Data hygiene pass**
   - move runtime outputs to `artifacts/`,
   - untrack generated files,
   - keep only source + sanitized examples.

2. **Portability pass**
   - env-based API base URL + Chrome profile path.

3. **README/presentation pass**
   - architecture + lifecycle + setup polish + screenshot/GIF.

4. **Coverage pass**
   - add 3 focused backend tests for tuning behavior.

5. **Scrape quality pass**
   - normalize/trim description extraction and verify improved signal quality.

---

## Commands You’ll Likely Need

Untrack ignored files:
```powershell
git rm -r --cached .
git add .
git status
```

Run backend test:
```powershell
python -m pytest backend\tests\test_pipeline.py
```

Run frontend:
```powershell
cd frontend
npm run dev
```

Run backend:
```powershell
python run-backend.py
```

---

## How to Resume After Compact

Prompt with:
- “Use `REPO_IMPROVEMENT_CONTEXT.md` and continue from step X in the execution plan.”

This should provide enough context to continue without repeating discovery.

