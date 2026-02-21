from typing import Any, Dict, List


def generate_suggestions_from_low_rated_rows(
    prefs: Dict[str, Any],
    rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    suggestions: List[Dict[str, Any]] = []
    healthcare_terms = ["health", "medical", "hospital", "clinic"]

    if rows:
        low_total = len(rows)
        health_hits = 0
        for row in rows:
            blob = " ".join([row.get("title") or "", row.get("company") or "", row.get("description") or ""]).lower()
            if any(term in blob for term in healthcare_terms):
                health_hits += 1

        if health_hits / low_total >= 0.2:
            existing = set((prefs.get("industry_preferences", {}) or {}).get("soft_penalize", []))
            if "healthcare" not in existing:
                suggestions.append(
                    {
                        "op": "add",
                        "path": "industry_preferences.soft_penalize",
                        "value": "healthcare",
                        "reason": "Many low-rated jobs appear healthcare-related; add soft penalty.",
                    }
                )
    return suggestions


def apply_operation(prefs: Dict[str, Any], op: Dict[str, Any]) -> None:
    path = op.get("path", "")
    value = op.get("value")
    if not path:
        return
    parts = path.split(".")
    cur = prefs
    for part in parts[:-1]:
        if part not in cur or not isinstance(cur[part], dict):
            cur[part] = {}
        cur = cur[part]

    key = parts[-1]
    if op.get("op") == "add":
        if key not in cur or not isinstance(cur[key], list):
            cur[key] = []
        if value not in cur[key]:
            cur[key].append(value)
    elif op.get("op") == "set":
        cur[key] = value
