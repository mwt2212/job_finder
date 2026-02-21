from typing import Any, Dict

from backend.onboarding_validate import validate_all


def onboarding_validation_snapshot(
    resume_data: Dict[str, Any],
    preferences_data: Dict[str, Any],
    rules_data: Dict[str, Any],
    searches_data: Dict[str, Any],
) -> Dict[str, Any]:
    return validate_all(resume_data, preferences_data, rules_data, searches_data)
