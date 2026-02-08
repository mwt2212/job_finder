import json
import time
import random
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

# ================== PATHS (FIXED) ==================
BASE_DIR = Path(__file__).parent

SHORTLIST = BASE_DIR / "tier2_shortlist.json"
OUTFILE = BASE_DIR / "tier2_full.json"

CHROME_PROFILE_PATH = r"C:\Users\Michael\Desktop\Job Finder\chrome-profile"

# ================== VIEWPORT ==================
VIEWPORT = {"width": 1280, "height": 1440}

# ================== TIMING ==================
def sleep(a, b):
    time.sleep(random.uniform(a, b))

# ================== EXTRACTION ==================
def extract_job_description(page) -> str:
    selectors = [
        "div.jobs-description__content",
        "div.jobs-box__html-content",
        "article.jobs-description__container",
        "div#job-details",
        "main"
    ]
    for sel in selectors:
        loc = page.locator(sel).first
        try:
            if loc.count() and loc.is_visible():
                txt = loc.inner_text().strip()
                if len(txt) > 200:
                    return txt
        except Exception:
            pass
    return ""

def extract_salary_hint(text: str) -> str:
    if not text:
        return ""
    m = re.search(
        r"\$[\d,]{2,3}\s*(?:k|K)?\s*(?:-|to)\s*\$[\d,]{2,3}\s*(?:k|K)?",
        text
    )
    if m:
        return m.group(0)
    m2 = re.search(r"\$[\d,]{2,3}\s*(?:k|K)", text)
    return m2.group(0) if m2 else ""

# ================== MAIN ==================
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Limit number of jobs to scrape")
    args = parser.parse_args()

    if not SHORTLIST.exists():
        raise FileNotFoundError(f"Missing input file: {SHORTLIST}")

    shortlist = json.loads(SHORTLIST.read_text(encoding="utf-8"))
    if args.limit and args.limit > 0:
        shortlist = shortlist[: args.limit]
    results = []

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=CHROME_PROFILE_PATH,
            headless=False,
            args=["--start-maximized"]
        )
        page = context.new_page()
        page.set_viewport_size(VIEWPORT)

        try:
            for i, job in enumerate(shortlist, start=1):
                print(f"[{i}/{len(shortlist)}] Opening job page")
                page.goto(job["url"], wait_until="domcontentloaded", timeout=60000)
                sleep(2.5, 4.5)

                desc = extract_job_description(page)
                salary = extract_salary_hint(desc)

                results.append({
                    **job,
                    "description": desc,
                    "salary_hint": salary
                })

                # Save every job (Ctrl+C safe)
                OUTFILE.write_text(
                    json.dumps(results, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )

                sleep(3.0, 6.0)
                if i % 15 == 0:
                    sleep(10.0, 18.0)

        except KeyboardInterrupt:
            print("\nInterrupted — progress saved.")
        finally:
            OUTFILE.write_text(
                json.dumps(results, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            context.close()

    print(f"\nSaved {len(results)} jobs -> {OUTFILE}")

if __name__ == "__main__":
    main()
