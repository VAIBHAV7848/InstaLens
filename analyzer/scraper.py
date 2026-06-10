"""
Instagram profile scraper using Playwright.

Logs in with user credentials and fetches public profile data:
- Profile details (followers, following, bio, name)
- Captions from recent posts and reels
- Hashtags

Bypasses GraphQL API blocks by automating a headless browser.
"""

import os
import time
import re
import json
from playwright.sync_api import sync_playwright

def parse_stat_number(val_str: str) -> int:
    """Parse Instagram stat strings (e.g. 1.2M, 394, 1,500) to integers."""
    val_str = val_str.strip().lower().replace(",", "").replace(" ", "")
    try:
        if "k" in val_str:
            return int(float(val_str.replace("k", "")) * 1000)
        if "m" in val_str:
            return int(float(val_str.replace("m", "")) * 1000000)
        return int(val_str)
    except:
        return 0

def login_with_playwright(username, password):
    """Authenticate with Instagram in browser and save session cookies."""
    session_file = f"playwright_session_{username}.json"
    print(f"[InstaLens] Performing Playwright login for @{username} (Headful Mode)...", flush=True)
    
    with sync_playwright() as p:
        # Launch headful browser so user can see and complete security checks
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # Navigate to login
        page.goto("https://www.instagram.com/accounts/login/", timeout=60000)
        time.sleep(5)
        
        # Detect inputs
        if page.query_selector("input[name='username']"):
            page.fill("input[name='username']", username)
            page.fill("input[name='password']", password)
            page.click("button[type='submit']")
        elif page.query_selector("input[name='email']"):
            page.fill("input[name='email']", username)
            page.fill("input[name='pass']", password)
            
            # Click visible login button
            buttons = page.query_selector_all("button, input[type='submit'], [role='button']")
            clicked = False
            for btn in buttons:
                if btn.is_visible():
                    txt = (btn.text_content() or btn.get_attribute("value") or "").strip()
                    if "log in" in txt.lower():
                        btn.click()
                        clicked = True
                        break
            if not clicked:
                raise Exception("Could not find submit button on login page.")
        else:
            # Fallback text click
            btn = page.query_selector("text=Log in")
            if btn:
                btn.click()
            else:
                raise Exception("Instagram login input fields not found.")
            
        # Poll for successful redirect/login (up to 90 seconds)
        print("[InstaLens] Waiting for login completion or verification checks. Please check the browser window...", flush=True)
        logged_in = False
        for i in range(45):
            time.sleep(2)
            # Check if login fields are gone and profile/feed elements are present
            if not (page.query_selector("input[name='username']") or page.query_selector("input[name='email']")):
                if "accounts/login" not in page.url and not page.query_selector("text=The login information you entered is incorrect"):
                    # Check if security code prompts are still active
                    if not (page.query_selector("input[name='security_code']") or page.query_selector("input[placeholder*='Security Code']")):
                        logged_in = True
                        break
        
        if not logged_in:
            page.screenshot(path="playwright_login_error.png")
            print("[InstaLens] Login verification timed out or failed. Saved failure screenshot to playwright_login_error.png", flush=True)
            err_el = page.query_selector("[role='alert'], #error_box")
            err_msg = err_el.text_content() if err_el else "Invalid credentials, verification required, or timeout."
            browser.close()
            raise Exception(f"Login failed: {err_msg}")
        else:
            print("[InstaLens] Login successful!", flush=True)
            # Save storage state
            context.storage_state(path=session_file)
            print(f"[InstaLens] Saved state to {session_file}", flush=True)
            
        browser.close()

def create_loader(username: str, password: str = None):
    """Placeholder to maintain compatibility with app.py credentials verification."""
    session_file = f"playwright_session_{username}.json"
    if not os.path.exists(session_file):
        if not password:
            raise Exception("No active session found. Please log in first.")
        login_with_playwright(username, password)
    else:
        if password: # Re-authenticate / overwrite
            login_with_playwright(username, password)
    return True

def scrape_profile(
    target_username: str,
    login_username: str,
    login_password: str = None,
    max_posts: int = 30,
    source: str = "posts",
) -> dict:
    """Scrape captions and hashtags from a target Instagram profile using Playwright browser automation."""
    target_username = extract_username_from_url(target_username)
    session_file = f"playwright_session_{login_username}.json"
    
    if not os.path.exists(session_file):
        if login_password:
            login_with_playwright(login_username, login_password)
        else:
            raise Exception("No active session found. Please log in first.")
            
    print(f"[InstaLens] Launching Playwright to scrape profile @{target_username}...", flush=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Load context with storage state
        context = browser.new_context(
            storage_state=session_file,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # Navigate to target profile
        url_suffix = "reposts/" if source == "reposts" else ""
        print(f"[InstaLens] Navigating to https://www.instagram.com/{target_username}/{url_suffix}", flush=True)
        page.goto(f"https://www.instagram.com/{target_username}/{url_suffix}", timeout=60000)
        time.sleep(5)
        
        # Verify if page loaded or was redirected to login or shows login prompts
        if "accounts/login" in page.url or page.query_selector("a[href*='/accounts/login']"):
            # Session expired! Try logging in again if we have password
            print("[InstaLens] Session expired or invalid. Attempting automatic re-login...", flush=True)
            browser.close()
            if login_password:
                login_with_playwright(login_username, login_password)
                # Retry once
                return scrape_profile(target_username, login_username, login_password, max_posts, source=source)
            else:
                raise Exception("Instagram session expired or invalid. Please log out and log in again.")
                
        # Check if profile does not exist
        if "Page Not Found" in page.title() or page.query_selector("text=isn't available"):
            raise Exception(f"Profile @{target_username} does not exist or is unavailable.")
            
        # Extract profile stats (followers, following, posts, full name, biography)
        full_name = target_username
        bio = ""
        post_count = 0
        followers = 0
        following = 0
        
        header_el = page.query_selector("header")
        if header_el:
            header_text = header_el.text_content()
            
            # Posts count
            posts_match = re.search(r'([\d,\.]+k?m?)\s*posts?', header_text, re.IGNORECASE)
            if posts_match:
                post_count = parse_stat_number(posts_match.group(1))
                
            # Followers
            followers_match = re.search(r'([\d,\.]+k?m?)\s*followers?', header_text, re.IGNORECASE)
            if followers_match:
                followers = parse_stat_number(followers_match.group(1))
                
            # Following
            following_match = re.search(r'([\d,\.]+k?m?)\s*following?', header_text, re.IGNORECASE)
            if following_match:
                following = parse_stat_number(following_match.group(1))
                
        meta_desc = page.locator("meta[name='description']").get_attribute("content")
        if not meta_desc:
            meta_desc = page.locator("meta[property='og:description']").get_attribute("content")
            
        # Parse full name and stats from meta description as fallback
        if meta_desc:
            # Parse stats
            followers_match = re.search(r'([\d,\.]+k?m?)\s*Followers', meta_desc)
            if followers_match:
                followers = parse_stat_number(followers_match.group(1))
            following_match = re.search(r'([\d,\.]+k?m?)\s*Following', meta_desc)
            if following_match:
                following = parse_stat_number(following_match.group(1))
            posts_match = re.search(r'([\d,\.]+k?m?)\s*Posts', meta_desc)
            if posts_match:
                post_count = parse_stat_number(posts_match.group(1))
                
            # Parse Full Name
            name_match = re.search(r'from\s+(.*?)\s+\(@' + re.escape(target_username) + r'\)', meta_desc)
            if name_match:
                full_name = name_match.group(1)
                
        # Bio can be queried by selecting the span under the profile header info
        for selector in ["header section h1 ~ span", "header h1 ~ div span", "header section div:last-child span"]:
            el = page.query_selector(selector)
            if el:
                txt = el.text_content().strip()
                if txt and len(txt) > 0 and not txt.isdigit():
                    bio = txt
                    break
            
        # Get post links
        links = page.query_selector_all("a[href*='/p/'], a[href*='/reel/']")
        post_urls = []
        for l in links:
            href = l.get_attribute("href")
            if href and ("/p/" in href or "/reel/" in href):
                full_url = f"https://www.instagram.com{href}"
                if full_url not in post_urls:
                    post_urls.append(full_url)
                    
        print(f"[InstaLens] Found {len(post_urls)} posts/reels. Limit is {max_posts}.", flush=True)
        
        # Scrape captions
        captions = []
        hashtags = []
        
        for url in post_urls[:max_posts]:
            print(f"[InstaLens] Loading post: {url}", flush=True)
            page.goto(url, timeout=60000)
            time.sleep(3)
            
            # Extract meta description
            desc = page.locator("meta[property='og:description']").get_attribute("content")
            if not desc:
                desc = page.locator("meta[name='description']").get_attribute("content")
                
            caption = ""
            if desc:
                # Regex match double quotes or single quotes
                match = re.search(r':\s*"(.*)"\s*\.?\s*$', desc, re.DOTALL)
                if not match:
                    match = re.search(r":\s*'(.*)'\s*\.?\s*$", desc, re.DOTALL)
                if match:
                    caption = match.group(1).strip()
                else:
                    # Parse from colon to the end if quotes not matched
                    parts = desc.split("on Instagram: ")
                    if len(parts) > 1:
                        caption = parts[1].strip()
                        # Strip outer quotes if present
                        if caption.startswith('"') and caption.endswith('"'):
                            caption = caption[1:-1]
                        elif caption.startswith("'") and caption.endswith("'"):
                            caption = caption[1:-1]
                            
            if caption:
                print(f"[InstaLens] Extracted caption: {caption[:60]}...", flush=True)
                captions.append(caption)
                # Extract hashtags from caption
                tags = re.findall(r"#(\w+)", caption)
                hashtags.extend([t.lower() for t in tags])
            else:
                print(f"[InstaLens] No caption found for post: {url}", flush=True)
                
        browser.close()
        
    profile_data = {
        "profile_name": full_name or target_username,
        "bio": bio,
        "followers": followers,
        "following": following,
        "post_count": post_count,
        "captions": captions,
        "hashtags": hashtags,
        "scraped_posts": len(captions),
    }
    
    if not profile_data["captions"]:
        source_name = "reposts tab" if source == "reposts" else "profile grid"
        raise Exception(
            f"No captions found on the {source_name} of @{target_username}. "
            "The profile may have no posts/reposts or only image/video posts without captions."
        )
        
    return profile_data

def extract_username_from_url(url_or_username: str) -> str:
    """Extract Instagram username from URL or raw input."""
    text = url_or_username.strip().rstrip("/")
    if "instagram.com" in text:
        parts = text.split("instagram.com/")
        if len(parts) > 1:
            username = parts[1].split("/")[0].split("?")[0]
            return username.lstrip("@")
    return text.lstrip("@")
