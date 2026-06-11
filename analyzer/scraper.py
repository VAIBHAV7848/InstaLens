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
):
    """Scrape captions and hashtags from a target Instagram profile using Playwright browser automation."""
    target_username = extract_username_from_url(target_username)
    session_file = f"playwright_session_{login_username}.json"
    
    if not os.path.exists(session_file):
        if login_password:
            yield "No active session found. Re-authenticating..."
            login_with_playwright(login_username, login_password)
        else:
            raise Exception("No active session found. Please log in first.")
            
    msg = f"Launching headless browser to analyze @{target_username}..."
    print(f"[InstaLens] {msg}", flush=True)
    yield msg
    
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
        msg = f"Opening profile grid (/{url_suffix or target_username})..."
        if source == "following":
            msg = "Opening profile and accessing following list..."
        print(f"[InstaLens] {msg}", flush=True)
        yield msg
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
                yield from scrape_profile(target_username, login_username, login_password, max_posts, source=source)
                return
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
            
        captions = []
        hashtags = []
        posts_detail = []

        if source == "following":
            print(f"[InstaLens] Scraping following list for @{target_username}...", flush=True)
            
            # Click on the following link
            following_link = page.locator(f"a[href*='/{target_username}/following/']")
            if not following_link.is_visible():
                following_link = page.locator("a:has-text('following')")
                
            if following_link.is_visible():
                following_link.click()
            else:
                try:
                    page.click("text=following")
                except:
                    # Fallback directly to selector click
                    page.click(f"a[href$='/following/']")
            
            # Wait for the modal/dialog to appear
            dialog_selector = "div[role='dialog']"
            page.wait_for_selector(dialog_selector, timeout=20000)
            time.sleep(3)
            
            # Locate the scrollable container inside the dialog
            scroll_container = page.locator("div[role='dialog'] div._aano")
            if not scroll_container.is_visible():
                scroll_container = page.locator("div[role='dialog'] div[style*='overflow-y'], div[role='dialog'] div[style*='overflow: auto']").first
            if not scroll_container.is_visible():
                scroll_container = page.locator("div[role='dialog']").first
                
            last_count = 0
            no_change_count = 0
            users = []
            
            for _ in range(25):
                # Scroll container to load more accounts
                scroll_container.evaluate("el => el.scrollTop = el.scrollHeight")
                time.sleep(1.5)
                
                # Scrape visible usernames and full names
                users = page.evaluate("""() => {
                    const results = [];
                    const rows = document.querySelectorAll("div[role='dialog'] ul li, div[role='dialog'] [role='dialog'] li, div[role='dialog'] div[style*='flex-direction: column'] > div");
                    for (let row of rows) {
                        const links = row.querySelectorAll("a");
                        if (links.length === 0) continue;
                        
                        let username = "";
                        for (let l of links) {
                            const href = l.getAttribute("href");
                            if (href && href !== "/" && !href.includes("following") && !href.includes("followers")) {
                                username = href.replace(/\\//g, "").split("?")[0];
                                break;
                            }
                        }
                        if (!username) continue;
                        
                        let fullName = "";
                        const spans = row.querySelectorAll("span");
                        for (let s of spans) {
                            const txt = s.textContent.trim();
                            if (txt && txt !== username && txt !== "Follow" && txt !== "Following" && txt !== "Requested" && txt !== "Remove" && !txt.includes("•")) {
                                fullName = txt;
                                break;
                            }
                        }
                        results.push({ username, fullName });
                    }
                    
                    const unique = [];
                    const seen = new Set();
                    for (let u of results) {
                        if (!seen.has(u.username)) {
                            seen.add(u.username);
                            unique.push(u);
                        }
                    }
                    return unique;
                }""")
                
                msg = f"Scrolling following list (Loaded {len(users)} accounts)..."
                print(f"[InstaLens] {msg}", flush=True)
                yield msg
                
                if len(users) >= max_posts:
                    users = users[:max_posts]
                    break
                    
                if len(users) == last_count:
                    no_change_count += 1
                    if no_change_count >= 3:
                        break
                else:
                    no_change_count = 0
                last_count = len(users)
                
            # Map followed users into text chunks
            for u in users:
                desc = u["username"]
                if u["fullName"]:
                    desc += f" - {u['fullName']}"
                captions.append(desc)
                
            # Extract hashtags from display names if any
            for desc in captions:
                tags = re.findall(r"#(\w+)", desc)
                hashtags.extend([t.lower() for t in tags])
        else:
            # Get post links (original grid/reposts scraping logic)
            links = page.query_selector_all("a[href*='/p/'], a[href*='/reel/']")
            post_urls = []
            for l in links:
                href = l.get_attribute("href")
                if href and ("/p/" in href or "/reel/" in href):
                    full_url = f"https://www.instagram.com{href}"
                    if full_url not in post_urls:
                        post_urls.append(full_url)
                        
            # Supplement with reposts if fewer than max_posts found in grid
            if len(post_urls) < max_posts and source != "reposts":
                try:
                    msg = f"Found {len(post_urls)} grid posts. Supplementing with reposts..."
                    print(f"[InstaLens] {msg}", flush=True)
                    yield msg
                    page.goto(f"https://www.instagram.com/{target_username}/reposts/", timeout=30000)
                    time.sleep(4)
                    reposts_links = page.query_selector_all("a[href*='/p/'], a[href*='/reel/']")
                    for l in reposts_links:
                        href = l.get_attribute("href")
                        if href and ("/p/" in href or "/reel/" in href):
                            full_url = f"https://www.instagram.com{href}"
                            if full_url not in post_urls:
                                post_urls.append(full_url)
                                if len(post_urls) >= max_posts:
                                    break
                except Exception as ex:
                    print(f"[InstaLens] Could not check reposts: {ex}", flush=True)

            # Supplement with tagged posts if still fewer than max_posts found
            if len(post_urls) < max_posts:
                try:
                    msg = f"Found {len(post_urls)} posts so far. Supplementing with tagged posts..."
                    print(f"[InstaLens] {msg}", flush=True)
                    yield msg
                    page.goto(f"https://www.instagram.com/{target_username}/tagged/", timeout=30000)
                    time.sleep(4)
                    tagged_links = page.query_selector_all("a[href*='/p/'], a[href*='/reel/']")
                    for l in tagged_links:
                        href = l.get_attribute("href")
                        if href and ("/p/" in href or "/reel/" in href):
                            full_url = f"https://www.instagram.com{href}"
                            if full_url not in post_urls:
                                post_urls.append(full_url)
                                if len(post_urls) >= max_posts:
                                    break
                except Exception as ex:
                    print(f"[InstaLens] Could not check tagged posts: {ex}", flush=True)

            total_to_scrape = min(len(post_urls), max_posts)
            msg = f"Found {len(post_urls)} total posts/reels (including tagged). Limit is {max_posts}."
            print(f"[InstaLens] {msg}", flush=True)
            yield msg
            
            for i, url in enumerate(post_urls[:max_posts]):
                msg = f"Extracting caption from post {i+1}/{total_to_scrape}..."
                print(f"[InstaLens] {msg}", flush=True)
                yield msg
                page.goto(url, timeout=60000)
                time.sleep(3)
                
                # Extract meta description
                desc = page.locator("meta[property='og:description']").get_attribute("content")
                if not desc:
                    desc = page.locator("meta[name='description']").get_attribute("content")
                    
                caption = ""
                likes = 0
                comments = 0
                date_str = ""
                
                if desc:
                    # Parse likes & comments
                    likes_match = re.search(r'(\d[\d,\.]*[KMB]?)\s*likes', desc, re.IGNORECASE)
                    comments_match = re.search(r'(\d[\d,\.]*[KMB]?)\s*comments', desc, re.IGNORECASE)
                    if likes_match:
                        likes = parse_interaction_count(likes_match.group(1))
                    if comments_match:
                        comments = parse_interaction_count(comments_match.group(1))
                        
                    # Parse date if available
                    date_match = re.search(r'on\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})', desc)
                    if date_match:
                        date_str = date_match.group(1)
                        
                    # Extract caption
                    match = re.search(r':\s*"(.*)"\s*\.?\s*$', desc, re.DOTALL)
                    if not match:
                        match = re.search(r":\s*'(.*)'\s*\.?\s*$", desc, re.DOTALL)
                    if match:
                        caption = match.group(1).strip()
                    else:
                        parts = desc.split("on Instagram: ")
                        if len(parts) > 1:
                            caption = parts[1].strip()
                            if caption.startswith('"') and caption.endswith('"'):
                                caption = caption[1:-1]
                            elif caption.startswith("'") and caption.endswith("'"):
                                caption = caption[1:-1]
                                
                # Detect format type
                is_video = False
                is_carousel = False
                if "/reel/" in url:
                    is_video = True
                else:
                    try:
                        if page.locator("video").count() > 0:
                            is_video = True
                    except:
                        pass
                    try:
                        if page.locator("button[aria-label='Next'], ._acaz").count() > 0:
                            is_carousel = True
                    except:
                        pass
                
                format_type = "Reel" if is_video else ("Carousel" if is_carousel else "Image")
                
                if caption:
                    print(f"[InstaLens] Extracted caption: {caption[:60]}...", flush=True)
                    captions.append(caption)
                    tags = re.findall(r"#(\w+)", caption)
                    hashtags.extend([t.lower() for t in tags])
                else:
                    print(f"[InstaLens] No caption found for post: {url}", flush=True)
                    
                posts_detail.append({
                    "url": url,
                    "caption": caption,
                    "likes": likes,
                    "comments": comments,
                    "format": format_type,
                    "date": date_str
                })
                
        browser.close()
        
    # Always append bio to captions if it exists, so bio is analyzed
    if bio and bio not in captions:
        captions.insert(0, bio)
        # also add tags from bio to hashtags
        tags = re.findall(r"#(\w+)", bio)
        hashtags.extend([t.lower() for t in tags])

    profile_data = {
        "profile_name": full_name or target_username,
        "bio": bio,
        "followers": followers,
        "following": following,
        "post_count": post_count,
        "captions": captions,
        "hashtags": hashtags,
        "scraped_posts": len(posts_detail),
        "posts_detail": posts_detail
    }
    
    # If still no captions (e.g., completely empty bio, empty grid, empty tagged)
    if not profile_data["captions"]:
        fallback_caption = f"Instagram profile of {full_name or target_username}. Follows {following} accounts and has {followers} followers."
        captions.append(fallback_caption)
        
    yield profile_data

def spy_target_activity(
    target_username: str,
    login_username: str,
    login_password: str = None,
    scan_depth_friends: int = 5,
    scan_depth_posts: int = 5
):
    """Spy on a target user's likes and comments across their followed accounts."""
    target_username = extract_username_from_url(target_username)
    session_file = f"playwright_session_{login_username}.json"
    
    if not os.path.exists(session_file):
        if login_password:
            yield "No active session found. Re-authenticating..."
            login_with_playwright(login_username, login_password)
        else:
            raise Exception("No active session found. Please log in first.")
            
    yield f"Launching headless browser to spy on @{target_username}..."
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            storage_state=session_file,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # Navigate to target profile
        yield f"Opening profile of @{target_username} to retrieve friends list..."
        page.goto(f"https://www.instagram.com/{target_username}/", timeout=60000)
        time.sleep(3)
        
        # Click Following link
        yield "Opening following modal..."
        following_link = page.locator(f"a[href*='/{target_username}/following/']")
        if not following_link.is_visible():
            following_link = page.locator("a:has-text('following')")
        if following_link.is_visible():
            following_link.click()
        else:
            try:
                page.click("text=following")
            except:
                page.click(f"a[href$='/following/']")
        
        # Wait for dialog
        dialog_selector = "div[role='dialog']"
        try:
            page.wait_for_selector(dialog_selector, timeout=15000)
        except Exception:
            browser.close()
            raise Exception("Could not open following list. Is the profile private?")
        time.sleep(3)
        
        # Locate scroll container
        scroll_container = page.locator("div[role='dialog'] div._aano")
        if not scroll_container.is_visible():
            scroll_container = page.locator("div[role='dialog'] div[style*='overflow-y'], div[role='dialog'] div[style*='overflow: auto']").first
        if not scroll_container.is_visible():
            scroll_container = page.locator("div[role='dialog']").first
            
        users = []
        # Scroll up to 3 times to get enough followings
        for _ in range(3):
            scroll_container.evaluate("el => el.scrollTop = el.scrollHeight")
            time.sleep(1.5)
            users = page.evaluate("""() => {
                const results = [];
                const rows = document.querySelectorAll("div[role='dialog'] ul li, div[role='dialog'] [role='dialog'] li, div[role='dialog'] div[style*='flex-direction: column'] > div");
                for (let row of rows) {
                    const links = row.querySelectorAll("a");
                    if (links.length === 0) continue;
                    let username = "";
                    for (let l of links) {
                        const href = l.getAttribute("href");
                        if (href && href !== "/" && !href.includes("following") && !href.includes("followers")) {
                            username = href.replace(/\\//g, "").split("?")[0];
                            break;
                        }
                    }
                    if (username) results.push(username);
                }
                return Array.from(new Set(results));
            }""")
            if len(users) >= scan_depth_friends:
                break
        
        friends_list = users[:scan_depth_friends]
        yield f"Found {len(friends_list)} friends to audit: {', '.join('@' + f for f in friends_list)}"
        
        likes_intercepted = []
        comments_intercepted = []
        all_texts = []
        posts_audited_count = 0
        
        for friend in friends_list:
            yield f"Auditing @{friend}'s recent posts..."
            page.goto(f"https://www.instagram.com/{friend}/", timeout=60000)
            time.sleep(3)
            
            # Extract post links
            post_links = page.locator("a[href*='/p/'], a[href*='/reel/']").evaluate_all("""links => {
                return Array.from(new Set(links.map(l => l.href))).slice(0, 15);
            }""")
            
            post_urls = post_links[:scan_depth_posts]
            yield f"Found {len(post_urls)} posts on @{friend}'s profile. Inspecting..."
            
            for post_url in post_urls:
                posts_audited_count += 1
                page.goto(post_url, timeout=60000)
                time.sleep(2.5)
                
                # Retrieve caption
                desc = page.locator("meta[property='og:description']").get_attribute("content")
                if not desc:
                    desc = page.locator("meta[name='description']").get_attribute("content")
                caption = ""
                if desc:
                    match = re.search(r':\s*"(.*)"\s*\.?\s*$', desc, re.DOTALL)
                    if not match:
                        match = re.search(r":\s*'(.*)'\s*\.?\s*$", desc, re.DOTALL)
                    if match:
                        caption = match.group(1).strip()
                
                # Check for like
                liked = False
                like_container = page.locator("section:has-text('Liked by'), div:has-text('Liked by')")
                if like_container.count() > 0:
                    text = like_container.first.text_content() or ""
                    if target_username.lower() in text.lower():
                        liked = True
                
                if not liked:
                    link_count = page.locator(f"a[href='/{target_username}/']").count()
                    if link_count > 0:
                        liked = True
                        
                if liked:
                    likes_intercepted.append({
                        "url": post_url,
                        "username": friend,
                        "caption": caption
                    })
                    if caption:
                        all_texts.append(caption)
                    yield f"🎯 INTERCEPTED: @{target_username} liked @{friend}'s post: {post_url}"
                
                # Check for comment
                comments_found = page.evaluate("""(target) => {
                    const results = [];
                    const links = document.querySelectorAll("a[href='/" + target + "/']");
                    for (let link of links) {
                        const row = link.closest("ul li, div[class*='Comment'], div[class*='comment']");
                        if (row) {
                            const spans = row.querySelectorAll("span");
                            for (let span of spans) {
                                const txt = span.textContent.trim();
                                if (txt && !txt.includes(target) && txt.length > 1) {
                                    results.push(txt);
                                    break;
                                }
                            }
                        }
                    }
                    return results;
                }""", target_username)
                
                for comment_text in comments_found:
                    comments_intercepted.append({
                        "url": post_url,
                        "username": friend,
                        "caption": caption,
                        "text": comment_text
                    })
                    all_texts.append(comment_text)
                    yield f"💬 INTERCEPTED: @{target_username} commented on @{friend}'s post: \"{comment_text}\""
                    
        browser.close()
        
    yield {
        "target_username": target_username,
        "friends_scanned": len(friends_list),
        "posts_audited": posts_audited_count,
        "likes_intercepted": len(likes_intercepted),
        "comments_intercepted": len(comments_intercepted),
        "likes": likes_intercepted,
        "comments": comments_intercepted,
        "all_texts": all_texts
    }

def extract_username_from_url(url_or_username: str) -> str:
    """Extract Instagram username from URL or raw input."""
    text = url_or_username.strip().rstrip("/")
    if "instagram.com" in text:
        parts = text.split("instagram.com/")
        if len(parts) > 1:
            username = parts[1].split("/")[0].split("?")[0]
            return username.lstrip("@")
    return text.lstrip("@")

def parse_interaction_count(count_str: str) -> int:
    """Helper to convert likes/comments strings like 1,234 or 10.5K or 1.2M to integers."""
    if not count_str:
        return 0
    count_str = count_str.upper().replace(",", "").replace(" ", "")
    try:
        if "K" in count_str:
            return int(float(count_str.replace("K", "")) * 1000)
        if "M" in count_str:
            return int(float(count_str.replace("M", "")) * 1000000)
        return int(float(count_str))
    except ValueError:
        return 0
