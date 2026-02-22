# Local Data and Recovery

## Local Data Map

### Runtime Data (Safe to Regenerate)
- `artifacts/tier2_metadata.json`
- `artifacts/tier2_shortlist.json`
- `artifacts/tier2_shortlist.csv`
- `artifacts/tier2_full.json`
- `artifacts/tier2_scored.json`
- `artifacts/apply.json`
- `artifacts/review.json`
- `artifacts/skip.json`
- `artifacts/cover_letters/*`
- `artifacts/ai_usage.jsonl`
- `artifacts/ai_usage_totals.json`
- `artifacts/*.log`

### Database
- Primary DB: `artifacts/jobfinder.db`
- Legacy fallback may appear as `jobfinder.db` in repo root on older runs.

### User Config Files
- `preferences.json`
- `shortlist_rules.json`
- `searches.json`
- `resume_profile.json`
- `cover_letter_templates.json`
- Optional local overrides:
  - `preferences.local.json`
  - `shortlist_rules.local.json`
  - `searches.local.json`
  - `resume_profile.local.json`
  - `cover_letter_templates.local.json`

### Browser Session Data
- LinkedIn profile directory:
  - `JOBFINDER_CHROME_PROFILE` if set
  - otherwise repo-local `chrome-profile/`

## Backup Procedure (Before Upgrades or Major Changes)

Run from repo root:

```powershell
$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$backupDir = "backups\$ts"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

# Core state
if (Test-Path "artifacts\jobfinder.db") { Copy-Item "artifacts\jobfinder.db" "$backupDir\jobfinder.db" -Force }
if (Test-Path "jobfinder.db") { Copy-Item "jobfinder.db" "$backupDir\jobfinder.legacy.db" -Force }

# Configs (base + local overrides)
$cfg = @(
  "preferences.json","shortlist_rules.json","searches.json","resume_profile.json","cover_letter_templates.json",
  "preferences.local.json","shortlist_rules.local.json","searches.local.json","resume_profile.local.json","cover_letter_templates.local.json"
)
foreach ($f in $cfg) {
  if (Test-Path $f) { Copy-Item $f "$backupDir\" -Force }
}

# Optional: preserve generated artifacts for audit/debug
if (Test-Path "artifacts") { Copy-Item "artifacts" "$backupDir\artifacts" -Recurse -Force }

Write-Host "Backup created at $backupDir"
```

## Restore Procedure

Stop backend/frontend first, then run from repo root:

```powershell
$backupDir = "backups\YYYYMMDD-HHMMSS"   # change to your backup folder

if (Test-Path "$backupDir\jobfinder.db") {
  New-Item -ItemType Directory -Force -Path "artifacts" | Out-Null
  Copy-Item "$backupDir\jobfinder.db" "artifacts\jobfinder.db" -Force
}

$cfg = @(
  "preferences.json","shortlist_rules.json","searches.json","resume_profile.json","cover_letter_templates.json",
  "preferences.local.json","shortlist_rules.local.json","searches.local.json","resume_profile.local.json","cover_letter_templates.local.json"
)
foreach ($f in $cfg) {
  if (Test-Path "$backupDir\$f") { Copy-Item "$backupDir\$f" $f -Force }
}

Write-Host "Restore complete. Start backend and run onboarding preflight."
```

## Recovery Playbooks

### Broken Pipeline State
1. Stop backend.
2. Backup current state first (procedure above).
3. Reset generated artifacts only:

```powershell
Remove-Item -Recurse -Force artifacts
New-Item -ItemType Directory artifacts | Out-Null
```

4. Restart backend: `python run-backend.py`
5. Run onboarding preflight and retry pipeline.

### Broken Config Validation
1. Open Onboarding tab and run validation/preflight.
2. Fix invalid config fields in UI or JSON files.
3. If needed, restore the last known-good config backup.
4. Re-run preflight until all hard checks pass.

### LinkedIn Session Lost
1. Run `python setup-linkedin-profile.py`.
2. Sign in to LinkedIn in that exact profile.
3. Confirm:
   - `GET /onboarding/linkedin/status` returns `ok: true`
   - `POST /onboarding/preflight` shows `linkedin_session: pass`

## Verification After Restore
1. `python run-backend.py`
2. Open UI and run Onboarding preflight.
3. Confirm:
   - config validation passes,
   - LinkedIn status is healthy,
   - `/jobs` returns expected records,
   - pipeline can start in `Test` size mode.

