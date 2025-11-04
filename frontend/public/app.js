const el = (q) => document.querySelector(q);
if (ctype.includes('text/event-stream')) {
    // stream
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';
    while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split('\n');
        buf = lines.pop() || '';
        for (const line of lines) {
            if (!line.startsWith('data:')) continue;
            const j = line.slice(5).trim();
            if (j === '[DONE]') continue;
            try {
                const evt = JSON.parse(j);
                if (evt.delta) updateLastAssistant(evt.delta);
                if (evt.status) updateLastAssistantStatus(evt.status);
                if (evt.role === 'auditor' && evt.message) { addMessage('auditor', evt.message); }
                if (evt.conversation_id) { setCfg({ conv: evt.conversation_id }); }
            } catch { /* ignore */ }
        }
    }
} else if (ctype.includes('application/json')) {
    const data = await resp.json();
    const msg = data.message || data.output || JSON.stringify(data, null, 2);
    updateLastAssistant(msg);
    if (data.conversation_id) setCfg({ conv: data.conversation_id });
} else {
    const text = await resp.text();
    updateLastAssistant(text || '(no content)');
}



function init() {
    // initial message
    addMessage('assistant', window.__APP__?.initialMessage || 'Hello!');


    // settings
    const cfg = getCfg();
    inpBase.value = cfg.base; inpToken.value = cfg.token; kvBackend.textContent = cfg.base;


    settingsBtn.addEventListener('click', () => settingsDlg.showModal());
    openSettingsBtn.addEventListener('click', () => settingsDlg.showModal());
    settingsDlg.addEventListener('close', () => {
        if (settingsDlg.returnValue !== 'cancel') {
            setCfg({ base: inpBase.value.trim(), token: inpToken.value.trim() });
        }
    });


    // samples
    document.querySelectorAll('.sample').forEach(btn => btn.addEventListener('click', () => {
        inputEl.value = btn.textContent.trim(); inputEl.focus();
    }));


    // send
    sendBtn.addEventListener('click', async () => {
        const t = inputEl.value.trim(); if (!t) return; inputEl.value = '';
        try { await callBackend(t); } catch (e) { updateLastAssistantStatus('Error – check PHP proxy/back‑end URL'); }
    });
    inputEl.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendBtn.click(); }
    });


    clearBtn.addEventListener('click', clearChat);
    exportBtn.addEventListener('click', exportChat);
}


init();