/**
 * InstaLens — Frontend Interactivity
 * Handles session checks, mode transitions, Instagram login/logout,
 * manual/auto submissions, and animated results rendering.
 */

document.addEventListener("DOMContentLoaded", () => {
    // ---- View Containers ----
    const loginView = document.getElementById("login-view");
    const dashboardView = document.getElementById("dashboard-view");
    const sessionBanner = document.getElementById("session-banner");
    const sessionUserText = document.getElementById("session-user-text");

    // ---- Elements ----
    const tabAuto = document.getElementById("tab-auto");
    const tabManual = document.getElementById("tab-manual");
    const panelAuto = document.getElementById("panel-auto");
    const panelManual = document.getElementById("panel-manual");
    const btnAnalyze = document.getElementById("btn-analyze");
    const btnText = btnAnalyze.querySelector(".btn-text");
    const btnLoading = btnAnalyze.querySelector(".btn-loading");
    const loadingText = document.getElementById("loading-text");
    const resultsSection = document.getElementById("results-section");
    const inputSection = document.getElementById("input-section");
    const btnNewAnalysis = document.getElementById("btn-new-analysis");
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const filePreviews = document.getElementById("file-previews");

    // ---- Login & Logout Buttons ----
    const btnLogin = document.getElementById("btn-login");
    const btnLogout = document.getElementById("btn-logout");
    const linkSkipLogin = document.getElementById("link-skip-login");

    let currentMode = "auto";
    let isLoggedIn = false;
    let loggedInUser = "";
    let uploadedFiles = [];

    // ---- Check Session On Load ----
    checkSession();

    async function checkSession() {
        try {
            const res = await fetch("/session");
            const data = await res.json();
            if (data.logged_in) {
                setupAuthenticatedState(data.username);
            } else {
                setupUnauthenticatedState();
            }
        } catch (err) {
            setupUnauthenticatedState();
        }
    }

    function setupAuthenticatedState(username) {
        isLoggedIn = true;
        loggedInUser = username;
        
        // UI updates
        loginView.hidden = true;
        dashboardView.hidden = false;
        sessionBanner.style.display = "flex";
        sessionUserText.textContent = `Logged in as @${username}`;
        
        // Show auto-scrape tab and make it active
        tabAuto.style.display = "flex";
        switchMode("auto");
    }

    function setupUnauthenticatedState() {
        isLoggedIn = false;
        loggedInUser = "";
        
        loginView.hidden = false;
        dashboardView.hidden = true;
    }

    // ---- Login Action ----
    if (btnLogin) {
        btnLogin.addEventListener("click", async () => {
            const user = document.getElementById("insta-username").value.trim();
            const pass = document.getElementById("insta-password").value.trim();

            if (!user || !pass) {
                return showError("Please enter both your Instagram username and password.");
            }

            // Set login button loading state
            setBtnLoading(btnLogin, true, "Connecting...");

            try {
                const res = await fetch("/login", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ username: user, password: pass })
                });

                const data = await res.json();
                if (data.error) {
                    showError(data.error);
                } else {
                    setupAuthenticatedState(data.username);
                }
            } catch (err) {
                showError("Connection failed. Make sure the server is running.");
            } finally {
                setBtnLoading(btnLogin, false, "Log In & Continue");
            }
        });
    }

    // ---- Logout Action ----
    if (btnLogout) {
        btnLogout.addEventListener("click", async () => {
            try {
                await fetch("/logout", { method: "POST" });
            } catch (err) {}
            setupUnauthenticatedState();
        });
    }

    // ---- Skip Login (Manual Only) ----
    if (linkSkipLogin) {
        linkSkipLogin.addEventListener("click", (e) => {
            e.preventDefault();
            // Transition to dashboard in manual mode only
            loginView.hidden = true;
            dashboardView.hidden = false;
            sessionBanner.style.display = "none"; // Hide active session info
            
            // Hide the Auto Scrape tab since they aren't authenticated
            tabAuto.style.display = "none";
            switchMode("manual");
        });
    }

    // ---- Mode Tabs ----
    function switchMode(mode) {
        currentMode = mode;
        document.querySelectorAll(".mode-tab").forEach(t => t.classList.remove("active"));
        document.querySelectorAll(".mode-panel").forEach(p => p.classList.remove("active"));
        if (mode === "auto") {
            tabAuto.classList.add("active");
            panelAuto.classList.add("active");
        } else {
            tabManual.classList.add("active");
            panelManual.classList.add("active");
        }
    }

    tabAuto.addEventListener("click", () => switchMode("auto"));
    tabManual.addEventListener("click", () => switchMode("manual"));

    // ---- File Upload (Manual Mode) ----
    if (dropZone) {
        dropZone.addEventListener("click", () => fileInput && fileInput.click());
        dropZone.addEventListener("dragover", (e) => { e.preventDefault(); dropZone.classList.add("dragover"); });
        dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
        dropZone.addEventListener("drop", (e) => {
            e.preventDefault();
            dropZone.classList.remove("dragover");
            handleFiles(e.dataTransfer.files);
        });
    }
    if (fileInput) {
        fileInput.addEventListener("change", () => handleFiles(fileInput.files));
    }

    function handleFiles(files) {
        for (const file of files) {
            if (file.type.startsWith("image/")) {
                uploadedFiles.push(file);
                renderFilePreviews();
            }
        }
    }

    function renderFilePreviews() {
        if (!filePreviews) return;
        filePreviews.innerHTML = "";
        uploadedFiles.forEach((file, idx) => {
            const div = document.createElement("div");
            div.className = "file-preview";
            div.innerHTML = `📷 ${file.name} <span class="remove-file" data-idx="${idx}">✕</span>`;
            filePreviews.appendChild(div);
        });
        filePreviews.querySelectorAll(".remove-file").forEach(btn => {
            btn.addEventListener("click", (e) => {
                uploadedFiles.splice(parseInt(e.target.dataset.idx), 1);
                renderFilePreviews();
            });
        });
    }

    // ---- Analyze Button ----
    btnAnalyze.addEventListener("click", () => {
        if (currentMode === "auto") { submitAuto(); }
        else { submitManual(); }
    });

    async function submitAuto() {
        const target = document.getElementById("target-profile").value.trim();
        const maxPosts = parseInt(document.getElementById("max-posts").value) || 30;
        const sourceEl = document.getElementById("content-source");
        const source = sourceEl ? sourceEl.value : "posts";

        if (!target) return showError("Please enter a target profile URL or username.");

        setLoading(true, "Scraping profile details...");

        try {
            setTimeout(() => { if (btnAnalyze.disabled) setLoadingText("Scraping posts..."); }, 3000);
            setTimeout(() => { if (btnAnalyze.disabled) setLoadingText("Running topic analysis..."); }, 10000);

            const res = await fetch("/analyze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    mode: "auto",
                    target_profile: target,
                    max_posts: maxPosts,
                    source: source,
                }),
            });

            const data = await res.json();
            if (data.error) { showError(data.error); setLoading(false); return; }
            renderResults(data);
        } catch (err) {
            showError("Network error. Make sure the server is running.");
        }
        setLoading(false);
    }

    async function submitManual() {
        const textInput = document.getElementById("text-input");
        const text = textInput ? textInput.value.trim() : "";

        if (!text && uploadedFiles.length === 0) {
            return showError("Please paste some text or upload screenshots.");
        }

        setLoading(true, "Analyzing content...");

        const formData = new FormData();
        if (text) formData.append("text", text);
        uploadedFiles.forEach(f => formData.append("screenshots", f));

        try {
            const res = await fetch("/analyze", { method: "POST", body: formData });
            const data = await res.json();
            if (data.error) { showError(data.error); setLoading(false); return; }
            renderResults(data);
        } catch (err) {
            showError("Network error. Make sure the server is running.");
        }
        setLoading(false);
    }

    // ---- Button Loading State Helpers ----
    function setBtnLoading(btn, loading, text) {
        btn.disabled = loading;
        const txtEl = btn.querySelector(".btn-text");
        const loadEl = btn.querySelector(".btn-loading");
        if (txtEl) txtEl.hidden = loading;
        if (loadEl) loadEl.hidden = !loading;
        if (loading && loadEl) {
            const txt = loadEl.querySelector("span");
            if (txt) txt.textContent = text;
        }
    }

    function setLoading(loading, text) {
        btnAnalyze.disabled = loading;
        btnText.hidden = loading;
        btnLoading.hidden = !loading;
        if (text) setLoadingText(text);
    }

    function setLoadingText(text) {
        if (loadingText) loadingText.textContent = text;
    }

    // ---- Render Results ----
    function renderResults(data) {
        inputSection.hidden = true;
        resultsSection.hidden = false;
        resultsSection.scrollIntoView({ behavior: "smooth" });

        // Profile info
        const profileCard = document.getElementById("profile-card");
        if (data.profile_info) {
            profileCard.hidden = false;
            document.getElementById("profile-name").textContent = data.profile_info.name || "Unknown";
            document.getElementById("profile-bio").textContent = data.profile_info.bio || "";
            document.getElementById("profile-posts").textContent = formatNum(data.profile_info.post_count);
            document.getElementById("profile-followers").textContent = formatNum(data.profile_info.followers);
            document.getElementById("profile-following").textContent = formatNum(data.profile_info.following);
            document.getElementById("profile-scraped").textContent = data.profile_info.scraped_posts;
        } else {
            profileCard.hidden = true;
        }

        // Summary
        document.getElementById("summary-text").textContent = data.summary || "";
        document.getElementById("confidence-value").textContent = data.overall_confidence + "%";

        // Stats
        const stats = data.input_stats || {};
        document.getElementById("stat-chunks-val").textContent = stats.text_chunks || 0;
        document.getElementById("stat-screenshots-val").textContent = stats.screenshots_processed || 0;
        document.getElementById("stat-tokens-val").textContent = stats.total_tokens || 0;
        document.getElementById("stat-hashtags-val").textContent = stats.total_hashtags || 0;

        // Topics
        const topicsList = document.getElementById("topics-list");
        topicsList.innerHTML = "";
        (data.top_topics || []).forEach(t => {
            const keywords = (t.matched_keywords || []).concat(t.matched_hashtags || [])
                .slice(0, 5).map(k => `<span class="topic-kw">${k}</span>`).join("");
            const div = document.createElement("div");
            div.className = "topic-item";
            div.innerHTML = `
                <div class="topic-header">
                    <span class="topic-name">${t.name}</span>
                    <span class="topic-confidence">${t.confidence}%</span>
                </div>
                <div class="topic-bar"><div class="topic-bar-fill" style="width: 0%"></div></div>
                ${keywords ? `<div class="topic-keywords">${keywords}</div>` : ""}
            `;
            topicsList.appendChild(div);
            // Animate bar
            requestAnimationFrame(() => {
                const bar = div.querySelector(".topic-bar-fill");
                if (bar) bar.style.width = t.confidence + "%";
            });
        });

        // Interests
        const interestsList = document.getElementById("interests-list");
        interestsList.innerHTML = "";
        (data.common_interests || []).forEach(i => {
            const chip = document.createElement("span");
            chip.className = "interest-chip";
            chip.innerHTML = `<span class="interest-dot"></span>${i}`;
            interestsList.appendChild(chip);
        });

        // Keywords
        const cloud = document.getElementById("keywords-cloud");
        cloud.innerHTML = "";
        const colors = [
            "rgba(168,85,247,0.15);color:#c084fc",
            "rgba(6,182,212,0.15);color:#22d3ee",
            "rgba(236,72,153,0.15);color:#f472b6",
            "rgba(16,185,129,0.15);color:#34d399",
            "rgba(245,158,11,0.15);color:#fbbf24",
        ];
        (data.repeated_keywords || []).forEach((k, i) => {
            const sizeClass = i < 3 ? "size-lg" : i < 7 ? "size-md" : "size-sm";
            const color = colors[i % colors.length];
            const tag = document.createElement("span");
            tag.className = `keyword-tag ${sizeClass}`;
            tag.style.cssText = `background:${color}`;
            tag.textContent = k.word;
            cloud.appendChild(tag);
        });

        // Hashtags
        const hashtagsList = document.getElementById("hashtags-list");
        hashtagsList.innerHTML = "";
        (data.repeated_hashtags || []).forEach(h => {
            const item = document.createElement("div");
            item.className = "hashtag-item";
            item.innerHTML = `
                <span class="hashtag-name">${h.tag}</span>
                <span class="hashtag-count">×${h.count}</span>
            `;
            hashtagsList.appendChild(item);
        });

        // Suggestions
        const suggestionsList = document.getElementById("suggestions-list");
        suggestionsList.innerHTML = "";
        (data.conversation_suggestions || []).forEach((s, i) => {
            const item = document.createElement("div");
            item.className = "suggestion-item";
            item.innerHTML = `
                <span class="suggestion-num">${i + 1}</span>
                <span class="suggestion-text">${s}</span>
            `;
            suggestionsList.appendChild(item);
        });
    }

    // ---- New Analysis ----
    btnNewAnalysis.addEventListener("click", () => {
        resultsSection.hidden = true;
        inputSection.hidden = false;
        inputSection.scrollIntoView({ behavior: "smooth" });
    });

    // ---- Helpers ----
    function formatNum(n) {
        if (!n) return "0";
        if (n >= 1000000) return (n / 1000000).toFixed(1) + "M";
        if (n >= 1000) return (n / 1000).toFixed(1) + "K";
        return n.toString();
    }

    function showError(msg) {
        const existing = document.querySelector(".error-toast");
        if (existing) existing.remove();
        const toast = document.createElement("div");
        toast.className = "error-toast";
        
        const isBlock = msg.includes("Instagram") || msg.includes("rate-limiting") || msg.includes("blocked") || msg.includes("403") || msg.includes("429") || msg.includes("credentials");
        
        if (isBlock) {
            toast.innerHTML = `
                <div style="margin-bottom: 8px; font-weight: 600; display: flex; align-items: center; gap: 6px;">
                    <span>⚠️</span> Instagram Blocked/Rate-limited
                </div>
                <div style="margin-bottom: 12px; font-size: 0.8rem; opacity: 0.95; line-height: 1.4;">
                    ${msg.replace(/\n/g, '<br>')}
                </div>
                <button class="toast-fallback-btn" style="
                    background: var(--gradient-main);
                    border: none;
                    border-radius: var(--radius-sm);
                    color: white;
                    padding: 6px 12px;
                    font-family: var(--font);
                    font-size: 0.8rem;
                    font-weight: 600;
                    cursor: pointer;
                    width: 100%;
                    text-align: center;
                    transition: opacity 0.2s;
                ">Try Manual Input Instead</button>
            `;
            const btn = toast.querySelector(".toast-fallback-btn");
            btn.addEventListener("click", () => {
                // If they are in the login view, transition to manual view first
                if (!loginView.hidden) {
                    loginView.hidden = true;
                    dashboardView.hidden = false;
                    sessionBanner.style.display = "none";
                    tabAuto.style.display = "none";
                }
                switchMode("manual");
                const textInput = document.getElementById("text-input");
                if (textInput) {
                    textInput.focus();
                    textInput.placeholder = "Paste recent captions or post text from @omganesh_014 here...";
                }
                toast.remove();
            });
        } else {
            toast.textContent = msg;
        }
        
        document.body.appendChild(toast);
        setTimeout(() => { if (toast.parentNode) toast.remove(); }, isBlock ? 15000 : 6000);
    }
});
