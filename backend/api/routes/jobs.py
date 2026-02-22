from fastapi import APIRouter

from backend.api import handlers
from backend.domain.models.dto import AiEvalFeedbackIn, RatingIn, ShortlistFeedbackIn, StatusIn


router = APIRouter()


@router.get("/jobs")
def api_list_jobs(
    search: str | None = None,
    workplace: str | None = None,
    status: str | None = None,
    rating: int | None = None,
    min_score: float | None = None,
    date_filter: str | None = None,
    source: str | None = None,
    require_description: bool | None = True,
):
    return handlers.api_list_jobs(
        search=search,
        workplace=workplace,
        status=status,
        rating=rating,
        min_score=min_score,
        date_filter=date_filter,
        source=source,
        require_description=require_description,
    )


@router.get("/jobs/{job_id}")
def api_get_job(job_id: int):
    return handlers.api_get_job(job_id)


@router.post("/ratings")
def api_rate_job(payload: RatingIn):
    return handlers.api_rate_job(payload)


@router.post("/status")
def api_status(payload: StatusIn):
    return handlers.api_status(payload)


@router.post("/feedback/shortlist")
def api_shortlist_feedback(payload: ShortlistFeedbackIn):
    return handlers.api_shortlist_feedback(payload)


@router.post("/feedback/ai")
def api_ai_feedback(payload: AiEvalFeedbackIn):
    return handlers.api_ai_feedback(payload)
