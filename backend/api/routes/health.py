from fastapi import APIRouter

from backend.api import handlers


router = APIRouter()


@router.get("/health")
def api_health():
    return handlers.api_health()


@router.get("/debug/env")
def api_debug_env():
    return handlers.api_debug_env()
