/**
 * SignalMine LP Chat - Frontend JavaScript
 * Connects to backend API with authentication and database support
 */

// ─────────────────────────────────────────────────────────────
// DOM Elements
// ─────────────────────────────────────────────────────────────

const messagesEl = document.getElementById('messages');
const inputEl = document.getElementById('input');
const sendBtn = document.getElementById('btn-send');
const newChatBtn = document.getElementById('btn-new-chat');
const modelSelect = document.getElementById('model-select');
const statusIndicator = document.getElementById('status-indicator');

// Auth elements
const userInfo = document.getElementById('user-info');
const authButtons = document.getElementById('auth-buttons');
const usernameDisplay = document.getElementById('username-display');
const btnLogout = document.getElementById('btn-logout');
const btnLogin = document.getElementById('btn-login');
const btnRegister = document.getElementById('btn-register');
const authForm = document.getElementById('authForm');
const authModalTitle = document.getElementById('authModalTitle');
const authSubmitBtn = document.getElementById('authSubmitBtn');
const authError = document.getElementById('authError');

// Custom models elements
const customModelsSection = document.getElementById('custom-models-section');
const customModelsList = document.getElementById('custom-models-list');
const modelForm = document.getElementById('modelForm');
const modelError = document.getElementById('modelError');
const modelProvider = document.getElementById('modelProvider');
const customUrlGroup = document.getElementById('customUrlGroup');

// Chat history elements
const chatHistorySection = document.getElementById('chat-history-section');
const chatHistoryList = document.getElementById('chat-history-list');
const newChatHistoryBtn = document.getElementById('btn-new-chat-history');

// Logs elements
const logsSection = document.getElementById('logs-section');

// ─────────────────────────────────────────────────────────────
// State
// ─────────────────────────────────────────────────────────────

let currentUser = null;
let authToken = null;
let conversationId = null;
let conversationHistory = [];
let isLoading = false;
let userModels = [];
let selectedCustomModelId = null;

// ─────────────────────────────────────────────────────────────
// API Configuration
// ─────────────────────────────────────────────────────────────

const API_BASE = '/api';

function getAuthHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }
    return headers;
}

// ─────────────────────────────────────────────────────────────
// Authentication Functions
// ─────────────────────────────────────────────────────────────

function loadStoredAuth() {
    const stored = localStorage.getItem('signalmine_auth');
    if (stored) {
        try {
            const data = JSON.parse(stored);
            authToken = data.token;
            currentUser = data.user;
            updateAuthUI();
            validateToken();
        } catch (e) {
            localStorage.removeItem('signalmine_auth');
        }
    }
}

async function validateToken() {
    if (!authToken) return;
    
    try {
        const resp = await fetch(`${API_BASE}/auth`, {
            headers: getAuthHeaders()
        });
        
        if (!resp.ok) {
            logout();
        } else {
            // Token valid, load user data
            loadUserData();
        }
    } catch (e) {
        console.error('Token validation failed:', e);
    }
}

async function login(username, password) {
    try {
        const resp = await fetch(`${API_BASE}/auth`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'login', username, password })
        });
        
        const data = await resp.json();
        
        if (data.success) {
            authToken = data.token;
            currentUser = data.user;
            localStorage.setItem('signalmine_auth', JSON.stringify({ token: authToken, user: currentUser }));
            updateAuthUI();
            loadUserData();
            return { success: true };
        } else {
            return { success: false, error: data.error };
        }
    } catch (e) {
        return { success: false, error: 'Connection error' };
    }
}

async function register(username, password) {
    try {
        const resp = await fetch(`${API_BASE}/auth`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'register', username, password })
        });
        
        const data = await resp.json();
        
        if (data.success) {
            authToken = data.token;
            currentUser = data.user;
            localStorage.setItem('signalmine_auth', JSON.stringify({ token: authToken, user: currentUser }));
            updateAuthUI();
            loadUserData();
            return { success: true };
        } else {
            return { success: false, error: data.error };
        }
    } catch (e) {
        return { success: false, error: 'Connection error' };
    }
}

async function logout() {
    if (authToken) {
        try {
            await fetch(`${API_BASE}/auth`, {
                method: 'DELETE',
                headers: getAuthHeaders()
            });
        } catch (e) {
            console.error('Logout error:', e);
        }
    }
    
    authToken = null;
    currentUser = null;
    userModels = [];
    localStorage.removeItem('signalmine_auth');
    updateAuthUI();
    clearChat();
}

function updateAuthUI() {
    if (currentUser) {
        userInfo.classList.remove('hidden');
        authButtons.classList.add('hidden');
        usernameDisplay.textContent = currentUser.username;
        customModelsSection.classList.remove('hidden');
        chatHistorySection.classList.remove('hidden');
        logsSection.classList.remove('hidden');
    } else {
        userInfo.classList.add('hidden');
        authButtons.classList.remove('hidden');
        customModelsSection.classList.add('hidden');
        chatHistorySection.classList.add('hidden');
        logsSection.classList.add('hidden');
    }
}

// ─────────────────────────────────────────────────────────────
// User Data Loading
// ─────────────────────────────────────────────────────────────

async function loadUserData() {
    if (!currentUser) return;
    
    await Promise.all([
        loadUserModels(),
        loadChatHistory()
    ]);
}

async function loadUserModels() {
    try {
        const resp = await fetch(`${API_BASE}/user-models`, {
            headers: getAuthHeaders()
        });
        
        if (resp.ok) {
            const data = await resp.json();
            userModels = data.models || [];
            renderCustomModels();
        }
    } catch (e) {
        console.error('Failed to load user models:', e);
    }
}

async function loadChatHistory() {
    try {
        const resp = await fetch(`${API_BASE}/chats`, {
            headers: getAuthHeaders()
        });
        
        if (resp.ok) {
            const data = await resp.json();
            renderChatHistory(data.chats || []);
        }
    } catch (e) {
        console.error('Failed to load chat history:', e);
    }
}

function renderCustomModels() {
    customModelsList.innerHTML = '';
    
    userModels.forEach(model => {
        const div = document.createElement('div');
        div.className = 'custom-model-item';
        div.innerHTML = `
            <span class="model-name">${model.Name}</span>
            <span class="model-provider">${model.provider}</span>
            <button class="btn-delete-model" data-id="${model.ID}" title="Delete">×</button>
        `;
        customModelsList.appendChild(div);
    });
    
    // Add delete handlers
    customModelsList.querySelectorAll('.btn-delete-model').forEach(btn => {
        btn.addEventListener('click', async () => {
            if (confirm('Delete this API key?')) {
                await deleteUserModel(btn.dataset.id);
            }
        });
    });
    
    // Update model select to include custom models
    updateModelSelect();
}

function renderChatHistory(chats) {
    chatHistoryList.innerHTML = '';
    
    chats.slice(0, 20).forEach(chat => {
        const div = document.createElement('div');
        div.className = 'chat-history-item';
        
        // Highlight active chat
        if (conversationId && chat.ID === conversationId) {
            div.classList.add('active');
        }
        
        div.dataset.id = chat.ID;
        div.innerHTML = `
            <span class="chat-name">${chat.Name || 'Untitled'}</span>
            <button class="btn-delete-chat" data-id="${chat.ID}" title="Delete">×</button>
        `;
        
        div.addEventListener('click', (e) => {
            if (!e.target.classList.contains('btn-delete-chat')) {
                loadChat(chat.ID);
            }
        });
        
        chatHistoryList.appendChild(div);
    });
    
    // Add delete handlers
    chatHistoryList.querySelectorAll('.btn-delete-chat').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            if (confirm('Delete this chat?')) {
                await deleteChat(btn.dataset.id);
            }
        });
    });
}

async function loadChat(chatId) {
    try {
        const resp = await fetch(`${API_BASE}/chats/${chatId}`, {
            headers: getAuthHeaders()
        });
        
        if (resp.ok) {
            const data = await resp.json();
            conversationId = chatId;
            conversationHistory = [];
            
            // Clear and render messages
            const welcome = messagesEl.querySelector('.message');
            messagesEl.innerHTML = '';
            
            data.messages.forEach(msg => {
                addMessage(msg.origin, msg.message);
                conversationHistory.push({
                    role: msg.origin,
                    content: msg.message
                });
            });
            
            // Update chat history to highlight active chat
            loadChatHistory();
        }
    } catch (e) {
        console.error('Failed to load chat:', e);
    }
}

async function deleteChat(chatId) {
    try {
        const resp = await fetch(`${API_BASE}/chats/${chatId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        
        if (resp.ok) {
            loadChatHistory();
            if (conversationId === chatId) {
                clearChat();
            }
        }
    } catch (e) {
        console.error('Failed to delete chat:', e);
    }
}

async function deleteUserModel(modelId) {
    try {
        const resp = await fetch(`${API_BASE}/user-models/${modelId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        
        if (resp.ok) {
            loadUserModels();
        }
    } catch (e) {
        console.error('Failed to delete model:', e);
    }
}

// ─────────────────────────────────────────────────────────────
// Model Functions
// ─────────────────────────────────────────────────────────────

async function fetchModels() {
    try {
        const resp = await fetch(`${API_BASE}/models`);
        const data = await resp.json();
        
        window.defaultModels = data.models;
        window.defaultModel = data.default;
        updateModelSelect();
    } catch (e) {
        console.error('Failed to fetch models:', e);
        modelSelect.innerHTML = '<option value="gpt-4o-mini">GPT-4o Mini</option>';
    }
}

function updateModelSelect() {
    modelSelect.innerHTML = '';
    
    // Add default models
    if (window.defaultModels) {
        const defaultGroup = document.createElement('optgroup');
        defaultGroup.label = 'Default Models';
        
        for (const [id, name] of Object.entries(window.defaultModels)) {
            const option = document.createElement('option');
            option.value = id;
            option.textContent = name;
            if (id === window.defaultModel) option.selected = true;
            defaultGroup.appendChild(option);
        }
        
        modelSelect.appendChild(defaultGroup);
    }
    
    // Add user's custom models
    if (userModels.length > 0) {
        const customGroup = document.createElement('optgroup');
        customGroup.label = 'My Models';
        
        userModels.forEach(model => {
            const option = document.createElement('option');
            option.value = `custom:${model.ID}`;
            option.textContent = `${model.Name} (${model.provider})`;
            customGroup.appendChild(option);
        });
        
        modelSelect.appendChild(customGroup);
    }
}

// ─────────────────────────────────────────────────────────────
// Chat Functions
// ─────────────────────────────────────────────────────────────

async function sendMessage(prompt) {
    if (isLoading || !prompt.trim()) return;

    isLoading = true;
    updateUI();

    addMessage('user', prompt);
    const loadingId = addMessage('assistant', '', true);

    try {
        const selectedModel = modelSelect.value;
        let model = selectedModel;
        let customModelId = null;
        
        if (selectedModel.startsWith('custom:')) {
            customModelId = parseInt(selectedModel.split(':')[1]);
            const customModel = userModels.find(m => m.ID === customModelId);
            model = customModel ? customModel.Name : 'gpt-4o-mini';
        }
        
        const body = {
            prompt: prompt,
            model: model,
            history: conversationHistory,
            chat_id: conversationId
        };
        
        if (customModelId) {
            body.custom_model_id = customModelId;
        }

        const resp = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(body)
        });

        const data = await resp.json();
        removeMessage(loadingId);

        if (data.error) {
            addMessage('assistant', `**Error:** ${data.error}`, false, true);
        } else {
            // Update conversation ID if provided (for logged-in users with DB)
            if (data.conversation_id) {
                conversationId = data.conversation_id;
            }
            
            conversationHistory.push({ role: 'user', content: prompt });
            conversationHistory.push({ role: 'assistant', content: JSON.stringify(data.linear_program) });
            addMessage('assistant', data.message, false, false, data.was_healed);
            
            // Refresh chat history if logged in and chat was saved
            if (currentUser && data.conversation_id) {
                loadChatHistory();
            }
        }

    } catch (e) {
        removeMessage(loadingId);
        addMessage('assistant', `**Connection Error:** Could not reach the server.`, false, true);
        console.error('Send error:', e);
    }

    isLoading = false;
    updateUI();
}

// ─────────────────────────────────────────────────────────────
// Logs Functions
// ─────────────────────────────────────────────────────────────

async function loadLogs() {
    try {
        const resp = await fetch(`${API_BASE}/logs`, {
            headers: getAuthHeaders()
        });
        
        if (resp.ok) {
            const data = await resp.json();
            renderLogs(data);
        }
    } catch (e) {
        console.error('Failed to load logs:', e);
    }
}

function renderLogs(data) {
    // Update summary
    document.getElementById('totalRequests').textContent = data.summary?.total_requests || 0;
    document.getElementById('totalTokens').textContent = data.summary?.total_tokens || 0;
    document.getElementById('avgResponseTime').textContent = `${data.summary?.avg_response_time_ms || 0}ms`;
    document.getElementById('healedCount').textContent = data.summary?.healed_count || 0;
    
    // Render logs table
    const tbody = document.getElementById('logsBody');
    tbody.innerHTML = '';
    
    (data.logs || []).forEach(log => {
        const tr = document.createElement('tr');
        const date = new Date(log.created_at);
        tr.innerHTML = `
            <td>${date.toLocaleString()}</td>
            <td>${log.chat_name || '-'}</td>
            <td>${log.model_used || '-'}</td>
            <td>${log.tokens_used || '-'}</td>
            <td>${log.response_time_ms || '-'}ms</td>
            <td>${log.was_healed ? '✓' : '-'}</td>
        `;
        tbody.appendChild(tr);
    });
}

// ─────────────────────────────────────────────────────────────
// UI Functions
// ─────────────────────────────────────────────────────────────

let messageCounter = 0;

function addMessage(role, content, isLoading = false, isError = false, wasHealed = false) {
    const id = `msg-${++messageCounter}`;
    const div = document.createElement('div');
    div.id = id;
    div.className = `message ${role}`;

    const avatarSvg = role === 'user'
        ? '<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>'
        : '<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>';

    let contentHtml;
    if (isLoading) {
        contentHtml = `<div class="loading-dots"><span></span><span></span><span></span></div>`;
    } else {
        contentHtml = renderMarkdown(content);
    }

    let statusHtml = '';
    if (wasHealed) {
        statusHtml = '<div class="message-status healed">Self-healing was applied to fix the output format</div>';
    } else if (isError) {
        statusHtml = '<div class="message-status error">Request failed</div>';
    }

    div.innerHTML = `
        <div class="message-avatar">${avatarSvg}</div>
        <div class="message-content">
            <div class="message-text">${contentHtml}</div>
            ${statusHtml}
        </div>
    `;

    messagesEl.appendChild(div);
    scrollToBottom();

    if (!isLoading) {
        renderMathIn(div);
        highlightCodeIn(div);
    }

    return id;
}

function removeMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function renderMarkdown(text) {
    if (!text) return '';

    if (typeof marked !== 'undefined') {
        marked.setOptions({ breaks: true, gfm: true });
        return marked.parse(text);
    }

    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\n/g, '<br>');
}

function renderMathIn(element) {
    if (typeof renderMathInElement !== 'undefined') {
        renderMathInElement(element, {
            delimiters: [
                { left: '$$', right: '$$', display: true },
                { left: '$', right: '$', display: false },
                { left: '\\[', right: '\\]', display: true },
                { left: '\\(', right: '\\)', display: false }
            ],
            throwOnError: false
        });
    }
}

function highlightCodeIn(element) {
    if (typeof hljs !== 'undefined') {
        element.querySelectorAll('pre code').forEach(block => {
            hljs.highlightElement(block);
        });
    }
}

function scrollToBottom() {
    const container = document.querySelector('.chat-container');
    container.scrollTop = container.scrollHeight;
}

function updateUI() {
    const hasText = inputEl.value.trim().length > 0;
    sendBtn.disabled = !hasText || isLoading;

    if (isLoading) {
        statusIndicator.textContent = 'Generating...';
        statusIndicator.className = 'status';
    } else {
        statusIndicator.textContent = '';
    }
}

function clearChat() {
    messagesEl.innerHTML = `
        <div class="message assistant">
            <div class="message-avatar">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                </svg>
            </div>
            <div class="message-content">
                <div class="message-text">
                    <p>Welcome to <strong>SignalMine LP Chat</strong>!</p>
                    <p>Describe your scheduling, assignment, or optimization problem in natural language, and I'll formulate it as a <strong>Linear Program</strong>.</p>
                    <p>I'll provide:</p>
                    <ul>
                        <li>Mathematical formulation with constraints</li>
                        <li>LaTeX notation</li>
                        <li>Python code to solve it</li>
                    </ul>
                    <p><em>If my output format is invalid, a self-healing agent will automatically fix it!</em></p>
                </div>
            </div>
        </div>
    `;

    conversationId = null;
    conversationHistory = [];
    inputEl.value = '';
    updateUI();
}

function autoResize() {
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 200) + 'px';
}

// ─────────────────────────────────────────────────────────────
// Event Listeners
// ─────────────────────────────────────────────────────────────

// Input handlers
inputEl.addEventListener('input', () => {
    updateUI();
    autoResize();
});

inputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        const text = inputEl.value.trim();
        if (text && !isLoading) {
            inputEl.value = '';
            autoResize();
            updateUI();
            sendMessage(text);
        }
    }
});

sendBtn.addEventListener('click', () => {
    const text = inputEl.value.trim();
    if (text && !isLoading) {
        inputEl.value = '';
        autoResize();
        updateUI();
        sendMessage(text);
    }
});

newChatBtn.addEventListener('click', clearChat);

if (newChatHistoryBtn) {
    newChatHistoryBtn.addEventListener('click', clearChat);
}

// Sample prompts
document.querySelectorAll('.sample-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        inputEl.value = btn.textContent.trim();
        inputEl.focus();
        autoResize();
        updateUI();
    });
});

// Auth events
btnLogout.addEventListener('click', logout);

btnRegister.addEventListener('click', () => {
    authModalTitle.textContent = 'Register';
    authSubmitBtn.textContent = 'Register';
    authForm.dataset.mode = 'register';
});

btnLogin.addEventListener('click', () => {
    authModalTitle.textContent = 'Login';
    authSubmitBtn.textContent = 'Login';
    authForm.dataset.mode = 'login';
});

authForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const username = document.getElementById('authUsername').value;
    const password = document.getElementById('authPassword').value;
    const mode = authForm.dataset.mode || 'login';
    
    authError.classList.add('d-none');
    authSubmitBtn.disabled = true;
    
    let result;
    if (mode === 'register') {
        result = await register(username, password);
    } else {
        result = await login(username, password);
    }
    
    authSubmitBtn.disabled = false;
    
    if (result.success) {
        bootstrap.Modal.getInstance(document.getElementById('authModal')).hide();
        authForm.reset();
    } else {
        authError.textContent = result.error;
        authError.classList.remove('d-none');
    }
});

// Model form events
modelProvider.addEventListener('change', () => {
    customUrlGroup.style.display = modelProvider.value === 'custom' ? 'block' : 'none';
});

modelForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const name = document.getElementById('modelName').value;
    const provider = document.getElementById('modelProvider').value;
    const apiKey = document.getElementById('modelApiKey').value;
    const baseUrl = document.getElementById('modelBaseUrl').value;
    
    modelError.classList.add('d-none');
    
    try {
        const resp = await fetch(`${API_BASE}/user-models`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                name,
                provider,
                api_key: apiKey,
                base_url: baseUrl || undefined
            })
        });
        
        const data = await resp.json();
        
        if (data.success) {
            bootstrap.Modal.getInstance(document.getElementById('modelModal')).hide();
            modelForm.reset();
            loadUserModels();
        } else {
            modelError.textContent = data.error;
            modelError.classList.remove('d-none');
        }
    } catch (e) {
        modelError.textContent = 'Connection error';
        modelError.classList.remove('d-none');
    }
});

// Logs modal event
document.getElementById('logsModal').addEventListener('show.bs.modal', loadLogs);

// ─────────────────────────────────────────────────────────────
// Initialize
// ─────────────────────────────────────────────────────────────

fetchModels();
loadStoredAuth();
updateUI();
