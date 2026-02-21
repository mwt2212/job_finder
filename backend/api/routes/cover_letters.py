from fastapi import APIRouter

from backend.domain.models.compat import CoverLetterGenerateIn, CoverLetterSaveIn, CoverLetterTemplateIn


router = APIRouter()


@router.get("/cover-letter-templates")
def api_cover_letter_templates():
    from backend import app as app_module

    return app_module.api_cover_letter_templates()


@router.post("/cover-letter-templates")
def api_cover_letter_template_create(payload: CoverLetterTemplateIn):
    from backend import app as app_module

    return app_module.api_cover_letter_template_create(payload)


@router.put("/cover-letter-templates/{template_id}")
def api_cover_letter_template_update(template_id: str, payload: CoverLetterTemplateIn):
    from backend import app as app_module

    return app_module.api_cover_letter_template_update(template_id, payload)


@router.delete("/cover-letter-templates/{template_id}")
def api_cover_letter_template_delete(template_id: str):
    from backend import app as app_module

    return app_module.api_cover_letter_template_delete(template_id)


@router.get("/cover-letters/{job_id}")
def api_cover_letters(job_id: int):
    from backend import app as app_module

    return app_module.api_cover_letters(job_id)


@router.post("/cover-letters/generate")
def api_cover_letter_generate(payload: CoverLetterGenerateIn):
    from backend import app as app_module

    return app_module.api_cover_letter_generate(payload)


@router.post("/cover-letters/save")
def api_cover_letter_save(payload: CoverLetterSaveIn):
    from backend import app as app_module

    return app_module.api_cover_letter_save(payload)


@router.get("/cover-letters/export/{cover_id}")
def api_cover_letter_export(cover_id: int, format: str = "txt"):
    from backend import app as app_module

    return app_module.api_cover_letter_export(cover_id, format)
