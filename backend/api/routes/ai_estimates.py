from typing import Optional

from fastapi import APIRouter

from backend.domain.models.compat import AiEstimatePipelineIn, CoverLetterGenerateIn


router = APIRouter()


@router.get("/ai/pricing")
def api_ai_pricing():
    from backend import app as app_module

    return app_module.api_ai_pricing()


@router.post("/ai/estimate/cover-letter")
def api_ai_estimate_cover_letter(payload: CoverLetterGenerateIn):
    from backend import app as app_module

    return app_module.api_ai_estimate_cover_letter(payload)


@router.post("/ai/estimate/pipeline")
def api_ai_estimate_pipeline(payload: AiEstimatePipelineIn):
    from backend import app as app_module

    return app_module.api_ai_estimate_pipeline(payload)


@router.post("/ai/estimate/eval")
def api_ai_estimate_eval(payload: Optional[AiEstimatePipelineIn] = None):
    from backend import app as app_module

    return app_module.api_ai_estimate_eval(payload)
