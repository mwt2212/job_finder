import os
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).parent
PROFILE_DIR = Path(
    os.getenv("JOBFINDER_CHROME_PROFILE") or (BASE_DIR / "chrome-profile")
).expanduser()

JOBS_URL = "https://www.linkedin.com/jobs/search/"


def login_required(page) -> bool:
    url = (page.url or "").lower()
    if "linkedin.com/login" in url or "linkedin.com/checkpoint" in url:
        return True
    try:
        if page.locator('input[name="session_key"]').count() > 0:
            return True
    except Exception:
        pass
    return False


def main() -> None:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Using profile: {PROFILE_DIR}")
    print("Opening LinkedIn jobs page in a persistent browser profile.")
    print("Sign in, complete any prompts, then return here and press Enter.")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            args=["--start-maximized"],
        )
        page = context.new_page()
        page.goto(JOBS_URL, wait_until="domcontentloaded", timeout=60000)

        input("After you are signed in on LinkedIn, press Enter to verify session...")
        page.goto(JOBS_URL, wait_until="domcontentloaded", timeout=60000)

        if login_required(page):
            print("Login not detected yet. Re-run this script after completing sign-in checks.")
        else:
            print("LinkedIn session looks good. You can now run the pipeline.")

        context.close()


if __name__ == "__main__":
    main()
