# Job Finder Local Release Readiness Plan

## Objective
Prepare the project for a reliable local-user release (single-user, self-hosted on user machines) without changing core functionality, endpoint contracts, config precedence, or pipeline behavior.

This plan is execution-focused, staged, and test-gated, following the same protocol style as `docs/reorganization-plan.md`.

## Scope and Release Model
- Target release model: local desktop usage by end users.
- Non-goals:
  - hosted multi-tenant deployment,
  - auth/permissions architecture,
  - backend behavioral redesign.
- Keep current contracts stable:
  - API paths/methods/response shapes,
  - pipeline order `scout -> shortlist -> scrape -> eval`,
  - config precedence `*.local.json -> *.json -> *.example.json`,
  - artifact/DB location semantics.

## Current State Snapshot
- Backend tests pass: `pytest -q backend/tests`
- Frontend production build passes: `cd frontend && npm run build`
- Repository can be clean between runs; generated assets should remain untracked unless intentionally versioned.
- Known operational constraints:
  - LinkedIn profile/session bootstrap required,
  - OpenAI key required for AI features,
  - frontend has no automated test suite yet.

## Execution Protocol (How This Plan Is Run)
- Work one stage at a time, in order, with no stage skipping.
- Each stage includes:
  - explicit implementation tasks,
  - required gates/tests,
  - completion report.
- At end of each stage, report:
  - scope implemented,
  - files changed,
  - tests/gates run and results,
  - risks/TODOs.
- Then explicitly prompt:
  - `Stage N complete. Continue to Stage N+1? (yes/no)`
- No automatic commits.

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

## Status Tracker
- Stage 0: `completed`
- Stage 1: `completed`
- Stage 2: `completed`
- Stage 3: `not_started`
- Stage 4: `not_started`
- Stage 5: `not_started`
- Stage 6: `not_started`

Update statuses here as stages complete.

## Stage Plan

## Stage 0: Baseline Freeze
1. Capture environment and command baseline for local release validation.
2. Confirm current gates pass from a clean state.
3. Record expected runtime prerequisites (Python, Node, Playwright, Chrome profile).

Deliverable:
- `docs/local-release-baseline.md`

Required gates:
- `pytest -q backend/tests`
- `cd frontend && npm run build`

---

## Stage 1: Setup and Bootstrap Hardening
1. Add/verify one-command local setup instructions for backend and frontend.
2. Add interpreter/venv guidance as optional troubleshooting (not a required setup step).
3. Ensure first-run onboarding/bootstrap flow is documented as required.
4. Ensure Playwright/Chromium install command is clearly included.

Deliverables:
- README setup section improvements
- Optional helper script docs (no behavior changes)

Required gates:
- `pytest -q backend/tests`
- `cd frontend && npm run build`

---

## Stage 2: LinkedIn Session and Pipeline UX Clarity
1. Document exact LinkedIn setup flow, expected success signal, and common failure resolution.
2. Add troubleshooting guidance for profile path mismatch and login cookie absence.
3. Verify pipeline preflight messaging remains consistent with docs.

Deliverables:
- README troubleshooting expansion
- Local-user runbook section for LinkedIn setup

Required gates:
- `pytest -q backend/tests`
- Manual check: onboarding LinkedIn status/init + pipeline preflight path

---

## Stage 3: Local Data and Recovery Documentation
1. Document where local data lives:
   - DB,
   - artifacts,
   - config files,
   - generated cover letters.
2. Add backup/restore procedure for safe upgrades.
3. Add reset/recovery procedure for broken local state.

Deliverables:
- New `docs/local-data-and-recovery.md`
- README links to recovery doc

Required gates:
- `pytest -q backend/tests`
- Manual check: backup/restore instructions validated on a temp copy

---

## Stage 4: Release Hygiene and Ignore Policy
1. Ensure build artifacts and transient backup files are ignored where appropriate.
2. Verify no accidental generated-file churn remains in normal workflows.
3. Keep intentional tracked assets untouched.

Deliverables:
- `.gitignore` updates (if needed)
- Documentation note on tracked vs generated files

Required gates:
- `git status` sanity after build and test runs
- `pytest -q backend/tests`
- `cd frontend && npm run build`

---

## Stage 5: Local Smoke Test Checklist and Validation Script
1. Publish a strict smoke checklist users can run in under 10 minutes:
   - backend startup,
   - frontend load,
   - onboarding preflight pass,
   - pipeline test run,
   - jobs/import visibility,
   - cover-letter generate/save/export quick check.
2. Optionally add a lightweight script/command bundle for repeated smoke runs.

Deliverables:
- `docs/local-smoke-checklist.md`
- Optional `scripts/local-smoke.ps1` (no product behavior changes)

Required gates:
- Execute checklist once on current machine and record pass/fail
- `pytest -q backend/tests`

---

## Stage 6: Release Packaging and Tag-Ready Notes
1. Write local release notes:
   - version,
   - installation commands,
   - required env vars,
   - known limitations,
   - troubleshooting links.
2. Add concise user-facing "Getting Started" sequence.
3. Final readiness review against this plan.

Deliverables:
- `docs/release-notes-local-vX.Y.Z.md` (or equivalent)
- README links to release notes and smoke checklist

Required gates:
- `pytest -q backend/tests`
- `cd frontend && npm run build`
- final `git status` clean check (except intended release artifacts)

## Non-Negotiable Invariants
- No endpoint contract changes.
- No config precedence changes.
- No pipeline order/behavior changes.
- No silent mutation of user-tuned config semantics.
- No automatic commits in plan execution.

## Definition of Done
- Local users can set up and run the app reliably with documented steps.
- Troubleshooting covers common failure modes (env, LinkedIn session, preflight).
- Data backup/restore and recovery are documented and tested.
- Required backend/frontend gates pass.
- Release notes and smoke checklist are published and linked from README.
