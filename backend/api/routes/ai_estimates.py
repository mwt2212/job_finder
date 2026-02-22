from typing import Optional

from fastapi import APIRouter

from backend.api import handlers
from backend.domain.models.dto import AiEstimatePipelineIn, CoverLetterGenerateIn


router = APIRouter()


@router.get("/ai/pricing")
def api_ai_pricing():
    return handlers.api_ai_pricing()


@router.post("/ai/estimate/cover-letter")
def api_ai_estimate_cover_letter(payload: CoverLetterGenerateIn):
    return handlers.api_ai_estimate_cover_letter(payload)


@router.post("/ai/estimate/pipeline")
def api_ai_estimate_pipeline(payload: AiEstimatePipelineIn):
    return handlers.api_ai_estimate_pipeline(payload)


@router.post("/ai/estimate/eval")
def api_ai_estimate_eval(payload: Optional[AiEstimatePipelineIn] = None):
    return handlers.api_ai_estimate_eval(payload)
