/**
 * SignalMine LP Chat - Frontend JavaScript
 * Connects to Flask backend API
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
const registerBtn = document.getElementById('btn-register');
const registerModal = document.getElementById('register-modal');
const registerForm = document.getElementById('register-form');
const registerMessage = document.getElementById('register-message');
const registerClose = document.getElementById('register-close');
const loginBtn = document.getElementById('btn-login');
const loginModal = document.getElementById('login-modal');
const loginForm = document.getElementById('login-form');
const loginMessage = document.getElementById('login-message');
const loginClose = document.getElementById('login-close');

// ─────────────────────────────────────────────────────────────
// State
// ─────────────────────────────────────────────────────────────

let conversationId = null;
let isLoading = false;

// ─────────────────────────────────────────────────────────────
// API Functions
// ─────────────────────────────────────────────────────────────

const API_BASE = '/api';

async function fetchModels() {
    try {
        const resp = await fetch(`${API_BASE}/models`);
        const data = await resp.json();

        modelSelect.innerHTML = '';
        for (const [id, name] of Object.entries(data.models)) {
            const option = document.createElement('option');
            option.value = id;
            option.textContent = name;
            if (id === data.default) option.selected = true;
            modelSelect.appendChild(option);
        }
    } catch (e) {
        console.error('Failed to fetch models:', e);
        // Fallback
        modelSelect.innerHTML = '<option value="gpt-4o-mini">GPT-4o Mini</option>';
    }
}

async function sendMessage(prompt) {
    if (isLoading || !prompt.trim()) return;

    isLoading = true;
    updateUI();

    // Add user message
    addMessage('user', prompt);

    // Add loading message
    const loadingId = addMessage('assistant', '', true);

    try {
        const resp = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                prompt: prompt,
                model: modelSelect.value,
                conversation_id: conversationId
            })
        });

        const data = await resp.json();

        // Remove loading message
        removeMessage(loadingId);

        if (data.error) {
            addMessage('assistant', `**Error:** ${data.error}`, false, true);
        } else {
            conversationId = data.conversation_id;
            addMessage('assistant', data.message, false, false, data.was_healed);
        }

    } catch (e) {
        removeMessage(loadingId);
        addMessage('assistant', `**Connection Error:** Could not reach the server. Make sure Flask is running on port 5000.`, false, true);
        console.error('Send error:', e);
    }

    isLoading = false;
    updateUI();
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
        statusHtml = '<div class="message-status healed">⚠️ Self-healing was applied to fix the output format</div>';
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

    // Render math and code highlighting
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

    // Configure marked
    if (typeof marked !== 'undefined') {
        marked.setOptions({
            breaks: true,
            gfm: true
        });
        return marked.parse(text);
    }

    // Fallback: basic HTML escaping and line breaks
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
    // Enable/disable send button
    const hasText = inputEl.value.trim().length > 0;
    sendBtn.disabled = !hasText || isLoading;

    // Update status
    if (isLoading) {
        statusIndicator.textContent = 'Generating...';
        statusIndicator.className = 'status';
    } else {
        statusIndicator.textContent = '';
    }
}

function clearChat() {
    // Keep only the welcome message
    const welcome = messagesEl.querySelector('.message');
    messagesEl.innerHTML = '';
    if (welcome) messagesEl.appendChild(welcome.cloneNode(true));

    // Reset conversation
    conversationId = null;
    inputEl.value = '';
    updateUI();
}

// ─────────────────────────────────────────────────────────────
// Auto-resize textarea
// ─────────────────────────────────────────────────────────────

function autoResize() {
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 200) + 'px';
}

// ─────────────────────────────────────────────────────────────
// Event Listeners
// ─────────────────────────────────────────────────────────────

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

// Sample prompts
document.querySelectorAll('.sample-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        inputEl.value = btn.textContent.trim();
        inputEl.focus();
        autoResize();
        updateUI();
    });
});

// Register Functions
// ─────────────────────────────────────────────────────────────

function openRegisterModal() {
    registerModal.style.display = 'flex';
    registerMessage.textContent = '';
}

function closeRegisterModal() {
    registerModal.style.display = 'none';
    registerForm.reset();
}

async function handleRegisterSubmit(e) {
    e.preventDefault();
    const username = document.getElementById('reg-username').value.trim();
    const password = document.getElementById('reg-password').value.trim();
    const confirmPassword = document.getElementById('reg-confirm-password').value.trim();

    if (!username || !password || !confirmPassword) {
        registerMessage.textContent = 'Please fill in all fields.';
        registerMessage.className = 'register-message error';
        return;
    }

    if (password !== confirmPassword) {
        registerMessage.textContent = 'Passwords do not match.';
        registerMessage.className = 'register-message error';
        return;
    }

    // Placeholder: Handle registration logic here (e.g., API call)
    // For now, just log and show success
    console.log('Registering user:', { username, password });
    registerMessage.textContent = 'Registration successful! (Placeholder - implement API connection)';
    registerMessage.className = 'register-message success';

    // Close modal after a delay
    setTimeout(() => {
        closeRegisterModal();
    }, 2000);
}

// Add these to the Event Listeners section
registerBtn.addEventListener('click', openRegisterModal);
registerForm.addEventListener('submit', handleRegisterSubmit);
registerClose.addEventListener('click', closeRegisterModal);

// Close modal when clicking outside
window.addEventListener('click', (e) => {
    if (e.target === registerModal) {
        closeRegisterModal();
    }
});

// Login Functions
// ─────────────────────────────────────────────────────────────

function openLoginModal() {
    loginModal.style.display = 'flex';
    loginMessage.textContent = '';
}

function closeLoginModal() {
    loginModal.style.display = 'none';
    loginForm.reset();
}

async function handleLoginSubmit(e) {
    e.preventDefault();
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value.trim();

    if (!username || !password) {
        loginMessage.textContent = 'Please fill in all fields.';
        loginMessage.className = 'login-message error';
        return;
    }

    // Placeholder: Handle login logic here (e.g., API call)
    // For now, just log and show success
    console.log('Logging in user:', { username, password });
    loginMessage.textContent = 'Login successful! (Placeholder - implement API connection)';
    loginMessage.className = 'login-message success';

    // Close modal after a delay
    setTimeout(() => {
        closeLoginModal();
    }, 2000);
}

// Add to Event Listeners
loginBtn.addEventListener('click', openLoginModal);
loginForm.addEventListener('submit', handleLoginSubmit);
loginClose.addEventListener('click', closeLoginModal);

// Close modal when clicking outside
window.addEventListener('click', (e) => {
    if (e.target === loginModal) {
        closeLoginModal();
    }
});

// ─────────────────────────────────────────────────────────────
// Initialize
// ─────────────────────────────────────────────────────────────

fetchModels();
updateUI();
