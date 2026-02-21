from typing import Any, Dict

from fastapi import APIRouter


router = APIRouter()


@router.get("/settings")
def api_get_settings():
    from backend import app as app_module

    return app_module.api_get_settings()


@router.put("/settings")
def api_put_settings(payload: Dict[str, Any]):
    from backend import app as app_module

    return app_module.api_put_settings(payload)


@router.get("/searches")
def api_get_searches():
    from backend import app as app_module

    return app_module.api_get_searches()
