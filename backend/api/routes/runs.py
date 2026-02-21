from typing import Optional

from fastapi import APIRouter

from backend.domain.models.compat import StartIn


router = APIRouter()


@router.post("/run/start")
def api_run_start(payload: StartIn):
    from backend import app as app_module

    return app_module.api_run_start(payload)


@router.post("/run/{step}")
def api_run_step(step: str, search: Optional[str] = None, query: Optional[str] = None, model: Optional[str] = None):
    from backend import app as app_module

    return app_module.api_run_step(step, search, query, model)


@router.get("/runs/stream")
def api_stream_runs():
    from backend import app as app_module

    return app_module.api_stream_runs()


@router.get("/runs/state")
def api_run_state():
    from backend import app as app_module

    return app_module.api_run_state()
