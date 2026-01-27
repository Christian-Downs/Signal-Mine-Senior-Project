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

// ─────────────────────────────────────────────────────────────
// State
// ─────────────────────────────────────────────────────────────

let conversationId = null;
let conversationHistory = [];  // Store history client-side for Vercel (stateless)
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
                history: conversationHistory  // Send history for Vercel (stateless)
            })
        });
        
        const data = await resp.json();
        
        // Remove loading message
        removeMessage(loadingId);
        
        if (data.error) {
            addMessage('assistant', `**Error:** ${data.error}`, false, true);
        } else {
            conversationId = data.conversation_id;
            // Update local history
            conversationHistory.push({ role: 'user', content: prompt });
            conversationHistory.push({ role: 'assistant', content: JSON.stringify(data.linear_program) });
            addMessage('assistant', data.message, false, false, data.was_healed);
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
    conversationHistory = [];  // Clear history for Vercel
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

// ─────────────────────────────────────────────────────────────
// Initialize
// ─────────────────────────────────────────────────────────────

fetchModels();
updateUI();
