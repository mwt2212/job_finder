import json
import time
import random
import urllib.parse
import math
import re
import argparse
from pathlib import Path
from collections import deque
from playwright.sync_api import sync_playwright

# ================== CONFIG ==================
BASE_URL = "https://www.linkedin.com/jobs/search/?distance=5&f_E=2&f_TPR=r86400&geoId=103112676&origin=JOB_SEARCH_PAGE_JOB_FILTER&sortBy=DD"
OUTFILE = "tier2_metadata.json"
SEARCHES_FILE = Path(__file__).parent / "searches.json"

CHROME_PROFILE_PATH = r"C:\Users\Michael\Desktop\Job Finder\chrome-profile"

PAGE_SIZE = 25
MAX_RESULTS = 1000  # hard cap for ETA + run length
MAX_START = 5000  # upper bound; script stops when results end

# Viewport: keep this. It’s what made 25/page reliable for you.
VIEWPORT = {"width": 1280, "height": 1440}

# Force location (since you’re filtering Chicago anyway)
FORCED_LOCATION = "Chicago, IL"

# ================== TIMING / PACING ==================
def sleep(a, b):
    time.sleep(random.uniform(a, b))

PAGE_LOAD_WAIT = (2.0, 3.5)
SCROLL_WAIT = (0.5, 0.9)
PAGE_COOLDOWN = (2.0, 4.0)
LONG_BREAK = (10.0, 18.0)

# ================== URL HELPERS ==================
def strip_param(url, key):
    p = urllib.parse.urlparse(url)
    q = dict(urllib.parse.parse_qsl(p.query))
    q.pop(key, None)
    return urllib.parse.urlunparse(p._replace(query=urllib.parse.urlencode(q)))

def set_param(url, key, value):
    p = urllib.parse.urlparse(url)
    q = dict(urllib.parse.parse_qsl(p.query))
    q[key] = value
    return urllib.parse.urlunparse(p._replace(query=urllib.parse.urlencode(q)))

def normalize_job_url(href):
    if not href:
        return ""
    if href.startswith("/"):
        href = "https://www.linkedin.com" + href
    return href.split("?")[0]

# ================== SAVE ==================
def save_partial(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)

# ================== ETA HELPERS ==================
def fmt_secs(sec):
    sec = int(max(0, sec))
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    if h > 0:
        return f"{h}h {m}m {s}s"
    return f"{m}m {s}s"

# ================== FIND SCROLL PANEL ==================
def find_results_panel(page):
    selectors = [
        "div.scaffold-layout__list",
        "div.scaffold-layout__list-container",
        "div.jobs-search-results-list",
    ]
    for sel in selectors:
        loc = page.locator(sel).first
        try:
            if loc.count() and loc.is_visible() and loc.locator('a[href*="/jobs/view/"]').count() > 0:
                return loc, sel
        except Exception:
            pass
    return None, None

def extract_total_results(page) -> int:
    """
    Best-effort parse of total results count from the page header.
    Returns 0 if not found.
    """
    selectors = [
        "h1.jobs-search-results-list__text",
        "span.results-context-header__job-count",
        "h1",
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if not loc.count():
                continue
            text = loc.inner_text().strip()
            if "result" not in text.lower():
                if sel != "h1":
                    continue
            m = re.search(r"([0-9,]+)", text)
            if m:
                return int(m.group(1).replace(",", ""))
        except Exception:
            continue
    return 0

def hydrate_panel(page, panel):
    """
    Scroll the left results panel until ~25 links are rendered (virtualized list).
    """
    def count_links():
        c = panel.locator("a.job-card-container__link").count()
        if c == 0:
            c = panel.locator('a[href*="/jobs/view/"]').count()
        return c

    try:
        panel.click(timeout=2000)
        panel.hover(timeout=2000)
    except Exception:
        pass

    prev = -1
    stable = 0

    for _ in range(18):
        cur = count_links()

        if cur >= 25:
            break

        if cur == prev:
            stable += 1
        else:
            stable = 0
            prev = cur

        if stable >= 3 and cur >= 22:
            break

        page.mouse.wheel(0, 1600)
        sleep(*SCROLL_WAIT)

    return count_links()

# ================== STRUCTURED EXTRACTION ==================
def safe_text(locator):
    try:
        if locator.count():
            return locator.first.inner_text().strip()
    except Exception:
        pass
    return ""

def first_nonempty(*vals):
    for v in vals:
        if v and v.strip():
            return v.strip()
    return ""

def infer_workplace(text_blob: str) -> str:
    t = (text_blob or "").lower()
    if "remote" in t:
        return "remote"
    if "hybrid" in t:
        return "hybrid"
    if "on-site" in t or "onsite" in t:
        return "onsite"
    return ""

def extract_company(li):
    """
    LinkedIn A/B tests these. Try a few robust patterns.
    """
    # Common class (sometimes works)
    c1 = safe_text(li.locator(".job-card-container__primary-description"))

    # Older variant
    c2 = safe_text(li.locator(".job-card-container__company-name"))

    # Sometimes company is the first "secondary" strong-ish line
    # Try common structure: spans/divs near the title link
    c3 = safe_text(li.locator('span.job-card-container__primary-description'))
    c4 = safe_text(li.locator('div.artdeco-entity-lockup__subtitle span'))
    c5 = safe_text(li.locator('div.artdeco-entity-lockup__subtitle'))

    # Last-resort heuristic from lines:
    raw = ""
    try:
        raw = li.inner_text().strip()
    except Exception:
        raw = ""

    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    # Typical ordering is [title, company, location/posted/other...]
    c6 = lines[1] if len(lines) >= 2 else ""

    # Filter out obvious non-company junk
    bad = {"easy apply", "promoted", "view job", "save", "applied", "applicants"}
    def ok(s):
        sl = (s or "").strip().lower()
        if not sl:
            return False
        if sl in bad:
            return False
        if " ago" in sl or " hours" in sl or " days" in sl:
            return False
        # too long usually means we're grabbing a blob
        if len(sl) > 80:
            return False
        return True

    for cand in [c1, c2, c3, c4, c5, c6]:
        if ok(cand):
            return cand.strip()

    return ""

def extract_fields_from_card(li_locator, job_url: str, location_label: str):
    """
    Best-effort extraction; keeps raw card_text as fallback.
    """
    raw = ""
    try:
        raw = li_locator.inner_text().strip()
    except Exception:
        raw = ""

    # Title
    title = safe_text(li_locator.locator("a.job-card-container__link span[aria-hidden='true']"))
    if not title:
        title = safe_text(li_locator.locator("a.job-card-container__link"))

    # Company (fixed)
    company = extract_company(li_locator)

    # Location forced
    location = location_label

    # Posted
    posted = safe_text(li_locator.locator("time"))
    if not posted:
        posted_guess = ""
        for line in (raw.splitlines() if raw else []):
            low = line.lower()
            if "ago" in low or "hour" in low or "hours" in low or "day" in low or "days" in low or "minute" in low:
                posted_guess = line.strip()
                break
        posted = posted_guess

    workplace = infer_workplace(raw)

    return {
        "url": job_url,
        "title": title,
        "company": company,
        "location": location,
        "posted": posted,
        "workplace": workplace,
        "card_text": raw[:1500],
    }

# ================== MAIN ==================
def load_searches() -> dict:
    if SEARCHES_FILE.exists():
        return json.loads(SEARCHES_FILE.read_text(encoding="utf-8"))
    return {
        "Chicago": {
            "url": BASE_URL,
            "location_label": "Chicago, IL"
        }
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--search", default="Chicago", help="Search label from searches.json")
    parser.add_argument("--query", default="", help="Optional LinkedIn keywords search")
    parser.add_argument("--max-results", type=int, default=MAX_RESULTS, help="Cap total jobs for this run")
    args = parser.parse_args()

    searches = load_searches()
    if args.search not in searches:
        raise SystemExit(f"Unknown search label: {args.search}")

    search_cfg = searches[args.search]
    base_url = search_cfg.get("url") or BASE_URL
    location_label = search_cfg.get("location_label") or FORCED_LOCATION

    out_path = Path(__file__).parent / OUTFILE
    max_results = max(1, int(args.max_results))
    base = strip_param(base_url, "start")
    if args.query:
        base = set_param(base, "keywords", args.query)

    jobs = []
    seen = set()

    # ETA state
    t0 = time.time()
    page_times = deque(maxlen=12)
    total_pages_cap = (MAX_START // PAGE_SIZE) + 1
    total_results = 0
    cap_pages = math.ceil(max_results / PAGE_SIZE)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=CHROME_PROFILE_PATH,
            headless=False,
            args=["--start-maximized"]
        )
        page = context.new_page()
        page.set_viewport_size(VIEWPORT)

        try:
            print(f"Cap: {max_results} jobs | Search: {args.search}")
            for idx, start in enumerate(range(0, MAX_START + 1, PAGE_SIZE)):
                page_t0 = time.time()

                url = set_param(base, "start", str(start))
                print(f"\nLoading start={start}")
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                sleep(*PAGE_LOAD_WAIT)

                # Make sure results exist
                try:
                    page.wait_for_selector('a[href*="/jobs/view/"]', timeout=20000)
                except Exception:
                    print("No job links appeared — stopping.")
                    save_partial(out_path, jobs)
                    break

                panel, panel_sel = find_results_panel(page)
                if not panel:
                    print("Could not find results panel — stopping.")
                    save_partial(out_path, jobs)
                    break

                rendered = hydrate_panel(page, panel)
                print(f"Results panel: {panel_sel} | links rendered: {rendered}")

                links = panel.locator("a.job-card-container__link")
                if links.count() == 0:
                    links = panel.locator('a[href*="/jobs/view/"]')

                new_on_page = 0

                for i in range(links.count()):
                    href = links.nth(i).get_attribute("href") or ""
                    job_url = normalize_job_url(href)

                    if not job_url or "/jobs/view/" not in job_url:
                        continue
                    if job_url in seen:
                        continue

                    seen.add(job_url)
                    new_on_page += 1

                    li = links.nth(i).locator("xpath=ancestor::li[1]")
                    if li.count():
                        job = extract_fields_from_card(li.first, job_url, location_label)
                        job["source"] = args.search
                        job["location"] = location_label
                        jobs.append(job)
                    else:
                        jobs.append({
                            "url": job_url,
                            "title": "",
                            "company": "",
                            "location": location_label,
                            "posted": "",
                            "workplace": "",
                            "card_text": "",
                            "source": args.search
                        })

                print(f"Added {new_on_page} jobs | Total: {len(jobs)}")
                save_partial(out_path, jobs)

                if len(jobs) >= max_results:
                    print(f"Reached cap of {max_results} jobs — stopping.")
                    break

                if new_on_page == 0:
                    print("No new jobs — end of results.")
                    break

                # ---- ETA / progress ----
                page_dt = time.time() - page_t0
                page_times.append(page_dt)
                avg_page = sum(page_times) / len(page_times)

                pages_done = idx + 1
                elapsed = time.time() - t0

                jobs_per_page = max(1, len(jobs) / pages_done)
                remaining_jobs = max(0, max_results - len(jobs))
                est_left_pages = remaining_jobs / jobs_per_page
                eta_est = est_left_pages * avg_page
                pct = min(100.0, (len(jobs) / max_results) * 100.0)
                print(
                    f"Timing: page {page_dt:.1f}s | avg {avg_page:.1f}s/page | "
                    f"elapsed {fmt_secs(elapsed)} | ETA(est) ~{fmt_secs(eta_est)} | "
                    f"{len(jobs)}/{max_results} ({pct:.1f}%)"
                )

                # ---- pacing ----
                sleep(*PAGE_COOLDOWN)
                if idx > 0 and idx % 15 == 0:
                    print("Taking a longer human break...")
                    sleep(*LONG_BREAK)

        except KeyboardInterrupt:
            print("\nInterrupted — saving progress.")
            save_partial(out_path, jobs)

        finally:
            print(f"\nSaved {len(jobs)} jobs -> {out_path}")
            context.close()

if __name__ == "__main__":
    main()
