# Reorganization Baseline Snapshot (Stage 0)

Captured: 2026-02-21  
Workspace: `c:\Users\Michael\Desktop\Job Finder`  
Source: live `backend/app.py` FastAPI app and current local runtime/config state.

## 1) Route Contract Snapshot

Command used:

```powershell
@'
from backend.app import app
import json

routes = []
for r in app.routes:
    path = getattr(r, "path", "")
    methods = sorted([m for m in (getattr(r, "methods", []) or []) if m not in {"HEAD","OPTIONS"}])
    if not path or not methods:
        continue
    if path in {"/docs", "/docs/oauth2-redirect", "/openapi.json", "/redoc"}:
        continue
    routes.append({"path": path, "methods": methods})

routes = sorted(routes, key=lambda x: (x["path"], ",".join(x["methods"])))
print(json.dumps(routes, indent=2))
'@ | python -
```

Snapshot output:

```json
[
  {"path": "/ai/estimate/cover-letter", "methods": ["POST"]},
  {"path": "/ai/estimate/eval", "methods": ["POST"]},
  {"path": "/ai/estimate/pipeline", "methods": ["POST"]},
  {"path": "/ai/pricing", "methods": ["GET"]},
  {"path": "/cover-letter-templates", "methods": ["GET"]},
  {"path": "/cover-letter-templates", "methods": ["POST"]},
  {"path": "/cover-letter-templates/{template_id}", "methods": ["DELETE"]},
  {"path": "/cover-letter-templates/{template_id}", "methods": ["PUT"]},
  {"path": "/cover-letters/export/{cover_id}", "methods": ["GET"]},
  {"path": "/cover-letters/generate", "methods": ["POST"]},
  {"path": "/cover-letters/save", "methods": ["POST"]},
  {"path": "/cover-letters/{job_id}", "methods": ["GET"]},
  {"path": "/debug/env", "methods": ["GET"]},
  {"path": "/feedback/ai", "methods": ["POST"]},
  {"path": "/feedback/shortlist", "methods": ["POST"]},
  {"path": "/health", "methods": ["GET"]},
  {"path": "/import", "methods": ["POST"]},
  {"path": "/jobs", "methods": ["GET"]},
  {"path": "/jobs/{job_id}", "methods": ["GET"]},
  {"path": "/onboarding/bootstrap", "methods": ["POST"]},
  {"path": "/onboarding/config", "methods": ["GET"]},
  {"path": "/onboarding/config/preferences", "methods": ["PUT"]},
  {"path": "/onboarding/config/resume-profile", "methods": ["PUT"]},
  {"path": "/onboarding/config/searches", "methods": ["PUT"]},
  {"path": "/onboarding/config/shortlist-rules", "methods": ["PUT"]},
  {"path": "/onboarding/linkedin/init", "methods": ["POST"]},
  {"path": "/onboarding/linkedin/status", "methods": ["GET"]},
  {"path": "/onboarding/migrate", "methods": ["POST"]},
  {"path": "/onboarding/preflight", "methods": ["POST"]},
  {"path": "/onboarding/profile-draft", "methods": ["POST"]},
  {"path": "/onboarding/resume-parse", "methods": ["POST"]},
  {"path": "/onboarding/searches", "methods": ["GET"]},
  {"path": "/onboarding/searches", "methods": ["POST"]},
  {"path": "/onboarding/searches/{label}", "methods": ["DELETE"]},
  {"path": "/onboarding/searches/{label}", "methods": ["PUT"]},
  {"path": "/onboarding/status", "methods": ["GET"]},
  {"path": "/onboarding/validate/preferences", "methods": ["POST"]},
  {"path": "/onboarding/validate/resume-profile", "methods": ["POST"]},
  {"path": "/onboarding/validate/searches", "methods": ["POST"]},
  {"path": "/onboarding/validate/shortlist-rules", "methods": ["POST"]},
  {"path": "/ratings", "methods": ["POST"]},
  {"path": "/run/start", "methods": ["POST"]},
  {"path": "/run/{step}", "methods": ["POST"]},
  {"path": "/runs/state", "methods": ["GET"]},
  {"path": "/runs/stream", "methods": ["GET"]},
  {"path": "/searches", "methods": ["GET"]},
  {"path": "/settings", "methods": ["GET"]},
  {"path": "/settings", "methods": ["PUT"]},
  {"path": "/status", "methods": ["POST"]},
  {"path": "/suggestions/apply", "methods": ["POST"]},
  {"path": "/suggestions/generate", "methods": ["POST"]}
]
```

## 2) Representative Endpoint JSON Fixtures

Command used:

```powershell
@'
from fastapi.testclient import TestClient
from backend.app import app
import json

client = TestClient(app)
for ep in [
    "/health", "/debug/env", "/jobs", "/settings", "/searches",
    "/onboarding/status", "/onboarding/config", "/ai/pricing",
    "/cover-letter-templates", "/runs/state"
]:
    r = client.get(ep)
    print(ep, r.status_code)
    print(json.dumps(r.json(), indent=2)[:4000])
'@ | python -
```

Fixture snapshots (condensed):

```json
{
  "/health": {
    "status_code": 200,
    "body": {
      "ok": true,
      "app_file": "C:\\Users\\Michael\\Desktop\\Job Finder\\backend\\app.py"
    }
  },
  "/debug/env": {
    "status_code": 200,
    "body": {
      "app_file": "C:\\Users\\Michael\\Desktop\\Job Finder\\backend\\app.py",
      "base_dir": "C:\\Users\\Michael\\Desktop\\Job Finder",
      "cwd": "C:\\Users\\Michael\\Desktop\\Job Finder",
      "scripts": {
        "scout": "...\\job-scout.py",
        "shortlist": "...\\shortlist.py",
        "scrape": "...\\deep-scrape-full.py",
        "eval": "...\\ai-eval.py",
        "sort": "...\\sort-results.py"
      }
    }
  },
  "/jobs": {
    "status_code": 200,
    "body": {
      "count": 500,
      "first_item": {
        "id": 4165,
        "url": "https://www.linkedin.com/jobs/view/4371517348/",
        "title": "Customer Facing AI Business Analyst",
        "company": "Atigro",
        "workplace": "remote",
        "scraped_at": "2026-02-12T21:55:27.107171Z",
        "score": 90,
        "rating": null,
        "status": null
      }
    }
  },
  "/settings": {
    "status_code": 200,
    "body": {
      "top_level_keys": ["preferences", "rules"],
      "preferences_keys": [
        "employment", "hard_constraints", "industry_preferences", "output",
        "profile_version", "qualification", "ranking_weights", "red_flag_keywords",
        "role_preferences", "search_filters", "travel", "tuning", "workplace_preferences"
      ],
      "rules_keys": [
        "company_penalties", "hard_reject_patterns", "healthcare_penalty",
        "not_entry_level_patterns", "optional_reject_patterns", "recency_scoring",
        "sales_adjacent_penalty", "target_n", "title_boosts", "workplace_score",
        "wrong_field_penalty"
      ]
    }
  },
  "/searches": {
    "status_code": 200,
    "body": {
      "searches_count": 4,
      "first_search": {
        "label": "Chicago",
        "location_label": "Chicago, IL",
        "keywords": ""
      }
    }
  },
  "/onboarding/status": {
    "status_code": 200,
    "body": {
      "ready": true,
      "checks": "4 checks (all pass)",
      "validation": {
        "resume_profile": {"ok": true},
        "preferences": {"ok": true},
        "shortlist_rules": {"ok": true},
        "searches": {"ok": true},
        "ok": true
      }
    }
  },
  "/onboarding/config": {
    "status_code": 200,
    "body": {
      "top_level_keys": ["preferences", "resume_profile", "searches", "shortlist_rules"]
    }
  },
  "/ai/pricing": {
    "status_code": 200,
    "body": {
      "as_of": "2026-02-12",
      "currency": "USD",
      "unit": "per_1m_tokens",
      "models": ["gpt-5.1", "gpt-5-mini", "gpt-5", "gpt-4.1", "gpt-4.1-mini"]
    }
  },
  "/cover-letter-templates": {
    "status_code": 200,
    "body": {
      "items_count": 1,
      "first_item": {
        "id": "tmpl-default-1",
        "created_at": "2026-02-12T00:00:00Z"
      }
    }
  },
  "/runs/state": {
    "status_code": 200,
    "body": {
      "running": false,
      "step": null,
      "status": null,
      "lines": [],
      "progress": {"current": 0, "total": 0, "pct": 0.0, "label": ""}
    }
  }
}
```

## 3) UI Smoke Checklist (Baseline)

1. Onboarding tab
- `POST /onboarding/bootstrap`
- `GET /onboarding/status`
- `PUT /onboarding/config/*` save flows
- `POST /onboarding/preflight`
- `GET /onboarding/linkedin/status`
- `POST /onboarding/linkedin/init`

2. Jobs tab
- `GET /jobs` list/filter/search
- `GET /jobs/{job_id}` detail
- `POST /ratings` save
- `POST /status` save
- `POST /feedback/shortlist`
- `POST /feedback/ai`

3. Pipeline tab
- `POST /run/start`
- `POST /run/{step}`
- `GET /runs/stream` SSE logs
- `GET /runs/state` progress/status
- `POST /onboarding/preflight` gate before run

4. Cover Letters tab
- `GET/POST/PUT/DELETE /cover-letter-templates*`
- `POST /ai/estimate/cover-letter`
- `POST /cover-letters/generate`
- `POST /cover-letters/save`
- `GET /cover-letters/export/{cover_id}` for `txt/docx/pdf`

5. Settings tab
- `GET /settings`
- `PUT /settings`
- `GET /searches`
- `POST /import`
- `POST /suggestions/generate`
- `POST /suggestions/apply`

## 4) Pipeline Output Checksum Workflow (Fixed Sample Run)

Sample run identity to keep constant:
- Search label: `Chicago`
- Pipeline size: `small`
- Query: empty string
- Eval model: default (no override)

Execution workflow:

```powershell
# 1) Run fixed sample pipeline
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8001/run/start" -ContentType "application/json" -Body '{"search":"Chicago","size":"small"}'

# 2) Wait until /runs/state reports running=false and status in {"completed","error"}
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8001/runs/state"

# 3) Capture deterministic file hashes from artifacts/
Get-ChildItem artifacts -File | Sort-Object Name | ForEach-Object {
  $hash = Get-FileHash -Algorithm SHA256 $_.FullName
  "{0}  {1}" -f $hash.Hash.ToLower(), $_.Name
}
```

Current artifact hash snapshot (captured 2026-02-21):

```text
01fd64b0aabc74039d90b363a8cbed3aa2ecea7de29d1e5d76bc065873881dfb  ai_usage_totals.json
b5e928390f2deb26002a9221e829b17b86e907f8765c0ffed876dfda7d9a1027  ai_usage.jsonl
16a68917f8e758191d63cc5ed5cb4bbd6fe6dde4f2b55111c596f8d010e0759e  apply.csv
9607e6d457c087fad5e8add893a21864f0968195752c97c2e0eeb17300620a62  apply.json
ff3067e285e597f039ece89eb8ce221891e4c0f54919397319c6af21e1e6a853  jobfinder.db
787b8f4da8a16ec305b55b31a07cc7b87e1b2cacb1624829c8a4db4d694dee39  review.csv
4dfcba6cf41b9e8ca2d589764e38bf1138f42abd41689cee2d32c527b51e145f  review.json
ef9bfc54bc7d09f2399e39ab8e2f6179766f58ca4d04cf3d517e08b8ebb89aba  skip.csv
4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945  skip.json
76e24a5cf5d18b438a0bc782a1c03e225979b1629f9353c85ba34ff630e22fcc  tier2_full.json
eb07a23654b4d1c6572c194bdbb3796a47ae527fa93f986c2826489342a0da13  tier2_metadata.json
6baa4799f1f1e3b3040815ecd7dbf30851df761258bc29916091c12a63bef39e  tier2_scored.json
94fba5c2ffb5c92e8dd01f613956ed968f7c46ea6b1f7c3347932ff5880857ab  tier2_shortlist.csv
aa59fc71cf5706037b08572ff71eb0f53395763a8dda625a3e9d4a3d7321e98c  tier2_shortlist.json
f467af6667d599415bb059627aad1be56f8d5003fb7c52c987d7cb9ac00a2f3c  tmp_server_err.log
4d146c1514afdd6d0824cbf04a8f7f5ce7b98fe2da0f50f8067e11d7e0b997f2  tmp_server_out.log
ba1ee549cb8060aa39445df9568bc8650c65046d6d7b71509fe2cff0efb43d56  tmp_uvicorn_err.log
27fc66dac2854bd1c5c36d927dfc31fb243b554633f184a6db5c397a333c6417  tmp_uvicorn_out.log
8ea48b12361c7d7b66b270651ddd1be3549af32e6762ef115e22b594b7bf7541  tuning_log.jsonl
```

## 5) Stage 0 Gate Commands

Required gate commands for this stage:

```powershell
pytest -q backend/tests
python -m py_compile backend\app.py backend\db.py
```
