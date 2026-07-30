document.addEventListener('DOMContentLoaded', () => {
    const loginModal = document.getElementById('login-modal');
    const appContent = document.getElementById('app-content');
    const loginForm = document.getElementById('login-form');
    const loginError = document.getElementById('login-error');
    
    let telemetryInterval;

    // Check if user is already logged in
    const token = sessionStorage.getItem('access_token');
    if (window.location.hash.startsWith('#invite=')) {
        loginModal.style.display = 'none';
        appContent.style.display = 'none';
        document.getElementById('register-modal').style.display = 'flex';
    } else if (token) {
        showApp(token);
    } else {
        loginModal.style.display = 'flex';
        appContent.style.display = 'none';
    }

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        
        loginError.textContent = '';
        
        try {
            // OAuth2 requires URL-encoded form data
            const formData = new URLSearchParams();
            formData.append('username', username);
            formData.append('password', password);

            const response = await fetch('/api/token', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Authentication failed');
            }

            const data = await response.json();
            sessionStorage.setItem('access_token', data.access_token);
            
            showApp(data.access_token);
        } catch (err) {
            loginError.textContent = err.message;
        }
    });

    function showApp(token) {
        loginModal.style.display = 'none';
        appContent.style.display = 'block';
        startTelemetry(token);
    }

    function startTelemetry(token) {
        if (telemetryInterval) clearInterval(telemetryInterval);
        
        const cpuStat = document.getElementById('cpu-stat');
        const ramStat = document.getElementById('ram-stat');
        const usersStat = document.getElementById('users-stat');
        
        const fetchStats = async () => {
            try {
                const response = await fetch('/api/system/telemetry', {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
                
                if (response.status === 401) {
                    // Token expired
                    sessionStorage.removeItem('access_token');
                    clearInterval(telemetryInterval);
                    alert("Session expired. Please log in again.");
                    window.location.reload();
                    return;
                }
                
                const data = await response.json();
                cpuStat.textContent = `${data.cpu_percent}%`;
                ramStat.textContent = `${data.ram_gb}GB`;
                usersStat.textContent = `${data.active_users} Active`;
                
                // Update badges
                const aiBadge = document.getElementById('ai-badge');
                if (data.ai_status === "Ready") {
                    aiBadge.textContent = "Llama 3 (Ready)";
                    aiBadge.className = "badge active";
                    aiBadge.style.display = "inline-block";
                } else {
                    aiBadge.textContent = "Offline";
                    aiBadge.className = "badge error";
                    aiBadge.style.display = "inline-block";
                }
                
                const sharedBadge = document.getElementById('shared-badge');
                if (data.shared_expiring_soon > 0) {
                    sharedBadge.textContent = `${data.shared_expiring_soon} Expiring Soon`;
                    sharedBadge.style.display = "inline-block";
                } else {
                    sharedBadge.style.display = "none";
                }
                
            } catch (err) {
                console.error("Failed to fetch telemetry:", err);
            }
        };
        
        fetchStats(); // Fetch immediately
        telemetryInterval = setInterval(fetchStats, 5000); // Poll every 5s
    }
});

// ================= NAVIGATION & MODALS =================
function closeModal(id) {
    document.getElementById(id).style.display = 'none';
    if(id === 'lightbox-modal') {
        document.getElementById('lightbox-img').src = '';
        document.getElementById('lightbox-controls').style.display = 'flex'; // restore
    }
}

// ================= CUSTOM DIALOGS =================
function customConfirm(message) {
    return new Promise((resolve) => {
        const modal = document.getElementById('custom-confirm');
        document.getElementById('confirm-text').textContent = message;
        modal.style.display = 'flex';
        
        document.getElementById('confirm-ok').onclick = () => {
            modal.style.display = 'none';
            resolve(true);
        };
        document.getElementById('confirm-cancel').onclick = () => {
            modal.style.display = 'none';
            resolve(false);
        };
    });
}

function customPrompt(message) {
    return new Promise((resolve) => {
        const modal = document.getElementById('custom-prompt');
        document.getElementById('prompt-text').textContent = message;
        const input = document.getElementById('prompt-input');
        input.value = '';
        modal.style.display = 'flex';
        input.focus();
        
        document.getElementById('prompt-ok').onclick = () => {
            modal.style.display = 'none';
            resolve(input.value);
        };
        document.getElementById('prompt-cancel').onclick = () => {
            modal.style.display = 'none';
            resolve(null);
        };
    });
}

function logout() {
    sessionStorage.removeItem('access_token');
    window.location.reload();
}

function getAuthHeaders() {
    return {
        'Authorization': `Bearer ${sessionStorage.getItem('access_token')}`
    };
}

// ================= GALLERY LOGIC =================
let selectedMediaIds = new Set();
let galleryItems = {}; // To easily map id to filename

async function fetchMediaBlob(id) {
    const res = await fetch(`/api/media/download/${id}`, { headers: getAuthHeaders() });
    if (!res.ok) throw new Error("Failed to fetch media blob");
    return await res.blob();
}

function openMedia() {
    document.getElementById('gallery-modal').style.display = 'flex';
    selectedMediaIds.clear();
    updateBulkActionBar();
    loadGallery();
}

async function loadGallery() {
    const grid = document.getElementById('gallery-grid');
    grid.innerHTML = '<div style="color:var(--neon-cyan)">Loading encrypted media...</div>';
    
    try {
        const res = await fetch('/api/media/list', { headers: getAuthHeaders() });
        if (!res.ok) throw new Error("Failed to fetch media");
        const items = await res.json();
        
        grid.innerHTML = '';
        if (items.length === 0) {
            grid.innerHTML = '<div style="color:var(--text-secondary)">No encrypted media found.</div>';
            return;
        }

        galleryItems = {}; // reset map

        for (const item of items) {
            galleryItems[item.id] = item;
            
            try {
                const imgBlob = await fetchMediaBlob(item.id);
                const url = URL.createObjectURL(imgBlob);
                item.url = url; // save for lightbox
                
                const div = document.createElement('div');
                div.className = 'gallery-item';
                div.innerHTML = `
                    <input type="checkbox" class="item-select-checkbox" ${selectedMediaIds.has(item.id) ? 'checked' : ''} onclick="toggleSelection('${item.id}', this, event)">
                    <img src="${url}" alt="${item.filename}" onclick="openLightbox('${item.id}')">
                    <div class="item-overlay">
                        <span class="item-name">${item.filename}</span>
                        <div class="item-actions">
                            <button class="action-btn" onclick="downloadMedia('${item.id}', '${item.filename}')"><i class="ph ph-download-simple"></i></button>
                            <button class="action-btn" onclick="shareMedia('${item.id}')"><i class="ph ph-share-network"></i></button>
                            <button class="action-btn delete-btn" onclick="deleteMedia('${item.id}')"><i class="ph ph-trash"></i></button>
                        </div>
                    </div>
                `;
                grid.appendChild(div);
            } catch (e) {
                const div = document.createElement('div');
                div.className = 'gallery-item';
                div.innerHTML = `<i class="ph ph-warning-circle" style="color:red"></i>`;
                grid.appendChild(div);
            }
        }
    } catch (e) {
        grid.innerHTML = `<div style="color:red">${e.message}</div>`;
    }
}

document.getElementById('media-upload-input')?.addEventListener('change', async (e) => {
    const files = e.target.files;
    if (files.length === 0) return;
    
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        // Must match the 'files' parameter in FastAPI
        formData.append('files', files[i]);
    }
    
    // Clear input
    e.target.value = '';
    
    const grid = document.getElementById('gallery-grid');
    grid.innerHTML = `<div style="color:var(--neon-cyan)">Encrypting and uploading ${files.length} file(s)...</div>`;
    
    try {
        const res = await fetch('/api/media/upload', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: formData
        });
        if (res.ok) {
            loadGallery();
        } else {
            const err = await res.json();
            alert("Upload failed: " + err.detail);
            loadGallery();
        }
    } catch (err) {
        alert("Upload error.");
        loadGallery();
    }
});

// ================= BULK ACTIONS & SELECTION =================
function toggleSelection(id, checkboxElem, event) {
    event.stopPropagation();
    // Use string/number conversion safety if needed, IDs are passed as strings here
    const numericId = parseInt(id, 10);
    if (checkboxElem.checked) {
        selectedMediaIds.add(numericId);
    } else {
        selectedMediaIds.delete(numericId);
    }
    updateBulkActionBar();
}

function updateBulkActionBar() {
    const bar = document.getElementById('bulk-action-bar');
    const count = document.getElementById('bulk-count');
    
    if (selectedMediaIds.size > 0) {
        bar.style.display = 'flex';
        count.textContent = `${selectedMediaIds.size} selected`;
    } else {
        bar.style.display = 'none';
    }
}

function clearSelection() {
    selectedMediaIds.clear();
    updateBulkActionBar();
    loadGallery(); // Repaint checkboxes
}

async function bulkDownload() {
    for (let id of selectedMediaIds) {
        const item = galleryItems[id];
        if (item) {
            await downloadMedia(id, item.filename);
            // small delay to prevent browser overload
            await new Promise(r => setTimeout(r, 500));
        }
    }
    clearSelection();
}

async function bulkDelete() {
    const sure = await customConfirm(`Are you sure you want to securely shred ${selectedMediaIds.size} file(s)?`);
    if (!sure) return;
    
    for (let id of selectedMediaIds) {
        try {
            await fetch(`/api/media/delete/${id}`, { method: 'DELETE', headers: getAuthHeaders() });
        } catch (e) {}
    }
    clearSelection(); // triggers reload
}

async function bulkShare() {
    const settings = await shareSettingsPrompt();
    if (!settings) return;
    
    for (let id of selectedMediaIds) {
        const formData = new FormData();
        formData.append('target_username', settings.username);
        formData.append('expires_in_hours', settings.days * 24);
        
        try {
            await fetch(`/api/media/share/${id}`, {
                method: 'POST',
                headers: getAuthHeaders(),
                body: formData
            });
        } catch (e) {}
    }
    alert("Bulk share completed! Ephemeral Keys were generated.");
    clearSelection();
}

// ================= LIGHTBOX & DOWNLOAD =================
let currentLightboxMediaId = null;

function openLightbox(id) {
    currentLightboxMediaId = parseInt(id, 10);
    const item = galleryItems[currentLightboxMediaId];
    if(!item) return;
    
    const modal = document.getElementById('lightbox-modal');
    document.getElementById('lightbox-img').src = item.url;
    modal.style.display = 'flex';
}

async function lightboxDownload() {
    if(!currentLightboxMediaId) return;
    const item = galleryItems[currentLightboxMediaId];
    await downloadMedia(currentLightboxMediaId, item.filename);
}

async function lightboxDelete() {
    if(!currentLightboxMediaId) return;
    await deleteMedia(currentLightboxMediaId);
    closeModal('lightbox-modal');
}

async function lightboxShare() {
    if(!currentLightboxMediaId) return;
    await shareMedia(currentLightboxMediaId);
}

async function downloadMedia(id, filename) {
    const blob = await fetchMediaBlob(id);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// ================= SHARE & DELETE =================
async function deleteMedia(id) {
    const sure = await customConfirm("Are you sure you want to securely shred this file?");
    if (!sure) return;
    
    try {
        const res = await fetch(`/api/media/delete/${id}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        if (res.ok) {
            loadGallery();
        } else {
            alert("Delete failed.");
        }
    } catch (err) {
        alert("Delete error.");
    }
}

async function shareMedia(id) {
    const settings = await shareSettingsPrompt();
    if (!settings) return;
    
    const formData = new FormData();
    formData.append('target_username', settings.username);
    formData.append('expires_in_hours', settings.days * 24);
    
    try {
        const res = await fetch(`/api/media/share/${id}`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: formData
        });
        if (res.ok) {
            alert("Shared securely! An Ephemeral Key was generated.");
        } else {
            const err = await res.json();
            alert("Share failed: " + err.detail);
        }
    } catch (err) {
        alert("Share error.");
    }
}

function shareSettingsPrompt() {
    return new Promise((resolve) => {
        const modal = document.getElementById('share-settings-modal');
        const input = document.getElementById('share-username-input');
        const select = document.getElementById('share-expires-select');
        
        input.value = '';
        select.value = '1';
        modal.style.display = 'flex';
        input.focus();
        
        document.getElementById('share-submit').onclick = () => {
            if (!input.value) {
                alert("Please enter a username");
                return;
            }
            modal.style.display = 'none';
            resolve({ username: input.value, days: parseInt(select.value, 10) });
        };
        
        document.getElementById('share-cancel').onclick = () => {
            modal.style.display = 'none';
            resolve(null);
        };
    });
}

// ================= PRIVATE AI LOGIC =================
let currentChatId = null;
let currentChatHistory = [];

function openAI() {
    document.getElementById('ai-modal').style.display = 'flex';
    checkAIStatus();
    fetchAIModels();
    loadAISidebar();
    if(!currentChatId) {
        newAIChat();
    } else {
        renderCurrentChat();
    }
}

async function fetchAIModels() {
    const select = document.getElementById('ai-model-select');
    try {
        const res = await fetch('/api/ai/models', { headers: getAuthHeaders() });
        const data = await res.json();
        
        select.innerHTML = '';
        if (data.models && data.models.length > 0) {
            data.models.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m.name;
                opt.textContent = m.name;
                select.appendChild(opt);
            });
        } else {
            select.innerHTML = '<option value="">No local models found. Did you pull one?</option>';
        }
    } catch (e) {
        select.innerHTML = '<option value="">Error loading models</option>';
    }
}

function getStoredChats() {
    const username = document.getElementById('username')?.value || 'user'; // Basic fallback
    const key = `ai_history_${username}`;
    const stored = localStorage.getItem(key);
    return stored ? JSON.parse(stored) : [];
}

function saveStoredChats(chats) {
    const username = document.getElementById('username')?.value || 'user';
    const key = `ai_history_${username}`;
    localStorage.setItem(key, JSON.stringify(chats));
}

function loadAISidebar() {
    const list = document.getElementById('ai-history-list');
    const chats = getStoredChats();
    list.innerHTML = '';
    
    chats.forEach(chat => {
        const div = document.createElement('div');
        div.className = 'history-item';
        div.style.display = 'flex';
        div.style.justifyContent = 'space-between';
        div.style.alignItems = 'center';
        
        const titleSpan = document.createElement('span');
        titleSpan.textContent = chat.title || 'New Chat';
        titleSpan.style.flex = '1';
        titleSpan.onclick = () => loadChatSession(chat.id);
        
        const delBtn = document.createElement('button');
        delBtn.innerHTML = '<i class="ph ph-trash"></i>';
        delBtn.className = 'action-btn delete-btn';
        delBtn.style.padding = '4px';
        delBtn.style.marginLeft = '8px';
        delBtn.onclick = (e) => deleteAIChat(chat.id, e);
        
        div.appendChild(titleSpan);
        div.appendChild(delBtn);
        list.appendChild(div);
    });
}

async function deleteAIChat(id, event) {
    if (event) event.stopPropagation();
    const sure = await customConfirm("Delete this AI chat history?");
    if (!sure) return;
    
    let chats = getStoredChats();
    chats = chats.filter(c => c.id !== id);
    saveStoredChats(chats);
    
    if (currentChatId === id) {
        newAIChat();
    }
    loadAISidebar();
}

function newAIChat() {
    currentChatId = Date.now().toString();
    currentChatHistory = [];
    renderCurrentChat();
}

function loadChatSession(id) {
    const chats = getStoredChats();
    const chat = chats.find(c => c.id === id);
    if(chat) {
        currentChatId = chat.id;
        currentChatHistory = chat.messages || [];
        renderCurrentChat();
    }
}

function renderCurrentChat() {
    const historyDiv = document.getElementById('chat-history');
    historyDiv.innerHTML = '<div class="chat-msg ai">Welcome to the Private AI. All conversations are processed locally and securely.</div>';
    
    currentChatHistory.forEach(msg => {
        const div = document.createElement('div');
        div.className = `chat-msg ${msg.role === 'user' ? 'user' : 'ai'}`;
        div.textContent = msg.content;
        historyDiv.appendChild(div);
    });
    
    historyDiv.scrollTop = historyDiv.scrollHeight;
}

async function checkAIStatus() {
    try {
        const res = await fetch('/api/ai/status', { headers: getAuthHeaders() });
        const data = await res.json();
        const text = document.getElementById('ai-status-text');
        
        // Let's also verify if Ollama is actually responding by checking if we loaded models
        const select = document.getElementById('ai-model-select');
        if (select && select.options.length > 0 && select.options[0].value === "") {
            text.textContent = "Ollama Offline / No Models";
            return;
        }

        if (data.active_model) {
            text.textContent = `Model Active: ${data.active_model} (${data.users_count} users)`;
        } else {
            text.textContent = "AI Idle (Ready)";
        }
    } catch (e) {
        document.getElementById('ai-status-text').textContent = "Offline";
    }
}

document.getElementById('chat-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const input = document.getElementById('chat-input');
    const msg = input.value;
    if(!msg) return;
    
    const historyDiv = document.getElementById('chat-history');
    const modelSelect = document.getElementById('ai-model-select');
    const selectedModel = modelSelect.value || "llama3";
    
    // Add User Message
    const uDiv = document.createElement('div');
    uDiv.className = 'chat-msg user';
    uDiv.textContent = msg;
    historyDiv.appendChild(uDiv);
    input.value = '';
    
    currentChatHistory.push({role: "user", content: msg});
    
    // Add AI Loading
    const aiDiv = document.createElement('div');
    aiDiv.className = 'chat-msg ai';
    aiDiv.innerHTML = '<i class="ph ph-spinner ph-spin"></i> Processing local AI...';
    historyDiv.appendChild(aiDiv);
    historyDiv.scrollTop = historyDiv.scrollHeight;
    
    try {
        const res = await fetch('/api/ai/chat', {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model: selectedModel,
                messages: currentChatHistory,
                stream: false
            })
        });
        
        if (res.ok) {
            const data = await res.json();
            const aiContent = data.message.content;
            aiDiv.textContent = aiContent;
            currentChatHistory.push({role: "assistant", content: aiContent});
            
            // Save to local storage
            let chats = getStoredChats();
            let existing = chats.find(c => c.id === currentChatId);
            if(existing) {
                existing.messages = currentChatHistory;
            } else {
                chats.unshift({
                    id: currentChatId,
                    title: msg.substring(0, 30) + "...",
                    messages: currentChatHistory
                });
            }
            saveStoredChats(chats);
            loadAISidebar();
            
        } else {
            const errData = await res.json();
            aiDiv.textContent = "Error: " + errData.detail;
            currentChatHistory.pop(); // remove user msg if failed
        }
    } catch (e) {
        aiDiv.textContent = "Failed to connect to local AI.";
        currentChatHistory.pop();
    }
    checkAIStatus();
});

// ================= SHARED FOLDERS =================
function openShared() {
    document.getElementById('shared-modal').style.display = 'flex';
    switchSharedTab('with-me');
}

function switchSharedTab(tab) {
    document.getElementById('tab-with-me').classList.remove('active');
    document.getElementById('tab-by-me').classList.remove('active');
    document.getElementById('shared-with-me-section').style.display = 'none';
    document.getElementById('shared-by-me-section').style.display = 'none';
    
    if (tab === 'with-me') {
        document.getElementById('tab-with-me').classList.add('active');
        document.getElementById('shared-with-me-section').style.display = 'block';
        loadShared();
    } else if (tab === 'by-me') {
        document.getElementById('tab-by-me').classList.add('active');
        document.getElementById('shared-by-me-section').style.display = 'block';
        loadSharedByMe();
    }
}

async function loadShared() {
    const list = document.getElementById('shared-list');
    list.innerHTML = '<div style="color:var(--neon-cyan)">Fetching shared items...</div>';
    
    try {
        const res = await fetch('/api/media/shared', { headers: getAuthHeaders() });
        const items = await res.json();
        
        list.innerHTML = '';
        if (items.length === 0) {
            list.innerHTML = '<div style="color:var(--text-secondary)">No files have been shared with you.</div>';
            return;
        }

        for (const item of items) {
            const div = document.createElement('div');
            div.className = 'shared-item';
            div.innerHTML = `
                <div>
                    <h3 style="margin-bottom:0.25rem; cursor:pointer;" onclick="viewShared(${item.share_id})">${item.filename}</h3>
                    <div style="font-size:0.85rem; color:var(--text-secondary)">Expires: ${new Date(item.expires_at).toLocaleString()}</div>
                </div>
                <div style="display:flex; gap:0.5rem;">
                    <button class="cyber-btn sm outline" onclick="viewShared(${item.share_id})"><i class="ph ph-eye"></i> View</button>
                    <button class="cyber-btn sm" onclick="downloadShared(${item.share_id}, '${item.filename}')"><i class="ph ph-download-simple"></i> Download</button>
                </div>
            `;
            list.appendChild(div);
        }
    } catch (e) {
        list.innerHTML = `<div style="color:red">Failed to load.</div>`;
    }
}

async function loadSharedByMe() {
    const list = document.getElementById('shared-by-me-list');
    list.innerHTML = '<div style="color:var(--neon-cyan)">Fetching active shares...</div>';
    
    try {
        const res = await fetch('/api/media/shared/by_me', { headers: getAuthHeaders() });
        const items = await res.json();
        
        list.innerHTML = '';
        if (items.length === 0) {
            list.innerHTML = '<div style="color:var(--text-secondary)">You are not sharing any files.</div>';
            return;
        }

        for (const item of items) {
            const div = document.createElement('div');
            div.className = 'shared-item';
            div.innerHTML = `
                <div>
                    <h3 style="margin-bottom:0.25rem;">${item.filename}</h3>
                    <div style="font-size:0.85rem; color:var(--text-secondary)">Shared with: <span style="color:var(--neon-cyan)">${item.target_username}</span></div>
                    <div style="font-size:0.75rem; color:var(--text-secondary)">Expires: ${new Date(item.expires_at).toLocaleString()}</div>
                </div>
                <button class="cyber-btn sm" style="background:#ef4444; border-color:#ef4444; color:white;" onclick="revokeShare(${item.share_id})"><i class="ph ph-trash"></i> Cancel Share</button>
            `;
            list.appendChild(div);
        }
    } catch (e) {
        list.innerHTML = `<div style="color:red">Failed to load.</div>`;
    }
}

async function revokeShare(id) {
    const sure = await customConfirm("Are you sure you want to cancel this share? The ephemeral key will be securely shredded.");
    if (!sure) return;
    
    try {
        const res = await fetch(`/api/media/shared/${id}`, { method: 'DELETE', headers: getAuthHeaders() });
        if(res.ok) {
            loadSharedByMe();
        } else {
            alert("Failed to revoke share.");
        }
    } catch (e) {
        alert("Error revoking share.");
    }
}

async function downloadShared(share_id, filename) {
    try {
        const res = await fetch(`/api/media/download/shared/${share_id}`, { headers: getAuthHeaders() });
        if (!res.ok) throw new Error("Failed to download");
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    } catch(e) {
        alert("Download failed. The share may have expired or been deleted.");
    }
}

async function viewShared(share_id) {
    try {
        const res = await fetch(`/api/media/download/shared/${share_id}`, { headers: getAuthHeaders() });
        if (!res.ok) throw new Error("Failed to download");
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        
        // Open in lightbox
        const modal = document.getElementById('lightbox-modal');
        document.getElementById('lightbox-img').src = url;
        modal.style.display = 'flex';
        // Hide standard lightbox controls since it's a shared item (they can't share/delete it)
        document.getElementById('lightbox-controls').style.display = 'none';
        
    } catch(e) {
        alert("View failed. The share may have expired or been deleted.");
    }
}

// ================= AUTH FLOWS =================
function logout() {
    sessionStorage.removeItem('access_token');
    window.location.reload();
}

function forgotPassword() {
    document.getElementById('login-modal').style.display = 'none';
    document.getElementById('recover-modal').style.display = 'flex';
}

document.addEventListener('DOMContentLoaded', () => {
    // Register Form Handler
    document.getElementById('register-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const pwd = document.getElementById('reg-password').value;
        const confirm = document.getElementById('reg-confirm').value;
        
        if (pwd !== confirm) {
            alert("Passwords do not match!");
            return;
        }
        
        const inviteToken = window.location.hash.replace('#invite=', '');
        
        try {
            const res = await fetch('/api/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: inviteToken, password: pwd })
            });
            
            if (!res.ok) {
                const err = await res.json();
                alert(err.detail || "Registration failed");
                return;
            }
            
            const data = await res.json();
            document.getElementById('register-form').style.display = 'none';
            document.getElementById('reg-success').style.display = 'block';
            document.getElementById('reg-recovery-code').textContent = data.recovery_code;
            
        } catch(e) {
            alert("Network error.");
        }
    });

    // Recover Form Handler
    document.getElementById('recover-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('rec-username').value.trim().toLowerCase();
        const code = document.getElementById('rec-code').value.trim();
        const newPwd = document.getElementById('rec-new-password').value;
        
        const submitBtn = e.target.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<i class="ph ph-spinner"></i> Recovering...';
        submitBtn.disabled = true;
        
        try {
            const res = await fetch('/api/auth/recover', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: username, recovery_code: code, new_password: newPwd })
            });
            
            if (!res.ok) {
                let errMsg = "Recovery failed";
                try {
                    const err = await res.json();
                    errMsg = err.detail || errMsg;
                } catch(_) {}
                alert(errMsg);
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
                return;
            }
            
            const data = await res.json();
            document.getElementById('recover-form').style.display = 'none';
            document.getElementById('rec-success').style.display = 'block';
            document.getElementById('rec-new-code').textContent = data.new_recovery_code;
            
        } catch(e) {
            alert("Network error: " + e.message);
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        }
    });
});

// ================= SECURE VAULT (PASSWORDS & 2FA) =================
let authInterval = null;

function openVault() {
    document.getElementById('vault-modal').style.display = 'flex';
    switchVaultTab('passwords');
}

function switchVaultTab(tab) {
    document.querySelectorAll('.vault-tab').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.vault-section').forEach(sec => sec.style.display = 'none');
    
    if (tab === 'passwords') {
        document.querySelector('button[onclick="switchVaultTab(\'passwords\')"]').classList.add('active');
        document.getElementById('vault-passwords-section').style.display = 'block';
        loadPasswords();
        if (authInterval) clearInterval(authInterval);
    } else if (tab === 'auth') {
        document.querySelector('button[onclick="switchVaultTab(\'auth\')"]').classList.add('active');
        document.getElementById('vault-auth-section').style.display = 'block';
        loadAuths();
        authInterval = setInterval(loadAuths, 1000); // Poll every second to update timer bars
    }
}

// --- Passwords ---
async function loadPasswords() {
    const list = document.getElementById('passwords-list');
    list.innerHTML = '<div style="color:var(--neon-cyan)">Decrypting vault...</div>';
    
    try {
        const res = await fetch('/api/vault/passwords', { headers: getAuthHeaders() });
        const items = await res.json();
        
        list.innerHTML = '';
        if (items.length === 0) {
            list.innerHTML = '<div style="color:var(--text-secondary)">No passwords saved.</div>';
            return;
        }

        for (const item of items) {
            const div = document.createElement('div');
            div.className = 'vault-item';
            div.innerHTML = `
                <div class="vault-item-info">
                    <h3>${item.website}</h3>
                    <p>${item.username}</p>
                </div>
                <div style="display:flex; gap:0.5rem;">
                    <button class="cyber-btn sm outline" onclick="copyToClipboard('${item.password}', 'Password copied!')">Copy</button>
                    <button class="cyber-btn sm" style="background:#ef4444; border-color:#ef4444;" onclick="deletePassword(${item.id})"><i class="ph ph-trash"></i></button>
                </div>
            `;
            list.appendChild(div);
        }
    } catch (e) {
        list.innerHTML = `<div style="color:red">Failed to decrypt vault.</div>`;
    }
}

async function addPassword(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    btn.textContent = 'Encrypting...';
    
    const body = {
        website: document.getElementById('pw-site').value,
        username: document.getElementById('pw-user').value,
        password: document.getElementById('pw-pass').value
    };
    
    try {
        const res = await fetch('/api/vault/passwords', {
            method: 'POST',
            headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (res.ok) {
            e.target.reset();
            loadPasswords();
        } else {
            alert("Failed to save password.");
        }
    } catch (e) {
        alert("Error saving password.");
    } finally {
        btn.textContent = 'Save Password';
    }
}

async function deletePassword(id) {
    const sure = await customConfirm("Permanently delete this password?");
    if(!sure) return;
    
    try {
        await fetch(`/api/vault/passwords/${id}`, { method: 'DELETE', headers: getAuthHeaders() });
        loadPasswords();
    } catch(e) {}
}

function generatePassword() {
    const chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+~`|}{[]:;?><,./-=";
    let pw = "";
    for(let i=0; i<16; i++) {
        pw += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    document.getElementById('pw-pass').value = pw;
}

// --- Authenticator ---
async function loadAuths() {
    const list = document.getElementById('auth-list');
    
    try {
        const res = await fetch('/api/vault/auth', { headers: getAuthHeaders() });
        const items = await res.json();
        
        list.innerHTML = '';
        if (items.length === 0) {
            list.innerHTML = '<div style="color:var(--text-secondary)">No 2FA tokens saved.</div>';
            return;
        }

        for (const item of items) {
            const pct = (item.ttl / 30) * 100;
            const div = document.createElement('div');
            div.className = 'vault-item';
            div.innerHTML = `
                <div class="vault-item-info">
                    <h3>${item.name}</h3>
                    <p class="auth-code">${item.code.substring(0,3)} ${item.code.substring(3,6)}</p>
                    <div class="auth-timer-bar" style="width: ${pct}%"></div>
                </div>
                <div style="display:flex; gap:0.5rem; align-items: flex-start;">
                    <button class="cyber-btn sm outline" onclick="copyToClipboard('${item.code}', 'Code copied!')">Copy</button>
                    <button class="cyber-btn sm" style="background:#ef4444; border-color:#ef4444;" onclick="deleteAuth(${item.id})"><i class="ph ph-trash"></i></button>
                </div>
            `;
            list.appendChild(div);
        }
    } catch (e) {
        // Silently fail to allow polling without flash
        if(list.innerHTML === '') list.innerHTML = `<div style="color:red">Failed to load tokens.</div>`;
    }
}

async function addAuth(e) {
    e.preventDefault();
    let secret = document.getElementById('auth-secret').value;
    
    // Check if it's a Google Auth Migration URI
    if(secret.startsWith("otpauth-migration://")) {
        try {
            const btn = e.target.querySelector('button[type="submit"]');
            btn.textContent = 'Importing...';
            const res = await fetch('/api/vault/auth/migration', {
                method: 'POST',
                headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
                body: JSON.stringify({ uri: secret })
            });
            if (res.ok) {
                const data = await res.json();
                alert(data.message);
                e.target.reset();
                loadAuths();
            } else {
                const data = await res.json();
                alert("Failed to import: " + data.detail);
            }
        } catch (e) {
            alert("Error importing migration data.");
        } finally {
            e.target.querySelector('button[type="submit"]').textContent = 'Add Authenticator';
        }
        return;
    }
    
    // Check if it's a standard URI from QR code
    if(secret.startsWith("otpauth://totp/")) {
        try {
            const url = new URL(secret);
            const params = new URLSearchParams(url.search);
            if(params.has('secret')) {
                secret = params.get('secret');
                document.getElementById('auth-secret').value = secret;
                // Auto-fill name if empty
                if(!document.getElementById('auth-name').value) {
                    let label = decodeURIComponent(url.pathname).replace('/','');
                    document.getElementById('auth-name').value = label;
                }
            }
        } catch(e) {}
    }
    
    const body = {
        name: document.getElementById('auth-name').value,
        secret: secret
    };
    
    try {
        const res = await fetch('/api/vault/auth', {
            method: 'POST',
            headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (res.ok) {
            e.target.reset();
            loadAuths();
        } else {
            const data = await res.json();
            alert("Failed to add: " + data.detail);
        }
    } catch (e) {
        alert("Error adding authenticator.");
    }
}

async function deleteAuth(id) {
    const sure = await customConfirm("Permanently delete this authenticator? You may lose access to the account if you haven't backed up the secret.");
    if(!sure) return;
    
    try {
        await fetch(`/api/vault/auth/${id}`, { method: 'DELETE', headers: getAuthHeaders() });
        loadAuths();
    } catch(e) {}
}

let html5QrcodeScanner = null;

function startQRScanner() {
    const reader = document.getElementById('qr-reader');
    if (html5QrcodeScanner) {
        html5QrcodeScanner.clear();
        html5QrcodeScanner = null;
        reader.style.display = 'none';
        return;
    }
    
    reader.style.display = 'block';
    // Use the library we injected via CDN
    html5QrcodeScanner = new Html5QrcodeScanner(
        "qr-reader", { fps: 10, qrbox: 250 }, false);
        
    html5QrcodeScanner.render((decodedText, decodedResult) => {
        // Success callback
        html5QrcodeScanner.clear();
        html5QrcodeScanner = null;
        reader.style.display = 'none';
        
        document.getElementById('auth-secret').value = decodedText;
        
        // Handle Google Auth Migration URI
        if(decodedText.startsWith("otpauth-migration://")) {
            // Auto-submit immediately to process migration
            document.getElementById('auth-name').value = "Google Auth Import"; // Placeholder
            document.getElementById('add-auth-form').dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
            return;
        }
        
        // Try parsing name from URI
        if(decodedText.startsWith("otpauth://totp/")) {
            try {
                const url = new URL(decodedText);
                let label = decodeURIComponent(url.pathname).replace('/','');
                if(label) document.getElementById('auth-name').value = label;
            } catch(e) {}
        }
        
        // Auto-submit if both fields populated
        if(document.getElementById('auth-name').value && document.getElementById('auth-secret').value) {
            document.getElementById('add-auth-form').dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
        }
        
    }, (error) => {
        // Ignore parsing errors while scanning
    });
}

function copyToClipboard(text, msg) {
    navigator.clipboard.writeText(text).then(() => alert(msg)).catch(e => console.error("Clipboard failed", e));
}
