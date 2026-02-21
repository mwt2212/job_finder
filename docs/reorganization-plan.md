# Job Finder Reorganization Plan (No Functional Changes)

## Objective
Refactor project structure into logical modules while preserving exact behavior, API contracts, runtime outputs, config precedence, and UI workflows.

This plan is intentionally conservative: every phase is reversible, test-gated, and focused on moves/extractions before any logic edits.

## Handoff-Ready Context (Read This First)
Use this section as source of truth when resuming in a future session.

### Repository and Runtime Basics
- Repo root: `c:\Users\Michael\Desktop\Job Finder`
- Backend entrypoint: `run-backend.py` -> `backend.app:app` on `127.0.0.1:8001`
- Frontend entrypoint: `frontend/src/main.jsx` (Vite)
- Primary monolith files:
  - `backend/app.py`
  - `frontend/src/App.jsx`
- DB location behavior:
  - prefers `artifacts/jobfinder.db`
  - falls back to legacy `jobfinder.db` if needed

### Pipeline Behavior Contract
- Orchestrated pipeline order: `scout -> shortlist -> scrape -> eval`
- Sort script exists but is not part of the threaded full pipeline run.
- Script files currently invoked by backend:
  - `job-scout.py`
  - `shortlist.py`
  - `deep-scrape-full.py`
  - `ai-eval.py`
  - `sort-results.py`
- Run state is global and lock-protected (`RUN_STATE`) with SSE stream at `/runs/stream`.
- Starting pipeline or running scout no longer mutates `preferences.json` location fields.

### Config and Data Contract
- Config precedence (where implemented): `*.local.json -> *.json -> *.example.json`
- Key config files:
  - `preferences*.json`
  - `shortlist_rules*.json`
  - `searches*.json`
  - `resume_profile*.json`
  - `cover_letter_templates*.json`
- Runtime outputs live under `artifacts/`.
- Location is no longer an evaluation preference factor in `preferences.search_filters`.
- City selection should be handled via `searches` entries (`label`, `url`, `location_label`).

### API Surface Contract (Must Not Change)
- Health/debug: `/health`, `/debug/env`
- Jobs and feedback: `/jobs`, `/jobs/{job_id}`, `/ratings`, `/status`, `/feedback/shortlist`, `/feedback/ai`
- Settings/searches: `/settings`, `/searches`
- Onboarding: `/onboarding/*` endpoints currently in `backend/app.py`
- AI pricing/estimates: `/ai/pricing`, `/ai/estimate/*`
- Cover letters/templates: `/cover-letter-templates*`, `/cover-letters*`
- Pipeline run control: `/run/start`, `/run/{step}`, `/runs/stream`, `/runs/state`
- Import/suggestions: `/import`, `/suggestions/generate`, `/suggestions/apply`

### Test Baseline
- Backend tests currently expected:
  - `pytest -q backend/tests`
  - Current baseline: `49 passed` (as of latest update)
- Backend test modules:
  - `backend/tests/test_ai_usage.py`
  - `backend/tests/test_api_routes.py`
  - `backend/tests/test_cover_letters_api.py`
  - `backend/tests/test_onboarding.py`
  - `backend/tests/test_pipeline.py`
  - `backend/tests/test_runs_import_suggestions_api.py`

### Current Reorg Status Tracker
- Stage 0: `completed`
- Stage 1: `not_started`
- Stage 2: `not_started`
- Stage 3: `not_started`
- Stage 4: `not_started`
- Stage 5: `not_started`
- Stage 6: `not_started`
- Stage 7: `not_started`

Update these statuses in this file as stages complete.

## Execution Protocol (How This Will Be Run)
- Work one stage at a time, in order, with no stage skipping.
- Each stage has:
  - explicit implementation steps,
  - required tests/gates,
  - required completion report.
- At the end of each stage, stop and report:
  - what was implemented,
  - files changed,
  - tests run + results,
  - known risks or follow-ups.
- Then explicitly prompt:
  - `Stage N complete. Continue to Stage N+1? (yes/no)`
- Add comments only where needed to preserve intent during extraction:
  - non-obvious compatibility shims,
  - temporary adapters,
  - behavior-preserving wrappers.
- Do not add explanatory comments for self-evident code.
- Testing is mandatory after each stage; no new stage starts if gates fail.

### Stage Completion Report Template
```md
## Stage N Completion Report
- Scope implemented:
- Files changed:
- Behavior invariants checked:
- Tests run:
  - command:
  - result:
- Manual checks run:
- Known risks / TODOs:
- Suggested commit message (not executed):

Stage N complete. Continue to Stage N+1? (yes/no)
```

### Session Resume Prompt (Copy/Paste)
```text
Use docs/reorganization-plan.md as the only source of truth. Continue from the first stage marked not_started.
Follow the Execution Protocol exactly:
1) implement only that stage,
2) run required tests/gates,
3) produce the Stage Completion Report in the specified format,
4) include a suggested git commit message (do not run git commit),
5) stop and ask: "Stage N complete. Continue to Stage N+1? (yes/no)".
Do not change functionality, endpoint contracts, config precedence, or pipeline behavior.
Do not create commits automatically.
```

### If Context Is Missing in a Future Session
- Re-read these files before implementing:
  - `backend/app.py`
  - `backend/db.py`
  - `backend/onboarding_validate.py`
  - `backend/onboarding_migrate.py`
  - `frontend/src/App.jsx`
  - `job-scout.py`
  - `shortlist.py`
  - `deep-scrape-full.py`
  - `ai-eval.py`
  - `sort-results.py`
  - `backend/tests/test_onboarding.py`
  - `backend/tests/test_pipeline.py`
  - `backend/tests/test_ai_usage.py`
  - `backend/tests/test_api_routes.py`
  - `backend/tests/test_cover_letters_api.py`
  - `backend/tests/test_runs_import_suggestions_api.py`

### Known Test Gaps (Important)
- Frontend is not covered by automated tests yet (no component/e2e coverage).
- Live LinkedIn scraping behavior cannot be fully validated in unit tests.
- Live OpenAI generation behavior/cost/latency cannot be fully validated in unit tests.
- Some concurrency timing edge cases are mocked rather than stress-tested.
- `docx`/`pdf` export paths are exercised less deeply than `txt`.

## Non-Negotiable Invariants
- Keep all existing endpoint paths, methods, request/response shapes, and status codes.
- Keep pipeline execution order and defaults:
  - pipeline thread: `scout -> shortlist -> scrape -> eval`
  - step route support for `sort` remains available.
- Keep file precedence behavior:
  - `*.local.json -> *.json -> *.example.json` for supported config types.
- Keep artifacts and DB behavior:
  - `artifacts/jobfinder.db` resolution behavior and imports stay unchanged.
- Keep run-state semantics:
  - single active run lock, SSE log stream behavior, progress parsing.
- Keep frontend tab behavior and user flows exactly as-is.
- Keep CLI script arguments and output file names exactly as-is.

## Current System Map

### Backend
- Main app: `backend/app.py`
- DB layer: `backend/db.py`
- Onboarding validators/migrations:
  - `backend/onboarding_validate.py`
  - `backend/onboarding_migrate.py`
  - `backend/onboarding_schema.py`
- Tests:
  - `backend/tests/test_onboarding.py`
  - `backend/tests/test_pipeline.py`
  - `backend/tests/test_ai_usage.py`

### Pipeline Scripts
- Scout: `job-scout.py`
- Shortlist: `shortlist.py`
- Scrape: `deep-scrape-full.py`
- Eval: `ai-eval.py`
- Sort: `sort-results.py`
- LinkedIn session setup: `setup-linkedin-profile.py`

### Shared Utilities
- AI usage/cost accounting: `ai_usage.py`
- Description cleaning: `text_cleaning.py`
- Backend launcher: `run-backend.py`

### Frontend
- SPA entry: `frontend/src/App.jsx`
- Bootstrapping: `frontend/src/main.jsx`
- Styling: `frontend/src/styles.css`

### Runtime Data and Config
- Artifacts: `artifacts/`
- Configs: `preferences*.json`, `shortlist_rules*.json`, `searches*.json`, `resume_profile*.json`, `cover_letter_templates*.json`

## Target Structure (Logical Ownership)

### Backend target layout
```text
backend/
  app.py                      # thin composition root only
  api/
    deps.py
    router.py
    routes/
      health.py
      jobs.py
      settings.py
      onboarding.py
      ai_estimates.py
      cover_letters.py
      runs.py
      imports.py
      suggestions.py
  domain/
    models/
      dto.py                  # pydantic request/response models
    services/
      onboarding_service.py
      pipeline_service.py
      ai_service.py
      cover_letter_service.py
      tuning_service.py
      search_service.py
      settings_service.py
  infra/
    db/
      repository.py           # extracted from db.py
      schema.py               # schema/init/migration helpers
    files/
      config_loader.py
      artifact_paths.py
  legacy/
    compat.py                 # temporary compatibility imports
```

### Frontend target layout
```text
frontend/src/
  app/
    AppShell.jsx
    routes.jsx                # tab switching shell
  api/
    client.js
    endpoints.js
  features/
    onboarding/
    jobs/
    settings/
    pipeline/
    coverLetters/
  shared/
    components/
    hooks/
    utils/
    constants/
  styles/
    tokens.css
    layout.css
    features/*.css
  main.jsx
```

### Pipeline target layout
```text
pipeline/
  scout.py
  shortlist.py
  scrape.py
  eval.py
  sort.py
  common/
    paths.py
    browser.py
    io.py
scripts/
  job-scout.py                # compatibility wrapper
  shortlist.py                # compatibility wrapper
  deep-scrape-full.py         # compatibility wrapper
  ai-eval.py                  # compatibility wrapper
  sort-results.py             # compatibility wrapper
```

Important: wrappers preserve current invocation names and arguments so no caller breaks.

## Stage Plan

## Stage 0: Baseline Freeze and Safety Net
1. Capture route contract snapshots.
2. Capture representative JSON responses for critical endpoints.
3. Record UI smoke checklist for each tab.
4. Record pipeline output checksum workflow for a fixed sample run.
5. Run full backend tests as baseline gate.

Deliverables:
- `docs/reorg-baseline.md` with command outputs and endpoint fixtures.
- Optional `backend/tests/test_api_contract_smoke.py`.

Gate:
- All existing tests pass.
- No code movement yet.

Required commands:
- `pytest -q backend/tests`
- `python -m py_compile backend\app.py backend\db.py`

## Stage 1: Backend Extraction Scaffolding (No Logic Moves Yet)
1. Create package skeleton (`backend/api`, `backend/domain`, `backend/infra`).
2. Move pydantic classes from `backend/app.py` into `backend/domain/models/dto.py`.
3. Re-export models in a temporary compatibility module to avoid route churn.
4. Keep `backend/app.py` behavior identical by importing moved models.

Gate:
- Tests unchanged and passing.
- `python -m py_compile` passes for backend modules.

Required commands:
- `pytest -q backend/tests`
- `python -m py_compile backend\app.py`

## Stage 2: Route Decomposition by Vertical Slice
Order is chosen to minimize coupling risk.

1. Extract read-only routes first:
   - health/debug/jobs/searches/settings GET.
2. Extract onboarding routes next:
   - config read/write, validators, bootstrap, preflight, linkedin helpers, migrate.
3. Extract cover-letter and AI estimate routes.
4. Extract run/import/suggestions routes last (most stateful).

Rules:
- Move code first, do not refactor internals in the same commit.
- Preserve function names during move where possible.
- Keep central `RUN_STATE` in one module and import it.

Gate per slice:
- Same endpoint contract tests pass.
- Existing backend tests pass.

Required commands:
- `pytest -q backend/tests`

## Stage 3: Service Layer Extraction
1. Move pure logic helpers from route files into services:
   - onboarding validation orchestration
   - AI estimate calculations
   - cover-letter prompt assembly + generation flow
   - run orchestration helpers
   - tuning logic
2. Keep route handlers as thin adapters.
3. Introduce typed service inputs/outputs where possible without changing payload shape.

Gate:
- Existing tests pass.
- Add targeted unit tests for extracted services with no behavior drift.

Required commands:
- `pytest -q backend/tests`

## Stage 4: DB/Infra Layer Normalization
1. Split `backend/db.py` into:
   - schema/init module
   - repository module (CRUD/upserts/queries)
2. Keep identical SQL and transaction boundaries.
3. Provide compatibility import surface so old imports still resolve during transition.

Gate:
- Query behavior tests unchanged.
- No SQL changes unless required for parity bugs.

Required commands:
- `pytest -q backend/tests`

## Stage 5: Frontend Decomposition (Behavior-Preserving)
1. Introduce `api/client.js` and centralized endpoint helper functions.
2. Split `App.jsx` by tab feature in this order:
   - Jobs
   - Settings
   - Pipeline
   - Cover Letters
   - Onboarding
3. Move utilities/constants to `shared/utils` and `shared/constants`.
4. Keep same state model first; do not redesign state management during split.
5. Keep CSS rendering equivalent; move styles in chunks by feature.

Gate:
- Manual UI parity checklist passes.
- Build passes (`npm run build`).
- No endpoint usage changes.

Required commands:
- `cd frontend && npm run build`
- `pytest -q backend/tests`

## Stage 6: Pipeline Reorganization with CLI Compatibility
1. Create `pipeline/` modules and move script logic with unchanged behavior.
2. Replace root scripts with thin wrappers calling new module `main()`.
3. Preserve CLI flags, defaults, output paths, and printed progress line formats.
4. Keep backend script path resolution working by either:
   - updating `SCRIPT_NAMES` to wrapper locations, or
   - preserving original script names as wrappers.

Gate:
- Backend run routes still execute successfully.
- Dry run of each step produces same output shape and key fields.

Required commands:
- `pytest -q backend/tests`
- `python -m py_compile job-scout.py shortlist.py deep-scrape-full.py ai-eval.py sort-results.py`

## Stage 7: Final Composition and Cleanup
1. Make `backend/app.py` composition-only:
   - app creation
   - middleware
   - router includes
   - lifespan wiring
2. Remove temporary compatibility shims after all imports are migrated.
3. Update README architecture section to reflect final structure.

Gate:
- Full tests and smoke checks pass.
- No user-visible behavior changes observed.

Required commands:
- `pytest -q backend/tests`
- `cd frontend && npm run build`

## Test and Verification Strategy

### Automated
- Existing suite:
  - `pytest -q backend/tests`
- Add high-value parity tests:
  - endpoint contract smoke for representative responses
  - run-state and SSE stream behavior
  - cover-letter estimate/generate/save/export path
  - pipeline estimate parity for both size-based and file-based eval

### Manual Smoke Checklist
1. Onboarding:
   - bootstrap, status, config save, preflight, linkedin status/init.
2. Jobs tab:
   - filter/search/detail, rating/status saves, shortlist/ai feedback.
3. Pipeline:
   - run start, run step, stream logs, progress bar, preflight gate.
4. Cover letters:
   - templates CRUD, estimate, generate, save, export.
5. Settings:
   - load/save/import/suggestions.

### Data Parity Checks
- For a fixed artifact input set, compare before/after:
  - record counts and key fields in `tier2_*` outputs.
  - DB row counts by table.
  - run logs presence and status.

## Risk Register and Mitigations
- Risk: Hidden coupling in `backend/app.py`.
  - Mitigation: small vertical slices + route contract tests.
- Risk: Frontend state regressions during split.
  - Mitigation: keep state model unchanged initially; split presentation first.
- Risk: Pipeline script invocation breakage.
  - Mitigation: keep script wrappers with identical CLI.
- Risk: Import path churn.
  - Mitigation: temporary compatibility modules and incremental removal.

## Suggested Commit Cadence
1. `chore(reorg): add baseline contracts and parity checklist`
2. `refactor(backend): introduce api/domain/infra skeleton + DTO extraction`
3. `refactor(backend): move read-only routes`
4. `refactor(backend): move onboarding routes`
5. `refactor(backend): move cover-letter and ai estimate routes`
6. `refactor(backend): move run/import/suggestions routes`
7. `refactor(frontend): extract api client and jobs feature`
8. `refactor(frontend): extract settings + pipeline features`
9. `refactor(frontend): extract cover letters + onboarding features`
10. `refactor(pipeline): module-ize scripts with wrappers`
11. `refactor(core): thin composition roots + remove compat shims`

Each commit should be independently testable and deployable.

## Definition of Done
- `backend/app.py` is composition-focused, not a monolith.
- `frontend/src/App.jsx` is replaced by feature modules with unchanged UX.
- Pipeline code is in dedicated modules, wrappers preserve old CLI usage.
- All existing functionality verified with automated tests and manual smoke checks.
- API, config precedence, and artifact outputs remain behaviorally equivalent.

