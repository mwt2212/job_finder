from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class RatingIn(BaseModel):
    job_id: int
    stars: int
    notes: Optional[str] = ""
    tags: List[str] = []


class StatusIn(BaseModel):
    job_id: int
    status: str


class SuggestionsApplyIn(BaseModel):
    operations: List[Dict[str, Any]]


class ImportIn(BaseModel):
    sources: Optional[List[str]] = None


class StartIn(BaseModel):
    search: str
    size: str
    query: Optional[str] = ""
    eval_model: Optional[str] = None


class ShortlistFeedbackIn(BaseModel):
    job_id: int
    verdict: str  # keep/remove
    reason: Optional[str] = ""


class AiEvalFeedbackIn(BaseModel):
    job_id: int
    correct_bucket: str  # apply/review/skip
    reasoning_quality: int  # 1-5


class CoverLetterGenerateIn(BaseModel):
    job_id: int
    feedback: Optional[str] = ""
    model: Optional[str] = None
    template_id: Optional[str] = None
    draft: Optional[str] = None
    locked_indices: Optional[List[int]] = None


class CoverLetterSaveIn(BaseModel):
    id: int
    content: str
    feedback: Optional[str] = ""


class CoverLetterTemplateIn(BaseModel):
    text: str


class AiEstimatePipelineIn(BaseModel):
    size: str
    model: Optional[str] = None


class OnboardingSearchIn(BaseModel):
    label: str
    location_label: str
    keywords: Optional[str] = ""
    url: Optional[str] = ""


class OnboardingSearchUpdateIn(BaseModel):
    location_label: Optional[str] = None
    keywords: Optional[str] = None
    url: Optional[str] = None
    label: Optional[str] = None


class OnboardingProfileDraftIn(BaseModel):
    text: str
