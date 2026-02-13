from typing import List


DESCRIPTION_TRUNCATE_MARKERS = [
    "set alert for similar jobs",
    "see more jobs like this",
    "job search smarter with premium",
    "looking for talent?",
    "linkedin corporation",
    "about the company",
    "select language",
]

NOISE_LINE_MARKERS = [
    "show more",
    "show less",
    "sign in to view more",
    "join now",
]


def clean_job_description(text: str, max_len: int = 8000) -> str:
    if not text:
        return ""

    lines = (text or "").splitlines()
    kept: List[str] = []
    last_blank = False
    for line in lines:
        raw = line.rstrip()
        low = raw.strip().lower()
        if any(marker in low for marker in DESCRIPTION_TRUNCATE_MARKERS):
            break
        if any(noise == low for noise in NOISE_LINE_MARKERS):
            continue
        if not raw.strip():
            if not last_blank:
                kept.append("")
            last_blank = True
            continue
        kept.append(raw)
        last_blank = False

    cleaned = "\n".join(kept).strip()
    return cleaned[:max_len]
