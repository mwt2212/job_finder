from fastapi import APIRouter

from backend.api import handlers
from backend.domain.models.dto import ImportIn


router = APIRouter()


@router.post("/import")
def api_import(payload: ImportIn):
    return handlers.api_import(payload)
