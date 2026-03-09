// Projection Display - receives state updates and renders 5-line lyrics view

const CONTEXT_LINES = 2; // lines before and after the active line

const client = new WSClient(SESSION_ID, 'display', (msg) => {
    if (msg.type === 'state_sync' || msg.type === 'state_update') {
        updateDisplay(msg.data);
    }
});

function updateDisplay(state) {
    const container = document.getElementById('lyrics-lines');
    const blankEl = document.getElementById('blank-overlay');

    // Blank overlay
    if (state.is_blank) {
        blankEl.classList.remove('hidden');
    } else {
        blankEl.classList.add('hidden');
    }

    const lines = state.current_item_lines || [];
    const idx = state.current_line_index;

    if (lines.length === 0) {
        // Manual text or no lines — show single line
        container.innerHTML = state.current_text
            ? `<div class="lyric-line active">${escapeHtml(state.current_text)}</div>`
            : '';
        return;
    }

    // Build 5-line window: [idx-2, idx-1, idx, idx+1, idx+2]
    const start = idx - CONTEXT_LINES;
    const end = idx + CONTEXT_LINES;
    let html = '';

    for (let i = start; i <= end; i++) {
        if (i < 0 || i >= lines.length) {
            // Empty placeholder to keep spacing stable
            html += '<div class="lyric-line">&nbsp;</div>';
            continue;
        }
        const text = escapeHtml(lines[i].text || '');
        let cls = 'lyric-line';
        if (i === idx) {
            cls += ' active';
        } else if (Math.abs(i - idx) === 1) {
            cls += ' near';
        }
        html += `<div class="${cls}">${text}</div>`;
    }

    container.innerHTML = html;
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
