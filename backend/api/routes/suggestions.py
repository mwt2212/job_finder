from fastapi import APIRouter

from backend.api import handlers
from backend.domain.models.dto import SuggestionsApplyIn


router = APIRouter()


@router.post("/suggestions/generate")
def api_generate_suggestions():
    return handlers.api_generate_suggestions()


@router.post("/suggestions/apply")
def api_apply_suggestions(payload: SuggestionsApplyIn):
    return handlers.api_apply_suggestions(payload)
