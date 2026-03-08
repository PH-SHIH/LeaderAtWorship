/**
 * LeaderAtWorship — Subtitle Sync Player
 *
 * Loads song metadata + subtitle lines, sets up HTML5 audio player,
 * and synchronizes subtitle highlighting with audio playback.
 *
 * Requires: SONG_ID global variable set by the template.
 */

let song = null;
let subtitleLines = [];
let currentLineIndex = -1;
let isSeeking = false;
let currentSubtitleFileId = null;
let editingLineIndex = -1;

// ── Helpers ────────────────────────────────────────────────

function formatTime(ms) {
    const totalSeconds = Math.floor(ms / 1000);
    const m = Math.floor(totalSeconds / 60);
    const s = totalSeconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
}

function formatTimeFromSeconds(sec) {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
}

// ── Binary Search for Current Subtitle Line ────────────────

function findCurrentLine(currentMs) {
    if (subtitleLines.length === 0) return -1;

    let lo = 0;
    let hi = subtitleLines.length - 1;
    let result = -1;

    while (lo <= hi) {
        const mid = (lo + hi) >> 1;
        if (subtitleLines[mid].start_ms <= currentMs) {
            result = mid;
            lo = mid + 1;
        } else {
            hi = mid - 1;
        }
    }

    // Check if we're still within this line's end_ms
    if (result >= 0 && currentMs > subtitleLines[result].end_ms) {
        return -1; // In a gap between lines
    }
    return result;
}

// ── Render ──────────────────────────────────────────────────

function renderSongHeader(song) {
    document.getElementById('song-title').textContent = song.title;
    const parts = [];
    if (song.artist) parts.push(song.artist);
    if (song.key_signature) parts.push(`調性: ${song.key_signature}`);
    if (song.tempo_bpm) parts.push(`${song.tempo_bpm} BPM`);
    document.getElementById('song-meta').textContent = parts.join(' | ');
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function renderSubtitleLines(lines) {
    const container = document.getElementById('subtitle-lines');
    container.innerHTML = lines.map((line, i) => `
        <div class="subtitle-line" data-index="${i}" data-start-ms="${line.start_ms}"
             data-line-id="${line.id || ''}" data-source="${line.source_type || ''}">
            <span class="line-time">${formatTime(line.start_ms)}</span>
            <span class="line-text">${escapeHtml(line.text)}</span>
            ${line.text_secondary ? `<span class="line-text-secondary">${escapeHtml(line.text_secondary)}</span>` : ''}
            <span class="line-actions">
                <button onclick="event.stopPropagation(); startEditLine(${i})" title="編輯">&#9998;</button>
                <button onclick="event.stopPropagation(); deleteLine(${i})" title="刪除">&times;</button>
                <button onclick="event.stopPropagation(); insertLineAfter(${i})" title="插入新行">+</button>
            </span>
        </div>
    `).join('');

    // Click to seek (but not on action buttons)
    container.addEventListener('click', (e) => {
        if (e.target.closest('.line-actions')) return;
        if (e.target.closest('.subtitle-edit-form')) return;
        const lineEl = e.target.closest('.subtitle-line');
        if (lineEl) {
            const startMs = parseInt(lineEl.dataset.startMs);
            const audio = document.getElementById('audio-player');
            audio.currentTime = startMs / 1000;
            if (audio.paused) audio.play();
        }
    });
}

// ── Inline Editing ─────────────────────────────────────────

function startEditLine(index) {
    editingLineIndex = index;
    const line = subtitleLines[index];
    const lineEl = document.querySelectorAll('.subtitle-line')[index];
    if (!lineEl) return;

    const form = document.createElement('div');
    form.className = 'subtitle-edit-form';
    form.innerHTML = `
        <input type="text" value="${escapeHtml(line.text)}" id="edit-text" placeholder="歌詞文字">
        <label>起始
            <input type="number" value="${line.start_ms}" id="edit-start" step="100">
        </label>
        <label>結束
            <input type="number" value="${line.end_ms}" id="edit-end" step="100">
        </label>
        <div class="edit-btns">
            <button class="btn btn-primary" onclick="saveEditLine(${index})" style="font-size: 13px; padding: 4px 10px;">儲存</button>
            <button class="btn" onclick="cancelEditLine()" style="font-size: 13px; padding: 4px 10px;">取消</button>
        </div>
    `;

    lineEl.style.display = 'none';
    lineEl.parentNode.insertBefore(form, lineEl.nextSibling);

    form.querySelector('#edit-text').focus();
    form.querySelector('#edit-text').select();
}

async function saveEditLine(index) {
    const line = subtitleLines[index];
    const text = document.getElementById('edit-text').value;
    const startMs = parseInt(document.getElementById('edit-start').value);
    const endMs = parseInt(document.getElementById('edit-end').value);

    const body = {};
    if (text !== line.text) body.text = text;
    if (startMs !== line.start_ms) body.start_ms = startMs;
    if (endMs !== line.end_ms) body.end_ms = endMs;

    if (Object.keys(body).length === 0) {
        cancelEditLine();
        return;
    }

    const resp = await fetch(`/api/v1/subtitles/lines/${line.id}`, {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body),
    });

    if (resp.ok) {
        await reloadSubtitles();
    } else {
        alert('儲存失敗');
    }
}

function cancelEditLine() {
    editingLineIndex = -1;
    const form = document.querySelector('.subtitle-edit-form');
    if (form) {
        const hiddenLine = form.previousElementSibling;
        if (hiddenLine) hiddenLine.style.display = '';
        form.remove();
    }
}

async function deleteLine(index) {
    const line = subtitleLines[index];
    if (!confirm(`確定刪除此行？\n「${line.text}」`)) return;

    const resp = await fetch(`/api/v1/subtitles/lines/${line.id}`, {
        method: 'DELETE',
    });

    if (resp.ok) {
        await reloadSubtitles();
    } else {
        alert('刪除失敗');
    }
}

async function insertLineAfter(index) {
    const line = subtitleLines[index];
    const nextLine = subtitleLines[index + 1];

    // Default: insert between current and next line
    const newStartMs = line.end_ms + 50;
    const newEndMs = nextLine ? nextLine.start_ms - 50 : line.end_ms + 3000;

    const text = prompt('輸入新行歌詞：');
    if (!text) return;

    const resp = await fetch(`/api/v1/subtitles/${currentSubtitleFileId}/lines`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            index: line.index + 1,
            start_ms: Math.max(0, newStartMs),
            end_ms: Math.max(newStartMs + 100, newEndMs),
            text,
        }),
    });

    if (resp.ok) {
        await reloadSubtitles();
    } else {
        alert('新增失敗');
    }
}

async function reloadSubtitles() {
    cancelEditLine();
    const subResp = await fetch(`/api/v1/subtitles/by-song/${SONG_ID}`);
    if (subResp.ok) {
        const subtitleFiles = await subResp.json();
        if (subtitleFiles.length > 0 && subtitleFiles[0].lines.length > 0) {
            const subFile = subtitleFiles[0];
            currentSubtitleFileId = subFile.id;
            subtitleLines = subFile.lines.sort((a, b) => a.start_ms - b.start_ms);
            renderSubtitleLines(subtitleLines);
            renderAlignmentBadge(subFile);
        }
    }
}

function renderLyrics(lyrics) {
    if (lyrics.length === 0) return;
    const primary = lyrics.find(l => l.is_primary) || lyrics[0];
    document.getElementById('lyrics-content').textContent = primary.content;
    document.getElementById('lyrics-section').classList.remove('hidden');
}

function renderAlignmentBadge(subtitleFile) {
    const info = document.getElementById('alignment-info');
    if (!info || !subtitleFile.alignment_source) return;

    const confidence = subtitleFile.alignment_confidence || 0;
    const matched = subtitleFile.alignment_matched || 0;
    const total = subtitleFile.alignment_total || 0;
    const pct = Math.round(confidence * 100);

    let badgeClass = 'badge-low';
    if (pct >= 80) badgeClass = 'badge-good';
    else if (pct >= 60) badgeClass = 'badge-ok';

    const algo = subtitleFile.alignment_algorithm;
    const algoLabel = algo === 'anchor' ? '錨點對齊' : '逐行匹配';
    info.innerHTML = `<span class="alignment-badge ${badgeClass}">${algoLabel} ${pct}% (${matched}/${total} 行匹配)</span>`;
    info.classList.remove('hidden');
}

// ── Subtitle Sync ───────────────────────────────────────────

function highlightLine(index) {
    const lines = document.querySelectorAll('.subtitle-line');
    lines.forEach((el, i) => {
        el.classList.toggle('active', i === index);
    });
}

function scrollToLine(index) {
    if (index < 0) return;
    const el = document.querySelectorAll('.subtitle-line')[index];
    if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

function setupSubtitleSync(audio) {
    audio.addEventListener('timeupdate', () => {
        if (isSeeking) return;
        const currentMs = audio.currentTime * 1000;
        const newIndex = findCurrentLine(currentMs);
        if (newIndex !== currentLineIndex) {
            // Skip phantom lines during auto-scroll (they are in instrumental sections)
            const isPhantom = newIndex >= 0 && subtitleLines[newIndex].source_type === 'phantom';
            highlightLine(isPhantom ? -1 : newIndex);
            if (!isPhantom) scrollToLine(newIndex);
            currentLineIndex = newIndex;
        }
    });
}

// ── Player Controls ─────────────────────────────────────────

function setupPlayerControls(audio) {
    const playBtn = document.getElementById('play-btn');
    const seekBar = document.getElementById('seek-bar');
    const currentTimeEl = document.getElementById('current-time');
    const durationEl = document.getElementById('duration');

    // Play/pause
    playBtn.addEventListener('click', () => {
        if (audio.paused) {
            audio.play();
        } else {
            audio.pause();
        }
    });

    audio.addEventListener('play', () => {
        playBtn.innerHTML = '&#10074;&#10074;'; // pause icon
    });

    audio.addEventListener('pause', () => {
        playBtn.innerHTML = '&#9654;'; // play icon
    });

    // Duration
    audio.addEventListener('loadedmetadata', () => {
        durationEl.textContent = formatTimeFromSeconds(audio.duration);
        seekBar.max = audio.duration;
    });

    // Time update → seek bar + time display
    audio.addEventListener('timeupdate', () => {
        if (!isSeeking) {
            seekBar.value = audio.currentTime;
            currentTimeEl.textContent = formatTimeFromSeconds(audio.currentTime);
        }
    });

    // Seek bar interaction
    seekBar.addEventListener('mousedown', () => { isSeeking = true; });
    seekBar.addEventListener('touchstart', () => { isSeeking = true; });

    seekBar.addEventListener('input', () => {
        currentTimeEl.textContent = formatTimeFromSeconds(seekBar.value);
    });

    seekBar.addEventListener('change', () => {
        audio.currentTime = parseFloat(seekBar.value);
        isSeeking = false;
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        if (e.code === 'Space') {
            e.preventDefault();
            if (audio.paused) audio.play();
            else audio.pause();
        }
        if (e.code === 'ArrowLeft') {
            e.preventDefault();
            audio.currentTime = Math.max(0, audio.currentTime - 5);
        }
        if (e.code === 'ArrowRight') {
            e.preventDefault();
            audio.currentTime = Math.min(audio.duration, audio.currentTime + 5);
        }
    });
}

// ── Track Switching ─────────────────────────────────────────

function setupTrackSwitch(audio) {
    document.querySelectorAll('input[name="track"]').forEach(radio => {
        radio.addEventListener('change', () => {
            const currentTime = audio.currentTime;
            const wasPlaying = !audio.paused;
            audio.src = `/api/v1/audio/stream/${SONG_ID}?track=${radio.value}`;

            audio.addEventListener('loadedmetadata', function restore() {
                audio.currentTime = currentTime;
                if (wasPlaying) audio.play();
                audio.removeEventListener('loadedmetadata', restore);
            });

            audio.load();
        });
    });
}

// ── Init ────────────────────────────────────────────────────

async function init() {
    // 1. Load song metadata
    const songResp = await fetch(`/api/v1/songs/${SONG_ID}`);
    if (!songResp.ok) {
        document.getElementById('song-title').textContent = '歌曲不存在';
        return;
    }
    song = await songResp.json();
    renderSongHeader(song);

    // 2. Show lyrics if available
    if (song.lyrics && song.lyrics.length > 0) {
        renderLyrics(song.lyrics);
    }

    // 3. Setup audio player if audio exists
    if (!song.audio_path) {
        document.getElementById('no-audio-msg').classList.remove('hidden');
        return;
    }

    const audio = document.getElementById('audio-player');
    audio.src = `/api/v1/audio/stream/${SONG_ID}?track=original`;
    document.getElementById('player-section').classList.remove('hidden');

    // Show vocals/accompaniment options if available
    if (song.vocals_path) {
        document.getElementById('vocals-option').classList.remove('hidden');
    }
    if (song.accompaniment_path) {
        document.getElementById('accompaniment-option')?.classList.remove('hidden');
    }

    setupPlayerControls(audio);
    setupTrackSwitch(audio);

    // 4. Load subtitles
    const subResp = await fetch(`/api/v1/subtitles/by-song/${SONG_ID}`);
    if (subResp.ok) {
        const subtitleFiles = await subResp.json();
        if (subtitleFiles.length > 0 && subtitleFiles[0].lines.length > 0) {
            const subFile = subtitleFiles[0];
            currentSubtitleFileId = subFile.id;
            subtitleLines = subFile.lines.sort((a, b) => a.start_ms - b.start_ms);
            renderSubtitleLines(subtitleLines);
            renderAlignmentBadge(subFile);
            document.getElementById('subtitle-section').classList.remove('hidden');
            // Hide lyrics section when we have timed subtitles
            document.getElementById('lyrics-section').classList.add('hidden');
            setupSubtitleSync(audio);
        }
    }
}

init();
