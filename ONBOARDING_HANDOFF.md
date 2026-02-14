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

Config privacy split (already implemented for two files):
- Resume/profile loading precedence is now:
  - `resume_profile.local.json` -> `resume_profile.json` -> `resume_profile.example.json`
- Cover-letter template loading precedence is now:
  - `cover_letter_templates.local.json` -> `cover_letter_templates.json` -> `cover_letter_templates.example.json`
- Local files are gitignored and intended to hold personal data.

---

## User-Specific Inputs Required For Correct Behavior

A user must have all of these configured:

1. Environment/auth
- `OPENAI_API_KEY`
- Valid LinkedIn session in dedicated Chrome profile (`JOBFINDER_CHROME_PROFILE`)

2. Personalization config
- `resume_profile.local.json` (preferred) or fallback chain
- `preferences.json`
- `shortlist_rules.json`
- `searches.json`
- `cover_letter_templates.local.json` (for personalized templates)

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
- Natural-language profile builder (plain English to config draft)

2. Backend onboarding endpoints
- Status/readiness summary
- Validation endpoints for each config block
- Save endpoints
- Preflight verifier endpoint
- AI-assisted profile draft endpoint
- Search/city CRUD endpoints

3. Config bootstrap + migration
- Generate missing JSON from templates/defaults on first run
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
- `resume_profile.example.json` (already exists)
- `cover_letter_templates.example.json` (already exists)
- `preferences.example.json` (recommended to add)
- `shortlist_rules.example.json` (recommended to add)
- `searches.example.json` (recommended to add)

Validation/migration:
- `backend/onboarding_schema.py`
- `backend/onboarding_validate.py`
- `backend/onboarding_migrate.py`

Optional local-only convention (future-safe):
- `resume_profile.local.json`
- `cover_letter_templates.local.json`
- `preferences.local.json`
- `shortlist_rules.local.json`
- `searches.local.json`

Then add loader precedence:
1. `*.local.json`
2. normal file (`*.json`)
3. example/default

Status:
- Resume/templates precedence is done.
- Preferences/rules/searches local precedence is still pending.

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

Natural-language profile draft:
- `POST /onboarding/profile-draft`
  - Input: free-text goals/preferences/background
  - Output: structured draft for:
    - `resume_profile`
    - `preferences`
    - `shortlist_rules` (safe defaults + inferred adjustments)
    - `searches` seed suggestions
  - Must return confidence + missing-fields prompts

Search and city management:
- `GET /onboarding/searches`
- `POST /onboarding/searches`
- `PUT /onboarding/searches/{label}`
- `DELETE /onboarding/searches/{label}`
  - Keep user-friendly fields:
    - `label`
    - `location_label`
    - optional keywords
    - generated LinkedIn URL

LinkedIn/session checks:
- `POST /onboarding/linkedin/init` (optional wrapper around setup script guidance)
- `GET /onboarding/linkedin/status` (login/session check)

Readiness:
- `POST /onboarding/preflight`
  - Returns structured checks: pass/warn/fail with fix suggestions

Bootstrap:
- `POST /onboarding/bootstrap`
  - Ensures all required user-local files exist (copy from examples/defaults when missing)
  - Returns created/copied file list

Schema/migrations:
- `POST /onboarding/migrate`

---

## Frontend Wizard Requirements

Create onboarding flow in UI (new tab or modal):

Step 1: Environment
- Detect backend connectivity
- Show API key presence status (boolean only, never reveal secret)
- Run bootstrap endpoint to create any missing local config skeletons

Step 2: LinkedIn Session
- Explain dedicated profile behavior
- Trigger/setup instructions (`setup-linkedin-profile.py`)
- Verify status check from backend

Step 3: Resume/Profile
- Minimum fields: target roles, skills, education summary, years experience
- Optional: resume upload/parsing later
- Show validation errors inline

Step 3A: Plain-English Intake (new)
- Text box: "Describe your background and what you want in your next job"
- Guided helper prompts for missing essentials:
  - preferred roles
  - industries to avoid/prefer
  - salary expectations
  - workplace preference
  - location constraints
  - red flags (e.g., cold-calling heavy)
- "Generate draft profile" action calls `/onboarding/profile-draft`
- Show draft JSON + editable form before save
- Do not auto-save without user confirmation

Step 4: Preferences
- Salary floor, remote/hybrid/onsite handling, no-cold-calling, industry penalties

Step 5: Search Setup
- At least one search entry in `searches.json` with label/url/location
- Include simple "Add city/search" UI:
  - city/location input
  - optional keywords
  - auto-generate URL
  - edit/delete existing searches

Step 6: Review & Save
- Show normalized JSON preview
- Save all configs to local files where applicable

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
- No duplicate labels
- URL should include expected LinkedIn jobs search shape

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
- Playwright/browser dependency is available

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
- Confirm no manual code edits or path edits needed

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
- New run descriptions are cleaned (no common LinkedIn boilerplate tails)

5. Reload persistence
- Restart backend/frontend
- Onboarding status remains complete

6. Regression checks
- Existing non-onboarded users still supported via fallback defaults
- No break in current pipeline scripts
- Existing users with `.local` files keep behavior unchanged

---

## Suggested Implementation Order (Concrete)

1. Add missing example files (`preferences.example.json`, `shortlist_rules.example.json`, `searches.example.json`)
2. Build backend bootstrap + validation + status + preflight endpoints
3. Add loader precedence for `preferences/rules/searches` to support `.local` chain
4. Add config migration layer
5. Add frontend onboarding wizard (basic version)
6. Wire preflight gating into pipeline start UI
7. Add polish: inline fix links, better copy, optional resume parsing

---

## Product Acceptance Criteria (Out-Of-Box)

For "download, follow simple instructions, and use effectively":

- New user can clone + install deps + start backend/frontend without editing source.
- On first launch, onboarding flow guides setup in under ~10 minutes.
- User does not need to hand-edit JSON files.
- User can describe preferences in plain English and get a usable draft profile.
- User can complete LinkedIn session setup once, then pipeline reuses it.
- User can add/edit/remove cities/searches from UI without touching JSON.
- After onboarding, `Small` pipeline runs successfully and returns usable ranked jobs.
- Preflight clearly blocks and explains missing prerequisites.
- Existing advanced users can still override via `.local` files and env vars.

Quality bar for profile-draft step:
- If confidence is low, system asks targeted follow-up questions instead of forcing weak defaults.
- Draft must be editable before save.
- Final saved config must pass all validators.

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
