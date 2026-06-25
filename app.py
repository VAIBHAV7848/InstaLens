"""
Instagram Profile Topic Analyzer — Flask Web App

Main entry point. Serves the web UI and handles analysis requests.
Supports both automatic profile scraping and manual text input.
"""

import os
import tempfile
import urllib.request

from flask import Flask, render_template, request, jsonify, session, Response, stream_with_context

from analyzer.preprocessor import preprocess_multiple
from analyzer.ocr_engine import extract_text_from_multiple, is_tesseract_available
from analyzer.topic_analyzer import analyze
from analyzer.report_generator import generate_report
from analyzer.scraper import scrape_profile, extract_username_from_url, create_loader, spy_target_activity
from analyzer.taxonomy_manager import load_taxonomy, save_taxonomy
from analyzer.matchmaker import calculate_compatibility
from analyzer.cleaner import fetch_connections, unfollow_user, remove_follower
import json

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max upload
app.secret_key = "instalens_secure_session_key_123"  # Secret key for session signing

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp", "gif"}


def allowed_file(filename: str) -> bool:
    """Check if uploaded file has an allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def run_analysis(all_texts: list[str], profile_info=None, source="posts", ocr_count=0):
    """
    Run the analysis pipeline on the input texts.

    Args:
        all_texts: List of clean caption or text strings
        profile_info: Dict containing Instagram profile metadata
        source: Content source type (posts/reposts/following)

    Returns:
        JSON-serializable report dict
    """
    preprocessed = preprocess_multiple(all_texts)

    analysis = analyze(
        tokens=preprocessed["all_tokens"],
        hashtags=preprocessed["all_hashtags"],
        clean_texts=preprocessed["clean_texts"],
        entities=preprocessed["all_entities"],
    )

    report = generate_report(analysis, source=source, profile_info=profile_info)

    report["input_stats"] = {
        "text_chunks": len(all_texts),
        "screenshots_processed": ocr_count,
        "total_tokens": len(preprocessed["all_tokens"]),
        "total_hashtags": len(preprocessed["all_hashtags"]),
    }

    if profile_info:
        report["profile_info"] = {
            "name": profile_info.get("profile_name", ""),
            "bio": profile_info.get("bio", ""),
            "followers": profile_info.get("followers", 0),
            "following": profile_info.get("following", 0),
            "post_count": profile_info.get("post_count", 0),
            "scraped_posts": profile_info.get("scraped_posts", 0),
        }

    return report


@app.route("/")
def index():
    """Serve the main page."""
    tesseract_available = is_tesseract_available()
    return render_template("index.html", tesseract_available=tesseract_available)


@app.route("/session", methods=["GET"])
def get_session():
    """Get the current session authentication status."""
    username = session.get("instagram_user")
    return jsonify({
        "logged_in": username is not None,
        "username": username
    })


@app.route("/login", methods=["POST"])
def login():
    """Log in to Instagram and save the session cache."""
    try:
        data = request.get_json() or {}
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()

        if not username or not password:
            return jsonify({"error": "Please enter both your Instagram username and password."}), 400

        # Try to authenticate and create session
        create_loader(username, password)
        session["instagram_user"] = username
        return jsonify({"success": True, "username": username})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 401


@app.route("/logout", methods=["POST"])
def logout():
    """Log out and clear session."""
    session.pop("instagram_user", None)
    return jsonify({"success": True})


@app.route("/analyze", methods=["POST"])
def analyze_profile():
    """
    Handle analysis requests.
    """
    try:
        content_type = request.content_type or ""

        # --- AUTO MODE (JSON) ---
        if "application/json" in content_type:
            data = request.get_json()
            mode = data.get("mode", "auto")

            if mode == "auto":
                target = data.get("target_profile", "").strip()
                max_posts = int(data.get("max_posts", 30))
                source = data.get("source", "posts").strip().lower()

                login_user = session.get("instagram_user")
                if not login_user:
                    return jsonify({"error": "Please log in first to use Auto Scrape."}), 401

                if not target:
                    return jsonify({"error": "Please enter a target profile URL or username."}), 400

                # Extract username from URL
                target_username = extract_username_from_url(target)

                # Scrape profile using session cache (no password needed)
                profile_generator = scrape_profile(
                    target_username=target_username,
                    login_username=login_user,
                    login_password=None,
                    max_posts=max_posts,
                    source=source,
                )
                
                profile_data = None
                for item in profile_generator:
                    if isinstance(item, dict):
                        profile_data = item
                        
                if not profile_data:
                    return jsonify({"error": "No profile data scraped."}), 500

                all_texts = profile_data["captions"]

                # Run analysis
                report = run_analysis(all_texts, profile_info=profile_data, source=source)
                return jsonify(report)

        # --- MANUAL MODE (form data) ---
        all_texts = []
        ocr_count = 0

        # 1. Get pasted text
        raw_text = request.form.get("text", "").strip()
        if raw_text:
            chunks = [c.strip() for c in raw_text.split("\n\n") if c.strip()]
            if not chunks:
                chunks = [raw_text]
            all_texts.extend(chunks)

        # 2. Process uploaded screenshots (OCR)
        if "screenshots" in request.files:
            files = request.files.getlist("screenshots")
            temp_paths = []

            for f in files:
                if f and f.filename and allowed_file(f.filename):
                    ext = f.filename.rsplit(".", 1)[1].lower()
                    tmp = tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False)
                    f.save(tmp.name)
                    temp_paths.append(tmp.name)

            if temp_paths:
                ocr_texts = extract_text_from_multiple(temp_paths)
                all_texts.extend(ocr_texts)
                ocr_count = len(ocr_texts)

                for path in temp_paths:
                    try:
                        os.unlink(path)
                    except OSError:
                        pass

        if not all_texts:
            return jsonify({
                "error": "No input provided. Please paste some captions or upload screenshots."
            }), 400

        report = run_analysis(all_texts, ocr_count=ocr_count)
        return jsonify(report)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/ocr_extract", methods=["POST"])
def ocr_extract():
    """Extract text from uploaded screenshots using Tesseract OCR, returning the raw text string."""
    try:
        if "screenshots" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        
        files = request.files.getlist("screenshots")
        temp_paths = []
        for f in files:
            if f and f.filename and allowed_file(f.filename):
                ext = f.filename.rsplit(".", 1)[1].lower()
                tmp = tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False)
                f.save(tmp.name)
                temp_paths.append(tmp.name)
        
        if not temp_paths:
            return jsonify({"error": "No valid image files provided"}), 400
        
        ocr_texts = extract_text_from_multiple(temp_paths)
        
        # clean up temp files
        for path in temp_paths:
            try:
                os.unlink(path)
            except OSError:
                pass
                
        combined_text = "\n\n".join(ocr_texts)
        return jsonify({"success": True, "text": combined_text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/analyze_stream", methods=["POST"])
def analyze_stream():
    """Analyze a profile using a Server-Sent Events stream for live progress updates."""
    target = request.form.get("target", "").strip()
    login_user = request.form.get("login_username", "").strip()
    login_pass = request.form.get("login_password", "").strip() or None
    max_posts = int(request.form.get("max_posts", 30))
    source = request.form.get("source", "posts")
    
    if not target:
        return jsonify({"error": "Target is required."}), 400
    if not login_user:
        return jsonify({"error": "Login Username is required."}), 400

    target_username = extract_username_from_url(target)

    def generate():
        try:
            import json
            yield f"data: {json.dumps({'status': 'Initializing scraper context...'})}\n\n"
            
            profile_data = None
            profile_generator = scrape_profile(
                target_username=target_username,
                login_username=login_user,
                login_password=login_pass,
                max_posts=max_posts,
                source=source,
            )
            
            for item in profile_generator:
                if isinstance(item, str):
                    yield f"data: {json.dumps({'status': item})}\n\n"
                elif isinstance(item, dict):
                    profile_data = item

            if not profile_data:
                yield f"data: {json.dumps({'error': 'No profile data scraped.'})}\n\n"
                return

            yield f"data: {json.dumps({'status': 'Running NLP Analysis & Topic Classification...'})}\n\n"
            
            # Run analysis pipeline
            report = run_analysis(profile_data["captions"], profile_info=profile_data, source=source)
            yield f"data: {json.dumps({'report': report})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@app.route("/spy_stream", methods=["POST"])
def spy_stream():
    """Spy on a target's engagements via SSE stream."""
    target = request.form.get("target", "").strip()
    login_user = request.form.get("login_username", "").strip()
    login_pass = request.form.get("login_password", "").strip() or None
    friends_count = int(request.form.get("friends_count", 5))
    posts_count = int(request.form.get("posts_count", 5))
    
    if not target:
        return jsonify({"error": "Target is required."}), 400
    if not login_user:
        return jsonify({"error": "Login Username is required."}), 400

    target_username = extract_username_from_url(target)

    def generate():
        try:
            import json
            yield f"data: {json.dumps({'status': 'Initializing Activity Spy context...'})}\n\n"
            
            spy_data = None
            spy_generator = spy_target_activity(
                target_username=target_username,
                login_username=login_user,
                login_password=login_pass,
                scan_depth_friends=friends_count,
                scan_depth_posts=posts_count,
            )
            
            for item in spy_generator:
                if isinstance(item, str):
                    yield f"data: {json.dumps({'status': item})}\n\n"
                elif isinstance(item, dict):
                    spy_data = item

            if not spy_data:
                yield f"data: {json.dumps({'error': 'No activity spy data scraped.'})}\n\n"
                return

            yield f"data: {json.dumps({'status': 'Analyzing Shadow Interests & Interactions...'})}\n\n"
            
            texts = spy_data["all_texts"]
            if not texts:
                texts = [f"No direct interactions captured on recent posts of followed friends for @{target_username}."]
                
            report = run_analysis(texts, profile_info=None, source="posts")
            
            report["is_spy"] = True
            report["spy_data"] = {
                "friends_scanned": spy_data["friends_scanned"],
                "posts_audited": spy_data["posts_audited"],
                "likes_intercepted": spy_data["likes_intercepted"],
                "comments_intercepted": spy_data["comments_intercepted"],
                "likes": spy_data["likes"],
                "comments": spy_data["comments"]
            }
            
            yield f"data: {json.dumps({'report': report})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@app.route("/api/taxonomy", methods=["GET"])
def get_taxonomy_api():
    """Get the active interest taxonomy."""
    return jsonify(load_taxonomy())


@app.route("/api/taxonomy", methods=["POST"])
def save_taxonomy_api():
    """Save the edited taxonomy."""
    new_taxonomy = request.json
    if not isinstance(new_taxonomy, dict):
        return jsonify({"error": "Invalid taxonomy format."}), 400
    if save_taxonomy(new_taxonomy):
        return jsonify({"success": True})
    return jsonify({"error": "Failed to save taxonomy."}), 500


@app.route("/api/export_cli_script", methods=["GET"])
def export_cli_script():
    """Generate a cookie-injected standalone Kali Linux CLI Python scraper script."""
    username = session.get("instagram_user")
    if not username:
        return jsonify({"error": "Please log in first to export the authenticated CLI script."}), 401
    
    session_file = f"playwright_session_{username}.json"
    import os
    if not os.path.exists(session_file):
        return jsonify({"error": "Session state file not found. Please log in again."}), 404
        
    with open(session_file, "r") as f:
        session_data = f.read()

    # Standalone CLI python script template
    cli_template = f"""#!/usr/bin/env python3
import sys
import os
import re
import json
import time

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("[InstaLens CLI] Playwright not found! Installing requirements...")
    os.system("pip3 install playwright")
    os.system("playwright install chromium")
    from playwright.sync_api import sync_playwright

SESSION_STATE = {session_data}

def run_scraper(target_username, max_posts=10):
    print(f"[InstaLens CLI] Initializing scrape for @{{target_username}} (Authenticated as @{username})...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        )
        context.add_cookies(SESSION_STATE.get("cookies", []))
        
        page = context.new_page()
        print(f"[InstaLens CLI] Navigating to profile...")
        page.goto(f"https://www.instagram.com/{{target_username}}/", timeout=60000)
        time.sleep(5)
        
        if "Page Not Found" in page.title() or page.query_selector("text=isn't available"):
            print(f"[Error] Profile @{{target_username}} is private or does not exist.")
            browser.close()
            return
            
        print("[InstaLens CLI] Scraping profile feed links...")
        links = page.query_selector_all("a[href*='/p/'], a[href*='/reel/']")
        post_urls = []
        for l in links:
            href = l.get_attribute("href")
            if href and ("/p/" in href or "/reel/" in href):
                full_url = f"https://www.instagram.com{{href}}"
                if full_url not in post_urls:
                    post_urls.append(full_url)
                    
        total = min(len(post_urls), max_posts)
        print(f"[InstaLens CLI] Found {{len(post_urls)}} posts. Scraping top {{total}} captions...")
        
        captions = []
        for i, url in enumerate(post_urls[:total]):
            print(f"  [{{i+1}}/{{total}}] Scraping: {{url}}")
            page.goto(url, timeout=60000)
            time.sleep(3)
            
            desc = page.locator("meta[property='og:description']").get_attribute("content")
            if not desc:
                desc = page.locator("meta[name='description']").get_attribute("content")
            
            if desc:
                match = re.search(r':\s*"(.*)"\s*\\.?\s*$', desc, re.DOTALL)
                if not match:
                    match = re.search(r":\s*'(.*)'\s*\\.?\s*$", desc, re.DOTALL)
                if match:
                    captions.append(match.group(1).strip())
                else:
                    parts = desc.split("on Instagram: ")
                    if len(parts) > 1:
                        captions.append(parts[1].strip())
                        
        print("\\n" + "="*50)
        print(f" SCRAPED DATA SUMMARY FOR @{{target_username}}")
        print("="*50)
        print(f"Total Captions Extracted: {{len(captions)}}")
        for idx, cap in enumerate(captions):
            print(f"\\nPost {{idx+1}}:")
            print(f"  {{cap[:120]}}...")
        print("="*50)
        browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 instalens_cli.py <instagram_username> [max_posts]")
        sys.exit(1)
    target = sys.argv[1].replace("@", "")
    posts = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    run_scraper(target, posts)
"""
    return Response(
        cli_template,
        mimetype="text/plain",
        headers={"Content-Disposition": "attachment;filename=instalens_cli.py"}
    )


@app.route("/match_stream", methods=["POST"])
def match_stream():
    """Stream matchmaking calculation steps and results using SSE."""
    profile_a_source = request.form.get("profile_a_source", "text").strip().lower()
    profile_a_val = request.form.get("profile_a_val", "").strip()
    profile_b_source = request.form.get("profile_b_source", "text").strip().lower()
    profile_b_val = request.form.get("profile_b_val", "").strip()

    login_user = request.form.get("login_username", "").strip()
    login_pass = request.form.get("login_password", "").strip() or None
    max_posts = int(request.form.get("max_posts", 15))

    if not profile_a_val or not profile_b_val:
        return jsonify({"error": "Both inputs for Profile A and Profile B are required."}), 400

    def generate():
        import json
        try:
            yield f"data: {json.dumps({'status': 'Initializing Matchmaker workspace...'})}\n\n"

            def analyze_profile_source(source_type, val, label):
                if source_type == "scrape":
                    if not login_user:
                        raise Exception(f"Instagram session needed to scrape target {label}.")
                    yield f"data: {json.dumps({'status': f'Spawning browser for {label} (@{val})...'})}\n\n"
                    target_username = extract_username_from_url(val)
                    profile_generator = scrape_profile(
                        target_username=target_username,
                        login_username=login_user,
                        login_password=login_pass,
                        max_posts=max_posts,
                        source="posts",
                    )
                    profile_data = None
                    for item in profile_generator:
                        if isinstance(item, str):
                            yield f"data: {json.dumps({'status': f'[{label}] {item}'})}\n\n"
                        elif isinstance(item, dict):
                            profile_data = item
                    if not profile_data:
                        raise Exception(f"Failed to scrape profile for {label}.")
                    yield f"data: {json.dumps({'status': f'Analyzing scraped captions for {label}...'})}\n\n"
                    return run_analysis(profile_data["captions"], profile_info=profile_data, source="posts")
                else:
                    yield f"data: {json.dumps({'status': f'Processing manual text input for {label}...'})}\n\n"
                    chunks = [c.strip() for c in val.split("\n\n") if c.strip()]
                    if not chunks:
                        chunks = [val]
                    return run_analysis(chunks)

            # 1. Analyze Profile A
            gen_a = analyze_profile_source(profile_a_source, profile_a_val, "Profile A")
            report_a = None
            try:
                while True:
                    yield next(gen_a)
            except StopIteration as e:
                report_a = e.value

            # 2. Analyze Profile B
            gen_b = analyze_profile_source(profile_b_source, profile_b_val, "Profile B")
            report_b = None
            try:
                while True:
                    yield next(gen_b)
            except StopIteration as e:
                report_b = e.value

            yield f"data: {json.dumps({'status': 'Running Cosine & Jaccard compatibility matrices...'})}\n\n"
            
            # 3. Compute Compatibility Match
            match_report = calculate_compatibility(report_a, report_b)
            
            # Add labels to reports for rendering
            match_report["is_match"] = True
            match_report["profile_a_label"] = f"@{extract_username_from_url(profile_a_val)}" if profile_a_source == "scrape" else "Profile A (Text)"
            match_report["profile_b_label"] = f"@{extract_username_from_url(profile_b_val)}" if profile_b_source == "scrape" else "Profile B (Text)"
            
            yield f"data: {json.dumps({'report': match_report})}\n\n"

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@app.route("/api/clean_account/fetch", methods=["POST"])
def clean_account_fetch():
    """Stream fetching of followers/following lists."""
    login_user = session.get("instagram_user")
    connection_type = request.form.get("type", "following").strip()
    
    if not login_user:
        return jsonify({"error": "Not logged in."}), 401
        
    def generate():
        try:
            for item in fetch_connections(login_user, connection_type=connection_type):
                yield f"data: {json.dumps(item)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@app.route("/api/clean_account/unfollow", methods=["POST"])
def clean_account_unfollow():
    login_user = session.get("instagram_user")
    if not login_user:
        return jsonify({"error": "Not logged in."}), 401
        
    data = request.get_json() or {}
    target = data.get("target")
    if not target:
        return jsonify({"error": "Missing target."}), 400
        
    try:
        success = unfollow_user(target, login_user)
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/clean_account/remove_follower", methods=["POST"])
def clean_account_remove_follower():
    """Remove a follower from your account."""
    login_user = session.get("instagram_user")
    if not login_user:
        return jsonify({"error": "Not logged in."}), 401

    data = request.get_json() or {}
    target = data.get("target")
    if not target:
        return jsonify({"error": "Missing target."}), 400

    try:
        success = remove_follower(target, login_user)
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/clean_account/whitelist", methods=["GET", "POST"])
def clean_account_whitelist():
    login_user = session.get("instagram_user")
    if not login_user:
        return jsonify({"error": "Not logged in."}), 401
        
    whitelist_file = f"whitelist_{login_user}.json"
    
    if request.method == "GET":
        if os.path.exists(whitelist_file):
            with open(whitelist_file, "r") as f:
                return jsonify(json.load(f))
        return jsonify([])
    else:
        data = request.get_json() or []
        with open(whitelist_file, "w") as f:
            json.dump(data, f)
        return jsonify({"success": True})


ALLOWED_IMAGE_DOMAINS = (
    "cdninstagram.com",
    "fbcdn.net",
    "instagram.com",
)


@app.route("/api/proxy_image")
def proxy_image():
    """Proxy Instagram CDN images to bypass CORS/CORP restrictions."""
    url = request.args.get("url", "")
    if not url:
        return "", 404

    # Security: only proxy known Instagram CDN domains
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if not any(parsed.hostname and parsed.hostname.endswith(d) for d in ALLOWED_IMAGE_DOMAINS):
        return jsonify({"error": "Domain not allowed"}), 403

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.instagram.com/",
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            img_data = resp.read()
            content_type = resp.headers.get("Content-Type", "image/jpeg")
            return Response(
                img_data,
                content_type=content_type,
                headers={"Cache-Control": "public, max-age=86400"}  # Cache 24h
            )
    except Exception:
        return "", 502


if __name__ == "__main__":
    print("\n🔍 Instagram Profile Topic Analyzer")
    print("=" * 42)
    print(f"📡 Server running at http://localhost:5000")
    print(f"🖼️  Tesseract OCR: {'Available ✓' if is_tesseract_available() else 'Not found ✗'}")
    print("=" * 42 + "\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
