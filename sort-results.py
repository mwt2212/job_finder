import json
import csv
from pathlib import Path

BASE_DIR = Path(__file__).parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"
PREFS = BASE_DIR / "preferences.json"

OUT_APPLY_JSON  = ARTIFACTS_DIR / "apply.json"
OUT_REVIEW_JSON = ARTIFACTS_DIR / "review.json"
OUT_SKIP_JSON   = ARTIFACTS_DIR / "skip.json"

OUT_APPLY_CSV  = ARTIFACTS_DIR / "apply.csv"
OUT_REVIEW_CSV = ARTIFACTS_DIR / "review.csv"
OUT_SKIP_CSV   = ARTIFACTS_DIR / "skip.csv"


def artifact_input(name: str) -> Path:
    artifact = ARTIFACTS_DIR / name
    legacy = BASE_DIR / name
    return artifact if artifact.exists() else legacy

def load_thresholds():
    if PREFS.exists():
        prefs = json.loads(PREFS.read_text(encoding="utf-8"))
        tuning = prefs.get("tuning", {}) or {}
        thresholds = tuning.get("sort_thresholds", {}) or {}
        apply_min = int(thresholds.get("apply_min_score", 75))
        review_min = int(thresholds.get("review_min_score", 55))
        return apply_min, review_min
    return 75, 55

def categorize(item):
    apply_min, review_min = load_thresholds()
    ev = item.get("ai_eval", {}) or {}
    score = int(ev.get("fit_score", 0) or 0)
    action = (ev.get("next_action") or "").lower()

    # Respect model action first
    if action == "apply":
        return "apply"
    if action == "skip":
        return "skip"

    # Otherwise use thresholds
    if score >= apply_min:
        return "apply"
    if score >= review_min:
        return "review"
    return "skip"

def row(item):
    ev = item.get("ai_eval", {}) or {}
    return {
        "score": ev.get("fit_score", ""),
        "next_action": ev.get("next_action", ""),
        "qualified": ev.get("qualified", ""),
        "cold_call_risk": ev.get("cold_call_risk", ""),
        "workplace_match": ev.get("workplace_match", ""),
        "mobility_signal": ev.get("mobility_signal", ""),
        "salary_verdict": ev.get("salary_verdict", ""),
        "title": item.get("title", ""),
        "company": item.get("company", ""),
        "workplace": item.get("workplace", ""),
        "posted": item.get("posted", ""),
        "url": item.get("url", ""),
        "top_reasons": " | ".join((ev.get("top_reasons") or [])[:6]),
        "red_flags": " | ".join((ev.get("red_flags") or [])[:6]),
    }

def save_json(path, items):
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

def save_csv(path, items):
    fields = [
        "score","next_action","qualified","cold_call_risk","workplace_match",
        "mobility_signal","salary_verdict","title","company","workplace","posted",
        "url","top_reasons","red_flags"
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for it in items:
            w.writerow(row(it))

def main():
    infile = artifact_input("tier2_scored.json")
    if not infile.exists():
        raise FileNotFoundError(f"Missing input file: {infile}")
    data = json.loads(infile.read_text(encoding="utf-8"))
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--final-top", type=int, default=0, help="Limit to top N across apply/review")
    args = parser.parse_args()

    apply_list, review_list, skip_list = [], [], []

    for item in data:
        bucket = categorize(item)
        if bucket == "apply":
            apply_list.append(item)
        elif bucket == "review":
            review_list.append(item)
        else:
            skip_list.append(item)

    # sort by score desc
    def score(it):
        return int((it.get("ai_eval", {}) or {}).get("fit_score", 0) or 0)

    apply_list.sort(key=score, reverse=True)
    review_list.sort(key=score, reverse=True)
    skip_list.sort(key=score, reverse=True)

    if args.final_top and args.final_top > 0:
        combined = apply_list + review_list
        combined.sort(key=score, reverse=True)
        keep = combined[: args.final_top]
        keep_urls = {x.get("url", "") for x in keep}
        apply_list = [x for x in apply_list if x.get("url", "") in keep_urls]
        review_list = [x for x in review_list if x.get("url", "") in keep_urls]
        moved = [x for x in combined if x.get("url", "") not in keep_urls]
        skip_list = moved + skip_list

    save_json(OUT_APPLY_JSON, apply_list)
    save_json(OUT_REVIEW_JSON, review_list)
    save_json(OUT_SKIP_JSON, skip_list)

    save_csv(OUT_APPLY_CSV, apply_list)
    save_csv(OUT_REVIEW_CSV, review_list)
    save_csv(OUT_SKIP_CSV, skip_list)

    print(f"Apply:  {len(apply_list)} -> {OUT_APPLY_CSV.name}")
    print(f"Review: {len(review_list)} -> {OUT_REVIEW_CSV.name}")
    print(f"Skip:   {len(skip_list)} -> {OUT_SKIP_CSV.name}")

if __name__ == "__main__":
    main()
