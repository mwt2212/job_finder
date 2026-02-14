import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"

OUTFILE = ARTIFACTS_DIR / "tier2_shortlist.json"
OUTCSV = ARTIFACTS_DIR / "tier2_shortlist.csv"
RULES_FILE = BASE_DIR / "shortlist_rules.json"
PREFS_FILE = BASE_DIR / "preferences.json"
RESUME_LOCAL_FILE = BASE_DIR / "resume_profile.local.json"
RESUME_FILE = BASE_DIR / "resume_profile.json"
RESUME_EXAMPLE_FILE = BASE_DIR / "resume_profile.example.json"

# -----------------------
# Helpers
# -----------------------

def load_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def artifact_input(name: str) -> Path:
    artifact = ARTIFACTS_DIR / name
    legacy = BASE_DIR / name
    return artifact if artifact.exists() else legacy


def resolve_resume_path() -> Path:
    if RESUME_LOCAL_FILE.exists():
        return RESUME_LOCAL_FILE
    if RESUME_FILE.exists():
        return RESUME_FILE
    return RESUME_EXAMPLE_FILE


def norm(s: str) -> str:
    return (s or "").strip()


def text_blob(job: dict) -> str:
    return f"{job.get('title','')} {job.get('company','')} {job.get('card_text','')}".lower()


def has_any(patterns, text):
    for pat in patterns:
        if re.search(pat, text, flags=re.I):
            return True, pat
    return False, ""


def score_posted(posted: str, recency_cfg: dict) -> int:
    p = (posted or "").lower()
    if not p:
        return 0
    if "just now" in p:
        return recency_cfg.get("just_now", 25)
    m = re.search(r"(\d+)\s*min", p)
    if m:
        mins = int(m.group(1))
        max_score = recency_cfg.get("minutes_max", 22)
        step = recency_cfg.get("minutes_step", 5)
        return max(max_score - mins // step, 5)
    h = re.search(r"(\d+)\s*hour", p)
    if h:
        hrs = int(h.group(1))
        start = recency_cfg.get("hours_start", 20)
        return max(start - hrs, 2)
    d = re.search(r"(\d+)\s*day", p)
    if d:
        days = int(d.group(1))
        start = recency_cfg.get("days_start", 8)
        return max(start - 2 * days, 0)
    if "repost" in p:
        return recency_cfg.get("repost_score", 4)
    return 0


def extract_years_required(text: str) -> int:
    years = [int(m.group(1)) for m in re.finditer(r"(\d+)\+?\s+years", text)]
    return max(years) if years else 0


def qualification_score(job: dict, resume: dict) -> float:
    text = text_blob(job)
    skills = [s.lower() for s in resume.get("skills", [])]
    if skills:
        matched = sum(1 for s in skills if s.lower() in text)
        skills_score = matched / len(skills)
    else:
        skills_score = 0.0

    degree = (resume.get("education", {}) or {}).get("degree", "").lower()
    degree_score = 1.0
    if any(x in text for x in ["master", "ms", "m.s.", "mba", "phd", "doctorate"]):
        degree_score = 0.2
    elif any(x in text for x in ["bachelor", "b.s", "bs", "ba"]):
        degree_score = 1.0 if degree else 0.3

    years = extract_years_required(text)
    if years == 0:
        years_score = 1.0
    elif years <= 2:
        years_score = 1.0
    elif years <= 4:
        years_score = 0.6
    elif years <= 6:
        years_score = 0.3
    else:
        years_score = 0.1

    base = 0.5 * skills_score + 0.3 * degree_score + 0.2 * years_score

    # If metadata-only, lean more on title match to target roles
    title = (job.get("title") or "").lower()
    target_roles = [r.lower() for r in resume.get("target_roles", [])]
    title_match = 1.0 if any(r in title for r in target_roles) else 0.0
    if len(text) < 250:
        base = max(base, 0.35 + 0.25 * title_match)

    return round(base, 3)


def employment_ok(text: str, prefs: dict) -> bool:
    if not prefs.get("employment", {}).get("hard_block_non_full_time", False):
        return True
    if any(term in text for term in ["part-time", "part time", "contract", "temporary", "intern", "internship"]):
        return False
    return True


def cold_call_ok(text: str, prefs: dict) -> bool:
    if prefs.get("hard_constraints", {}).get("no_cold_calling"):
        red_flags = prefs.get("red_flag_keywords", [])
        for kw in red_flags:
            if kw.lower() in text:
                return False
    return True


def sales_adjacent_penalty(text: str) -> bool:
    keywords = ["sales", "account executive", "business development", "client success", "customer success", "quota"]
    return any(k in text for k in keywords)


def healthcare_penalty(text: str) -> bool:
    keywords = ["health", "medical", "hospital", "clinic", "patient"]
    return any(k in text for k in keywords)


def to_csv(rows, path: Path):
    import csv
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["score","qualification_score","title","company","workplace","posted","url"])
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k,"") for k in w.fieldnames})


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-n", type=int, default=0, help="Override shortlist size")
    args = parser.parse_args()

    rules = load_json(RULES_FILE, {})
    prefs = load_json(PREFS_FILE, {})
    resume = load_json(resolve_resume_path(), {})

    infile = artifact_input("tier2_metadata.json")
    if not infile.exists():
        raise FileNotFoundError(f"Missing input file: {infile}")
    data = json.loads(infile.read_text(encoding="utf-8"))

    hard_reject = rules.get("hard_reject_patterns", [])
    not_entry = rules.get("not_entry_level_patterns", [])
    optional_reject = rules.get("optional_reject_patterns", [])
    title_boosts = rules.get("title_boosts", {})
    company_penalties = rules.get("company_penalties", {})
    workplace_score = rules.get("workplace_score", {})
    recency_cfg = rules.get("recency_scoring", {})

    sales_penalty = rules.get("sales_adjacent_penalty", -8)
    health_penalty = rules.get("healthcare_penalty", -10)
    wrong_field_penalty = rules.get("wrong_field_penalty", -6)

    min_match_score = (prefs.get("qualification", {}) or {}).get("min_match_score", 0.55)
    meta_min_match = max(0.25, float(min_match_score) - 0.35)
    safe_ratio = (prefs.get("qualification", {}) or {}).get("safe_vs_stretch_ratio", 0.7)
    target_n = (prefs.get("output", {}) or {}).get("shortlist_k", rules.get("target_n", 120))
    if args.target_n and args.target_n > 0:
        target_n = args.target_n

    scored = []

    for job in data:
        t = text_blob(job)

        if not employment_ok(t, prefs):
            continue
        if not cold_call_ok(t, prefs):
            continue

        hit, pat = has_any(hard_reject, t)
        if hit:
            continue
        hit, pat = has_any(not_entry, t)
        if hit:
            continue
        hit, pat = has_any(optional_reject, t)
        if hit:
            continue

        reasons = []
        score = 0

        wp = (job.get("workplace") or "").lower().strip()
        score += workplace_score.get(wp, workplace_score.get("unknown", 2))
        reasons.append(f"workplace:{wp or 'unknown'}")

        ps = score_posted(job.get("posted", ""), recency_cfg)
        score += ps
        if ps:
            reasons.append(f"posted:+{ps}")

        title = (job.get("title") or "").lower()
        for pat, w in title_boosts.items():
            if re.search(pat, title, flags=re.I):
                score += w
                reasons.append(f"title:{pat}+{w}")

        role_hints = [
            "analyst", "coordinator", "associate", "specialist",
            "operations", "project", "program", "compliance",
            "risk", "data", "finance", "financial"
        ]
        if not any(hint in title for hint in role_hints):
            score += wrong_field_penalty
            reasons.append(f"wrong_field:{wrong_field_penalty}")

        company = (job.get("company") or "").lower()
        for pat, w in company_penalties.items():
            if re.search(pat, company, flags=re.I):
                score += w
                reasons.append(f"company:{pat}{w}")

        if sales_adjacent_penalty(t) and prefs.get("role_preferences", {}).get("soft_penalize_sales_adjacent", True):
            score += sales_penalty
            reasons.append(f"sales_adjacent:{sales_penalty}")

        if healthcare_penalty(t) and "healthcare" in (prefs.get("industry_preferences", {}).get("soft_penalize", [])):
            score += health_penalty
            reasons.append(f"healthcare:{health_penalty}")

        if "entry level" in t or "new grad" in t or "recent graduate" in t:
            score += 8
            reasons.append("entry:+8")

        q_score = qualification_score(job, resume)
        if len(t) < 250:
            if q_score < meta_min_match:
                continue
        else:
            if q_score < min_match_score:
                continue

        scored.append({
            "score": score,
            "qualification_score": q_score,
            "url": job.get("url", ""),
            "title": norm(job.get("title", "")),
            "company": norm(job.get("company", "")),
            "workplace": norm(job.get("workplace", "")),
            "posted": norm(job.get("posted", "")),
            "reasons": reasons,
        })

    scored.sort(key=lambda x: (x["score"], x["qualification_score"]), reverse=True)

    safe = [s for s in scored if s["qualification_score"] >= 0.65]
    stretch = [s for s in scored if 0.45 <= s["qualification_score"] < 0.65]

    safe_count = int(round(target_n * safe_ratio))
    shortlist = safe[:safe_count]
    remaining = target_n - len(shortlist)
    shortlist.extend(stretch[:max(0, remaining)])

    if len(shortlist) < target_n:
        remaining = target_n - len(shortlist)
        shortlist.extend(scored[len(shortlist):len(shortlist) + remaining])

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTFILE.write_text(json.dumps(shortlist, ensure_ascii=False, indent=2), encoding="utf-8")
    to_csv(shortlist, OUTCSV)

    print(f"Input jobs: {len(data)}")
    print(f"Scored (kept): {len(scored)}")
    print(f"Shortlist saved: {len(shortlist)} -> {OUTFILE} and {OUTCSV}")
    if shortlist:
        print("\nTop 5:")
        for r in shortlist[:5]:
            print(f"{r['score']:>3} | {r['workplace']:<6} | {r['posted']:<12} | {r['title'][:60]} @ {r['company'][:40]}")


if __name__ == "__main__":
    main()
