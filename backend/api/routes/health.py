from fastapi import APIRouter


router = APIRouter()


@router.get("/health")
def api_health():
    from backend import app as app_module

    return app_module.api_health()


@router.get("/debug/env")
def api_debug_env():
    from backend import app as app_module

    return app_module.api_debug_env()
