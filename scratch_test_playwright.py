import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "scrape_outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


def load_environment() -> dict:
    """
    Loads credentials and settings from .env.
    Never hardcode username/password inside this file.
    """

    if load_dotenv:
        load_dotenv(PROJECT_ROOT / ".env")

    username = os.getenv("INSTAGRAM_USERNAME", "").strip()
    password = os.getenv("INSTAGRAM_PASSWORD", "").strip()
    target_profile = os.getenv("TARGET_PROFILE", "").strip()

    headless = os.getenv("HEADLESS", "false").strip().lower() in {"1", "true", "yes"}
    max_posts = int(os.getenv("MAX_POSTS", "10"))
    max_scrolls = int(os.getenv("MAX_SCROLLS", "8"))

    if not username:
        raise RuntimeError("Missing INSTAGRAM_USERNAME in .env")

    if not password:
        raise RuntimeError("Missing INSTAGRAM_PASSWORD in .env")

    if not target_profile:
        raise RuntimeError("Missing TARGET_PROFILE in .env")

    return {
        "username": username,
        "password": password,
        "target_profile": normalize_instagram_username(target_profile),
        "headless": headless,
        "max_posts": max_posts,
        "max_scrolls": max_scrolls,
    }


def normalize_instagram_username(value: str) -> str:
    """
    Accepts either:
    - omganesh_014
    - https://www.instagram.com/omganesh_014/
    Returns clean username only.
    """

    value = value.strip()

    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)
        parts = [part for part in parsed.path.split("/") if part]
        if not parts:
            raise ValueError("Invalid Instagram profile URL")
        value = parts[0]

    value = value.strip("@").strip("/")

    if not re.fullmatch(r"[A-Za-z0-9._]{1,30}", value):
        raise ValueError(f"Invalid Instagram username: {value}")

    return value


def safe_text(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def wait_small(seconds: float = 2.0) -> None:
    time.sleep(seconds)


def click_if_visible(page, selector: str, timeout: int = 3000) -> bool:
    try:
        locator = page.locator(selector).first
        locator.wait_for(state="visible", timeout=timeout)
        locator.click()
        return True
    except Exception:
        return False


def login_to_instagram(page, username: str, password: str) -> None:
    print("[1/5] Opening Instagram login page...")

    page.goto("https://www.instagram.com/accounts/login/", wait_until="domcontentloaded", timeout=60000)

    try:
        page.wait_for_selector("input[name='username']", timeout=20000)
    except PlaywrightTimeoutError:
        raise RuntimeError("Instagram login form did not load. Check internet or Instagram availability.")

    print("[2/5] Filling login form...")

    page.fill("input[name='username']", username)
    page.fill("input[name='password']", password)

    submit_button = page.locator("button[type='submit']").first
    submit_button.click()

    print("[3/5] Waiting for login result...")
    wait_small(8)

    current_url = page.url.lower()

    if "challenge" in current_url or "checkpoint" in current_url:
        raise RuntimeError(
            "Instagram requires verification/checkpoint. "
            "Open browser with HEADLESS=false and complete it manually."
        )

    if "accounts/login" in current_url:
        visible_error = get_visible_text(page)
        raise RuntimeError(f"Login may have failed. Current page still login page. Message: {visible_error}")

    # Handle common post-login popups without forcing them.
    click_if_visible(page, "text=Not Now", timeout=2500)
    click_if_visible(page, "text=Not now", timeout=2500)

    print("[OK] Login completed.")


def get_visible_text(page) -> str:
    try:
        body = page.locator("body").inner_text(timeout=3000)
        return safe_text(body)[:300]
    except Exception:
        return ""


def collect_post_links(page, target_profile: str, max_posts: int, max_scrolls: int) -> List[str]:
    profile_url = f"https://www.instagram.com/{target_profile}/"

    print(f"[4/5] Opening target profile: {profile_url}")

    page.goto(profile_url, wait_until="domcontentloaded", timeout=60000)
    wait_small(5)

    if "accounts/login" in page.url.lower():
        raise RuntimeError("You are not logged in. Instagram redirected back to login page.")

    body_text = get_visible_text(page).lower()

    if "sorry, this page isn't available" in body_text or "page isn't available" in body_text:
        raise RuntimeError("Target profile does not exist or is not available.")

    post_urls = []

    for scroll_index in range(max_scrolls):
        links = page.query_selector_all("a[href*='/p/'], a[href*='/reel/']")

        for link in links:
            href = link.get_attribute("href")
            if not href:
                continue

            if "/p/" not in href and "/reel/" not in href:
                continue

            full_url = href
            if href.startswith("/"):
                full_url = f"https://www.instagram.com{href}"

            clean_url = full_url.split("?")[0].rstrip("/") + "/"

            if clean_url not in post_urls:
                post_urls.append(clean_url)

            if len(post_urls) >= max_posts:
                break

        print(f"  Scroll {scroll_index + 1}/{max_scrolls}: collected {len(post_urls)} unique links")

        if len(post_urls) >= max_posts:
            break

        page.mouse.wheel(0, 2500)
        wait_small(2)

    return post_urls[:max_posts]


def extract_caption_from_meta(meta_description: str) -> str:
    """
    Handles formats like:
    - username on Instagram: "caption here"
    - 10K likes, 50 comments - username on Instagram: "caption here"
    - username on Instagram: 'caption here'
    """

    meta_description = safe_text(meta_description)

    if not meta_description:
        return ""

    patterns = [
        r"on Instagram:\s*\"(.+?)\"$",
        r"on Instagram:\s*'(.+?)'$",
        r"on Instagram:\s*“(.+?)”$",
        r"on Instagram:\s*(.+)$",
    ]

    for pattern in patterns:
        match = re.search(pattern, meta_description)
        if match:
            caption = match.group(1)
            return safe_text(caption.strip("\"'“”"))

    return ""


def extract_post_caption(page, post_url: str) -> dict:
    print(f"  Extracting: {post_url}")

    result = {
        "url": post_url,
        "caption": "",
        "meta_description": "",
        "status": "unknown",
    }

    try:
        page.goto(post_url, wait_until="domcontentloaded", timeout=60000)
        wait_small(3)

        meta_description = ""

        meta_og = page.query_selector("meta[property='og:description']")
        if meta_og:
            meta_description = meta_og.get_attribute("content") or ""

        if not meta_description:
            meta_name = page.query_selector("meta[name='description']")
            if meta_name:
                meta_description = meta_name.get_attribute("content") or ""

        caption = extract_caption_from_meta(meta_description)

        result["meta_description"] = safe_text(meta_description)
        result["caption"] = caption
        result["status"] = "success" if caption else "no_caption_found"

    except Exception as error:
        result["status"] = "error"
        result["error"] = str(error)

    return result


def save_results(target_profile: str, results: List[dict]) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"{target_profile}_captions_{timestamp}.json"

    payload = {
        "target_profile": target_profile,
        "total_posts": len(results),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "results": results,
    }

    output_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_file


def main() -> None:
    try:
        config = load_environment()

        username = config["username"]
        password = config["password"]
        target_profile = config["target_profile"]
        headless = config["headless"]
        max_posts = config["max_posts"]
        max_scrolls = config["max_scrolls"]

        print("=" * 60)
        print("InstaLens Playwright Test Scraper")
        print("=" * 60)
        print(f"Target profile : {target_profile}")
        print(f"Max posts      : {max_posts}")
        print(f"Headless       : {headless}")
        print("=" * 60)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=headless,
                slow_mo=80 if not headless else 0,
            )

            context = browser.new_context(
                viewport={"width": 1366, "height": 768},
                locale="en-US",
            )

            page = context.new_page()

            try:
                login_to_instagram(page, username, password)

                post_urls = collect_post_links(
                    page=page,
                    target_profile=target_profile,
                    max_posts=max_posts,
                    max_scrolls=max_scrolls,
                )

                print(f"[OK] Found {len(post_urls)} post/reel URLs.")

                if not post_urls:
                    print("No posts/reels found. Profile may be private, empty, or Instagram blocked loading.")
                    return

                print("[5/5] Extracting captions...")

                results = []
                for post_url in post_urls:
                    result = extract_post_caption(page, post_url)
                    results.append(result)

                    caption_preview = result.get("caption") or result.get("status")
                    print(f"    -> {caption_preview[:120]}")

                output_file = save_results(target_profile, results)

                print("=" * 60)
                print("DONE")
                print(f"Saved output: {output_file}")
                print("=" * 60)

            finally:
                context.close()
                browser.close()

    except KeyboardInterrupt:
        print("\nStopped by user.")
        sys.exit(130)

    except Exception as error:
        print("\nERROR:", error)
        sys.exit(1)


if __name__ == "__main__":
    main()
