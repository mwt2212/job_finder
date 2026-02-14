import copy
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.onboarding_schema import CURRENT_SCHEMA_VERSION, DEFAULT_PREFERENCES, DEFAULT_SHORTLIST_RULES


def _now_ts() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _backup_file(path: Path) -> Optional[Path]:
    if not path.exists():
        return None
    backup = path.with_name(f"{path.name}.bak.{_now_ts()}")
    shutil.copy2(path, backup)
    return backup


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _save_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _schema_version(data: Dict[str, Any]) -> str:
    value = str(data.get("schema_version") or "").strip()
    return value if value else "v1"


def _ensure_schema_version(data: Dict[str, Any], changes: List[str]) -> None:
    if str(data.get("schema_version") or "").strip() != CURRENT_SCHEMA_VERSION:
        data["schema_version"] = CURRENT_SCHEMA_VERSION
        changes.append(f"set schema_version={CURRENT_SCHEMA_VERSION}")


def migrate_resume_profile(data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    migrated = copy.deepcopy(_as_dict(data))
    changes: List[str] = []
    _ensure_schema_version(migrated, changes)
    return migrated, changes


def migrate_preferences(data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    migrated = copy.deepcopy(_as_dict(data))
    changes: List[str] = []

    _ensure_schema_version(migrated, changes)

    if not isinstance(migrated.get("qualification"), dict):
        migrated["qualification"] = copy.deepcopy(DEFAULT_PREFERENCES["qualification"])
        changes.append("created qualification defaults")
    elif migrated["qualification"].get("min_match_score") is None:
        migrated["qualification"]["min_match_score"] = DEFAULT_PREFERENCES["qualification"]["min_match_score"]
        changes.append("set qualification.min_match_score default")

    if not isinstance(migrated.get("hard_constraints"), dict):
        migrated["hard_constraints"] = copy.deepcopy(DEFAULT_PREFERENCES["hard_constraints"])
        changes.append("created hard_constraints defaults")
    elif "min_base_salary_usd" not in migrated["hard_constraints"]:
        migrated["hard_constraints"]["min_base_salary_usd"] = DEFAULT_PREFERENCES["hard_constraints"]["min_base_salary_usd"]
        changes.append("set hard_constraints.min_base_salary_usd default")

    return migrated, changes


def migrate_shortlist_rules(data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    migrated = copy.deepcopy(_as_dict(data))
    changes: List[str] = []

    _ensure_schema_version(migrated, changes)

    workplace = migrated.get("workplace_score")
    if not isinstance(workplace, dict):
        migrated["workplace_score"] = copy.deepcopy(DEFAULT_SHORTLIST_RULES["workplace_score"])
        changes.append("created workplace_score defaults")
    else:
        for key, default_val in DEFAULT_SHORTLIST_RULES["workplace_score"].items():
            if key not in workplace:
                workplace[key] = default_val
                changes.append(f"set workplace_score.{key} default")

    for key in ("sales_adjacent_penalty", "healthcare_penalty", "wrong_field_penalty"):
        if key not in migrated:
            migrated[key] = DEFAULT_SHORTLIST_RULES[key]
            changes.append(f"set {key} default")

    return migrated, changes


def migrate_searches(data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    raw = _as_dict(data)
    migrated: Dict[str, Any] = {}
    changes: List[str] = []

    for label, cfg in raw.items():
        if not isinstance(cfg, dict):
            continue
        entry = copy.deepcopy(cfg)
        if str(entry.get("schema_version") or "").strip() != CURRENT_SCHEMA_VERSION:
            entry["schema_version"] = CURRENT_SCHEMA_VERSION
            changes.append(f"set searches['{label}'].schema_version={CURRENT_SCHEMA_VERSION}")
        migrated[label] = entry

    return migrated, changes


def migrate_config_file(config_id: str, path: Path, data: Dict[str, Any]) -> Dict[str, Any]:
    if config_id == "resume_profile":
        migrated, changes = migrate_resume_profile(data)
    elif config_id == "preferences":
        migrated, changes = migrate_preferences(data)
    elif config_id == "shortlist_rules":
        migrated, changes = migrate_shortlist_rules(data)
    elif config_id == "searches":
        migrated, changes = migrate_searches(data)
    else:
        return {"id": config_id, "path": str(path), "status": "skipped", "reason": "unknown config id"}

    from_version = _schema_version(data)
    to_version = _schema_version(migrated)
    changed = changes or (from_version != to_version)

    if not changed:
        return {
            "id": config_id,
            "path": str(path),
            "status": "noop",
            "from_version": from_version,
            "to_version": to_version,
            "changes": [],
        }

    backup = _backup_file(path)
    _save_json(path, migrated)
    return {
        "id": config_id,
        "path": str(path),
        "status": "migrated",
        "from_version": from_version,
        "to_version": to_version,
        "backup_path": str(backup) if backup else "",
        "changes": changes,
    }

