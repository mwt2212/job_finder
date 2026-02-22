from fastapi import APIRouter

from backend.api import handlers
from backend.domain.models.dto import CoverLetterGenerateIn, CoverLetterSaveIn, CoverLetterTemplateIn


router = APIRouter()


@router.get("/cover-letter-templates")
def api_cover_letter_templates():
    return handlers.api_cover_letter_templates()


@router.post("/cover-letter-templates")
def api_cover_letter_template_create(payload: CoverLetterTemplateIn):
    return handlers.api_cover_letter_template_create(payload)


@router.put("/cover-letter-templates/{template_id}")
def api_cover_letter_template_update(template_id: str, payload: CoverLetterTemplateIn):
    return handlers.api_cover_letter_template_update(template_id, payload)


@router.delete("/cover-letter-templates/{template_id}")
def api_cover_letter_template_delete(template_id: str):
    return handlers.api_cover_letter_template_delete(template_id)


@router.get("/cover-letters/{job_id}")
def api_cover_letters(job_id: int):
    return handlers.api_cover_letters(job_id)


@router.post("/cover-letters/generate")
def api_cover_letter_generate(payload: CoverLetterGenerateIn):
    return handlers.api_cover_letter_generate(payload)


@router.post("/cover-letters/save")
def api_cover_letter_save(payload: CoverLetterSaveIn):
    return handlers.api_cover_letter_save(payload)


@router.get("/cover-letters/export/{cover_id}")
def api_cover_letter_export(cover_id: int, format: str = "txt"):
    return handlers.api_cover_letter_export(cover_id, format)
