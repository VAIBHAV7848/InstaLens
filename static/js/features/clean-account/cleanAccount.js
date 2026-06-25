document.addEventListener('DOMContentLoaded', () => {
    // UI Elements
    const btnRunClean = document.getElementById('btn-run-clean');
    const statusContainer = document.getElementById('clean-status-container');
    const statusText = document.getElementById('clean-status-text');
    const statusCount = document.getElementById('clean-status-count');
    const resultsContainer = document.getElementById('clean-results-container');
    const tableBody = document.getElementById('clean-table-body');
    const progressBar = document.getElementById('clean-progress-bar');
    
    // Stats elements
    const statSuccess = document.getElementById('clean-stat-success');
    const statFailed = document.getElementById('clean-stat-failed');
    const statSkipped = document.getElementById('clean-stat-skipped');
    
    // Action elements
    const btnSelectAll = document.getElementById('btn-select-all');
    const btnDeselectAll = document.getElementById('btn-deselect-all');
    const searchInput = document.getElementById('clean-search');
    const btnBulkUnfollow = document.getElementById('btn-bulk-unfollow');
    const btnBulkRemoveFollower = document.getElementById('btn-bulk-remove-follower');
    const btnCancelUnfollow = document.getElementById('btn-cancel-unfollow');
    
    // Filters
    const filterNonFollowers = document.getElementById('filter-non-followers');
    const filterFans = document.getElementById('filter-fans');
    const filterMutual = document.getElementById('filter-mutual');

    let following = new Map();
    let followers = new Map();
    let currentFilter = 'non-followers'; // 'non-followers', 'fans', 'mutual'
    let whitelist = new Set();
    let isProcessing = false;
    let actionQueue = [];
    let actionStats = { success: 0, failed: 0, skipped: 0, total: 0 };

    // Fetch whitelist on load
    fetchWhitelist();

    async function fetchWhitelist() {
        try {
            const res = await fetch('/api/clean_account/whitelist');
            const data = await res.json();
            if (Array.isArray(data)) {
                whitelist = new Set(data);
            }
        } catch (e) {
            console.error('Failed to load whitelist', e);
        }
    }

    async function saveWhitelist() {
        try {
            await fetch('/api/clean_account/whitelist', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(Array.from(whitelist))
            });
        } catch (e) {
            console.error('Failed to save whitelist', e);
        }
    }

    /** Update filter button active state and toggle action buttons */
    function updateFilterUI() {
        const filters = [
            { btn: filterNonFollowers, key: 'non-followers' },
            { btn: filterFans, key: 'fans' },
            { btn: filterMutual, key: 'mutual' }
        ];
        filters.forEach(({ btn, key }) => {
            if (!btn) return;
            if (key === currentFilter) {
                btn.style.background = 'rgba(168, 85, 247, 0.15)';
                btn.style.borderColor = 'var(--accent-purple)';
                btn.style.color = 'var(--accent-purple)';
            } else {
                btn.style.background = '';
                btn.style.borderColor = '';
                btn.style.color = '';
            }
        });

        // Show/hide action buttons based on filter
        if (btnBulkUnfollow) {
            btnBulkUnfollow.style.display = (currentFilter === 'non-followers') ? 'inline-block' : 'none';
        }
        if (btnBulkRemoveFollower) {
            btnBulkRemoveFollower.style.display = (currentFilter === 'fans') ? 'inline-block' : 'none';
        }

        // Update action hint text
        const hintText = document.getElementById('clean-action-hint-text');
        if (hintText) {
            if (currentFilter === 'non-followers') {
                hintText.textContent = 'These accounts don\'t follow you back. Select them and click "❌ Unfollow Selected" to stop following them.';
            } else if (currentFilter === 'fans') {
                hintText.textContent = 'These people follow you but you don\'t follow them back. Select them and click "🚫 Remove from My Followers" to remove them from your followers list.';
            } else {
                hintText.textContent = 'These are your mutual connections — you follow each other. No bulk action available for mutuals.';
            }
        }
    }

    if (btnRunClean) {
        btnRunClean.addEventListener('click', async () => {
            btnRunClean.disabled = true;
            const btnText = btnRunClean.querySelector('.btn-text');
            const btnLoading = btnRunClean.querySelector('.btn-loading');
            if (btnText) btnText.hidden = true;
            if (btnLoading) btnLoading.hidden = false;

            statusContainer.style.display = 'block';
            resultsContainer.style.display = 'none';
            following.clear();
            followers.clear();
            
            try {
                // Fetch Following
                statusText.innerText = 'Fetching Following list...';
                await fetchConnections('following', following);
                
                // Fetch Followers
                statusText.innerText = 'Fetching Followers list...';
                await fetchConnections('followers', followers);

                // Compute counts
                let nonFollowBackCount = 0;
                let fansCount = 0;
                let mutualCount = 0;
                const allUsers = new Set([...following.keys(), ...followers.keys()]);
                allUsers.forEach(username => {
                    const isFollowing = following.has(username);
                    const isFollower = followers.has(username);
                    if (isFollowing && !isFollower) nonFollowBackCount++;
                    else if (!isFollowing && isFollower) fansCount++;
                    else if (isFollowing && isFollower) mutualCount++;
                });

                statusText.innerText = `Analysis Complete — Following: ${following.size} · Followers: ${followers.size}`;

                // Update filter button labels with counts
                if (filterNonFollowers) filterNonFollowers.textContent = `❌ I Follow · They Don't (${nonFollowBackCount})`;
                if (filterFans) filterFans.textContent = `🚫 They Follow · I Don't (${fansCount})`;
                if (filterMutual) filterMutual.textContent = `🤝 Mutual (${mutualCount})`;

                resultsContainer.style.display = 'block';
                updateFilterUI();
                renderTable();
            } catch (err) {
                statusText.innerText = `Error: ${err.message}`;
            } finally {
                btnRunClean.disabled = false;
                if (btnText) btnText.hidden = false;
                if (btnLoading) btnLoading.hidden = true;
            }
        });
    }

    async function fetchConnections(type, mapStorage) {
        return new Promise((resolve, reject) => {
            const formData = new FormData();
            formData.append('type', type);
            
            fetch('/api/clean_account/fetch', {
                method: 'POST',
                body: formData
            }).then(response => {
                if (!response.ok) throw new Error('Network error');
                
                const reader = response.body.getReader();
                const decoder = new TextDecoder("utf-8");
                let buffer = "";
                
                function processStream() {
                    reader.read().then(({done, value}) => {
                        if (done) {
                            resolve();
                            return;
                        }
                        
                        buffer += decoder.decode(value, {stream: true});
                        let events = buffer.split("\n\n");
                        buffer = events.pop();
                        
                        for (let ev of events) {
                            if (ev.startsWith("data: ")) {
                                try {
                                    let data = JSON.parse(ev.substring(6));
                                    if (data.error) {
                                        reject(new Error(data.error));
                                        return;
                                    }
                                    if (data.status) {
                                        statusText.innerText = data.status;
                                    }
                                    if (data.result && data.type === type) {
                                        data.result.forEach(u => mapStorage.set(u.username, u));
                                    }
                                } catch (e) {}
                            }
                        }
                        processStream();
                    }).catch(reject);
                }
                processStream();
            }).catch(reject);
        });
    }

    function renderTable() {
        tableBody.innerHTML = '';
        let listToShow = [];
        const searchTerm = searchInput.value.toLowerCase();
        
        const allUsers = new Set([...following.keys(), ...followers.keys()]);
        
        allUsers.forEach(username => {
            const isFollowing = following.has(username);
            const isFollower = followers.has(username);
            const userObj = following.get(username) || followers.get(username);
            
            let include = false;
            let statusBadge = '';
            
            if (currentFilter === 'non-followers' && isFollowing && !isFollower) {
                include = true;
                statusBadge = '<span style="color: var(--accent-red); font-size: 0.75rem; border: 1px solid var(--accent-red); padding: 2px 6px; border-radius: 10px;">Not Following Back</span>';
            } else if (currentFilter === 'fans' && !isFollowing && isFollower) {
                include = true;
                statusBadge = '<span style="color: var(--accent-cyan); font-size: 0.75rem; border: 1px solid var(--accent-cyan); padding: 2px 6px; border-radius: 10px;">Fan</span>';
            } else if (currentFilter === 'mutual' && isFollowing && isFollower) {
                include = true;
                statusBadge = '<span style="color: var(--accent-green); font-size: 0.75rem; border: 1px solid var(--accent-green); padding: 2px 6px; border-radius: 10px;">Mutual</span>';
            }
            
            if (include && userObj) {
                if (searchTerm && !username.toLowerCase().includes(searchTerm) && !(userObj.fullName && userObj.fullName.toLowerCase().includes(searchTerm))) {
                    include = false;
                }
            }
            
            if (include) {
                listToShow.push({ ...userObj, statusBadge });
            }
        });
        
        listToShow.forEach(user => {
            const tr = document.createElement('tr');
            tr.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
            const isWhitelisted = whitelist.has(user.username);
            
            tr.innerHTML = `
                <td style="padding: 0.75rem;">
                    <input type="checkbox" class="user-select-cb" data-username="${user.username}" ${isWhitelisted ? 'disabled' : ''}>
                </td>
                <td style="padding: 0.75rem; display: flex; align-items: center; gap: 10px;">
                    <div style="width: 32px; height: 32px; border-radius: 50%; background: #333; overflow: hidden; display: flex; align-items: center; justify-content: center; font-size: 10px;">
                        ${user.avatar ? `<img src="/api/proxy_image?url=${encodeURIComponent(user.avatar)}" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.outerHTML='👤'">` : '👤'}
                    </div>
                    <div>
                        <div style="font-weight: 600;">${user.username} ${user.verified ? '✓' : ''}</div>
                        <div style="font-size: 0.75rem; color: var(--text-secondary);">${user.fullName || ''}</div>
                    </div>
                </td>
                <td style="padding: 0.75rem;">${user.statusBadge}</td>
                <td style="padding: 0.75rem;">
                    <button class="btn-whitelist" data-username="${user.username}" style="background: none; border: none; cursor: pointer; font-size: 1.2rem; filter: grayscale(${isWhitelisted ? '0' : '1'}); opacity: ${isWhitelisted ? '1' : '0.3'};">⭐</button>
                </td>
            `;
            tableBody.appendChild(tr);
        });
        
        // Attach whitelist events
        document.querySelectorAll('.btn-whitelist').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const uname = e.currentTarget.dataset.username;
                if (whitelist.has(uname)) {
                    whitelist.delete(uname);
                    e.currentTarget.style.filter = 'grayscale(1)';
                    e.currentTarget.style.opacity = '0.3';
                } else {
                    whitelist.add(uname);
                    e.currentTarget.style.filter = 'grayscale(0)';
                    e.currentTarget.style.opacity = '1';
                }
                saveWhitelist();
                
                // Update checkbox disabled state
                const cb = document.querySelector(`.user-select-cb[data-username="${uname}"]`);
                if (cb) {
                    cb.disabled = whitelist.has(uname);
                    if (cb.disabled) cb.checked = false;
                }
            });
        });
    }

    // --- Filter event listeners ---
    if (filterNonFollowers) {
        filterNonFollowers.addEventListener('click', () => {
            currentFilter = 'non-followers';
            updateFilterUI();
            renderTable();
        });
    }
    if (filterFans) {
        filterFans.addEventListener('click', () => {
            currentFilter = 'fans';
            updateFilterUI();
            renderTable();
        });
    }
    if (filterMutual) {
        filterMutual.addEventListener('click', () => {
            currentFilter = 'mutual';
            updateFilterUI();
            renderTable();
        });
    }
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            renderTable();
        });
    }

    if (btnSelectAll) {
        btnSelectAll.addEventListener('click', () => {
            document.querySelectorAll('.user-select-cb:not([disabled])').forEach(cb => cb.checked = true);
        });
    }
    if (btnDeselectAll) {
        btnDeselectAll.addEventListener('click', () => {
            document.querySelectorAll('.user-select-cb').forEach(cb => cb.checked = false);
        });
    }

    // --- Bulk Unfollow ---
    if (btnBulkUnfollow) {
        btnBulkUnfollow.addEventListener('click', async () => {
            const selected = Array.from(document.querySelectorAll('.user-select-cb:checked')).map(cb => cb.dataset.username);
            if (selected.length === 0) return;
            
            if (!confirm(`You are about to unfollow:\n\n${selected.length} accounts\n\nContinue?`)) {
                return;
            }
            
            actionQueue = selected;
            isProcessing = true;
            actionStats = { success: 0, failed: 0, skipped: 0, total: selected.length };
            
            btnBulkUnfollow.style.display = 'none';
            btnCancelUnfollow.style.display = 'inline-block';
            statusContainer.style.display = 'block';
            progressBar.style.width = '0%';
            
            processActionQueue('unfollow');
        });
    }

    // --- Bulk Remove Followers ---
    if (btnBulkRemoveFollower) {
        btnBulkRemoveFollower.addEventListener('click', async () => {
            const selected = Array.from(document.querySelectorAll('.user-select-cb:checked')).map(cb => cb.dataset.username);
            if (selected.length === 0) return;

            if (!confirm(`You are about to REMOVE these followers:\n\n${selected.length} accounts\n\nThey will no longer follow you. Continue?`)) {
                return;
            }

            actionQueue = selected;
            isProcessing = true;
            actionStats = { success: 0, failed: 0, skipped: 0, total: selected.length };

            btnBulkRemoveFollower.style.display = 'none';
            btnCancelUnfollow.style.display = 'inline-block';
            statusContainer.style.display = 'block';
            progressBar.style.width = '0%';

            processActionQueue('remove_follower');
        });
    }

    // --- Cancel ---
    if (btnCancelUnfollow) {
        btnCancelUnfollow.addEventListener('click', () => {
            isProcessing = false;
            btnCancelUnfollow.style.display = 'none';
            updateFilterUI();
            statusText.innerText = 'Operation Cancelled.';
        });
    }

    /**
     * Unified queue processor for both unfollow and remove_follower actions.
     * @param {'unfollow' | 'remove_follower'} actionType
     */
    async function processActionQueue(actionType) {
        const actionLabel = actionType === 'remove_follower' ? 'Removing follower' : 'Unfollowing';
        const endpoint = actionType === 'remove_follower'
            ? '/api/clean_account/remove_follower'
            : '/api/clean_account/unfollow';

        if (!isProcessing || actionQueue.length === 0) {
            isProcessing = false;
            btnCancelUnfollow.style.display = 'none';
            updateFilterUI();
            if (actionQueue.length === 0) {
                statusText.innerText = `${actionType === 'remove_follower' ? 'Remove Followers' : 'Unfollow'} Operation Completed.`;
            }
            renderTable();
            return;
        }

        const username = actionQueue.shift();

        statusText.innerText = `${actionLabel} @${username}...`;
        const currentProgress = actionStats.total - actionQueue.length;
        statusCount.innerText = `${currentProgress} / ${actionStats.total}`;
        progressBar.style.width = `${(currentProgress / actionStats.total) * 100}%`;

        if (whitelist.has(username)) {
            actionStats.skipped++;
            updateStats();
            setTimeout(() => processActionQueue(actionType), 500);
            return;
        }

        try {
            const res = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target: username })
            });
            const data = await res.json();

            if (data.success) {
                actionStats.success++;
                if (actionType === 'remove_follower') {
                    followers.delete(username);
                } else {
                    following.delete(username);
                }
            } else {
                actionStats.failed++;
                console.error(`Failed to ${actionType} ${username}: ${data.error}`);
            }
        } catch (e) {
            actionStats.failed++;
        }

        updateStats();

        // Random delay between 2-5 seconds to avoid rate limits
        const delay = Math.floor(Math.random() * 3000) + 2000;
        setTimeout(() => processActionQueue(actionType), delay);
    }
    
    function updateStats() {
        statSuccess.innerText = `Success: ${actionStats.success}`;
        statFailed.innerText = `Failed: ${actionStats.failed}`;
        statSkipped.innerText = `Skipped: ${actionStats.skipped}`;
    }
});
