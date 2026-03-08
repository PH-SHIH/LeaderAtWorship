// Projection Controller - sends commands to the server

const client = new WSClient(SESSION_ID, 'controller', (msg) => {
    if (msg.type === 'state_sync' || msg.type === 'state_update') {
        updateControllerUI(msg.data);
    }
});

// Cache items from state for rendering line lists
let cachedItems = [];
let currentSongId = null;

function sendCommand(action) {
    client.send({ action });
}

function sendText() {
    const text = document.getElementById('manual-text').value;
    client.send({ action: 'set_text', text });
}

function gotoItem(index) {
    client.send({ action: 'goto_item', index });
}

function gotoLine(index) {
    client.send({ action: 'goto_line', index });
}

function updateControllerUI(state) {
    document.getElementById('current-text').textContent = state.current_text || '等待中...';
    document.getElementById('current-text-secondary').textContent = state.current_text_secondary || '';
    document.getElementById('connection-status').textContent = '已連線';

    // Position info
    const posInfo = document.getElementById('position-info');
    if (state.total_items > 0) {
        const itemLabel = state.current_item_label || '';
        posInfo.textContent = `${itemLabel}  (${state.current_item_index + 1}/${state.total_items}) — 第 ${state.current_line_index + 1}/${state.total_lines || '?'} 行`;
    } else {
        posInfo.textContent = '';
    }

    // Flow navigation
    if (state.items && state.items.length > 0) {
        cachedItems = state.items;
        document.getElementById('flow-nav').style.display = 'flex';
        renderItemNav(state);
        renderLineNav(state);
    }

    // Audio player — update when song changes
    updateAudioPlayer(state);
}

// ── Audio Player ──────────────────────────────────────────

function updateAudioPlayer(state) {
    const section = document.getElementById('audio-player-section');
    const audio = document.getElementById('audio-player');
    const title = document.getElementById('audio-title');
    const songId = state.current_song_id;

    if (!songId) {
        section.style.display = 'none';
        if (!audio.paused) audio.pause();
        currentSongId = null;
        return;
    }

    section.style.display = 'block';
    title.textContent = `播放：${state.current_item_label || ''}`;

    // Only reload audio source when song actually changes
    if (songId !== currentSongId) {
        currentSongId = songId;
        const track = document.querySelector('input[name="track"]:checked').value;
        audio.src = `/api/v1/audio/stream/${songId}?track=${track}`;
    }
}

// Track selector change
document.querySelectorAll('input[name="track"]').forEach(radio => {
    radio.addEventListener('change', () => {
        const audio = document.getElementById('audio-player');
        if (!currentSongId) return;
        const currentTime = audio.currentTime;
        const wasPlaying = !audio.paused;
        audio.src = `/api/v1/audio/stream/${currentSongId}?track=${radio.value}`;
        audio.currentTime = currentTime;
        if (wasPlaying) audio.play();
    });
});

// ── Flow Navigation Rendering ─────────────────────────────

function renderItemNav(state) {
    const ul = document.getElementById('item-nav-list');
    ul.innerHTML = cachedItems.map((item, i) => {
        const active = i === state.current_item_index ? 'active' : '';
        const typeLabel = item.item_type === 'song' ? '' : `<span class="item-type">${escapeHtml(item.item_type)}</span> `;
        return `<li class="${active}" onclick="gotoItem(${i})">${typeLabel}${escapeHtml(item.label)}</li>`;
    }).join('');
}

function renderLineNav(state) {
    const panel = document.getElementById('line-panel-title');
    const ul = document.getElementById('line-nav-list');

    const itemIdx = state.current_item_index;
    const item = cachedItems[itemIdx];
    if (!item) {
        panel.textContent = '字幕行';
        ul.innerHTML = '';
        return;
    }

    panel.textContent = `${escapeHtml(item.label)} — 字幕行`;

    const lines = state.current_item_lines || [];
    if (lines.length === 0) {
        ul.innerHTML = '<li style="color: #94a3b8; cursor: default;">無字幕</li>';
        return;
    }

    ul.innerHTML = lines.map((line, i) => {
        const active = i === state.current_line_index ? 'active' : '';
        const text = escapeHtml(line.text || '');
        const truncated = text.length > 40 ? text.substring(0, 40) + '...' : text;
        return `<li class="${active}" onclick="gotoLine(${i})">${truncated}</li>`;
    }).join('');

    // Auto-scroll active line into view
    requestAnimationFrame(() => {
        const activeEl = ul.querySelector('.active');
        if (activeEl) activeEl.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    });
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
