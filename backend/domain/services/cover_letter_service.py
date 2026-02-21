import json
import re
from datetime import datetime
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

from ai_usage import (
    estimate_cost,
    estimate_cost_range,
    estimate_tokens,
    get_avg_output_tokens,
    load_pricing,
)


DATE_RE = re.compile(
    r"^(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}$",
    re.IGNORECASE,
)
GREETING_RE = re.compile(r"^dear\b", re.IGNORECASE)
SIGNATURE_RE = re.compile(r"^(sincerely|best|regards|respectfully|yours)\b", re.IGNORECASE)


def cover_letter_prompt(job: Dict[str, Any], resume: Dict[str, Any], feedback: str) -> str:
    feedback_line = f"\nFeedback from candidate to adjust tone/content:\n{feedback}\n" if feedback else ""
    return f"""
Write a short, 3-paragraph cover letter tailored to this role.

Constraints:
- Keep it concise (3 short paragraphs).
- Highlight transferable skills, avoid sales-heavy emphasis.
- Only emphasize experience/skills that are reasonably applicable to this role; do not stretch.
- If there are gaps, briefly soften them with a positive, forward-looking sentence (without exaggeration).
- Keep the tone human and natural; no filler or generic fluff.
- The candidate has already graduated (August 2025). Do not say "graduating" or imply they are still in school.
- Be less verbose and avoid em dashes entirely.
- Use a predictable 3-paragraph structure:
  1) Opening: role interest + quick fit hook.
  2) Middle: 2-3 concrete, relevant strengths tied to the job.
  3) Closing: gratitude + interest in next steps.
- Always include a brief thank-you in the closing.

Candidate profile:
{json.dumps(resume, ensure_ascii=False)}

Job:
Title: {job.get('title','')}
Company: {job.get('company','')}
Location: {job.get('location','')}
Workplace: {job.get('workplace','')}
Description:
{job.get('description','') or job.get('raw_card_text','')}
{feedback_line}
Return only the cover letter text.
""".strip()


def _current_date_str() -> str:
    now = datetime.now(ZoneInfo("America/Chicago"))
    return f"{now.strftime('%B')} {now.day}, {now.year}"


def split_blocks(text: str) -> List[str]:
    if not text:
        return []
    blocks = re.split(r"\n\s*\n+", text)
    return [b.strip() for b in blocks if b.strip()]


def split_cover_sections(text: str) -> Dict[str, Any]:
    blocks = split_blocks(text)
    greeting_idx = None
    signature_idx = None
    for i, block in enumerate(blocks):
        first_line = (block.splitlines()[0] if block.splitlines() else "").strip()
        if greeting_idx is None and GREETING_RE.match(first_line or ""):
            greeting_idx = i
        if signature_idx is None and SIGNATURE_RE.match(first_line or ""):
            signature_idx = i

    if greeting_idx is not None and signature_idx is not None and signature_idx < greeting_idx:
        signature_idx = None

    header = blocks[:greeting_idx] if greeting_idx is not None else []
    greeting = blocks[greeting_idx] if greeting_idx is not None else ""
    body_start = greeting_idx + 1 if greeting_idx is not None else 0
    body_end = signature_idx if signature_idx is not None else len(blocks)
    body = blocks[body_start:body_end]
    signature = blocks[signature_idx:] if signature_idx is not None else []
    return {"header": header, "greeting": greeting, "body": body, "signature": signature}


def _apply_date_and_company_to_header(
    blocks: List[str],
    ensure_date: bool,
    company: str,
) -> List[str]:
    if not blocks and not ensure_date:
        return []
    updated: List[str] = []
    replaced_date = False
    for block in blocks:
        lines = block.splitlines()
        new_lines = []
        for line in lines:
            stripped = line.strip()
            if DATE_RE.match(stripped):
                new_lines.append(_current_date_str())
                replaced_date = True
            elif company and stripped.lower() == "ruan":
                new_lines.append(company)
            else:
                new_lines.append(line)
        updated_block = "\n".join(new_lines).strip()
        if updated_block:
            updated.append(updated_block)
    if ensure_date and not replaced_date:
        updated = [_current_date_str(), *updated] if updated else [_current_date_str()]
    return updated


def assemble_cover_letter(
    sections: Dict[str, Any],
    body_paragraphs: List[str],
    ensure_date: bool,
    company: str,
) -> str:
    header = _apply_date_and_company_to_header(sections.get("header", []), ensure_date, company)
    greeting = sections.get("greeting") or ""
    signature = sections.get("signature") or []

    parts: List[str] = []
    parts.extend([h for h in header if h.strip()])
    if greeting.strip():
        parts.append("")
        parts.append(greeting.strip())
    indented_body = []
    for p in body_paragraphs:
        text = str(p).strip()
        if text:
            indented_body.append("    " + text)
    parts.extend(indented_body)
    if signature:
        parts.append("")
        parts.extend([s for s in signature if str(s).strip()])
    return "\n\n".join(parts).strip()


def parse_model_paragraphs(text: str) -> List[str]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()
    try:
        data = json.loads(cleaned)
        paragraphs = data.get("paragraphs")
        if isinstance(paragraphs, list):
            return [str(p).strip() for p in paragraphs if str(p).strip()]
    except Exception:
        pass
    return split_blocks(text)


def cover_letter_prompt_locked(
    job: Dict[str, Any],
    resume: Dict[str, Any],
    feedback: str,
    body_seeds: List[str],
    locked_map: Dict[int, str],
) -> str:
    feedback_line = f"\nFeedback from candidate to adjust tone/content:\n{feedback}\n" if feedback else ""
    locked_indices = sorted(locked_map.keys())
    title = job.get("title", "") or ""
    short_title = re.split(r"\s*[,/|–-]\s*", title)[0] if title else ""
    return f"""
Write the body of a cover letter with exactly {len(body_seeds)} paragraphs.

Locked paragraph indices (0-based): {json.dumps(locked_indices)}.
Seed paragraphs (0-based array): {json.dumps(body_seeds, ensure_ascii=False)}.
Locked paragraph text (index -> paragraph): {json.dumps(locked_map, ensure_ascii=False)}.

Rules:
- Return JSON only: {{"paragraphs": ["p1", "p2", "..."]}}
- The array length MUST be exactly {len(body_seeds)}.
- Locked paragraphs must be copied verbatim with identical wording and punctuation.
- Unlocked paragraphs should be rewritten from their seed text while improving flow and relevance.
- Use locked paragraphs as context to keep cohesion and avoid contradictions.
- No bullets; plain paragraphs only.
- Keep it concise, human, and professional. No fluff.
- Avoid em dashes entirely.
- The candidate has already graduated (August 2025). Do not imply they are still in school.
- Structure: Opening (interest + fit), Body (concrete strengths), Closing (gratitude + next steps + brief thank-you).
- Prefer a concise role title; if the job title is long or has commas/slashes, use a shortened form.

Candidate profile:
{json.dumps(resume, ensure_ascii=False)}

Job:
Title: {title}
Short title (if needed): {short_title}
Company: {job.get('company','')}
Location: {job.get('location','')}
Workplace: {job.get('workplace','')}
Description:
{job.get('description','') or job.get('raw_card_text','')}
{feedback_line}
""".strip()


def estimate_cover_letter(
    job: Dict[str, Any],
    resume: Dict[str, Any],
    feedback: str,
    model: str,
    body_seeds: List[str],
    locked_indices: List[int],
) -> Dict[str, Any]:
    dedup_locked = sorted(set(locked_indices or []))
    dedup_locked = [i for i in dedup_locked if 0 <= i < len(body_seeds)]
    locked_map = {i: body_seeds[i] for i in dedup_locked}
    prompt = cover_letter_prompt_locked(job, resume, feedback or "", body_seeds, locked_map)
    input_tokens_est = estimate_tokens(prompt)
    output_tokens_est = get_avg_output_tokens("cover_letter", model, default=350)

    pricing = load_pricing()
    cost_est = estimate_cost(pricing, model, input_tokens_est, output_tokens_est) if pricing else None
    cost_range = estimate_cost_range(pricing, model, input_tokens_est, output_tokens_est) if pricing else {"low": None, "high": None}
    return {
        "model": model,
        "input_tokens_est": input_tokens_est,
        "output_tokens_est": output_tokens_est,
        "cost_est": cost_est,
        "cost_est_range": cost_range,
    }
