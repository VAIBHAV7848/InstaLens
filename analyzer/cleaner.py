import os
import time
from playwright.sync_api import sync_playwright
from analyzer.scraper import login_with_playwright

def fetch_connections(login_username, login_password=None, connection_type="following"):
    """Fetch either 'following' or 'followers' for the logged-in user."""
    session_file = f"playwright_session_{login_username}.json"
    
    if not os.path.exists(session_file):
        if login_password:
            yield {"status": "No active session found. Re-authenticating..."}
            login_with_playwright(login_username, login_password)
        else:
            raise Exception("No active session found. Please log in first.")

    yield {"status": f"Launching headless browser to fetch {connection_type}..."}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            storage_state=session_file,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        yield {"status": f"Opening profile..."}
        page.goto(f"https://www.instagram.com/{login_username}/", timeout=60000)
        time.sleep(5)
        
        if "accounts/login" in page.url or page.query_selector("a[href*='/accounts/login']"):
            browser.close()
            raise Exception("Instagram session expired or invalid. Please log out and log in again.")

        # Extract expected count from profile header for validation
        expected_count = 0
        try:
            count_text = page.evaluate(f"""() => {{
                const links = document.querySelectorAll('a[href*="/{login_username}/{connection_type}/"]');
                for (let l of links) {{
                    const spans = l.querySelectorAll('span');
                    for (let s of spans) {{
                        const t = s.textContent.trim().replace(/,/g, '');
                        if (/^\\d+$/.test(t)) return parseInt(t);
                    }}
                    const t = l.textContent.trim().replace(/,/g, '');
                    const m = t.match(/(\\d+)/);
                    if (m) return parseInt(m[1]);
                }}
                return 0;
            }}""")
            expected_count = int(count_text) if count_text else 0
        except Exception:
            pass
            
        yield {"status": f"Opening {connection_type} list (expects ~{expected_count})..."}
        
        # Click the following/followers link
        link = page.locator(f"a[href*='/{login_username}/{connection_type}/']")
        if not link.is_visible():
            link = page.locator(f"a:has-text('{connection_type}')")
            
        if link.is_visible():
            link.click()
        else:
            try:
                page.click(f"text={connection_type}")
            except:
                page.click(f"a[href$='/{connection_type}/']")
                
        dialog_selector = "div[role='dialog']"
        try:
            page.wait_for_selector(dialog_selector, timeout=15000)
        except Exception:
            browser.close()
            raise Exception(f"Could not open {connection_type} list.")
            
        time.sleep(3)
        
        # Find scrollable container — try multiple selectors from most to least specific
        scroll_container = None
        scroll_selectors = [
            "div[role='dialog'] div._aano",                              # Instagram's known class
            "div[role='dialog'] div[style*='overflow: hidden auto']",    # Common overflow pattern
            "div[role='dialog'] div[style*='overflow-y: auto']",         # Standard scrollable
            "div[role='dialog'] div[style*='overflow-y: scroll']",       # Scroll variant
            "div[role='dialog'] div[style*='overflow: auto']",           # Generic auto
            "div[role='dialog'] ul",                                     # Direct list container
        ]
        
        for sel in scroll_selectors:
            try:
                candidate = page.locator(sel).first
                if candidate.is_visible():
                    scroll_container = candidate
                    break
            except Exception:
                continue
        
        if not scroll_container:
            # Last resort: find the deepest scrollable div inside the dialog via JS
            scroll_container_handle = page.evaluate_handle("""() => {
                const dialog = document.querySelector("div[role='dialog']");
                if (!dialog) return null;
                const divs = dialog.querySelectorAll('div');
                let best = null;
                let bestHeight = 0;
                for (let d of divs) {
                    if (d.scrollHeight > d.clientHeight && d.clientHeight > 100) {
                        if (d.scrollHeight > bestHeight) {
                            bestHeight = d.scrollHeight;
                            best = d;
                        }
                    }
                }
                return best || dialog;
            }""")
            scroll_container = scroll_container_handle.as_element()
            
        # Fallback to dialog itself
        if not scroll_container:
            scroll_container = page.locator("div[role='dialog']").first

        all_users = {}
        last_count = 0
        no_change_count = 0
        
        # Username extraction JS — robust version
        extraction_js = r"""() => {
            const dialog = document.querySelector("div[role='dialog']");
            if (!dialog) return [];
            
            const scrollable = dialog.querySelector('div[style*="overflow: hidden auto"]') || 
                               dialog.querySelector('div[style*="overflow-y: auto"]') ||
                               dialog.querySelector('div[style*="overflow-y: scroll"]') ||
                               dialog.querySelector('div._aano');
            if (!scrollable) return [];
            
            const rowContainer = scrollable.firstElementChild;
            if (!rowContainer) return [];
            
            const rows = Array.from(rowContainer.children);
            const results = [];
            
            for (let row of rows) {
                const links = Array.from(row.querySelectorAll("a"));
                if (links.length === 0) continue;
                
                let username = "";
                let avatar = "";
                let verified = false;
                let fullName = "";
                
                for (let l of links) {
                    const href = l.getAttribute("href");
                    if (!href) continue;
                    const parts = href.split('/').filter(Boolean);
                    if (parts.length === 1 && !['explore', 'reels', 'p', 'direct', 'emails'].includes(parts[0])) {
                        username = parts[0];
                        const img = l.querySelector("img");
                        if (img) avatar = img.src || "";
                    }
                }
                
                if (!username) continue;
                
                if (row.querySelector('svg[aria-label="Verified"]') || row.querySelector('[title="Verified"]')) {
                    verified = true;
                }
                
                const spans = Array.from(row.querySelectorAll("span"));
                for (let s of spans) {
                    const txt = s.textContent.trim();
                    if (txt && txt !== username && txt.length < 50 
                        && txt !== "Remove" && txt !== "Following" && txt !== "Follow" && txt !== "Requested"
                        && !txt.includes("•") && !/^\d+$/.test(txt)) {
                        fullName = txt;
                        break;
                    }
                }
                
                results.push({ username, fullName, avatar, verified });
            }
            return results;
        }"""
        
        for scroll_num in range(300):  # Allow more scrolls for large accounts
            # Scroll to bottom using all scrollable containers in the dialog
            try:
                page.evaluate("""() => {
                    const dialog = document.querySelector("div[role='dialog']");
                    if (!dialog) return;
                    const divs = dialog.querySelectorAll('div');
                    for (let d of divs) {
                        if (d.scrollHeight > d.clientHeight) {
                            d.scrollTop = d.scrollHeight;
                            d.dispatchEvent(new Event('scroll', { bubbles: true }));
                        }
                    }
                }""")
            except Exception:
                try:
                    if scroll_container:
                        scroll_container.evaluate("el => el.scrollTop = el.scrollHeight")
                except:
                    pass
            
            time.sleep(3)  # Patient wait for lazy loading
            
            chunk = page.evaluate(extraction_js)
            
            for u in chunk:
                all_users[u["username"]] = u
            
            pct = f" ({(len(all_users)/expected_count*100):.0f}%)" if expected_count > 0 else ""
            yield {"status": f"Scrolling {connection_type} list — Loaded {len(all_users)}{pct}..."}
            
            if len(all_users) == last_count:
                no_change_count += 1
                if no_change_count >= 5:  # More patient: 5 retries * 2s = 10s of no new data
                    break
            else:
                no_change_count = 0
            last_count = len(all_users)
            
            # Early exit if we've reached expected count
            if expected_count > 0 and len(all_users) >= expected_count:
                break
            
        browser.close()

    completeness = ""
    if expected_count > 0:
        completeness = f" (Expected: {expected_count}, Got: {len(all_users)})"
    yield {"status": f"Finished fetching {connection_type}: {len(all_users)} accounts{completeness}"}
    yield {"result": list(all_users.values()), "type": connection_type}


def unfollow_user(target_username, login_username):
    """Unfollow a specific user."""
    session_file = f"playwright_session_{login_username}.json"
    
    if not os.path.exists(session_file):
        raise Exception("No active session found. Please log in first.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            storage_state=session_file,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        page.goto(f"https://www.instagram.com/{target_username}/", timeout=60000)
        time.sleep(3)
        
        if "accounts/login" in page.url:
            browser.close()
            raise Exception("Session expired.")
            
        if "Page Not Found" in page.title() or page.query_selector("text=isn't available"):
            browser.close()
            raise Exception("User not found.")
            
        # Click Following button
        button = page.locator("button", has_text="Following").first
        if button.is_visible():
            button.click()
            time.sleep(1)
            # Confirm unfollow
            unfollow_btn = page.locator("div[role='dialog'] button:has-text('Unfollow')").first
            if not unfollow_btn.is_visible():
                unfollow_btn = page.locator("button:has-text('Unfollow')").first
                
            if unfollow_btn.is_visible():
                unfollow_btn.click()
                time.sleep(2)
                browser.close()
                return True
            else:
                browser.close()
                raise Exception("Unfollow confirmation button not found.")
        else:
            browser.close()
            raise Exception("Following button not found. You might not be following this user.")


def remove_follower(target_username, login_username):
    """Remove a follower from your account by visiting their profile and using the three-dot menu."""
    session_file = f"playwright_session_{login_username}.json"

    if not os.path.exists(session_file):
        raise Exception("No active session found. Please log in first.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            storage_state=session_file,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        page.goto(f"https://www.instagram.com/{target_username}/", timeout=60000)
        time.sleep(3)

        if "accounts/login" in page.url:
            browser.close()
            raise Exception("Session expired.")

        if "Page Not Found" in page.title() or page.query_selector("text=isn't available"):
            browser.close()
            raise Exception("User not found.")

        # Click the three-dot (⋯) menu button on the profile
        menu_btn = page.locator("div[role='button'] svg[aria-label='Options']").first
        if not menu_btn.is_visible():
            menu_btn = page.locator("button svg[aria-label='Options']").first
        if not menu_btn.is_visible():
            # Fallback: look for the ellipsis/three-dot button near the top of the profile
            menu_btn = page.locator("[aria-label='Options']").first

        if menu_btn.is_visible():
            menu_btn.click()
            time.sleep(1.5)

            # Click "Remove follower" from the dropdown/dialog menu
            remove_btn = page.locator("button:has-text('Remove follower')").first
            if not remove_btn.is_visible():
                remove_btn = page.locator("div[role='dialog'] button:has-text('Remove')").first

            if remove_btn.is_visible():
                remove_btn.click()
                time.sleep(2)
                browser.close()
                return True
            else:
                browser.close()
                raise Exception("'Remove follower' option not found in menu. They may not be following you.")
        else:
            browser.close()
            raise Exception("Options menu button not found on profile page.")

