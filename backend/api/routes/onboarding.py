from typing import Any, Dict

from fastapi import APIRouter, File, UploadFile

from backend.api import handlers
from backend.domain.models.dto import (
    OnboardingProfileDraftIn,
    OnboardingSearchIn,
    OnboardingSearchUpdateIn,
)


router = APIRouter()


@router.get("/onboarding/config")
def api_onboarding_get_config():
    return handlers.api_onboarding_get_config()


@router.put("/onboarding/config/resume-profile")
def api_onboarding_put_resume_profile(payload: Dict[str, Any]):
    return handlers.api_onboarding_put_resume_profile(payload)


@router.put("/onboarding/config/preferences")
def api_onboarding_put_preferences(payload: Dict[str, Any]):
    return handlers.api_onboarding_put_preferences(payload)


@router.put("/onboarding/config/shortlist-rules")
def api_onboarding_put_shortlist_rules(payload: Dict[str, Any]):
    return handlers.api_onboarding_put_shortlist_rules(payload)


@router.put("/onboarding/config/searches")
def api_onboarding_put_searches(payload: Any):
    return handlers.api_onboarding_put_searches(payload)


@router.post("/onboarding/profile-draft")
def api_onboarding_profile_draft(payload: OnboardingProfileDraftIn):
    return handlers.api_onboarding_profile_draft(payload)


@router.post("/onboarding/resume-parse")
async def api_onboarding_resume_parse(file: UploadFile = File(...)):
    return await handlers.api_onboarding_resume_parse(file)


@router.get("/onboarding/searches")
def api_onboarding_get_searches():
    return handlers.api_onboarding_get_searches()


@router.post("/onboarding/searches")
def api_onboarding_create_search(payload: OnboardingSearchIn):
    return handlers.api_onboarding_create_search(payload)


@router.put("/onboarding/searches/{label}")
def api_onboarding_update_search(label: str, payload: OnboardingSearchUpdateIn):
    return handlers.api_onboarding_update_search(label, payload)


@router.delete("/onboarding/searches/{label}")
def api_onboarding_delete_search(label: str):
    return handlers.api_onboarding_delete_search(label)


@router.get("/onboarding/linkedin/status")
def api_onboarding_linkedin_status():
    return handlers.api_onboarding_linkedin_status()


@router.post("/onboarding/linkedin/init")
def api_onboarding_linkedin_init():
    return handlers.api_onboarding_linkedin_init()


@router.post("/onboarding/bootstrap")
def api_onboarding_bootstrap():
    return handlers.api_onboarding_bootstrap()


@router.get("/onboarding/status")
def api_onboarding_status():
    return handlers.api_onboarding_status()


@router.post("/onboarding/validate/resume-profile")
def api_onboarding_validate_resume_profile(payload: Dict[str, Any]):
    return handlers.api_onboarding_validate_resume_profile(payload)


@router.post("/onboarding/validate/preferences")
def api_onboarding_validate_preferences(payload: Dict[str, Any]):
    return handlers.api_onboarding_validate_preferences(payload)


@router.post("/onboarding/validate/shortlist-rules")
def api_onboarding_validate_shortlist_rules(payload: Dict[str, Any]):
    return handlers.api_onboarding_validate_shortlist_rules(payload)


@router.post("/onboarding/validate/searches")
def api_onboarding_validate_searches(payload: Any):
    return handlers.api_onboarding_validate_searches(payload)


@router.post("/onboarding/preflight")
def api_onboarding_preflight():
    return handlers.api_onboarding_preflight()


@router.post("/onboarding/migrate")
def api_onboarding_migrate():
    return handlers.api_onboarding_migrate()
