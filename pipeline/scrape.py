import json
import time
import random
import re
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
from text_cleaning import clean_job_description

# ================== PATHS (FIXED) ==================
BASE_DIR = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = BASE_DIR / "artifacts"

OUTFILE = ARTIFACTS_DIR / "tier2_full.json"

CHROME_PROFILE_PATH = Path(
    os.getenv("JOBFINDER_CHROME_PROFILE") or (BASE_DIR / "chrome-profile")
).expanduser()

# ================== VIEWPORT ==================
DEFAULT_VIEWPORT = {"width": 1280, "height": 1440}

# ================== TIMING ==================
def sleep(a, b):
    time.sleep(random.uniform(a, b))


def _parse_viewport_override() -> dict | None:
    raw = (os.getenv("JOBFINDER_VIEWPORT") or "").strip().lower()
    if not raw:
        return None
    m = re.match(r"^\s*(\d{3,5})\s*[x,]\s*(\d{3,5})\s*$", raw)
    if not m:
        return None
    w = int(m.group(1))
    h = int(m.group(2))
    if w < 600 or h < 600:
        return None
    return {"width": w, "height": h}


def _resolve_viewport(page) -> dict:
    override = _parse_viewport_override()
    if override:
        return override
    # Prefer OS-level monitor size; Playwright's default emulated viewport
    # can report 1280x720 before we set a real viewport.
    try:
        import ctypes

        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        sw = int(user32.GetSystemMetrics(0))
        sh = int(user32.GetSystemMetrics(1))
        if sw > 0 and sh > 0:
            return {"width": max(900, sw // 2), "height": max(900, sh)}
    except Exception:
        pass
    try:
        dims = page.evaluate(
            "() => ({w: window.screen.availWidth || window.screen.width || 0, h: window.screen.availHeight || window.screen.height || 0})"
        )
        sw = int((dims or {}).get("w") or 0)
        sh = int((dims or {}).get("h") or 0)
        if sw > 0 and sh > 0:
            return {"width": max(900, sw // 2), "height": max(900, sh)}
    except Exception:
        pass
    return DEFAULT_VIEWPORT


def _login_required(page) -> bool:
    url = (page.url or "").lower()
    if "linkedin.com/login" in url or "linkedin.com/checkpoint" in url:
        return True
    try:
        if page.locator('input[name="session_key"]').count() > 0:
            return True
        if page.locator('a[href*="/login"]').count() > 0 and page.locator("text=Sign in").count() > 0:
            return True
    except Exception:
        pass
    return False

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
def artifact_input(name: str) -> Path:
    artifact = ARTIFACTS_DIR / name
    legacy = BASE_DIR / name
    return artifact if artifact.exists() else legacy


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Limit number of jobs to scrape")
    args = parser.parse_args()

    shortlist_path = artifact_input("tier2_shortlist.json")
    if not shortlist_path.exists():
        raise FileNotFoundError(f"Missing input file: {shortlist_path}")
    shortlist = json.loads(shortlist_path.read_text(encoding="utf-8"))
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    if args.limit and args.limit > 0:
        shortlist = shortlist[: args.limit]
    results = []

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(CHROME_PROFILE_PATH),
            headless=False,
            args=["--start-maximized"]
        )
        page = context.new_page()
        viewport = _resolve_viewport(page)
        page.set_viewport_size(viewport)
        print(f"Viewport: {viewport['width']}x{viewport['height']}")

        try:
            for i, job in enumerate(shortlist, start=1):
                print(f"[{i}/{len(shortlist)}] Opening job page")
                page.goto(job["url"], wait_until="domcontentloaded", timeout=60000)
                sleep(2.5, 4.5)
                if i == 1 and _login_required(page):
                    raise RuntimeError(
                        "LinkedIn login is required for scraping. Run `python setup-linkedin-profile.py`, sign in once, "
                        "and reuse the same JOBFINDER_CHROME_PROFILE."
                    )

                raw_desc = extract_job_description(page)
                desc = clean_job_description(raw_desc)
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
