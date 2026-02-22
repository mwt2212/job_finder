from typing import Any, Dict

from fastapi import APIRouter

from backend.api import handlers


router = APIRouter()


@router.get("/settings")
def api_get_settings():
    return handlers.api_get_settings()


@router.put("/settings")
def api_put_settings(payload: Dict[str, Any]):
    return handlers.api_put_settings(payload)


@router.get("/searches")
def api_get_searches():
    return handlers.api_get_searches()
