# 🔍 InstaLens — Instagram Profile Topic & Interest Analyzer

<p align="center">
  <img src="https://img.shields.io/github/license/VAIBHAV7848/-InstaLens?style=for-the-badge&color=a855f7" alt="License">
  <img src="https://img.shields.io/github/stars/VAIBHAV7848/-InstaLens?style=for-the-badge&color=06b6d4" alt="Stars">
  <img src="https://img.shields.io/github/forks/VAIBHAV7848/-InstaLens?style=for-the-badge&color=ec4899" alt="Forks">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python Version">
</p>

InstaLens is a premium, developer-friendly Instagram OSINT & content analysis tool. It automatically fetches profile details, posts, reels, and reposts, processes screenshots using OCR, and applies token-based NLP analysis to categorize interests, predict partner compatibility, and suggest conversation icebreakers.

---

## ✨ Key Features

*   🤖 **Dual Scraping Modes**:
    *   **Auto Scrape**: Automated Playwright browser crawler to scrape target profiles, post grids, reels, or the **Reposts** section.
    *   **Manual Input**: Drag-and-drop screenshots or paste raw text.
*   🕵️ **Activity Spy**: Live tracking and real-time monitoring of targets (extracting liked posts, liked reels, and activity timelines).
*   💖 **Dating & Partner Matchmaker**:
    *   Calculates partner compatibility between two profiles (Scraped profile vs Scraped profile, Scraped vs Manual paste, or Manual text blocks).
    *   Executes **Cosine Similarity** over topic vectors, **Jaccard Similarity** over hashtag sets, determines a compatibility tier, and prints a customized narrative description.
    *   Renders shared and unique interests in Venn-diagram chips alongside custom bridge icebreakers.
*   🌐 **Deep Profile Wide Matching**:
    *   **Bio Injection**: Public profile biographies are prepended as the first caption for rich NLP interest extraction.
    *   **Reposts & Tagged Tab Fallbacks**: If a profile has fewer posts than the scraping limit, the system automatically crawls their **Reposts** (`/reposts/`) and **Tagged** (`/tagged/`) posts tabs.
    *   **Zero-Post Fallback**: If a profile has no posts, tagged posts, or biography, the engine falls back to metadata counts (followers/following) to prevent analysis exceptions.
*   🖼️ **Tesseract OCR Integration**: Instantly extract text and captions from uploaded images or screenshot logs.
*   🧠 **Token-Based NLP Taxonomy**: Pre-configured taxonomy with high-precision classification models covering dozens of popular categories (e.g., Tech, Gaming, Fitness, Travel, Finance).
*   🛡️ **Smart Login Security Bypass**: Automatically prompts and executes in **Headful Mode** (`headless=False`) if Instagram triggers security verifications (SMS/Email OTP or Captchas), letting you authenticate securely.

---

## 🛠️ Tech Stack

*   **Language & Runtime**: Python 3.11+
*   **Web Framework**: Flask (with Server-Sent Events SSE streaming)
*   **Automation**: Playwright (Chromium)
*   **OCR**: Tesseract OCR (via `pytesseract`)

---

## 🚀 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/VAIBHAV7848/-InstaLens.git
cd -InstaLens
```

### 2. Install System Dependencies
Install **Tesseract OCR** on your operating system:
*   **Ubuntu/Debian**: `sudo apt install tesseract-ocr`
*   **macOS**: `brew install tesseract`
*   **Windows**: Download installer from GitHub and add it to your system PATH.

### 3. Create a Virtual Environment & Install Packages
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Install Playwright Browsers
```bash
playwright install chromium
```

### 5. Launch the Server
```bash
python app.py
```
Open **`http://localhost:5000`** in your browser to start using InstaLens.

---

## 🐳 Running with Docker (Recommended for Portability)

To run InstaLens on any device without manually installing system dependencies like Tesseract OCR or configuring virtual environments, you can use Docker:

### 1. Build and Start Container
```bash
docker compose up --build
```

### 2. Access the Application
Open **`http://localhost:5000`** in your web browser. 

*Note: Dynamically created Instagram session profiles (`playwright_session_*.json`) are automatically persisted on your host machine via volume mounts.*

---

## 💡 How It Works

1.  **Session Establishment**: Authenticate with Instagram. If a login verification challenge is met, a headful browser window will open on your desktop to let you resolve it.
2.  **Scraping**: Select either the **Posts & Reels** grid or the **Reposts** tab of your target.
3.  **OCR & NLP**: The system reads all captions and screenshot text, tokenizes key terms, matches them with the `TOPIC_TAXONOMY` database, and evaluates scores.
4.  **Insights**: Instantly view interest breakdowns, repeated keywords, and conversation suggestions customized to the target's style.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
