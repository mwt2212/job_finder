from fastapi import APIRouter

from backend.domain.models.compat import SuggestionsApplyIn


router = APIRouter()


@router.post("/suggestions/generate")
def api_generate_suggestions():
    from backend import app as app_module

    return app_module.api_generate_suggestions()


@router.post("/suggestions/apply")
def api_apply_suggestions(payload: SuggestionsApplyIn):
    from backend import app as app_module

    return app_module.api_apply_suggestions(payload)
