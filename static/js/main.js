/**
 * InstaLens — Frontend Interactivity
 * Handles session checks, mode transitions, Instagram login/logout,
 * manual/auto submissions, and animated results rendering.
 */

document.addEventListener("DOMContentLoaded", () => {
    // ---- View Containers ----
    const loginView = document.getElementById("login-view");
    const loginGateLanding = document.getElementById("login-gate-landing");
    const loginGateForm = document.getElementById("login-gate-form");
    const dashboardView = document.getElementById("dashboard-view");
    const sessionBanner = document.getElementById("session-banner");
    const sessionUserText = document.getElementById("session-user-text");

    // ---- Landing & Login Buttons ----
    const btnShowLoginForm = document.getElementById("btn-show-login-form");
    const btnBackToLanding = document.getElementById("btn-back-to-landing");
    const btnSkipLoginDirect = document.getElementById("btn-skip-login-direct");
    const btnLogin = document.getElementById("btn-login");
    const btnLogout = document.getElementById("btn-logout");
    const btnTogglePassword = document.getElementById("btn-toggle-password");

    // ---- Workspace Mode Tabs ----
    const tabAuto = document.getElementById("tab-auto");
    const tabSpy = document.getElementById("tab-spy");
    const tabManual = document.getElementById("tab-manual");
    const tabMatch = document.getElementById("tab-match");
    const panelAuto = document.getElementById("panel-auto");
    const panelSpy = document.getElementById("panel-spy");
    const panelManual = document.getElementById("panel-manual");
    const panelMatch = document.getElementById("panel-match");

    // ---- Submission Buttons ----
    const btnRunAuto = document.getElementById("btn-run-auto");
    const btnRunSpy = document.getElementById("btn-run-spy");
    const btnRunManual = document.getElementById("btn-run-manual");
    const btnRunMatch = document.getElementById("btn-run-match");
    const btnClearManual = document.getElementById("btn-clear-manual");

    // ---- Matchmaker Inputs ----
    const matchASource = document.getElementById("match-a-source");
    const matchBSource = document.getElementById("match-b-source");
    const matchAScrapeGroup = document.getElementById("match-a-scrape-group");
    const matchATextGroup = document.getElementById("match-a-text-group");
    const matchBScrapeGroup = document.getElementById("match-b-scrape-group");
    const matchBTextGroup = document.getElementById("match-b-text-group");

    // ---- OCR Elements ----
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const filePreviews = document.getElementById("file-previews");
    const ocrPreviewPanel = document.getElementById("ocr-preview-panel");
    const ocrSpinner = document.getElementById("ocr-spinner");
    const ocrExtractedPreview = document.getElementById("ocr-extracted-preview");
    const btnOcrAppend = document.getElementById("btn-ocr-append");
    const btnOcrReplace = document.getElementById("btn-ocr-replace");

    // ---- Results Dashboard ----
    const resultsSection = document.getElementById("results-section");
    const inputSection = document.getElementById("input-section");
    const btnNewAnalysis = document.getElementById("btn-new-analysis");

    let currentMode = "auto";
    let isLoggedIn = false;
    let loggedInUser = "";
    let uploadedFiles = [];
    let lastReportData = null;

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
        
        loginView.hidden = true;
        dashboardView.hidden = false;
        sessionBanner.style.display = "flex";
        sessionUserText.textContent = `Logged in as @${username}`;
        
        // Show all tabs
        tabAuto.style.display = "flex";
        if (tabSpy) tabSpy.style.display = "flex";
        if (tabMatch) tabMatch.style.display = "flex";
        switchMode("auto");
    }

    function setupUnauthenticatedState() {
        isLoggedIn = false;
        loggedInUser = "";
        
        loginView.hidden = false;
        loginGateLanding.hidden = false;
        loginGateForm.hidden = true;
        dashboardView.hidden = true;
        
        tabAuto.style.display = "none";
        if (tabSpy) tabSpy.style.display = "none";
        if (tabMatch) tabMatch.style.display = "flex"; // Keep matchmaker open for offline text matching!
    }

    // ---- Welcome / Landing Page Routing ----
    if (btnShowLoginForm) {
        btnShowLoginForm.addEventListener("click", () => {
            loginGateLanding.hidden = true;
            loginGateForm.hidden = false;
        });
    }

    if (btnBackToLanding) {
        btnBackToLanding.addEventListener("click", () => {
            loginGateLanding.hidden = false;
            loginGateForm.hidden = true;
        });
    }

    if (btnSkipLoginDirect) {
        btnSkipLoginDirect.addEventListener("click", () => {
            loginView.hidden = true;
            dashboardView.hidden = false;
            sessionBanner.style.display = "none";
            tabAuto.style.display = "none";
            if (tabSpy) tabSpy.style.display = "none";
            switchMode("manual");
        });
    }

    // Password visibility toggle
    if (btnTogglePassword) {
        btnTogglePassword.addEventListener("click", () => {
            const pwdField = document.getElementById("insta-password");
            if (pwdField.type === "password") {
                pwdField.type = "text";
                btnTogglePassword.textContent = "🙈";
            } else {
                pwdField.type = "password";
                btnTogglePassword.textContent = "👁️";
            }
        });
    }

    // ---- Login Action ----
    if (btnLogin) {
        btnLogin.addEventListener("click", async () => {
            const user = document.getElementById("insta-username").value.trim();
            const pass = document.getElementById("insta-password").value.trim();

            if (!user || !pass) {
                return showError("Please enter both your Instagram username and password.");
            }

            setBtnLoading(btnLogin, true, "Connect & Continue", "Establishing session...");

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
                    showToast("Instagram session connected successfully!", "success");
                }
            } catch (err) {
                showError("Connection failed. Make sure the server is running.");
            } finally {
                setBtnLoading(btnLogin, false, "Connect & Continue", "");
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
            showToast("Logged out of Instagram.", "success");
        });
    }

    // ---- Download CLI Scraper ----
    const btnDownloadCli = document.getElementById("btn-download-cli");
    if (btnDownloadCli) {
        btnDownloadCli.addEventListener("click", () => {
            window.location.href = "/api/export_cli_script";
        });
    }

    // ---- Mode Tabs Switcher ----
    function switchMode(mode) {
        currentMode = mode;
        document.querySelectorAll(".mode-tab").forEach(t => t.classList.remove("active"));
        document.querySelectorAll(".mode-panel").forEach(p => p.classList.remove("active"));
        
        const activeTab = document.getElementById(`tab-${mode}`);
        const activePanel = document.getElementById(`panel-${mode}`);
        if (activeTab) activeTab.classList.add("active");
        if (activePanel) activePanel.classList.add("active");
    }

    const tabClean = document.getElementById("tab-clean");
    if (tabAuto) tabAuto.addEventListener("click", () => switchMode("auto"));
    if (tabSpy) tabSpy.addEventListener("click", () => switchMode("spy"));
    if (tabManual) tabManual.addEventListener("click", () => switchMode("manual"));
    if (tabMatch) tabMatch.addEventListener("click", () => switchMode("match"));
    if (tabClean) tabClean.addEventListener("click", () => switchMode("clean"));

    // ---- Matchmaker Input Source Toggles ----
    if (matchASource && matchAScrapeGroup && matchATextGroup) {
        matchASource.addEventListener("change", (e) => {
            if (e.target.value === "scrape") {
                matchAScrapeGroup.hidden = false;
                matchATextGroup.hidden = true;
            } else {
                matchAScrapeGroup.hidden = true;
                matchATextGroup.hidden = false;
            }
        });
    }

    if (matchBSource && matchBScrapeGroup && matchBTextGroup) {
        matchBSource.addEventListener("change", (e) => {
            if (e.target.value === "scrape") {
                matchBScrapeGroup.hidden = false;
                matchBTextGroup.hidden = true;
            } else {
                matchBScrapeGroup.hidden = true;
                matchBTextGroup.hidden = false;
            }
        });
    }

    // ---- Collapsible Settings Utility ----
    function setupCollapsible(headerId, contentId, wrapperId) {
        const header = document.getElementById(headerId);
        const content = document.getElementById(contentId);
        const wrapper = document.getElementById(wrapperId);
        if (header && content && wrapper) {
            header.addEventListener("click", () => {
                const isActive = content.classList.contains("active");
                if (isActive) {
                    content.classList.remove("active");
                    wrapper.classList.remove("active");
                } else {
                    content.classList.add("active");
                    wrapper.classList.add("active");
                }
            });
        }
    }
    setupCollapsible("header-settings-auto", "content-settings-auto", "settings-auto-wrapper");
    setupCollapsible("header-settings-spy", "content-settings-spy", "settings-spy-wrapper");
    setupCollapsible("header-settings-match", "content-settings-match", "settings-match-wrapper");

    // Collapsible scrape progress logs
    const btnToggleLogs = document.getElementById("btn-toggle-logs");
    const progressLogs = document.getElementById("scrape-progress-logs");
    const logToggleArrow = document.getElementById("log-toggle-arrow");
    if (btnToggleLogs && progressLogs && logToggleArrow) {
        btnToggleLogs.addEventListener("click", () => {
            if (progressLogs.style.display === "none") {
                progressLogs.style.display = "flex";
                logToggleArrow.textContent = "▼ Collapse Logs";
            } else {
                progressLogs.style.display = "none";
                logToggleArrow.textContent = "▲ Expand Logs";
            }
        });
    }

    // ---- File Upload & OCR Review Flow ----
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
        const screenshotFiles = [];
        for (const file of files) {
            if (file.type.startsWith("image/")) {
                uploadedFiles.push(file);
                screenshotFiles.push(file);
            }
        }
        renderFilePreviews();
        if (screenshotFiles.length > 0) {
            runOcrExtraction(screenshotFiles);
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
                if (uploadedFiles.length === 0 && ocrPreviewPanel) {
                    ocrPreviewPanel.hidden = true;
                }
            });
        });
    }

    async function runOcrExtraction(files) {
        if (!ocrPreviewPanel || !ocrExtractedPreview) return;
        
        ocrPreviewPanel.hidden = false;
        if (ocrSpinner) ocrSpinner.hidden = false;
        ocrExtractedPreview.textContent = "Running local Tesseract OCR on uploaded screenshots...";

        const formData = new FormData();
        files.forEach(f => formData.append("screenshots", f));

        try {
            const res = await fetch("/api/ocr_extract", {
                method: "POST",
                body: formData
            });
            const data = await res.json();
            if (data.error) {
                ocrExtractedPreview.textContent = `OCR Failed: ${data.error}`;
                showToast("OCR text extraction failed.", "error");
            } else {
                ocrExtractedPreview.textContent = data.text || "(No text extracted)";
                showToast("Screenshots parsed! Review extracted text below.", "success");
            }
        } catch (err) {
            ocrExtractedPreview.textContent = "Failed to run OCR. Make sure Tesseract is installed on the system.";
            showToast("Tesseract error.", "error");
        } finally {
            if (ocrSpinner) ocrSpinner.hidden = true;
        }
    }

    // Bind OCR append/replace actions
    if (btnOcrAppend) {
        btnOcrAppend.addEventListener("click", () => {
            const textInput = document.getElementById("text-input");
            const ocrText = ocrExtractedPreview.textContent.trim();
            if (textInput && ocrText && !ocrText.startsWith("Running") && !ocrText.startsWith("OCR Failed")) {
                textInput.value = textInput.value ? (textInput.value + "\n\n" + ocrText) : ocrText;
                showToast("Extracted text appended to editor!", "success");
            }
        });
    }

    if (btnOcrReplace) {
        btnOcrReplace.addEventListener("click", () => {
            const textInput = document.getElementById("text-input");
            const ocrText = ocrExtractedPreview.textContent.trim();
            if (textInput && ocrText && !ocrText.startsWith("Running") && !ocrText.startsWith("OCR Failed")) {
                textInput.value = ocrText;
                showToast("Editor text replaced with extracted text!", "success");
            }
        });
    }

    if (btnClearManual) {
        btnClearManual.addEventListener("click", () => {
            const textInput = document.getElementById("text-input");
            if (textInput) textInput.value = "";
            uploadedFiles = [];
            renderFilePreviews();
            if (ocrPreviewPanel) ocrPreviewPanel.hidden = true;
            showToast("Inputs cleared.", "success");
        });
    }

    // ---- Submission Triggers ----
    if (btnRunAuto) btnRunAuto.addEventListener("click", submitAuto);
    if (btnRunSpy) btnRunSpy.addEventListener("click", submitSpy);
    if (btnRunManual) btnRunManual.addEventListener("click", submitManual);
    if (btnRunMatch) btnRunMatch.addEventListener("click", submitMatch);

    // ---- Auto Scrape Action ----
    async function submitAuto() {
        const target = document.getElementById("target-profile").value.trim();
        const maxPosts = parseInt(document.getElementById("max-posts").value) || 30;
        const sourceEl = document.getElementById("content-source");
        const source = sourceEl ? sourceEl.value : "posts";

        if (!target) return showError("Please enter a target profile URL or username.");

        setBtnLoading(btnRunAuto, true, "Run Auto Scraping", "Launching browser...");
        
        const progressCard = document.getElementById("scrape-progress-card");
        const progressLogs = document.getElementById("scrape-progress-logs");
        const progressTitle = document.getElementById("progress-card-title");
        
        if (progressCard) progressCard.hidden = false;
        if (progressLogs) {
            progressLogs.innerHTML = "";
            progressLogs.style.display = "flex"; // Make sure it's expanded
        }
        if (progressTitle) progressTitle.textContent = "Scraping target profile...";

        try {
            const formData = new FormData();
            formData.append("target", target);
            formData.append("login_username", loggedInUser);
            formData.append("max_posts", maxPosts);
            formData.append("source", source);

            const res = await fetch("/analyze_stream", {
                method: "POST",
                body: formData
            });

            const reader = res.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let buffer = "";

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n\n");
                buffer = lines.pop();

                for (const line of lines) {
                    if (line.startsWith("data: ")) {
                        const jsonStr = line.substring(6).trim();
                        try {
                            const eventData = JSON.parse(jsonStr);
                            if (eventData.status) {
                                const p = document.createElement("div");
                                p.style.cssText = "margin-bottom: 2px;";
                                p.innerHTML = `<span style="color: var(--accent-cyan);">➔</span> ${eventData.status}`;
                                if (progressLogs) {
                                    progressLogs.appendChild(p);
                                    progressLogs.scrollTop = progressLogs.scrollHeight;
                                }
                                setBtnLoading(btnRunAuto, true, "Run Auto Scraping", eventData.status);
                            }
                            if (eventData.error) {
                                showError(eventData.error);
                                setBtnLoading(btnRunAuto, false, "Run Auto Scraping", "");
                                if (progressCard) progressCard.hidden = true;
                                return;
                            }
                            if (eventData.report) {
                                lastReportData = eventData.report;
                                renderResults(eventData.report);
                            }
                        } catch (e) {
                            console.error("Error parsing stream line:", e);
                        }
                    }
                }
            }
        } catch (err) {
            showError("Network connection error during stream scraping.");
        }
        setBtnLoading(btnRunAuto, false, "Run Auto Scraping", "");
        if (progressCard) progressCard.hidden = true;
    }

    // ---- Activity Spy Action ----
    async function submitSpy() {
        const target = document.getElementById("spy-target-profile").value.trim();
        const friendsCount = parseInt(document.getElementById("spy-depth-friends").value) || 5;
        const postsCount = parseInt(document.getElementById("spy-depth-posts").value) || 5;

        if (!target) return showError("Please enter a target username or profile link.");

        setBtnLoading(btnRunSpy, true, "Initiate Scan Sequence", "Auditing followed circle...");

        const progressCard = document.getElementById("scrape-progress-card");
        const progressLogs = document.getElementById("scrape-progress-logs");
        const progressTitle = document.getElementById("progress-card-title");

        if (progressCard) progressCard.hidden = false;
        if (progressLogs) {
            progressLogs.innerHTML = "";
            progressLogs.style.display = "flex";
        }
        if (progressTitle) progressTitle.textContent = "Spying on target engagements...";

        try {
            const formData = new FormData();
            formData.append("target", target);
            formData.append("login_username", loggedInUser);
            formData.append("friends_count", friendsCount);
            formData.append("posts_count", postsCount);

            const res = await fetch("/spy_stream", {
                method: "POST",
                body: formData
            });

            const reader = res.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let buffer = "";

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n\n");
                buffer = lines.pop();

                for (const line of lines) {
                    if (line.startsWith("data: ")) {
                        const jsonStr = line.substring(6).trim();
                        try {
                            const eventData = JSON.parse(jsonStr);
                            if (eventData.status) {
                                const p = document.createElement("div");
                                p.style.cssText = "margin-bottom: 2px;";
                                p.innerHTML = `<span style="color: var(--accent-purple);">➔</span> ${eventData.status}`;
                                if (progressLogs) {
                                    progressLogs.appendChild(p);
                                    progressLogs.scrollTop = progressLogs.scrollHeight;
                                }
                                setBtnLoading(btnRunSpy, true, "Initiate Scan Sequence", eventData.status);
                            }
                            if (eventData.error) {
                                showError(eventData.error);
                                setBtnLoading(btnRunSpy, false, "Initiate Scan Sequence", "");
                                if (progressCard) progressCard.hidden = true;
                                return;
                            }
                            if (eventData.report) {
                                lastReportData = eventData.report;
                                renderResults(eventData.report);
                            }
                        } catch (e) {
                            console.error("Error parsing spy stream line:", e);
                        }
                    }
                }
            }
        } catch (err) {
            showError("Network connection error during spy scraping.");
        }
        setBtnLoading(btnRunSpy, false, "Initiate Scan Sequence", "");
        if (progressCard) progressCard.hidden = true;
    }

    // ---- Manual Submit Action ----
    async function submitManual() {
        const textInput = document.getElementById("text-input");
        const text = textInput ? textInput.value.trim() : "";

        if (!text && uploadedFiles.length === 0) {
            return showError("Please paste some captions or upload screenshots.");
        }

        setBtnLoading(btnRunManual, true, "Run Offline Analysis", "Running NLP Engine...");

        const formData = new FormData();
        if (text) formData.append("text", text);
        uploadedFiles.forEach(f => formData.append("screenshots", f));

        try {
            const res = await fetch("/analyze", { method: "POST", body: formData });
            const data = await res.json();
            if (data.error) {
                showError(data.error);
                setBtnLoading(btnRunManual, false, "Run Offline Analysis", "");
                return;
            }
            lastReportData = data;
            renderResults(data);
        } catch (err) {
            showError("Network error. Make sure the server is running.");
        }
        setBtnLoading(btnRunManual, false, "Run Offline Analysis", "");
    }

    // ---- Matchmaker Submit Action ----
    async function submitMatch() {
        const sourceA = matchASource.value;
        const sourceB = matchBSource.value;
        
        let valA = "";
        let valB = "";
        
        if (sourceA === "scrape") {
            valA = document.getElementById("match-a-target").value.trim();
            if (!valA) return showError("Please enter an Instagram username for Profile A.");
            if (!isLoggedIn) return showError("You must be logged in to Instagram to scrape Profile A.");
        } else {
            valA = document.getElementById("match-a-text").value.trim();
            if (!valA) return showError("Please paste text captions/messages for Profile A.");
        }

        if (sourceB === "scrape") {
            valB = document.getElementById("match-b-target").value.trim();
            if (!valB) return showError("Please enter an Instagram username for Profile B.");
            if (!isLoggedIn) return showError("You must be logged in to Instagram to scrape Profile B.");
        } else {
            valB = document.getElementById("match-b-text").value.trim();
            if (!valB) return showError("Please paste text captions/messages for Profile B.");
        }

        setBtnLoading(btnRunMatch, true, "Calculate Compatibility", "Initializing...");

        const progressCard = document.getElementById("scrape-progress-card");
        const progressLogs = document.getElementById("scrape-progress-logs");
        const progressTitle = document.getElementById("progress-card-title");

        if (progressCard) progressCard.hidden = false;
        if (progressLogs) {
            progressLogs.innerHTML = "";
            progressLogs.style.display = "flex";
        }
        if (progressTitle) progressTitle.textContent = "Calculating Compatibility...";

        try {
            const formData = new FormData();
            formData.append("profile_a_source", sourceA);
            formData.append("profile_a_val", valA);
            formData.append("profile_b_source", sourceB);
            formData.append("profile_b_val", valB);
            formData.append("max_posts", document.getElementById("match-max-posts").value || 15);
            if (isLoggedIn) {
                formData.append("login_username", loggedInUser);
            }

            const res = await fetch("/match_stream", {
                method: "POST",
                body: formData
            });

            const reader = res.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let buffer = "";

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n\n");
                buffer = lines.pop();

                for (const line of lines) {
                    if (line.startsWith("data: ")) {
                        const jsonStr = line.substring(6).trim();
                        try {
                            const eventData = JSON.parse(jsonStr);
                            if (eventData.status) {
                                const p = document.createElement("div");
                                p.style.cssText = "margin-bottom: 2px;";
                                p.innerHTML = `<span style="color: var(--accent-pink);">➔</span> ${eventData.status}`;
                                if (progressLogs) {
                                    progressLogs.appendChild(p);
                                    progressLogs.scrollTop = progressLogs.scrollHeight;
                                }
                                setBtnLoading(btnRunMatch, true, "Calculate Compatibility", eventData.status);
                            }
                            if (eventData.error) {
                                showError(eventData.error);
                                setBtnLoading(btnRunMatch, false, "Calculate Compatibility", "");
                                if (progressCard) progressCard.hidden = true;
                                return;
                            }
                            if (eventData.report) {
                                lastReportData = eventData.report;
                                renderMatchResults(eventData.report);
                            }
                        } catch (e) {
                            console.error("Error parsing match stream line:", e);
                        }
                    }
                }
            }
        } catch (err) {
            showError("Network connection error during matchmaking analysis.");
        }
        setBtnLoading(btnRunMatch, false, "Calculate Compatibility", "");
        if (progressCard) progressCard.hidden = true;
    }

    // ---- Render Matchmaker compatibility results dashboard ----
    function renderMatchResults(data) {
        document.getElementById("section-profile-overview").style.display = "none";
        document.getElementById("section-engagement-metrics").style.display = "none";
        document.getElementById("section-content-behavior").style.display = "none";
        document.getElementById("section-interest-profiler").style.display = "none";
        document.getElementById("section-conversation-starters").style.display = "none";
        document.getElementById("section-spy-timeline").style.display = "none";
        document.getElementById("section-matchmaker-results").style.display = "block";
        document.getElementById("btn-export-report").style.display = "none";

        inputSection.hidden = true;
        resultsSection.hidden = false;
        resultsSection.scrollIntoView({ behavior: "smooth" });

        // Score gauge and badges
        document.getElementById("match-score-value").textContent = data.overall_compatibility + "%";
        
        const badge = document.getElementById("match-tier-badge");
        badge.textContent = data.tier;
        if (data.overall_compatibility >= 90) {
            badge.style.background = "var(--accent-pink)";
        } else if (data.overall_compatibility >= 75) {
            badge.style.background = "var(--accent-purple)";
        } else if (data.overall_compatibility >= 50) {
            badge.style.background = "var(--accent-cyan)";
        } else {
            badge.style.background = "var(--text-muted)";
        }
        
        document.getElementById("match-tier-desc").textContent = data.tier_description;
        document.getElementById("match-narrative").textContent = data.narrative;

        // Progress bars
        document.getElementById("match-breakdown-topics").textContent = data.breakdown.topics + "%";
        document.getElementById("match-breakdown-vibes").textContent = data.breakdown.vibes + "%";
        document.getElementById("match-breakdown-keywords").textContent = data.breakdown.keywords + "%";

        document.getElementById("match-bar-topics").style.width = "0%";
        document.getElementById("match-bar-vibes").style.width = "0%";
        document.getElementById("match-bar-keywords").style.width = "0%";

        setTimeout(() => {
            document.getElementById("match-bar-topics").style.width = data.breakdown.topics + "%";
            document.getElementById("match-bar-vibes").style.width = data.breakdown.vibes + "%";
            document.getElementById("match-bar-keywords").style.width = data.breakdown.keywords + "%";
        }, 100);

        // Venn-chips
        const sharedCont = document.getElementById("match-shared-interests");
        sharedCont.innerHTML = "";
        if (data.interests.shared.length === 0) {
            sharedCont.innerHTML = `<span style="font-size: 0.8rem; color: var(--text-muted);">None</span>`;
        } else {
            data.interests.shared.forEach(i => {
                const chip = document.createElement("span");
                chip.className = "interest-chip";
                chip.style.borderColor = "var(--accent-pink)";
                chip.innerHTML = `<span class="interest-dot" style="background: var(--accent-pink);"></span>${i}`;
                sharedCont.appendChild(chip);
            });
        }

        document.getElementById("match-label-unique-a").textContent = `Unique to ${data.profile_a_label}`;
        const uniqueACont = document.getElementById("match-unique-a");
        uniqueACont.innerHTML = "";
        if (data.interests.unique_a.length === 0) {
            uniqueACont.innerHTML = `<span style="font-size: 0.8rem; color: var(--text-muted);">None</span>`;
        } else {
            data.interests.unique_a.forEach(i => {
                const chip = document.createElement("span");
                chip.className = "interest-chip";
                chip.style.borderColor = "rgba(255,255,255,0.1)";
                chip.innerHTML = i;
                uniqueACont.appendChild(chip);
            });
        }

        document.getElementById("match-label-unique-b").textContent = `Unique to ${data.profile_b_label}`;
        const uniqueBCont = document.getElementById("match-unique-b");
        uniqueBCont.innerHTML = "";
        if (data.interests.unique_b.length === 0) {
            uniqueBCont.innerHTML = `<span style="font-size: 0.8rem; color: var(--text-muted);">None</span>`;
        } else {
            data.interests.unique_b.forEach(i => {
                const chip = document.createElement("span");
                chip.className = "interest-chip";
                chip.style.borderColor = "rgba(255,255,255,0.1)";
                chip.innerHTML = i;
                uniqueBCont.appendChild(chip);
            });
        }

        // Icebreakers
        const icebreakerCont = document.getElementById("match-icebreakers-list");
        icebreakerCont.innerHTML = "";
        data.icebreakers.forEach((s, idx) => {
            const div = document.createElement("div");
            div.className = "suggestion-item";
            div.style.display = "flex";
            div.style.justifyContent = "space-between";
            div.style.alignItems = "center";
            div.innerHTML = `
                <div style="display: flex; align-items: flex-start; gap: 0.75rem;">
                    <span class="suggestion-num" style="background: var(--accent-pink);">${idx + 1}</span>
                    <span class="suggestion-text">${s}</span>
                </div>
                <button class="btn-copy btn-copy-match" data-text="${s.replace(/"/g, '&quot;')}">Copy</button>
            `;
            icebreakerCont.appendChild(div);
        });

        icebreakerCont.querySelectorAll(".btn-copy-match").forEach(btn => {
            btn.addEventListener("click", (e) => {
                const txt = e.target.dataset.text;
                navigator.clipboard.writeText(txt).then(() => {
                    showToast("Icebreaker copied to clipboard!", "success");
                });
            });
        });
    }

    // ---- Helper for Button loading ----
    function setBtnLoading(btn, loading, defaultText, loadingText) {
        if (!btn) return;
        btn.disabled = loading;
        const txtEl = btn.querySelector(".btn-text");
        const loadEl = btn.querySelector(".btn-loading");
        if (txtEl) txtEl.hidden = loading;
        if (loadEl) loadEl.hidden = !loading;
        if (loading && loadEl) {
            const txt = loadEl.querySelector("span");
            if (txt) txt.textContent = loadingText;
        }
    }

    // ---- Render Results dashboard ----
    function renderResults(data) {
        // Reset dashboard visibility state for standard analysis
        document.getElementById("section-profile-overview").style.display = "block";
        document.getElementById("section-engagement-metrics").style.display = "block";
        document.getElementById("section-content-behavior").style.display = "block";
        document.getElementById("section-interest-profiler").style.display = "block";
        document.getElementById("section-conversation-starters").style.display = "block";
        document.getElementById("section-matchmaker-results").style.display = "none";
        document.getElementById("btn-export-report").style.display = "block";

        inputSection.hidden = true;
        resultsSection.hidden = false;
        resultsSection.scrollIntoView({ behavior: "smooth" });

        // Profile overview
        const profileCard = document.getElementById("profile-card");
        if (data.profile_info) {
            profileCard.style.display = "flex";
            document.getElementById("profile-name").textContent = data.profile_info.name || "Unknown";
            document.getElementById("profile-bio").textContent = data.profile_info.bio || "";
            document.getElementById("profile-posts").textContent = formatNum(data.profile_info.post_count);
            document.getElementById("profile-followers").textContent = formatNum(data.profile_info.followers);
            document.getElementById("profile-following").textContent = formatNum(data.profile_info.following);
            document.getElementById("profile-scraped").textContent = data.profile_info.scraped_posts;
        } else {
            profileCard.style.display = "none";
        }

        // Summary
        document.getElementById("summary-text").textContent = data.summary || "";
        document.getElementById("confidence-value").textContent = data.overall_confidence + "%";

        // OCR/Input stats
        const stats = data.input_stats || {};
        document.getElementById("stat-chunks-val").textContent = stats.text_chunks || 0;
        document.getElementById("stat-screenshots-val").textContent = stats.screenshots_processed || 0;
        document.getElementById("stat-tokens-val").textContent = stats.total_tokens || 0;
        document.getElementById("stat-hashtags-val").textContent = stats.total_hashtags || 0;

        // Engagement Metrics
        const eaCard = document.getElementById("engagement-analytics-card");
        const sectionER = document.getElementById("section-engagement-metrics");
        const sectionCB = document.getElementById("section-content-behavior");

        if (data.engagement_analytics && (data.profile_info || data.is_spy)) {
            if (sectionER) sectionER.style.display = "block";
            if (sectionCB) sectionCB.style.display = "block";
            eaCard.hidden = false;
            
            const ea = data.engagement_analytics;
            document.getElementById("metric-er").textContent = `${ea.engagement_rate}%`;
            document.getElementById("metric-likes").textContent = formatNum(ea.total_likes);
            document.getElementById("metric-comments").textContent = formatNum(ea.total_comments);
            document.getElementById("metric-avg-likes").textContent = formatNum(ea.avg_likes);
            
            const avgCommentsEl = document.getElementById("metric-avg-comments");
            if (avgCommentsEl) {
                avgCommentsEl.textContent = formatNum(ea.avg_comments || 0);
            }
            
            // Format ratios
            const fd = ea.format_distribution || {};
            document.getElementById("ratio-reels").textContent = `${fd.Reel || 0}%`;
            document.getElementById("ratio-carousels").textContent = `${fd.Carousel || 0}%`;
            document.getElementById("ratio-images").textContent = `${fd.Image || 0}%`;
            
            // Set initial widths to 0 before animating
            document.getElementById("bar-reels").style.width = "0%";
            document.getElementById("bar-carousels").style.width = "0%";
            document.getElementById("bar-images").style.width = "0%";

            setTimeout(() => {
                document.getElementById("bar-reels").style.width = `${fd.Reel || 0}%`;
                document.getElementById("bar-carousels").style.width = `${fd.Carousel || 0}%`;
                document.getElementById("bar-images").style.width = `${fd.Image || 0}%`;
            }, 100);
            
            // Weekday Frequency
            const wd = ea.weekday_distribution || {};
            const maxVal = Math.max(...Object.values(wd), 1);
            const heatmapContainer = document.getElementById("activity-heatmap");
            if (heatmapContainer) {
                heatmapContainer.innerHTML = "";
                const daysOrder = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
                daysOrder.forEach(day => {
                    const count = wd[day] || 0;
                    const pct = (count / maxVal) * 55; // Scale height to max 55px
                    
                    const col = document.createElement("div");
                    col.style.cssText = "display: flex; flex-direction: column; align-items: center; gap: 4px; flex: 1;";
                    col.innerHTML = `
                        <span style="font-size: 0.65rem; color: var(--accent-cyan); font-weight: 600;">${count}</span>
                        <div class="heatmap-bar" style="width: 14px; height: 0px; background: linear-gradient(180deg, var(--accent-cyan), var(--accent-purple)); border-radius: 6px; transition: height 0.8s cubic-bezier(0.16, 1, 0.3, 1);"></div>
                        <span style="font-size: 0.65rem; color: var(--text-muted); font-weight: 500;">${day.substring(0, 3)}</span>
                    `;
                    heatmapContainer.appendChild(col);
                    
                    setTimeout(() => {
                        const barEl = col.querySelector(".heatmap-bar");
                        if (barEl) barEl.style.height = `${pct}px`;
                    }, 100);
                });
            }
        } else {
            if (sectionER) sectionER.style.display = "none";
            if (sectionCB) sectionCB.style.display = "none";
        }

        // Vibe card
        const vibeCard = document.getElementById("vibe-card");
        if (data.vibe) {
            vibeCard.style.display = "block";
            document.getElementById("vibe-title").textContent = data.vibe.dominant_vibe;
            document.getElementById("vibe-score").textContent = `${data.vibe.vibe_score}% Match`;
            document.getElementById("vibe-desc").textContent = data.vibe.explanation;

            const breakdown = document.getElementById("vibe-breakdown");
            breakdown.innerHTML = "";
            Object.entries(data.vibe.breakdown || {}).forEach(([vibeName, val]) => {
                const row = document.createElement("div");
                row.className = "topic-item";
                row.innerHTML = `
                    <div class="topic-header">
                        <span class="topic-name" style="font-size:0.75rem; color:var(--text-secondary);">${vibeName}</span>
                        <span style="font-size:0.75rem; color:var(--accent-cyan); font-weight:600;">${val}%</span>
                    </div>
                    <div class="topic-bar" style="height:4px;"><div class="topic-bar-fill" style="width: 0%; background:linear-gradient(90deg, var(--accent-cyan), var(--accent-purple));"></div></div>
                `;
                breakdown.appendChild(row);
                requestAnimationFrame(() => {
                    row.querySelector(".topic-bar-fill").style.width = val + "%";
                });
            });
        } else {
            vibeCard.style.display = "none";
        }

        // Top Topics list
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
            requestAnimationFrame(() => {
                const bar = div.querySelector(".topic-bar-fill");
                if (bar) bar.style.width = t.confidence + "%";
            });
        });

        // Common Interest tags
        const interestsList = document.getElementById("interests-list");
        interestsList.innerHTML = "";
        (data.common_interests || []).forEach(i => {
            const chip = document.createElement("span");
            chip.className = "interest-chip";
            chip.innerHTML = `<span class="interest-dot"></span>${i}`;
            interestsList.appendChild(chip);
        });

        // Keywords Cloud
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

        // Hashtags list
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

        // Suggestions with Clipboard Copying
        const suggestionsList = document.querySelector("#section-conversation-starters .suggestions-list");
        if (suggestionsList) {
            suggestionsList.innerHTML = "";
            (data.conversation_suggestions || []).forEach((s, i) => {
                const item = document.createElement("div");
                item.className = "suggestion-item";
                item.style.display = "flex";
                item.style.justifyContent = "space-between";
                item.style.alignItems = "center";
                item.innerHTML = `
                    <div style="display: flex; align-items: flex-start; gap: 0.75rem;">
                        <span class="suggestion-num">${i + 1}</span>
                        <span class="suggestion-text">${s}</span>
                    </div>
                    <button class="btn-copy btn-copy-suggestion" data-text="${s.replace(/"/g, '&quot;')}">Copy</button>
                `;
                suggestionsList.appendChild(item);
            });
            // Attach copy action triggers
            suggestionsList.querySelectorAll(".btn-copy-suggestion").forEach(btn => {
                btn.addEventListener("click", (e) => {
                    const text = e.target.dataset.text;
                    navigator.clipboard.writeText(text).then(() => {
                        showToast("Suggestion copied to clipboard!", "success");
                    });
                });
            });
        }

        // Section 6: Activity Spy Interceptions Timeline
        const spySection = document.getElementById("section-spy-timeline");
        if (data.is_spy && data.spy_data) {
            if (spySection) spySection.style.display = "block";
            const sd = data.spy_data;
            document.getElementById("spy-stat-friends").textContent = sd.friends_scanned || 0;
            document.getElementById("spy-stat-posts").textContent = sd.posts_audited || 0;
            document.getElementById("spy-stat-likes").textContent = sd.likes_intercepted || 0;
            document.getElementById("spy-stat-comments").textContent = sd.comments_intercepted || 0;
            
            const spyList = document.getElementById("spy-interceptions-list");
            if (spyList) {
                spyList.innerHTML = "";
                if (sd.likes.length === 0 && sd.comments.length === 0) {
                    spyList.innerHTML = `<p style="text-align: center; color: var(--text-secondary); font-size: 0.85rem; padding: 1.5rem;">No direct interactions captured on recent posts of followed friends.</p>`;
                } else {
                    sd.likes.forEach(like => {
                        const div = document.createElement("div");
                        div.className = "suggestion-item";
                        div.innerHTML = `
                            <span class="suggestion-num" style="background: var(--accent-pink);">❤️</span>
                            <div class="suggestion-text">
                                Liked post by <strong>@${like.friend_username}</strong>: <span style="font-size:0.8rem; color: var(--text-secondary); font-style: italic;">"${like.post_caption}"</span>
                            </div>
                        `;
                        spyList.appendChild(div);
                    });
                    sd.comments.forEach(comment => {
                        const div = document.createElement("div");
                        div.className = "suggestion-item";
                        div.innerHTML = `
                            <span class="suggestion-num" style="background: var(--accent-purple);">💬</span>
                            <div class="suggestion-text">
                                Commented on post by <strong>@${comment.friend_username}</strong>: "${comment.comment_text}" <br>
                                <span style="font-size:0.75rem; color: var(--text-muted); font-style: italic;">Post: "${comment.post_caption}"</span>
                            </div>
                        `;
                        spyList.appendChild(div);
                    });
                }
            }
        } else {
            if (spySection) spySection.style.display = "none";
        }
    }

    // ---- Reset for New Analysis ----
    if (btnNewAnalysis) {
        btnNewAnalysis.addEventListener("click", () => {
            resultsSection.hidden = true;
            inputSection.hidden = false;
            inputSection.scrollIntoView({ behavior: "smooth" });
        });
    }

    // ---- Number Formatter helper ----
    function formatNum(n) {
        if (!n) return "0";
        if (n >= 1000000) return (n / 1000000).toFixed(1) + "M";
        if (n >= 1000) return (n / 1000).toFixed(1) + "K";
        return n.toString();
    }

    // ---- Toast Notifications Utility ----
    function showToast(message, type = "success") {
        const existing = document.querySelector(".toast-notification");
        if (existing) existing.remove();

        const toast = document.createElement("div");
        toast.className = `toast-notification ${type}`;
        toast.innerHTML = `
            <span>${type === 'success' ? '✓' : '⚠️'}</span>
            <span style="line-height:1.3;">${message}</span>
        `;
        document.body.appendChild(toast);
        setTimeout(() => {
            if (toast.parentNode) toast.remove();
        }, 5000);
    }

    function showError(msg) {
        const existing = document.querySelector(".toast-notification");
        if (existing) existing.remove();
        
        const toast = document.createElement("div");
        toast.className = "toast-notification error";
        
        const isBlock = msg.includes("Instagram") || msg.includes("rate-limiting") || msg.includes("blocked") || msg.includes("403") || msg.includes("429") || msg.includes("credentials");
        if (isBlock) {
            toast.style.flexDirection = "column";
            toast.style.alignItems = "flex-start";
            toast.style.maxWidth = "400px";
            toast.innerHTML = `
                <div style="font-weight: 600; display: flex; align-items: center; gap: 6px;">
                    <span>⚠️</span> Instagram Blocked/Rate-limited
                </div>
                <div style="font-size: 0.78rem; opacity: 0.95; line-height: 1.4; margin: 4px 0 8px 0;">
                    ${msg.replace(/\n/g, '<br>')}
                </div>
                <button class="btn-copy" id="toast-fallback-btn" style="width: 100%; padding: 4px; text-align: center; border-color: rgba(255,255,255,0.2); color: white;">Try Manual Input Instead</button>
            `;
            document.body.appendChild(toast);
            
            const btn = toast.querySelector("#toast-fallback-btn");
            if (btn) {
                btn.addEventListener("click", () => {
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
                    }
                    toast.remove();
                });
            }
        } else {
            toast.innerHTML = `
                <span>⚠️</span>
                <span>${msg}</span>
            `;
            document.body.appendChild(toast);
        }
        setTimeout(() => { if (toast.parentNode) toast.remove(); }, isBlock ? 12000 : 5000);
    }

    // ---- Export Report (Markdown File) ----
    const btnExportReport = document.getElementById("btn-export-report");
    if (btnExportReport) {
        btnExportReport.addEventListener("click", () => {
            if (!lastReportData) return alert("No report data available to export.");
            
            const targetUsername = document.getElementById("target-profile").value.trim() || "instagram_user";
            
            let md = `# InstaLens Report - Target Profile Analysis\n\n`;
            md += `*   **Target Profile**: @${targetUsername}\n`;
            md += `*   **Vibe Rating**: ${lastReportData.vibe ? lastReportData.vibe.dominant_vibe : "Unknown"} (${lastReportData.vibe ? lastReportData.vibe.vibe_score : 0}% Match)\n`;
            md += `*   **Confidence Score**: ${lastReportData.overall_confidence}%\n\n`;
            
            if (lastReportData.engagement_analytics) {
                const ea = lastReportData.engagement_analytics;
                md += `## Engagement & Content Analytics\n`;
                md += `*   **Engagement Rate**: ${ea.engagement_rate}%\n`;
                md += `*   **Total Likes**: ${ea.total_likes.toLocaleString()}\n`;
                md += `*   **Total Comments**: ${ea.total_comments.toLocaleString()}\n`;
                md += `*   **Average Likes**: ${ea.avg_likes.toLocaleString()}\n`;
                md += `*   **Average Comments**: ${(ea.avg_comments || 0).toLocaleString()}\n\n`;
                
                md += `### Content Format Distribution\n`;
                md += `*   **Reels**: ${ea.format_distribution.Reel}%\n`;
                md += `*   **Carousels**: ${ea.format_distribution.Carousel}%\n`;
                md += `*   **Images**: ${ea.format_distribution.Image}%\n\n`;
                
                md += `### Weekday Posting Activity\n`;
                Object.entries(ea.weekday_distribution).forEach(([day, count]) => {
                    md += `*   **${day}**: ${count} posts\n`;
                });
                md += `\n`;
            }
            
            md += `## Dominant Vibe Description\n> ${lastReportData.vibe ? lastReportData.vibe.explanation : "N/A"}\n\n`;
            md += `## Interests & Key Topics\n`;
            (lastReportData.top_topics || []).forEach(t => {
                md += `*   **${t.name}** (${t.confidence}% confidence)\n`;
                const kw = (t.matched_keywords || []).concat(t.matched_hashtags || []);
                if (kw.length) {
                    md += `    *   Keywords: ${kw.join(", ")}\n`;
                }
            });
            md += `\n`;
            
            md += `## Common Keywords\n`;
            md += (lastReportData.repeated_keywords || []).map(k => `*   \`${k.word}\``).join("\n") + "\n\n";
            
            md += `## Trending Hashtags\n`;
            md += (lastReportData.repeated_hashtags || []).map(h => `*   #${h.tag} (seen ×${h.count})`).join("\n") + "\n\n";
            
            md += `## Conversation Icebreakers\n`;
            (lastReportData.conversation_suggestions || []).forEach((s, idx) => {
                md += `${idx + 1}.  "${s}"\n`;
            });
            md += `\n---\n*Report generated locally by InstaLens.*`;
            
            const blob = new Blob([md], { type: "text/markdown" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `instalens_report_${targetUsername.replace(/https:\/\/instagram.com\//g, '').replace(/[^a-zA-Z0-9]/g, '_')}.md`;
            a.click();
            showToast("Report exported successfully!", "success");
        });
    }

    // ---- Taxonomy Modal Actions ----
    const btnTaxonomySettings = document.getElementById("btn-taxonomy-settings");
    const taxonomyModal = document.getElementById("taxonomy-modal");
    const btnCloseTaxonomy = document.getElementById("btn-close-taxonomy");
    const taxonomyListContainer = document.getElementById("taxonomy-list-container");
    const btnAddTaxonomyCategory = document.getElementById("btn-add-taxonomy-category");
    const btnResetTaxonomy = document.getElementById("btn-reset-taxonomy");
    const btnSaveTaxonomy = document.getElementById("btn-save-taxonomy");

    let activeTaxonomy = {};

    if (btnTaxonomySettings) {
        btnTaxonomySettings.addEventListener("click", openTaxonomyModal);
    }
    if (btnCloseTaxonomy) {
        btnCloseTaxonomy.addEventListener("click", () => taxonomyModal.hidden = true);
    }

    async function openTaxonomyModal() {
        taxonomyModal.hidden = false;
        setLoadingTaxonomy(true);
        try {
            const res = await fetch("/api/taxonomy");
            activeTaxonomy = await res.json();
            renderTaxonomyEditor();
        } catch (err) {
            showError("Failed to load taxonomy settings.");
        } finally {
            setLoadingTaxonomy(false);
        }
    }

    function setLoadingTaxonomy(loading) {
        if (loading && taxonomyListContainer) {
            taxonomyListContainer.innerHTML = `<div style="text-align: center; padding: 2rem;"><div class="spinner" style="margin: 0 auto;"></div><p style="margin-top: 10px; color: var(--text-secondary);">Loading taxonomy...</p></div>`;
        }
    }

    function renderTaxonomyEditor() {
        if (!taxonomyListContainer) return;
        taxonomyListContainer.innerHTML = "";
        Object.entries(activeTaxonomy).forEach(([catName, data]) => {
            const card = document.createElement("div");
            card.className = "taxonomy-cat-card";
            card.innerHTML = `
                <div class="taxonomy-cat-header">
                    <span class="taxonomy-cat-title">${catName}</span>
                    <button class="btn-delete-cat" data-cat="${catName}">Delete</button>
                </div>
                <div style="display: flex; flex-direction: column; gap: 8px;">
                    <div class="input-group">
                        <label style="font-size: 0.75rem;">Keywords (comma separated)</label>
                        <input type="text" class="input-field tax-kws" data-cat="${catName}" value="${data.keywords.join(', ')}">
                    </div>
                    <div class="input-group">
                        <label style="font-size: 0.75rem;">Hashtags (comma separated)</label>
                        <input type="text" class="input-field tax-hts" data-cat="${catName}" value="${data.hashtags.join(', ')}">
                    </div>
                </div>
            `;
            taxonomyListContainer.appendChild(card);
        });

        taxonomyListContainer.querySelectorAll(".btn-delete-cat").forEach(btn => {
            btn.addEventListener("click", (e) => {
                const cat = e.target.dataset.cat;
                delete activeTaxonomy[cat];
                renderTaxonomyEditor();
            });
        });
    }

    if (btnAddTaxonomyCategory) {
        btnAddTaxonomyCategory.addEventListener("click", () => {
            const catName = prompt("Enter new category name (e.g. Cooking, Finance):");
            if (!catName || !catName.trim()) return;
            const trimmed = catName.trim();
            if (activeTaxonomy[trimmed]) {
                return alert("Category already exists!");
            }
            activeTaxonomy[trimmed] = { keywords: [], hashtags: [] };
            renderTaxonomyEditor();
            taxonomyListContainer.scrollTop = taxonomyListContainer.scrollHeight;
        });
    }

    if (btnSaveTaxonomy) {
        btnSaveTaxonomy.addEventListener("click", async () => {
            taxonomyListContainer.querySelectorAll(".taxonomy-cat-card").forEach(card => {
                const kwInput = card.querySelector(".tax-kws");
                const htInput = card.querySelector(".tax-hts");
                const catName = kwInput.dataset.cat;

                activeTaxonomy[catName].keywords = kwInput.value.split(",")
                    .map(s => s.trim().toLowerCase()).filter(s => s.length > 0);
                activeTaxonomy[catName].hashtags = htInput.value.split(",")
                    .map(s => s.trim().toLowerCase().replace("#", "")).filter(s => s.length > 0);
            });

            setBtnLoading(btnSaveTaxonomy, true, "Save Changes", "Saving...");
            try {
                const res = await fetch("/api/taxonomy", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(activeTaxonomy)
                });
                const data = await res.json();
                if (data.success) {
                    taxonomyModal.hidden = true;
                    showToast("Taxonomy saved successfully!", "success");
                } else {
                    showError(data.error || "Failed to save taxonomy.");
                }
            } catch (err) {
                showError("Error connecting to server to save taxonomy.");
            } finally {
                setBtnLoading(btnSaveTaxonomy, false, "Save Changes", "");
            }
        });
    }

    if (btnResetTaxonomy) {
        btnResetTaxonomy.addEventListener("click", () => {
            if (confirm("Are you sure you want to reset to default taxonomy categories? This will overwrite your current settings.")) {
                activeTaxonomy = {
                    "Fitness & Gym": { "keywords": ["gym", "workout", "fitness", "exercise"], "hashtags": ["gym", "fitness"] },
                    "Love & Relationships": { "keywords": ["love", "heart", "relationship", "couple"], "hashtags": ["love", "relationship"] },
                    "College & Student Life": { "keywords": ["college", "university", "exam", "student"], "hashtags": ["collegelife", "student"] },
                    "Humor & Memes": { "keywords": ["meme", "funny", "joke"], "hashtags": ["meme", "funny"] },
                    "Cricket & Sports": { "keywords": ["cricket", "football", "match"], "hashtags": ["cricket", "sports"] },
                    "Movies & Entertainment": { "keywords": ["movie", "film", "netflix"], "hashtags": ["movie", "netflix"] },
                    "Music": { "keywords": ["music", "song", "playlist"], "hashtags": ["music", "song"] },
                    "Food & Cooking": { "keywords": ["food", "recipe", "cooking"], "hashtags": ["food", "cooking"] },
                    "Travel & Adventure": { "keywords": ["travel", "trip", "explore"], "hashtags": ["travel", "adventure"] },
                    "Technology & Coding": { "keywords": ["tech", "code", "ai", "developer"], "hashtags": ["tech", "coding"] }
                };
                renderTaxonomyEditor();
            }
        });
    }
});
