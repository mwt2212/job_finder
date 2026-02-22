from typing import Optional

from fastapi import APIRouter

from backend.api import handlers
from backend.domain.models.dto import StartIn


router = APIRouter()


@router.post("/run/start")
def api_run_start(payload: StartIn):
    return handlers.api_run_start(payload)


@router.post("/run/{step}")
def api_run_step(step: str, search: Optional[str] = None, query: Optional[str] = None, model: Optional[str] = None):
    return handlers.api_run_step(step, search, query, model)


@router.get("/runs/stream")
def api_stream_runs():
    return handlers.api_stream_runs()


@router.get("/runs/state")
def api_run_state():
    return handlers.api_run_state()
