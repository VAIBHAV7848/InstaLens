import sys
import time
from playwright.sync_api import sync_playwright

def test_scrape():
    username = "vibezforyou999"
    password = "VAIBHAV2667"
    target = "omganesh_014"

    print("Launching browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print("Navigating to login page...")
        try:
            page.goto("https://www.instagram.com/accounts/login/", timeout=60000)
            time.sleep(5)
            
            # Detect selectors
            if page.query_selector("input[name='username']"):
                page.fill("input[name='username']", username)
                page.fill("input[name='password']", password)
                page.click("button[type='submit']")
            elif page.query_selector("input[name='email']"):
                page.fill("input[name='email']", username)
                page.fill("input[name='pass']", password)
                
                # Click visible login button
                buttons = page.query_selector_all("button, input[type='submit'], [role='button']")
                for btn in buttons:
                    if btn.is_visible():
                        txt = (btn.text_content() or btn.get_attribute("value") or "").strip()
                        if "log in" in txt.lower():
                            btn.click()
                            break
            
            print("Login submitted. Waiting for redirection...")
            time.sleep(12)
            
            print("Navigating to target profile:", target)
            page.goto(f"https://www.instagram.com/{target}/", timeout=60000)
            time.sleep(5)
            
            # Find posts and reels links
            links = page.query_selector_all("a[href*='/p/'], a[href*='/reel/']")
            print(f"Found {len(links)} post/reel links.")
            
            post_urls = []
            for l in links:
                href = l.get_attribute("href")
                if href and ("/p/" in href or "/reel/" in href):
                    full_url = f"https://www.instagram.com{href}"
                    if full_url not in post_urls:
                        post_urls.append(full_url)
            
            print(f"Unique post URLs: {post_urls}")
            
            # Test extracting caption of the first 3 posts using meta description
            for url in post_urls[:3]:
                print(f"Loading post: {url}")
                page.goto(url, timeout=60000)
                time.sleep(3)
                
                # Extract meta description
                meta_desc = page.locator("meta[property='og:description']").get_attribute("content")
                if not meta_desc:
                    meta_desc = page.locator("meta[name='description']").get_attribute("content")
                
                print(f"Meta Description: '{meta_desc}'")
                
                # If meta description looks like:
                # "omganesh_014 on Instagram: 'Same problems, new location'" or
                # "omganesh_014 (@omganesh_014) on Instagram: 'Same problems...'"
                # We can extract the text inside the quotes!
                if meta_desc and "on Instagram: \"" in meta_desc:
                    parts = meta_desc.split("on Instagram: \"")
                    if len(parts) > 1:
                        caption = parts[1].rstrip("\"")
                        print(f"-> Extracted caption: '{caption}'")
                elif meta_desc and "on Instagram: '" in meta_desc:
                    parts = meta_desc.split("on Instagram: '")
                    if len(parts) > 1:
                        caption = parts[1].rstrip("'")
                        print(f"-> Extracted caption: '{caption}'")
                else:
                    print(f"-> Could not parse caption format from: {meta_desc}")
                
        except Exception as e:
            print("Exception occurred:", e)
        
        browser.close()

if __name__ == "__main__":
    test_scrape()
