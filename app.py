"""
Instagram Profile Topic Analyzer — Flask Web App

Main entry point. Serves the web UI and handles analysis requests.
Supports both automatic profile scraping and manual text input.
"""

import os
import tempfile

from flask import Flask, render_template, request, jsonify, session

from analyzer.preprocessor import preprocess_multiple
from analyzer.ocr_engine import extract_text_from_multiple, is_tesseract_available
from analyzer.topic_analyzer import analyze
from analyzer.report_generator import generate_report
from analyzer.scraper import scrape_profile, extract_username_from_url, create_loader

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max upload
app.secret_key = "instalens_secure_session_key_123"  # Secret key for session signing

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp", "gif"}


def allowed_file(filename: str) -> bool:
    """Check if uploaded file has an allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def run_analysis(all_texts: list[str], ocr_count: int = 0, profile_info: dict = None) -> dict:
    """
    Run the full NLP analysis pipeline on collected texts.

    Args:
        all_texts: All text chunks to analyze
        ocr_count: Number of texts from OCR
        profile_info: Optional profile metadata from scraper

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

    report = generate_report(analysis)

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
                profile_data = scrape_profile(
                    target_username=target_username,
                    login_username=login_user,
                    login_password=None,
                    max_posts=max_posts,
                    source=source,
                )

                all_texts = profile_data["captions"]

                # Run analysis
                report = run_analysis(all_texts, profile_info=profile_data)
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


if __name__ == "__main__":
    print("\n🔍 Instagram Profile Topic Analyzer")
    print("=" * 42)
    print(f"📡 Server running at http://localhost:5000")
    print(f"🖼️  Tesseract OCR: {'Available ✓' if is_tesseract_available() else 'Not found ✗'}")
    print("=" * 42 + "\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
