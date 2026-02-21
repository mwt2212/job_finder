from fastapi import APIRouter

from backend.api.routes.ai_estimates import router as ai_estimates_router
from backend.api.routes.cover_letters import router as cover_letters_router
from backend.api.routes.health import router as health_router
from backend.api.routes.imports import router as imports_router
from backend.api.routes.jobs import router as jobs_router
from backend.api.routes.onboarding import router as onboarding_router
from backend.api.routes.runs import router as runs_router
from backend.api.routes.settings import router as settings_router
from backend.api.routes.suggestions import router as suggestions_router


api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(jobs_router)
api_router.include_router(settings_router)
api_router.include_router(onboarding_router)
api_router.include_router(ai_estimates_router)
api_router.include_router(cover_letters_router)
api_router.include_router(runs_router)
api_router.include_router(imports_router)
api_router.include_router(suggestions_router)
