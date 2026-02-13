# Onboarding System Handoff (Post-Compaction Resume)

Use this file to continue onboarding work with minimal re-discovery.

## Objective

Build a first-run onboarding flow so a new user can complete setup once and then run pipeline with minimal manual steps.

Target outcome:
- User installs app
- Completes guided setup
- System verifies readiness
- User can click "Start pipeline" and get meaningful personalized results

---

## Why This Is Needed

Current app behavior depends on user-specific local data and environment setup:
- LinkedIn authenticated browser profile
- OpenAI API key
- Personalized config JSON files (`resume_profile.json`, `preferences.json`, `shortlist_rules.json`, `searches.json`)

Without onboarding, new users must hand-edit JSON and troubleshoot runtime failures manually.

---

## Current Repo Reality (Important)

Core app:
- Backend API/orchestrator: `backend/app.py`
- DB layer: `backend/db.py`
- Frontend dashboard: `frontend/src/App.jsx`

Pipeline scripts:
- `job-scout.py`
- `shortlist.py`
- `deep-scrape-full.py`
- `ai-eval.py`
- `sort-results.py`

Portability updates already implemented:
- `VITE_API_BASE` frontend env support
- `JOBFINDER_CHROME_PROFILE` env support in scout/scrape scripts
- `JOBFINDER_VIEWPORT` auto/override support

LinkedIn setup aid already implemented:
- `setup-linkedin-profile.py`
- Login-required detection added to `job-scout.py` and `deep-scrape-full.py`

Artifacts boundary:
- Runtime outputs now under `artifacts/`

---

## User-Specific Inputs Required For Correct Behavior

A user must have all of these configured:

1. Environment/auth
- `OPENAI_API_KEY`
- Valid LinkedIn session in dedicated Chrome profile (`JOBFINDER_CHROME_PROFILE`)

2. Personalization config
- `resume_profile.json`
- `preferences.json`
- `shortlist_rules.json`
- `searches.json`

3. Runtime prerequisites
- Python dependencies installed (`backend/requirements.txt`)
- Node dependencies installed (`frontend/package.json`)
- Playwright browser available
- Write access to repo and `artifacts/`

---

## Missing Product Layer (What To Build)

Implement a guided onboarding system with:

1. Setup wizard UI (frontend)
- Welcome
- API key setup status
- LinkedIn session setup
- Resume/profile capture
- Job preferences capture
- Search/location setup
- Review + save

2. Backend onboarding endpoints
- Status/readiness summary
- Validation endpoints for each config block
- Save endpoints
- Preflight verifier endpoint

3. Config bootstrap + migration
- Generate missing JSON from templates/defaults
- Schema versioning in each config
- Migration path for old versions

4. Preflight checks (single actionable report)
- API key present
- LinkedIn session valid
- Required config files exist and validate
- Required folders writable
- Optional: quick dry-run validation

---

## Recommended New Files

Config templates/examples:
- `config_examples/resume_profile.example.json`
- `config_examples/preferences.example.json`
- `config_examples/shortlist_rules.example.json`
- `config_examples/searches.example.json`

Validation/migration:
- `backend/onboarding_schema.py`
- `backend/onboarding_validate.py`
- `backend/onboarding_migrate.py`

Optional local-only convention (future-safe):
- `resume_profile.local.json`
- `preferences.local.json`
- `shortlist_rules.local.json`
- `searches.local.json`

Then add loader precedence:
1. `*.local.json`
2. normal file (`*.json`)
3. example/default

---

## Proposed API Surface (Backend)

Add endpoints (names can vary, keep semantics):

Status:
- `GET /onboarding/status`
  - Returns per-step completion + blocking issues

Profile and preferences:
- `GET /onboarding/config`
- `PUT /onboarding/config/resume-profile`
- `PUT /onboarding/config/preferences`
- `PUT /onboarding/config/shortlist-rules`
- `PUT /onboarding/config/searches`

LinkedIn/session checks:
- `POST /onboarding/linkedin/init` (optional wrapper around setup script guidance)
- `GET /onboarding/linkedin/status` (login/session check)

Readiness:
- `POST /onboarding/preflight`
  - Returns structured checks: pass/warn/fail with fix suggestions

Schema/migrations:
- `POST /onboarding/migrate`

---

## Frontend Wizard Requirements

Create onboarding flow in UI (new tab or modal):

Step 1: Environment
- Detect backend connectivity
- Show API key presence status (boolean only, never reveal secret)

Step 2: LinkedIn Session
- Explain dedicated profile behavior
- Trigger/setup instructions (`setup-linkedin-profile.py`)
- Verify status check from backend

Step 3: Resume/Profile
- Minimum fields: target roles, skills, education summary, years experience
- Optional: resume upload/parsing later
- Show validation errors inline

Step 4: Preferences
- Salary floor, remote/hybrid/onsite handling, no-cold-calling, industry penalties

Step 5: Search Setup
- At least one search entry in `searches.json` with label/url/location

Step 6: Review & Save
- Show normalized JSON preview
- Save all configs

Step 7: Preflight + First Run
- Run preflight and block pipeline start if critical checks fail
- Offer “Run Small pipeline” button on success

---

## Validation Rules (Minimum)

`resume_profile`:
- Non-empty `skills` array
- At least one `target_roles` entry

`preferences`:
- `qualification.min_match_score` numeric range [0.35, 0.85]
- `hard_constraints.min_base_salary_usd` int >= 0 when present

`shortlist_rules`:
- Required scoring structures present (`workplace_score`, penalties defaults)
- Numeric penalties within reasonable bounds

`searches`:
- At least one search object with `label`, `url`, `location_label`

Global:
- Unknown keys logged as warnings (not hard fail initially)

---

## Schema Versioning Strategy

Add `"schema_version"` field to each config JSON.

Migration behavior:
- If missing version => treat as v1 and migrate to current
- Backup old file before write: `*.bak.<timestamp>`
- Return migration report in endpoint response

---

## Preflight Definition Of Done

Preflight must verify all of:

Hard fail:
- Backend can read/write required config files
- Required config passes validation
- `OPENAI_API_KEY` is present
- LinkedIn session check passes

Warn only:
- Missing optional fields
- Suspiciously narrow searches
- Very strict thresholds likely to over-filter

Output format:
- `checks`: list of `{id, status, message, fix_hint}`
- `ready`: boolean

---

## Verification Checklist (Manual QA)

Run this checklist before marking onboarding complete:

1. Fresh clone simulation
- Remove local config and artifacts
- Follow README + onboarding only
- Confirm no manual JSON editing needed

2. First-run wizard
- Completes all steps without backend exceptions
- Saves valid config files

3. LinkedIn session gate
- With no login: preflight fails with actionable message
- After setup: preflight passes

4. Pipeline execution
- Run `Small` pipeline from UI
- Scout/shortlist/scrape/eval complete
- Results populate jobs table

5. Reload persistence
- Restart backend/frontend
- Onboarding status remains complete

6. Regression checks
- Existing non-onboarded users still supported via fallback defaults
- No break in current pipeline scripts

---

## Suggested Implementation Order (Concrete)

1. Build backend validation + status + preflight endpoints
2. Add config templates and loader/migration layer
3. Add frontend onboarding wizard (basic version)
4. Wire preflight gating into pipeline start UI
5. Add polish: inline fix links, better copy, optional resume parsing

---

## Commands For Next Session

Run backend:
```powershell
python run-backend.py
```

Run frontend:
```powershell
cd frontend
npm run dev
```

Run smoke compile:
```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; python -m py_compile backend\app.py backend\db.py job-scout.py deep-scrape-full.py
```

Run current tests:
```powershell
python -m pytest backend\tests\test_pipeline.py
```

---

## Resume Prompt For Future Session

Use this exact prompt after compaction:

"Use `ONBOARDING_HANDOFF.md` as source of truth. Implement onboarding step-by-step starting with backend preflight/status/validation endpoints, then frontend wizard, then pipeline gating. Keep backward compatibility with existing config files and add schema version migrations."
