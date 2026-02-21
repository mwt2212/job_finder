from fastapi import APIRouter

from backend.domain.models.compat import ImportIn


router = APIRouter()


@router.post("/import")
def api_import(payload: ImportIn):
    from backend import app as app_module

    return app_module.api_import(payload)
